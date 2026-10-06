"""The task set: load, validate against the schema in 03-rai/benchmark/AGENTS.md, select a size,
and hash the active set into a version (scores compare only within one version)."""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

RAI_AREAS = ("rules", "routing", "recall", "vault", "arabic")
AREAS = RAI_AREAS + ("coding",)
SIZES = {"quick": {"trials": 1}, "full": {"trials": 3}, "smoke": {"trials": 1}}
STATUSES = ("draft", "active")

# check type -> required fields (any-of groups written as tuples)
CHECKS = {
    "no_em_dash": [], "no_emoji": [], "english_only": [], "arabic": [],
    "max_lines": ["n"], "contains": [("any", "all")], "not_contains": ["any"],
    "regex": ["pattern"], "skill_used": ["name"], "skill_not_used": ["name"],
    "file_read": ["path"], "file_exists": ["path"], "file_absent": ["path"],
    "file_contains": ["path", ("any", "all")], "file_unchanged": ["path"],
    "writes_within": ["paths"], "pytest": [], "judge": ["rubric"],
}
FIELDS = ("id", "area", "prompt", "cwd", "checks", "quick", "status", "source", "added")
# Checks an agent passes only by doing the task. Every task needs one: a task built only from
# "did not do X" checks is passed by an empty answer.
POSITIVE = {"contains", "regex", "skill_used", "file_read", "file_exists", "file_absent",
            "file_contains", "arabic", "judge", "pytest"}


class TaskError(ValueError):
    pass


@dataclass
class Task:
    id: str
    area: str
    prompt: str
    cwd: str
    checks: list
    quick: bool
    status: str
    source: str
    added: str
    setup: dict = field(default_factory=dict)
    dir: Path | None = None          # coding tasks: the folder holding starter/, hidden_tests/

    @property
    def judged(self) -> bool:
        return any(c["type"] == "judge" for c in self.checks)


def validate(raw: dict, where: str = "") -> list:
    """Every problem with one raw task, as readable strings. Empty means valid."""
    p = []
    tid = raw.get("id", "?")
    for f in FIELDS:
        if f not in raw:
            p.append(f"{where}{tid}: missing {f}")
    if p:
        return p
    if raw["area"] not in AREAS:
        p.append(f"{where}{tid}: unknown area {raw['area']}")
    if not str(tid).startswith(f"{raw['area']}-"):
        p.append(f"{where}{tid}: id must start with '{raw['area']}-'")
    if raw["cwd"] not in ("helm", "work"):
        p.append(f"{where}{tid}: cwd must be helm or work")
    if raw["status"] not in STATUSES:
        p.append(f"{where}{tid}: status must be draft or active")
    if not isinstance(raw["quick"], bool):
        p.append(f"{where}{tid}: quick must be true or false")
    if not str(raw["prompt"]).strip():
        p.append(f"{where}{tid}: empty prompt")
    files = (raw.get("setup") or {}).get("files", {})
    if not isinstance(files, dict):
        p.append(f"{where}{tid}: setup.files must be an object")
    else:
        for rel in files:
            if rel.startswith("/") or ".." in Path(rel).parts:
                p.append(f"{where}{tid}: setup path escapes the cwd root: {rel}")
    if not raw["checks"]:
        p.append(f"{where}{tid}: no checks")
    judges = 0
    for c in raw["checks"]:
        t = c.get("type")
        if t not in CHECKS:
            p.append(f"{where}{tid}: unknown check type {t}")
            continue
        judges += t == "judge"
        for req in CHECKS[t]:
            if isinstance(req, tuple):
                if not any(k in c for k in req):
                    p.append(f"{where}{tid}: {t} needs one of {'/'.join(req)}")
            elif req not in c:
                p.append(f"{where}{tid}: {t} needs {req}")
        if t == "pytest" and raw["area"] != "coding":
            p.append(f"{where}{tid}: pytest check outside the coding area")
    if judges > 1:
        p.append(f"{where}{tid}: at most one judge check per task")
    if raw["checks"] and not any(c.get("type") in POSITIVE for c in raw["checks"]):
        p.append(f"{where}{tid}: needs one check the agent passes only by doing the task")
    return p


