"""The run: a queue of (target, task, trial) jobs worked in parallel waves, resumable at any point.

- A job is done once its graded row is in results/<run>/attempts.jsonl. Re-running a run id
  picks up exactly the jobs without a row. One runner per run: a lock refuses a second.
- A rate limit pauses that account (Anthropic or Google) until its reset, or for a backoff of
  30 minutes doubling to 3 hours. A job waits only on the account its next step needs (its
  harness, or the judge it still lacks), so the other account keeps working. A rate-limited
  attempt is re-run fresh, never scored.
- A crashed attempt is retried twice, then recorded as an infrastructure error and left out of
  the scores. A timeout is the agent's own failure and is scored.
- `night` holds dispatch to 23:00 to 08:00 local.
- State is crash-safe: run.json is replaced atomically, rows are fsynced, a torn line is skipped.
"""

import fcntl
import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from . import adapters, grade, judge, paths, sandbox, targets, tasks

BACKOFF_FIRST = 30 * 60
BACKOFF_MAX = 3 * 3600
MAX_RETRIES = 2
NIGHT = (23, 8)
ANSWER_CAP = 6000
PYTEST_TIMEOUT = 180
IDLE_SLEEP = 30
# -P keeps the work folder off sys.path, so a planted pytest.py cannot stand in for pytest
PYTEST_ARGS = ["-P", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", "hidden_tests/.bench-pytest.ini",
               "--rootdir", "hidden_tests", "--confcutdir", "hidden_tests", "hidden_tests"]


def default_exec(argv: list, stdin: str | None, timeout: int) -> tuple:
    """(stdout, stderr, exit code, wall seconds). Exit 124 marks a timeout.

    Overlayfs releases a layer a moment after its sandbox exits, so mounting the same layer
    again at once fails with EBUSY: wait and retry, up to about 20 seconds."""
    t0 = time.monotonic()
    try:
        for n in range(1, 9):
            r = subprocess.run(argv, input=stdin, capture_output=True, text=True, timeout=timeout,
                               stdin=None if stdin is not None else subprocess.DEVNULL)
            busy = r.returncode != 0 and "overlay mount" in r.stderr and "busy" in r.stderr
            if not busy:
                break
            time.sleep(0.5 * n)
        return r.stdout, r.stderr, r.returncode, time.monotonic() - t0
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")
        return out, err + f"\n[bench] timeout after {timeout}s", 124, time.monotonic() - t0


def in_night(now: datetime) -> bool:
    start, end = NIGHT
    return now.hour >= start or now.hour < end


def next_night(now: datetime) -> datetime:
    start = now.replace(hour=NIGHT[0], minute=0, second=0, microsecond=0)
    return start if now < start else start + timedelta(days=1)


def read_rows(f: Path) -> list:
    """Rows of an attempts.jsonl, skipping a torn line, the last row per key winning."""
    rows = {}
    if f.exists():
        for line in f.read_text().splitlines():
            try:
                r = json.loads(line)
                rows[r["key"]] = r
            except (json.JSONDecodeError, KeyError, TypeError):
                continue
    return list(rows.values())


def write_json(f: Path, obj) -> None:
    tmp = f.with_suffix(f.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1))
    os.replace(tmp, f)


@dataclass
class Job:
    target: targets.Target
    task: tasks.Task
    trial: int

    @property
    def key(self) -> str:
        return f"{self.target.key}|{self.task.id}|{self.trial}"

    @property
    def slug(self) -> str:
        return self.key.replace("|", "__")