def _task(raw: dict, d: Path | None = None) -> Task:
    return Task(**{f: raw[f] for f in FIELDS}, setup=raw.get("setup") or {}, dir=d)


def load(bench: Path) -> list:
    """All tasks, drafts included. Raises TaskError listing every problem found."""
    tasks, probs, seen = [], [], set()
    tdir = bench / "tasks"
    for area in RAI_AREAS:
        f = tdir / f"{area}.jsonl"
        if not f.exists():
            continue
        for n, line in enumerate(f.read_text().splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                probs.append(f"{f.name}:{n}: bad JSON ({e.msg})")
                continue
            got = validate(raw, f"{f.name}:{n}: ")
            if not got and raw["area"] != area:
                got = [f"{f.name}:{n}: {raw['id']}: area {raw['area']} in {area}.jsonl"]
            probs += got
            if not got:
                tasks.append(_task(raw))
    for d in sorted((tdir / "coding").glob("coding-*")) if (tdir / "coding").is_dir() else []:
        try:
            raw = json.loads((d / "task.json").read_text())
        except (OSError, json.JSONDecodeError) as e:
            probs.append(f"coding/{d.name}: unreadable task.json ({e})")
            continue
        got = validate(raw, f"coding/{d.name}: ")
        if not got and raw["id"] != d.name:
            got = [f"coding/{d.name}: id {raw['id']} does not match its folder"]
        if not got and not (d / "hidden_tests").is_dir():
            got = [f"coding/{d.name}: no hidden_tests/"]
        probs += got
        if not got:
            tasks.append(_task(raw, d))
    for t in tasks:
        if t.id in seen:
            probs.append(f"duplicate id {t.id}")
        seen.add(t.id)
    if probs:
        raise TaskError("\n".join(probs))
    return tasks


def probes() -> list:
    """The smoke run's two built-in tasks: is Rai's context loaded, and can the agent write a
    file in its sandbox. They prove a route works before a real run spends quota."""
    return [
        Task("probe-context", "rules", "In one line: what is your name, and whose assistant are you?",
             "helm", [{"type": "contains", "all": ["Rai", "John"]}], True, "active", "built-in", ""),
        Task("probe-tools", "coding", "Create a file named hello.txt in the current folder containing exactly: bench ok",
             "work", [{"type": "file_contains", "path": "hello.txt", "all": ["bench ok"]}], True, "active", "built-in", ""),
    ]


def select(tasks: list, size: str, areas: list | None = None) -> list:
    """The active tasks a run of this size covers, in a stable order."""
    if size not in SIZES:
        raise TaskError(f"unknown size {size}: quick, full or smoke")
    if size == "smoke":
        return probes()
    keep = [t for t in tasks if t.status == "active" and (size == "full" or t.quick)]
    if areas:
        keep = [t for t in keep if t.area in areas]
    return sorted(keep, key=lambda t: (AREAS.index(t.area), t.id))


def _dir_digest(d: Path) -> str:
    h = hashlib.sha256()
    for f in sorted(p for p in d.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(str(f.relative_to(d)).encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def set_version(tasks: list) -> str:
    """Hash of every active task (content, and the coding folders). Drafts do not count."""
    h = hashlib.sha256()
    for t in sorted((t for t in tasks if t.status == "active"), key=lambda t: t.id):
        body = {f: getattr(t, f) for f in FIELDS if f not in ("status", "added", "source", "quick")}
        body["setup"] = t.setup
        h.update(json.dumps(body, sort_keys=True, ensure_ascii=False).encode())
        if t.dir:
            h.update(_dir_digest(t.dir).encode())
    return h.hexdigest()[:10]