def new_run(run_id: str, mode: str, size: str, tgts: list, task_list: list, set_ver: str,
            night: bool = False, concurrency: int = 4, timeout: int = 900) -> dict:
    spec = {
        "run_id": run_id, "mode": mode, "size": size, "trials": tasks.SIZES[size]["trials"],
        "targets": [t.__dict__ for t in tgts], "tasks": [t.id for t in task_list],
        "set_version": set_ver, "tasks_digest": tasks.set_version(task_list),
        "night": night, "concurrency": max(1, concurrency), "timeout": timeout,
        "created": datetime.now().isoformat(timespec="seconds"),
        "status": {"state": "queued", "paused": {}, "done": 0,
                   "total": len(tgts) * len(task_list) * tasks.SIZES[size]["trials"]},
    }
    d = paths.run_dir(run_id)
    d.mkdir(parents=True, exist_ok=False)
    write_json(d / "run.json", spec)
    (d / "attempts.jsonl").touch()
    return spec


class RunBusy(RuntimeError):
    pass


class Runner:
    def __init__(self, run_id: str, execute=default_exec, clock=time.time, sleep=time.sleep, log=print):
        self.run_id = run_id
        self.dir = paths.run_dir(run_id)
        self.cache = paths.run_cache(run_id)
        self.spec = json.loads((self.dir / "run.json").read_text())
        self.cat = targets.load(paths.bench_dir())
        by_id = {t.id: t for t in tasks.load(paths.bench_dir()) + tasks.probes()}
        missing = [i for i in self.spec["tasks"] if i not in by_id]
        if missing:
            raise tasks.TaskError(f"run {run_id} names tasks no longer in the set: {missing[:5]}")
        run_tasks = [by_id[i] for i in self.spec["tasks"]]
        want = self.spec.get("tasks_digest")
        if want and tasks.set_version(run_tasks) != want:
            raise tasks.TaskError(f"run {run_id}: its tasks changed since it started; start a new run")
        tgts = [targets.Target(**t) for t in self.spec["targets"]]
        self.jobs = [Job(tg, t, n) for tg in tgts for t in run_tasks for n in range(1, self.spec["trials"] + 1)]
        self.execute, self.clock, self.sleep, self.log = execute, clock, sleep, log
        self.lock = threading.Lock()
        self.retries: dict = {}
        self.backoff: dict = {}
        self.paused: dict = dict(self.spec["status"].get("paused") or {})

    # ------------------------------------------------------------ state

    def done_keys(self) -> set:
        return {r["key"] for r in read_rows(self.dir / "attempts.jsonl")}

    def _append(self, row: dict) -> None:
        with self.lock:
            with (self.dir / "attempts.jsonl").open("ab+") as f:
                f.seek(0, os.SEEK_END)
                if f.tell():
                    f.seek(-1, os.SEEK_END)
                    if f.read(1) != b"\n":           # a torn line from a crash: close it off
                        f.write(b"\n")
                f.write((grade.dumps(row) + "\n").encode())
                f.flush()
                os.fsync(f.fileno())

    def _status(self, state: str, **extra) -> None:
        with self.lock:
            self.spec["status"].pop("resume_at", None)
            self.spec["status"].update({"state": state, "paused": self.paused, "done": len(self.done_keys()),
                                        "updated": datetime.now().isoformat(timespec="seconds"), **extra})
            write_json(self.dir / "run.json", self.spec)

    def _pause(self, account: str, resets_at: float | None) -> None:
        now = self.clock()
        if resets_at and resets_at > now:
            until = resets_at + 60
        else:
            wait = self.backoff.get(account, BACKOFF_FIRST)
            self.backoff[account] = min(wait * 2, BACKOFF_MAX)
            until = now + wait
        self.paused[account] = max(until, self.paused.get(account, 0))
        self.log(f"[bench] {account} limit: paused until {datetime.fromtimestamp(until):%H:%M}")

    def _pending(self, job: Job) -> Path:
        return self.cache / "pending" / f"{job.slug}.json"

    def _missing_judges(self, job: Job, state: dict) -> list:
        """(check index, judge name) pairs still without a verdict, in order."""
        out = []
        for i, (c, r) in enumerate(zip(job.task.checks, state["checks"])):
            if c["type"] != "judge":
                continue
            for name in self.cat.judges:
                if (r.get("judges") or {}).get(name) is None and \
                        not (r.get("reasons") or {}).get(name, "").startswith("judge failed"):
                    out.append((i, name))
        return out

    def _needs(self, job: Job) -> str | None:
        """The account this job's next step needs; None when only bookkeeping is left."""
        pend = self._pending(job)
        if pend.exists():
            try:
                state = json.loads(pend.read_text())
            except json.JSONDecodeError:
                pend.unlink()
                return self.cat.account(job.target.harness)
            missing = self._missing_judges(job, state)
            return self.cat.account(self.cat.judges[missing[0][1]]["harness"]) if missing else None
        return self.cat.account(job.target.harness)

    # ------------------------------------------------------------ the loop

    def run(self) -> dict:
        self.cache.mkdir(parents=True, exist_ok=True)
        with open(self.cache / "run.lock", "w") as lockf:
            try:
                fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RunBusy(f"run {self.run_id} is already running") from None
            return self._loop()

    def _loop(self) -> dict:
        self.snapshot = sandbox.build_snapshot(self.cache / "snapshot")
        self.identity = self._identity()
        while True:
            done = self.done_keys()
            todo = [j for j in self.jobs if j.key not in done]
            if not todo:
                self._status("done")
                for d in ("att", "snapshot"):           # raw/ and identity.md stay
                    sandbox.rmtree(self.cache / d)
                return self.spec
            now = self.clock()
            if self.spec.get("night") and not in_night(datetime.fromtimestamp(now)):
                until = next_night(datetime.fromtimestamp(now)).timestamp()
                self._status("waiting for night", resume_at=until)
                self.sleep(max(60, until - now))
                continue
            self.paused = {a: u for a, u in self.paused.items() if u > now}
            ready = [j for j in todo if self._needs(j) not in self.paused]
            if not ready:
                until = min(self.paused.values()) if self.paused else now + IDLE_SLEEP
                self._status("paused", resume_at=until)
                self.sleep(max(IDLE_SLEEP, until - now))
                continue
            self._status("running")
            wave = self._spread(ready, self.spec["concurrency"])
            with ThreadPoolExecutor(max_workers=len(wave)) as pool:
                results = list(pool.map(self._job, wave))
            for job, (kind, account, resets_at) in zip(wave, results):
                if kind == "limit":
                    self._pause(account, resets_at)
                elif kind == "ok":
                    self.backoff.pop(self.cat.account(job.target.harness), None)
            if all(kind == "wait" for kind, _, _ in results):
                self.sleep(IDLE_SLEEP)

    @staticmethod
    def _spread(ready: list, n: int) -> list:
        """Up to n jobs, alternating harnesses so one subscription never carries a whole wave."""
        by_h: dict = {}
        for j in ready:
            by_h.setdefault(j.target.harness, []).append(j)
        wave, lists = [], list(by_h.values())
        while len(wave) < max(1, n) and any(lists):
            for lst in lists:
                if lst and len(wave) < max(1, n):
                    wave.append(lst.pop(0))
        return wave

    # ------------------------------------------------------------ one job

    def _job(self, job: Job) -> tuple:
        try:
            return self._attempt(job)
        except Exception as e:  # never kill the run over one job
            return self._retry(job, f"runner error: {e!r}")

    def _retry(self, job: Job, why: str) -> tuple:
        n = self.retries.get(job.key, 0) + 1
        self.retries[job.key] = n
        self.log(f"[bench] {job.key}: {why} (try {n})")
        if n > MAX_RETRIES:
            self._append(self._row(job, None, [], infra="error", detail=why))
            return "ok", None, None
        return "retry", None, None

    def _attempt(self, job: Job) -> tuple:
        pend = self._pending(job)
        if pend.exists():                      # agent ran; only the judging is left
            state = json.loads(pend.read_text())
        else:
            got = self._run_agent(job)
            if got[0] != "graded":
                return got
            state = got[1]
            pend.parent.mkdir(parents=True, exist_ok=True)
            write_json(pend, state)
        step = self._judge(job, state)
        write_json(pend, state)
        if step:
            return step
        self._append(self._row(job, state["outcome"], state["checks"]))
        pend.unlink()
        return "ok", None, None

    def _run_agent(self, job: Job) -> tuple:
        att_root = self.cache / "att" / job.slug
        extra = {}
        if job.target.harness == "agy" and self.identity:
            extra["GEMINI.md"] = self.identity
        att = sandbox.prepare(att_root, self.snapshot, job.task, extra)
        argv, stdin = adapters.command(job.target.harness, job.target.model, job.task.prompt, job.target.effort)
        out, err, code, wall = self.execute(sandbox.bwrap_argv(att, job.target.harness, argv),
                                            stdin, self.spec["timeout"])
        raw = self.cache / "raw"
        raw.mkdir(parents=True, exist_ok=True)
        (raw / f"{job.slug}.out").write_text(out)
        (raw / f"{job.slug}.err").write_text(err)
        o = adapters.parse(job.target.harness, out, err, code)
        timed_out = code == 124
        if o.infra == "rate_limit":            # a limit is never the agent's fault, timeout or not
            sandbox.rmtree(att_root)
            return "limit", self.cat.account(job.target.harness), o.resets_at
        if not timed_out and o.infra == "error":
            sandbox.rmtree(att_root)
            return self._retry(job, o.detail or "harness error")
        subprocess.run(["chmod", "-R", "u+rwX", str(att.upper), str(att.work)], capture_output=True)
        files = sandbox.FileView(att)
        checks = grade.grade(job.task, o.text, o.tool_calls, files)
        changes = files.changes()             # before the hidden tests are copied in
        for c, r in zip(job.task.checks, checks):
            if c["type"] == "pytest":
                r["ok"], r["detail"] = self._pytest(job, att)
        outcome = {"text": o.text, "tools": [t["name"] for t in o.tool_calls][:200],
                   "usage": o.usage, "wall_s": round(wall, 1), "num_turns": o.num_turns,
                   "infra": "timeout" if timed_out else None,
                   "detail": "timed out" if timed_out else o.detail, "changes": changes[:50]}
        sandbox.rmtree(att_root)
        return "graded", {"outcome": outcome, "checks": checks, "request": job.task.prompt}

    def _pytest(self, job: Job, att: sandbox.Attempt) -> tuple:
        dst = att.work / "hidden_tests"
        sandbox.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(job.task.dir / "hidden_tests", dst)
        (dst / ".bench-pytest.ini").write_text("[pytest]\n")
        argv = ["uv", "run", "--offline", "--python", "3.12", "--with", "pytest", "python", *PYTEST_ARGS]
        att.cwd_kind = "work"
        out, err, code, _ = self.execute(sandbox.bwrap_argv(att, "none", argv, net=False), None, PYTEST_TIMEOUT)
        tail = (out + err).strip().splitlines()[-1:] or [""]
        return code == 0, tail[0][:200]

    def _judge(self, job: Job, state: dict) -> tuple | None:
        """Fill every judge verdict still missing. None when all are in; else ('limit', account,
        resets_at) on a new rate limit, or ('wait', account, None) when a judge's account is
        already paused."""
        jroot = self.cache / "att" / f"{job.slug}__judge"
        for i, name in self._missing_judges(job, state):
            c, r = job.task.checks[i], state["checks"][i]
            cfg = self.cat.judges[name]
            account = self.cat.account(cfg["harness"])
            if account in self.paused:
                return "wait", account, None
            r.setdefault("judges", {})
            r.setdefault("reasons", {})
            prompt = judge.build_prompt(c, state["request"], state["outcome"]["text"])
            jatt = sandbox.prepare(jroot, self.snapshot, _EmptyTask)

            def run(h, argv, stdin, _a=jatt):
                out, err, code, _ = self.execute(sandbox.bwrap_argv(_a, h, argv), stdin, 600)
                return out, err, code

            v = judge.judge_one(name, cfg, prompt, run)
            sandbox.rmtree(jroot)
            if v["infra"] == "rate_limit":
                return "limit", account, v["resets_at"]
            r["judges"][name] = v["verdict"]
            r["reasons"][name] = v["reason"] if v["infra"] is None else f"judge failed: {v['reason']}"
        for c, r in zip(job.task.checks, state["checks"]):
            if c["type"] == "judge":
                vals = [x for x in (r.get("judges") or {}).values() if x is not None]
                r["ok"] = all(vals) if vals else None
                r["detail"] = "; ".join(f"{k}: {v}" for k, v in (r.get("reasons") or {}).items())[:400]
        return None

    def _row(self, job: Job, o: dict | None, checks: list, infra=None, detail="") -> dict:
        o = o or {}
        views = {}
        for v in self.cat.judges:
            s, p = grade.score(checks, v)
            views[v] = {"score": round(s, 3), "pass": p}
        text = o.get("text", "")
        return {
            "run_id": self.run_id, "key": job.key, "set_version": self.spec["set_version"],
            "tasks_digest": self.spec.get("tasks_digest", self.spec["set_version"]),
            "size": self.spec["size"], "mode": self.spec["mode"],
            "target": job.target.__dict__, "task": job.task.id, "area": job.task.area, "trial": job.trial,
            "checks": checks, "views": views,
            "answer": text[:ANSWER_CAP] + ("\n[truncated]" if len(text) > ANSWER_CAP else ""),
            "tools": o.get("tools", []), "changes": o.get("changes", []),
            "usage": o.get("usage") or {}, "wall_s": o.get("wall_s", 0.0), "num_turns": o.get("num_turns"),
            "infra": infra or o.get("infra"), "detail": detail or o.get("detail", ""),
            "ts": datetime.now().isoformat(timespec="seconds"),
        }

    # ------------------------------------------------------------ Rai context for agy

    def _identity(self) -> str:
        """The context session-start gives Claude Code, plus his auto-memory index, rendered once
        per run, so agy gets the same Rai through its own GEMINI.md."""
        f = self.cache / "identity.md"
        if f.exists():
            return f.read_text()
        att = sandbox.prepare(self.cache / "att" / "identity", self.snapshot, _EmptyTask)
        att.cwd_kind = "helm"
        # RAI_HARNESS asks session-start for the full snapshot, as the non-Claude harnesses get it
        argv = ["bash", "-c", "RAI_HARNESS=bench python3 \"$HOME/helm/03-rai/hooks/session-start.py\""]
        out, err, code, _ = self.execute(sandbox.bwrap_argv(att, "none", argv), "{}", 60)
        sandbox.rmtree(att.root)
        text = out.strip()
        if not text:
            self.log(f"[bench] identity render empty (exit {code}): agy runs without Rai context. {err[-200:]}")
            return ""
        mem = self.snapshot / "03-rai" / "auto-memory" / "MEMORY.md"
        memory = f"\n\n## Auto-memory index\n\n{mem.read_text()}" if mem.is_file() else ""
        body = ("# Rai context\n\nYou are Rai, John's assistant. The block below is the context his "
                "sessions start with. His skills live in ~/helm/03-rai/skills/<name>/SKILL.md, indexed in "
                "~/helm/03-rai/skills/MANIFEST.md; his workflows in ~/helm/11-workflows/; memory notes in "
                "~/helm/03-rai/auto-memory/.\n\n" + text + memory + "\n")
        f.write_text(body)
        return body


class _EmptyTask:
    """A task with nothing planted, for judge and identity sandboxes."""
    cwd = "work"
    setup: dict = {}
    dir = None
