"""Tests for the /rai benchmark engine. No model is ever called: harnesses are faked by an
injected executor, and the one real-sandbox test runs plain shell commands in bubblewrap
against a throwaway HOME.

Run: uv run --offline --python 3.12 --with pytest \
       python3 -m pytest 03-rai/skills/rai/scripts/bench_lib/tests -q -p no:cacheprovider
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS))

from bench_lib import adapters, grade, judge, report, runner, sandbox, targets, tasks  # noqa: E402

GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
       "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]

TARGETS_TOML = """
[harness.claude-code]
enabled = true
account = "anthropic"
[harness.agy]
enabled = true
account = "google"
[harness.pi]
enabled = false
account = "pi"
reason = "no compliant route"

[model."opus-5.5"]
harness = "claude-code"
id = "claude-opus-5-5"
label = "Opus"
default = true
[model."gemini"]
harness = "agy"
id = "gemini-3.1-pro-high"
label = "Gemini"
default = true
[model."cc-s46"]
harness = "claude-code"
id = "claude-sonnet-4-6"
label = "CC Sonnet 4.6"
[model."agy-s46"]
harness = "agy"
id = "claude-sonnet-4-6"
label = "AGY Sonnet 4.6"
[model."pi-m"]
harness = "pi"
id = "x"
label = "Pi model"

[harness_mode]
claude-code = "cc-s46"
agy = "agy-s46"

[judge.opus]
harness = "claude-code"
id = "opus"
[judge.gemini]
harness = "agy"
id = "gemini-3.1-pro-high"
"""


def task_raw(**kw):
    raw = {"id": "rules-001", "area": "rules", "prompt": "What is the capital of France?", "cwd": "helm",
           "checks": [{"type": "contains", "any": ["paris"]}, {"type": "no_em_dash"}],
           "quick": True, "status": "active", "source": "written", "added": "2026-10-01"}
    raw.update(kw)
    return raw


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A throwaway home: a git vault, a bench folder, a cache. The engine points only here."""
    home = tmp_path / "home"
    helm = home / "helm"
    bench = helm / "03-rai" / "benchmark"
    (bench / "tasks").mkdir(parents=True)
    (helm / "notes").mkdir()
    (helm / "notes" / "a.md").write_text("alpha\n")
    (helm / "AGENTS.md").write_text("vault\n")
    (bench / "targets.toml").write_text(TARGETS_TOML)
    (home / ".cache").mkdir()
    for k, v in {"HOME": home, "RAI_BENCH_HELM": helm, "RAI_BENCH_DIR": bench,
                 "RAI_BENCH_CACHE": home / ".cache" / "rai-bench"}.items():
        monkeypatch.setenv(k, str(v))
    subprocess.run([*GIT, "init", "-q", str(helm)], check=True)
    subprocess.run([*GIT, "-C", str(helm), "add", "-A"], check=True)
    subprocess.run([*GIT, "-C", str(helm), "commit", "-qm", "init"], check=True)

    class W:
        pass
    w = W()
    w.home, w.helm, w.bench = home, helm, bench

    def write_tasks(area, rows):
        (bench / "tasks" / f"{area}.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    w.write_tasks = write_tasks
    yield w
    sandbox.rmtree(home)          # overlay work dirs are mode 000: pytest alone cannot remove them


# ---------------------------------------------------------------- tasks

def test_validate_flags_bad_tasks():
    assert tasks.validate(task_raw()) == []
    bad = tasks.validate(task_raw(checks=[{"type": "nope"}], cwd="x", status="live"))
    assert any("unknown check type" in p for p in bad)
    assert any("cwd" in p for p in bad)
    assert any("status" in p for p in bad)
    assert any("needs one of" in p for p in tasks.validate(task_raw(checks=[{"type": "contains"}])))
    assert any("escapes" in p for p in tasks.validate(task_raw(setup={"files": {"../x": "y"}})))
    two_judges = [{"type": "judge", "rubric": "a"}, {"type": "judge", "rubric": "b"}]
    assert any("one judge" in p for p in tasks.validate(task_raw(checks=two_judges)))


def test_load_select_and_version(world):
    world.write_tasks("rules", [task_raw(), task_raw(id="rules-002", quick=False),
                                task_raw(id="rules-003", status="draft")])
    all_t = tasks.load(world.bench)
    assert [t.id for t in tasks.select(all_t, "quick")] == ["rules-001"]
    assert [t.id for t in tasks.select(all_t, "full")] == ["rules-001", "rules-002"]
    v1 = tasks.set_version(all_t)
    world.write_tasks("rules", [task_raw(), task_raw(id="rules-002", quick=False),
                                task_raw(id="rules-003", status="draft", prompt="changed draft")])
    assert tasks.set_version(tasks.load(world.bench)) == v1          # drafts never move the version
    world.write_tasks("rules", [task_raw(prompt="other"), task_raw(id="rules-002", quick=False)])
    assert tasks.set_version(tasks.load(world.bench)) != v1


def test_load_reports_every_problem(world):
    world.write_tasks("rules", [task_raw(), task_raw(), task_raw(id="rules-009", area="vault")])
    with pytest.raises(tasks.TaskError) as e:
        tasks.load(world.bench)
    assert "duplicate id rules-001" in str(e.value)
    assert "id must start" in str(e.value) or "area vault" in str(e.value)


# ---------------------------------------------------------------- targets

def test_targets_resolve(world):
    cat = targets.load(world.bench)
    assert [t.key for t in targets.resolve(cat, "model")] == ["opus-5.5", "gemini"]
    assert [t.key for t in targets.resolve(cat, "harness")] == ["cc-s46", "agy-s46"]
    with pytest.raises(targets.TargetError, match="disabled harness: pi: no compliant route"):
        targets.resolve(cat, "model", ["pi-m"])
    with pytest.raises(targets.TargetError, match="unknown model"):
        targets.resolve(cat, "model", ["nope"])
    assert cat.account("agy") == "google"


def test_live_catalog_parses_and_only_compliant_routes_are_on():
    bench = SCRIPTS.parents[2] / "benchmark"
    cat = targets.load(bench)
    assert {h for h in cat.harnesses if cat.enabled(h)} == {"claude-code", "agy"}
    assert all(cat.enabled(t.harness) for t in targets.resolve(cat, "model"))


# ---------------------------------------------------------------- adapters

def test_parse_claude_success_tools_and_usage():
    out = "\n".join(json.dumps(e) for e in [
        {"type": "system", "subtype": "init"},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Skill", "input": {"skill": "rai", "args": "sanity"}}]}},
        {"type": "result", "subtype": "success", "is_error": False, "result": "Done.",
         "usage": {"input_tokens": 5}, "num_turns": 2}])
    o = adapters.parse_claude(out, "", 0)
    assert o.infra is None and o.text == "Done." and o.tool_calls[0]["name"] == "Skill"
    assert o.usage == {"input_tokens": 5} and o.num_turns == 2


def test_parse_claude_rate_limit_with_exit_zero():
    out = json.dumps({"type": "result", "subtype": "success", "is_error": True,
                      "result": "Claude AI usage limit reached|1767225600"})
    o = adapters.parse_claude(out, "", 0)
    assert o.infra == "rate_limit" and o.resets_at == 1767225600.0


def test_parse_claude_max_turns_is_the_agents_failure():
    out = json.dumps({"type": "result", "subtype": "error_max_turns", "is_error": True, "result": ""})
    assert adapters.parse_claude(out, "", 1).infra is None


def test_parse_claude_crash_is_infra():
    assert adapters.parse_claude("", "segfault", 139).infra == "error"


def test_parse_agy_stream():
    out = "\n".join(json.dumps(e) for e in [
        {"type": "init", "conversation_id": "c"},
        {"type": "step_update", "step_index": 1, "state": "ACTIVE", "tool_name": "view_file",
         "tool_info": {"name": "view_file", "parameters": {"path": "/h/helm/11-workflows/04-debugging.md"}}},
        {"type": "step_update", "step_index": 1, "state": "DONE", "tool_name": "view_file",
         "tool_info": {"name": "view_file", "parameters": {"path": "/h/helm/11-workflows/04-debugging.md"}}},
        {"type": "result", "status": "SUCCESS", "response": "Use workflow 04.", "num_turns": 1,
         "usage": {"total_tokens": 9}}])
    o = adapters.parse_agy(out, "", 0)
    assert o.infra is None and o.text == "Use workflow 04." and len(o.tool_calls) == 1


def test_parse_agy_quota_error():
    out = json.dumps({"type": "result", "status": "ERROR", "error": "RESOURCE_EXHAUSTED: quota"})
    assert adapters.parse_agy(out, "", 1).infra == "rate_limit"


def test_parse_pi_and_opencode_shapes():
    pi = "\n".join(json.dumps(e) for e in [
        {"type": "tool_execution_start", "toolName": "read", "args": {"path": "skills/rai/SKILL.md"}},
        {"type": "message_end", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}],
                                             "stopReason": "stop"}}])
    o = adapters.parse_pi(pi, "", 0)
    assert o.text == "hi" and o.tool_calls[0]["name"] == "read"
    oc = "\n".join(json.dumps(e) for e in [
        {"type": "text", "part": {"text": "ok"}},
        {"type": "step_finish", "part": {"tokens": {"input": 3, "output": 2}}}])
    o = adapters.parse_opencode(oc, "", 0)
    assert o.text == "ok" and o.usage == {"input": 3, "output": 2}


def test_command_routes():
    argv, stdin = adapters.command("claude-code", "claude-opus-5-5", "hello")
    assert argv[:2] == ["claude", "-p"] and stdin == "hello" and "bypassPermissions" in argv
    argv, stdin = adapters.command("agy", "gemini-3.1-pro-high", "hello")
    assert argv[:3] == ["agy", "-p", "hello"] and stdin is None


# ---------------------------------------------------------------- grade

class Files:
    def __init__(self, before=None, after=None):
        self.b, self.a = before or {}, after or {}

    def before(self, rel):
        return self.b.get(rel)

    def after(self, rel):
        return self.a.get(rel)

    def exists(self, rel):
        return rel in self.a

    def changes(self):
        return sorted(r for r in set(self.a) | set(self.b) if self.a.get(r) != self.b.get(r))


@pytest.mark.parametrize("c,text,ok", [
    ({"type": "no_em_dash"}, "a — b", False),
    ({"type": "no_em_dash"}, "a - b", True),
    ({"type": "no_emoji"}, "done \U0001F680", False),
    ({"type": "no_emoji"}, "done", True),
    ({"type": "english_only"}, "hello مرحبا", False),
    ({"type": "arabic", "min_ratio": 0.6}, "مرحبا بك ok", True),
    ({"type": "arabic"}, "mostly english words م", False),
    ({"type": "max_lines", "n": 2}, "one\n\ntwo\nthree", False),
    ({"type": "max_lines", "n": 3}, "one\n\ntwo\nthree", True),
    ({"type": "contains", "any": ["PARIS", "lyon"]}, "It is Paris.", True),
    ({"type": "contains", "all": ["paris", "france"]}, "Paris", False),
    ({"type": "not_contains", "any": ["sorry"]}, "Sorry, no.", False),
    ({"type": "regex", "pattern": r"^\d+ files"}, "12 files changed", True),
])
def test_text_checks(c, text, ok):
    assert grade.check(c, text, [], Files())[0] is ok


def test_tool_checks():
    calls = [{"name": "Skill", "input": {"skill": "rai", "args": "sanity"}},
             {"name": "Read", "input": {"file_path": "/h/helm/11-workflows/24-changing-rai.md"}}]
    assert grade.check({"type": "skill_used", "name": "rai"}, "", calls, Files())[0]
    assert not grade.check({"type": "skill_used", "name": "recall"}, "", calls, Files())[0]
    assert grade.check({"type": "file_read", "path": "11-workflows/24-changing-rai.md"}, "", calls, Files())[0]
    assert not grade.check({"type": "skill_not_used", "name": "*"}, "", calls, Files())[0]
    read_skill = [{"name": "read", "input": {"path": "/h/helm/03-rai/skills/recall/SKILL.md"}}]
    assert grade.check({"type": "skill_used", "name": "recall"}, "", read_skill, Files())[0]
    assert grade.check({"type": "skill_not_used", "name": "*"}, "", [{"name": "Bash", "input": {"command": "ls"}}], Files())[0]


def test_file_checks():
    f = Files(before={"a.md": b"x", "keep.md": b"k"}, after={"a.md": b"x\nNew line", "keep.md": b"k", "09-ideas/s.md": b"seed"})
    assert grade.check({"type": "file_exists", "path": "09-ideas/s.md"}, "", [], f)[0]
    assert grade.check({"type": "file_absent", "path": "gone.md"}, "", [], f)[0]
    assert grade.check({"type": "file_contains", "path": "a.md", "all": ["new line"]}, "", [], f)[0]
    assert grade.check({"type": "file_unchanged", "path": "keep.md"}, "", [], f)[0]
    assert not grade.check({"type": "file_unchanged", "path": "a.md"}, "", [], f)[0]
    assert not grade.check({"type": "writes_within", "paths": ["09-ideas/"]}, "", [], f)[0]
    assert grade.check({"type": "writes_within", "paths": ["09-ideas", "a.md"]}, "", [], f)[0]
    assert not grade.check({"type": "writes_within", "paths": []}, "", [], f)[0]


def test_broken_check_fails_never_passes():
    t = tasks.Task("rules-001", "rules", "p", "helm", [{"type": "max_lines", "n": "x"}], True, "active", "", "")
    r = grade.grade(t, "a", [], Files())
    assert r[0]["ok"] is False and "check error" in r[0]["detail"]


def test_score_views():
    checks = [{"type": "contains", "ok": True}, {"type": "judge", "ok": None, "judges": {"opus": True, "gemini": False}}]
    assert grade.score(checks, "opus") == (1.0, True)
    assert grade.score(checks, "gemini") == (0.5, False)
    no_gemini = [{"type": "contains", "ok": True}, {"type": "judge", "judges": {"opus": True, "gemini": None}}]
    assert grade.score(no_gemini, "gemini") == (1.0, True)        # a missing verdict is left out


# ---------------------------------------------------------------- judge

def test_parse_verdict():
    assert judge.parse_verdict('noise {"pass": true, "reason": "ok"} tail') == (True, "ok")
    with pytest.raises(ValueError):
        judge.parse_verdict('{"pass": "yes"}')


def test_judge_prompt_hides_the_target():
    p = judge.build_prompt({"rubric": "Answers in line 1"}, "q?", "a.")
    assert "Answers in line 1" in p and "claude" not in p.lower() and "gemini" not in p.lower()


# ---------------------------------------------------------------- sandbox (real bubblewrap, fake HOME)

needs_bwrap = pytest.mark.skipif(not shutil.which("bwrap"), reason="bubblewrap not installed")


def _bwrap_works() -> bool:
    r = subprocess.run(["bwrap", "--ro-bind", "/", "/", "--dev", "/dev", "true"], capture_output=True)
    return r.returncode == 0


@needs_bwrap
def test_sandbox_writes_land_in_the_overlay_never_the_vault(world):
    if not _bwrap_works():
        pytest.skip("bubblewrap cannot create a namespace here")
    snap = sandbox.build_snapshot(world.home / ".cache" / "rai-bench" / "runs" / "r" / "snapshot")
    assert (snap / "notes" / "a.md").read_text() == "alpha\n"
    assert not (snap / "03-rai" / "benchmark").exists()                   # hidden tests never visible
    t = tasks.Task("vault-001", "vault", "p", "helm", [], True, "active", "", "",
                   setup={"files": {"inbox/in.md": "planted"}})
    att = sandbox.prepare(world.home / ".cache" / "rai-bench" / "runs" / "r" / "att" / "x", snap, t)
    script = ("echo new > ~/helm/notes/b.md && echo more >> ~/helm/notes/a.md && rm ~/helm/AGENTS.md"
              " && cat ~/helm/inbox/in.md && ls ~/helm/03-rai/benchmark 2>/dev/null; echo end")
    r = subprocess.run(sandbox.bwrap_argv(att, "none", ["bash", "-c", script]), capture_output=True, text=True)
    if "overlay" in r.stderr.lower() and r.returncode != 0:
        pytest.skip(f"unprivileged overlay unavailable: {r.stderr.strip()}")
    assert r.returncode == 0, r.stderr
    assert "planted" in r.stdout
    assert (world.helm / "notes" / "a.md").read_text() == "alpha\n"       # live vault untouched
    assert not (world.helm / "notes" / "b.md").exists()
    assert (world.helm / "AGENTS.md").exists()
    fv = sandbox.FileView(att)
    assert fv.after("notes/b.md") == b"new\n"
    assert fv.after("notes/a.md") == b"alpha\nmore\n"
    assert fv.after("AGENTS.md") is None and fv.before("AGENTS.md") == b"vault\n"
    assert fv.changes() == ["AGENTS.md", "notes/a.md", "notes/b.md"]       # the planted file is not a change


@needs_bwrap
def test_sandbox_state_and_cache_are_scratch(world):
    if not _bwrap_works():
        pytest.skip("bubblewrap cannot create a namespace here")
    snap = sandbox.build_snapshot(world.home / ".cache" / "rai-bench" / "runs" / "r" / "snapshot")
    t = tasks.Task("coding-001", "coding", "p", "work", [], True, "active", "", "")
    att = sandbox.prepare(world.home / ".cache" / "rai-bench" / "runs" / "r" / "att" / "y", snap, t)
    secret = world.home / ".cache" / "rai-bench" / "runs" / "other"
    secret.mkdir(parents=True)
    (secret / "answer.txt").write_text("leak")
    (world.home / ".cache" / "some-scratch").mkdir()
    (world.home / ".cache" / "some-scratch" / "solution.py").write_text("leak")
    script = ('echo "$XDG_STATE_HOME"; pwd; cat ~/.cache/rai-bench/runs/other/answer.txt 2>/dev/null || echo hidden;'
              ' cat ~/.cache/some-scratch/solution.py 2>/dev/null || echo hidden2;'
              ' echo w > out.txt; echo cfg > ~/.some-config')
    r = subprocess.run(sandbox.bwrap_argv(att, "none", ["bash", "-c", script]), capture_output=True, text=True)
    if r.returncode != 0 and "overlay" in r.stderr.lower():
        pytest.skip(f"unprivileged overlay unavailable: {r.stderr.strip()}")
    assert r.returncode == 0, r.stderr
    lines = r.stdout.split()
    assert lines[0] == str(att.scratch / "state")
    assert lines[1] == str(att.work)
    assert "hidden" in lines and "hidden2" in lines and "leak" not in r.stdout
    assert sandbox.FileView(att).changes() == ["out.txt"]
    assert not (world.home / ".some-config").exists()                      # home writes are discarded


@needs_bwrap
def test_sandbox_reuse_stragglers_and_cleanup(world):
    """The same layer mounts twice in a row (overlayfs frees it late), a detached child dies
    with the sandbox, and the attempt tree, overlay work dir included, is removable."""
    if not _bwrap_works():
        pytest.skip("bubblewrap cannot create a namespace here")
    snap = sandbox.build_snapshot(world.home / ".cache" / "rai-bench" / "runs" / "r" / "snapshot")
    t = tasks.Task("coding-001", "coding", "p", "work", [], True, "active", "", "")
    att = sandbox.prepare(world.home / ".cache" / "rai-bench" / "runs" / "r" / "att" / "s", snap, t)
    tag = "31.4159"
    out, err, code, _ = runner.default_exec(
        sandbox.bwrap_argv(att, "none", ["bash", "-c", f"setsid sleep {tag} >/dev/null 2>&1 & echo started"]), None, 60)
    if code != 0 and "overlay" in err.lower():
        pytest.skip(f"unprivileged overlay unavailable: {err.strip()}")
    assert code == 0 and "started" in out, err
    out, err, code, _ = runner.default_exec(sandbox.bwrap_argv(att, "none", ["true"]), None, 60)
    assert code == 0, err                                                   # immediate remount works
    left = subprocess.run(["pgrep", "-f", f"sleep {tag}"], capture_output=True, text=True).stdout.split()
    for pid in left:
        os.kill(int(pid), 9)
    assert not left, "a detached child outlived its sandbox"
    sandbox.rmtree(att.root)
    assert not att.root.exists()


def test_bwrap_argv_layout(world):
    t = tasks.Task("rules-001", "rules", "p", "helm", [], True, "active", "", "")
    snap = world.home / ".cache" / "rai-bench" / "s"
    att = sandbox.Attempt(world.home / ".cache" / "rai-bench" / "runs" / "r" / "att" / "z", snap, t.cwd)
    (world.home / ".claude" / "projects").mkdir(parents=True)
    (world.home / ".claude" / "history.jsonl").write_text("")
    (world.home / ".gemini").mkdir()
    a = sandbox.bwrap_argv(att, "claude-code", ["claude", "-p"])
    s = " ".join(a)
    assert f"--overlay {att.upper} {att.ovwork} {world.home / 'helm'}" in s
    assert f"--bind {att.scratch / 'claude' / 'projects'} {world.home / '.claude' / 'projects'}" in s
    assert f"--bind {att.scratch / 'claude' / 'history.jsonl'} {world.home / '.claude' / 'history.jsonl'}" in s
    assert f"--chdir {world.home / 'helm'} -- claude -p" in s
    assert ".claude.json" not in s                                         # lives in the throwaway home
    assert s.index(f"--tmp-overlay {world.home} ") < s.index("--overlay " + str(att.upper))
    g = " ".join(sandbox.bwrap_argv(att, "agy", ["agy"]))
    assert ".claude" not in g and f"--tmp-overlay {world.home} " in g
    # the desktop, the session bus and the whole ~/.cache are out of reach
    assert f"--tmpfs {world.home / '.cache'} " in s
    assert s.index(f"--tmpfs {world.home / '.cache'} ") < s.index(f"--bind {att.root} {att.root}")
    for var in ("DBUS_SESSION_BUS_ADDRESS", "WAYLAND_DISPLAY", "SSH_AUTH_SOCK"):
        assert f"--unsetenv {var}" in s
    run_user = Path(f"/run/user/{os.getuid()}")
    if run_user.is_dir():
        assert f"--tmpfs {run_user} " in s
    assert "--unshare-pid" in s


# ---------------------------------------------------------------- runner (fake executor)

class FakeHarness:
    """Stands in for every subprocess the runner starts. Answers by what the argv asks for."""

    def __init__(self, limit_first=0):
        self.calls = []
        self.limit_first = limit_first

    @staticmethod
    def inner(argv):
        return argv[argv.index("--") + 1:] if "--" in argv else argv

    @staticmethod
    def upper(argv):
        i = argv.index("--overlay")
        return Path(argv[i + 1])

    def __call__(self, argv, stdin, timeout):
        cmd = self.inner(argv)
        self.calls.append(cmd)
        if cmd[0] == "bash":                                   # identity render
            return "Rai identity block", "", 0, 0.1
        if cmd[0] == "uv":                                     # hidden tests
            return "1 passed", "", 0, 0.1
        prompt = stdin if cmd[0] == "claude" else cmd[2]
        if "strict grader" in prompt:                          # a judge
            v = json.dumps({"pass": True, "reason": "fine"})
            if cmd[0] == "claude":
                return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": v}), "", 0, 0.1
            return json.dumps({"type": "result", "status": "SUCCESS", "response": v}), "", 0, 0.1
        if cmd[0] == "claude":
            if self.limit_first > 0:
                self.limit_first -= 1
                return json.dumps({"type": "result", "subtype": "success", "is_error": True,
                                   "result": "API Error: Rate limit reached"}), "", 0, 0.1
            (self.upper(argv) / "notes").mkdir(parents=True, exist_ok=True)
            (self.upper(argv) / "notes" / "done.md").write_text("ok")
            return "\n".join(json.dumps(e) for e in [
                {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Write",
                                                              "input": {"file_path": "notes/done.md"}}]}},
                {"type": "result", "subtype": "success", "is_error": False, "result": "Paris", "num_turns": 1}]), "", 0, 2.0
        if cmd[0] == "agy":
            return json.dumps({"type": "result", "status": "SUCCESS", "response": "Lyon — maybe"}), "", 0, 3.0
        raise AssertionError(f"unexpected command {cmd}")


def fake_snapshot(monkeypatch):
    """Runner tests need no real vault copy: an empty snapshot dir stands in."""
    def build(dest, helm=None):
        (dest / "helm").mkdir(parents=True, exist_ok=True)
        return dest / "helm"
    monkeypatch.setattr(sandbox, "build_snapshot", build)


def _start(world, rows, mode="model", models=None, size="quick"):
    world.write_tasks("rules", rows)
    cat = targets.load(world.bench)
    tg = targets.resolve(cat, mode, models)
    all_t = tasks.load(world.bench)
    chosen = tasks.select(all_t, size)
    runner.new_run("r1", mode, size, tg, chosen, tasks.set_version(all_t))
    return "r1"


def test_runner_end_to_end_with_judges_and_report(world, monkeypatch):
    fake_snapshot(monkeypatch)
    rows = [task_raw(checks=[{"type": "contains", "any": ["paris"]}, {"type": "no_em_dash"},
                             {"type": "writes_within", "paths": ["notes/"]},
                             {"type": "judge", "rubric": "Answers directly"}])]
    _start(world, rows)
    fake = FakeHarness()
    runner.Runner("r1", execute=fake, sleep=lambda s: None, log=lambda m: None).run()
    lines = [json.loads(x) for x in (world.bench / "results" / "r1" / "attempts.jsonl").read_text().splitlines()]
    by = {r["target"]["key"]: r for r in lines}
    assert set(by) == {"opus-5.5", "gemini"}
    assert by["opus-5.5"]["views"]["opus"] == {"score": 1.0, "pass": True}
    assert by["opus-5.5"]["changes"] == ["notes/done.md"]
    g = by["gemini"]
    assert g["views"]["opus"]["pass"] is False and g["views"]["opus"]["score"] == 0.5   # wrong + em dash
    judged = [c for c in g["checks"] if c["type"] == "judge"][0]
    assert judged["judges"] == {"opus": True, "gemini": True}
    agy_runs = [c for c in fake.calls if c[0] == "agy" and "strict grader" not in c[2]]
    assert agy_runs, "agy attempt ran"
    text = report.run_report("r1")
    assert "Opus" in text and "Gemini" in text
    board = report.leaderboard()
    assert "## Tasks " in board and (world.bench / "leaderboard.md").exists()
    spec = json.loads((world.bench / "results" / "r1" / "run.json").read_text())
    assert spec["status"]["state"] == "done" and spec["status"]["done"] == 2


def test_runner_rate_limit_pauses_and_resumes(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["opus-5.5"])
    now = [1_000_000.0]
    slept = []

    def sleep(s):
        slept.append(s)
        now[0] += s

    fake = FakeHarness(limit_first=1)
    runner.Runner("r1", execute=fake, clock=lambda: now[0], sleep=sleep, log=lambda m: None).run()
    lines = (world.bench / "results" / "r1" / "attempts.jsonl").read_text().splitlines()
    assert len(lines) == 1 and json.loads(lines[0])["views"]["opus"]["pass"] is True
    assert slept and slept[0] >= runner.BACKOFF_FIRST - 1                 # waited out the limit


def test_runner_resume_skips_done_jobs(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw(), task_raw(id="rules-002")], models=["opus-5.5"])
    fake = FakeHarness()
    runner.Runner("r1", execute=fake, sleep=lambda s: None, log=lambda m: None).run()
    n = len(fake.calls)
    runner.Runner("r1", execute=fake, sleep=lambda s: None, log=lambda m: None).run()
    assert len(fake.calls) == n                                            # nothing re-ran


def test_runner_crash_retries_then_records_infra(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["opus-5.5"])

    def crash(argv, stdin, timeout):
        cmd = FakeHarness.inner(argv)
        if cmd[0] == "bash":
            return "id", "", 0, 0.1
        return "", "boom", 1, 0.1

    runner.Runner("r1", execute=crash, sleep=lambda s: None, log=lambda m: None).run()
    row = json.loads((world.bench / "results" / "r1" / "attempts.jsonl").read_text())
    assert row["infra"] == "error"
    assert report.summarize([row])[0]["infra_errors"] == 1


def test_agy_gets_the_rai_context_file(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["gemini"])
    seen = {}

    def spy(argv, stdin, timeout):
        cmd = FakeHarness.inner(argv)
        if cmd[0] == "agy" and "strict grader" not in cmd[2]:
            up = FakeHarness.upper(argv)
            seen["gemini_md"] = (up / "GEMINI.md").read_text()
        return FakeHarness()(argv, stdin, timeout)

    runner.Runner("r1", execute=spy, sleep=lambda s: None, log=lambda m: None).run()
    assert "Rai identity block" in seen["gemini_md"]
    row = json.loads((world.bench / "results" / "r1" / "attempts.jsonl").read_text())
    assert "GEMINI.md" not in row["changes"]                                # planted, not the agent's write


def test_night_window():
    from datetime import datetime as dt
    assert runner.in_night(dt(2026, 10, 1, 23, 30)) and runner.in_night(dt(2026, 10, 2, 7, 59))
    assert not runner.in_night(dt(2026, 10, 1, 12, 0))
    assert runner.next_night(dt(2026, 10, 1, 12, 0)) == dt(2026, 10, 1, 23, 0)


def test_spread_alternates_accounts():
    def J(h, i):
        task = tasks.Task(f"rules-00{i}", "rules", "p", "helm", [], True, "active", "", "")
        return runner.Job(targets.Target(f"{h}{i}", h, "m", "l"), task, 1)
    wave = runner.Runner._spread([J("claude-code", 1), J("claude-code", 2), J("agy", 1)], 2)
    assert {j.target.harness for j in wave} == {"claude-code", "agy"}


# ---------------------------------------------------------------- CLI

def test_cli_plan_and_models(world, capsys):
    import bench
    world.write_tasks("rules", [task_raw()])
    assert bench.main(["models"]) == 0
    assert "off: no compliant route" in capsys.readouterr().out
    assert bench.main(["plan", "--models", "opus-5.5,gemini"]) == 0
    out = capsys.readouterr().out
    assert "attempts: 2" in out and "no money" in out
    assert bench.main(["plan", "--models", "pi-m"]) == 1


def test_cli_approve(world, capsys):
    import bench
    world.write_tasks("rules", [task_raw(status="draft"), task_raw(id="rules-002", status="draft")])
    assert bench.main(["approve", "rules-002"]) == 0
    st = {t.id: t.status for t in tasks.load(world.bench)}
    assert st == {"rules-001": "draft", "rules-002": "active"}
    assert bench.main(["approve", "--area", "rules", "--all"]) == 0
    assert all(t.status == "active" for t in tasks.load(world.bench))


# ---------------------------------------------------------------- review fixes

def test_validate_needs_a_positive_check():
    only_negative = [{"type": "no_em_dash"}, {"type": "writes_within", "paths": []}]
    assert any("only by doing the task" in p for p in tasks.validate(task_raw(checks=only_negative)))


def test_empty_answer_fails_text_checks():
    for c in ({"type": "no_em_dash"}, {"type": "no_emoji"}, {"type": "english_only"},
              {"type": "max_lines", "n": 5}, {"type": "not_contains", "any": ["x"]}):
        assert grade.check(c, "  ", [], Files()) == (False, "empty answer")


def test_live_tasks_all_carry_a_positive_check():
    bench = SCRIPTS.parents[2] / "benchmark"
    for t in tasks.load(bench):
        assert any(c["type"] in tasks.POSITIVE for c in t.checks), t.id


@needs_bwrap
def test_opaque_dir_hides_lower_files(world):
    """rm -rf a dir and recreate it: the old files are gone, and the grader sees that."""
    if not _bwrap_works():
        pytest.skip("bubblewrap cannot create a namespace here")
    snap = sandbox.build_snapshot(world.home / ".cache" / "rai-bench" / "runs" / "r" / "snapshot")
    t = tasks.Task("vault-001", "vault", "p", "helm", [], True, "active", "", "")
    att = sandbox.prepare(world.home / ".cache" / "rai-bench" / "runs" / "r" / "att" / "o", snap, t)
    script = "rm -rf ~/helm/notes && mkdir ~/helm/notes && echo n > ~/helm/notes/new.md"
    r = subprocess.run(sandbox.bwrap_argv(att, "none", ["bash", "-c", script]), capture_output=True, text=True)
    if r.returncode != 0 and "overlay" in r.stderr.lower():
        pytest.skip(f"unprivileged overlay unavailable: {r.stderr.strip()}")
    assert r.returncode == 0, r.stderr
    fv = sandbox.FileView(att)
    assert fv.after("notes/a.md") is None and fv.after("notes/new.md") == b"n\n"
    assert set(fv.changes()) == {"notes/a.md", "notes/new.md"}


def test_scrub_drops_benchmark_memory(tmp_path):
    snap = tmp_path / "helm"
    (snap / "13-archive" / "historical-sessions").mkdir(parents=True)
    (snap / "13-archive" / "historical-sessions" / "s1.json").write_text('{"m": "edit 03-rai/benchmark/tasks/rules.jsonl"}')
    (snap / "13-archive" / "historical-sessions" / "s2.json").write_text('{"m": "unrelated"}')
    (snap / "03-rai" / "semantic-memory" / "daily").mkdir(parents=True)
    (snap / "03-rai" / "semantic-memory" / "daily" / "d.md").write_text("- kept\n- ran bench.py approve\n- kept too\n")
    (snap / "03-rai" / "benchmark").mkdir(parents=True)
    counts = sandbox.scrub(snap)
    assert counts == {"files": 1, "lines": 1}
    assert not (snap / "13-archive" / "historical-sessions" / "s1.json").exists()
    assert (snap / "03-rai" / "semantic-memory" / "daily" / "d.md").read_text() == "- kept\n- kept too\n"
    assert not (snap / "03-rai" / "benchmark").exists()


def test_judge_pause_waits_instead_of_spinning(world, monkeypatch):
    """Anthropic hits its limit on the Opus judge of an agy job: the run sleeps until the reset
    and finishes; it never spins, and the pause does not creep forward."""
    fake_snapshot(monkeypatch)
    rows = [task_raw(id=f"rules-00{i}", checks=[{"type": "contains", "any": ["lyon"]},
                                                 {"type": "judge", "rubric": "r"}]) for i in range(1, 4)]
    _start(world, rows, models=["gemini"])
    now = [1_000_000.0]
    sleeps = []

    def sleep(s):
        sleeps.append(s)
        now[0] += s

    limited = {"n": 2}
    base = FakeHarness()

    def ex(argv, stdin, timeout):
        cmd = FakeHarness.inner(argv)
        if cmd[0] == "claude" and limited["n"] > 0:
            limited["n"] -= 1
            return json.dumps({"type": "result", "subtype": "success", "is_error": True,
                               "result": "Claude AI usage limit reached"}), "", 0, 0.1
        return base(argv, stdin, timeout)

    runner.Runner("r1", execute=ex, clock=lambda: now[0], sleep=sleep, log=lambda m: None).run()
    rows = runner.read_rows(world.bench / "results" / "r1" / "attempts.jsonl")
    assert len(rows) == 3 and all(r["checks"][1]["judges"]["opus"] is True for r in rows)
    assert len(sleeps) < 10                                              # no hot loop
    agents = [c for c in base.calls if c[0] == "agy" and "strict grader" not in c[2]]
    assert len(agents) == 3                                              # every agy agent ran once


def test_run_lock_refuses_a_second_runner(world, monkeypatch):
    import fcntl
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["opus-5.5"])
    lockf = runner.paths.run_cache("r1") / "run.lock"
    lockf.parent.mkdir(parents=True, exist_ok=True)
    with open(lockf, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        with pytest.raises(runner.RunBusy):
            runner.Runner("r1", execute=FakeHarness(), sleep=lambda s: None, log=lambda m: None).run()


def test_torn_line_is_skipped_and_closed_off(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw(), task_raw(id="rules-002")], models=["opus-5.5"])
    f = world.bench / "results" / "r1" / "attempts.jsonl"
    f.write_text('{"key": "opus-5.5|rules-001|1", "torn')
    runner.Runner("r1", execute=FakeHarness(), sleep=lambda s: None, log=lambda m: None).run()
    rows = runner.read_rows(f)
    assert sorted(r["task"] for r in rows) == ["rules-001", "rules-002"]


def test_resume_refuses_changed_tasks(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["opus-5.5"])
    world.write_tasks("rules", [task_raw(prompt="a different question")])
    with pytest.raises(tasks.TaskError, match="changed since it started"):
        runner.Runner("r1", execute=FakeHarness(), sleep=lambda s: None, log=lambda m: None)


def test_rate_limit_beats_timeout(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw()], models=["opus-5.5"])
    calls = {"n": 0}

    def ex(argv, stdin, timeout):
        cmd = FakeHarness.inner(argv)
        if cmd[0] == "claude" and "strict grader" not in (stdin or "") and calls["n"] == 0:
            calls["n"] += 1
            return json.dumps({"type": "result", "subtype": "success", "is_error": True,
                               "result": "rate limit reached"}), "[bench] timeout", 124, 900.0
        return FakeHarness()(argv, stdin, timeout)

    now = [1_000_000.0]

    def sleep(s):
        now[0] += s

    runner.Runner("r1", execute=ex, clock=lambda: now[0], sleep=sleep, log=lambda m: None).run()
    row = runner.read_rows(world.bench / "results" / "r1" / "attempts.jsonl")[0]
    assert row["infra"] is None and row["views"]["opus"]["pass"] is True     # re-run, not scored as a fail


def test_judges_see_the_full_answer(world, monkeypatch):
    fake_snapshot(monkeypatch)
    _start(world, [task_raw(checks=[{"type": "contains", "any": ["paris"]}, {"type": "judge", "rubric": "r"}])],
           models=["opus-5.5"])
    long = "Paris. " + "x" * (runner.ANSWER_CAP + 50) + " THE-END"
    seen = []

    def ex(argv, stdin, timeout):
        cmd = FakeHarness.inner(argv)
        prompt = stdin if cmd[0] == "claude" else (cmd[2] if len(cmd) > 2 else "")
        if cmd[0] == "claude" and "strict grader" not in prompt:
            return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": long}), "", 0, 1.0
        if "strict grader" in prompt:
            seen.append("THE-END" in prompt)
        return FakeHarness()(argv, stdin, timeout)

    runner.Runner("r1", execute=ex, sleep=lambda s: None, log=lambda m: None).run()
    row = runner.read_rows(world.bench / "results" / "r1" / "attempts.jsonl")[0]
    assert seen and all(seen)
    assert row["answer"].endswith("[truncated]")


def test_pass_k_is_per_full_run():
    def row(run, task, ok, size="full", trial=1):
        return {"run_id": run, "key": f"k|{task}|{trial}|{run}", "task": task, "area": "rules", "size": size,
                "trial": trial, "target": {"key": "k", "label": "L", "harness": "h"}, "checks": [],
                "views": {"opus": {"score": 1.0 if ok else 0.0, "pass": ok},
                          "gemini": {"score": 1.0 if ok else 0.0, "pass": ok}}, "wall_s": 1.0}
    rows = [row("a", "t1", True, trial=1), row("a", "t1", True, trial=2),
            row("b", "t1", True, trial=1), row("b", "t1", False, trial=2)]
    s = report.summarize(rows)[0]
    assert s["pass_k"]["opus"] == 0.5                 # run a passed every trial, run b did not
    quick = [row("q", "t1", True, size="quick"), row("q2", "t1", True, size="quick")]
    assert report.summarize(quick)[0]["pass_k"]["opus"] is None
    assert s["areas"]["rules"]["opus"] == 0.75         # headline = pass rate


def test_planted_pytest_cannot_fake_a_pass(tmp_path):
    work = tmp_path / "work"
    (work / "hidden_tests").mkdir(parents=True)
    (work / "hidden_tests" / "test_x.py").write_text("def test_x():\n    assert False\n")
    (work / "hidden_tests" / ".bench-pytest.ini").write_text("[pytest]\n")
    (work / "pytest.py").write_text("import sys\nsys.exit(0)\n")
    r = subprocess.run([sys.executable, *runner.PYTEST_ARGS], cwd=work, capture_output=True, text=True)
    assert r.returncode != 0


# ---------------------------------------------------------------- effort levels

def test_efforts_expand_targets(world):
    cat = targets.load(world.bench)
    tg = targets.resolve(cat, "model", ["opus-5.5"], efforts=["low", "max"])
    assert [(t.key, t.effort, t.label) for t in tg] == [
        ("opus-5.5@low", "low", "Opus (low)"), ("opus-5.5@max", "max", "Opus (max)")]
    with pytest.raises(targets.TargetError, match="agy has no effort 'xhigh'"):
        targets.resolve(cat, "model", ["gemini"], efforts=["xhigh"])


def test_effort_reaches_the_cli():
    argv, _ = adapters.command("claude-code", "claude-opus-5-5", "q", "xhigh")
    assert argv[argv.index("--effort") + 1] == "xhigh"
    argv, _ = adapters.command("agy", "gemini-3.1-pro-high", "q", "low")
    assert argv[argv.index("--effort") + 1] == "low"
    assert "--effort" not in adapters.command("claude-code", "m", "q")[0]


def test_effort_runs_are_separate_rows(world, monkeypatch):
    fake_snapshot(monkeypatch)
    world.write_tasks("rules", [task_raw()])
    cat = targets.load(world.bench)
    tg = targets.resolve(cat, "model", ["opus-5.5"], efforts=["low", "high"])
    all_t = tasks.load(world.bench)
    runner.new_run("r1", "model", "quick", tg, tasks.select(all_t, "quick"), tasks.set_version(all_t))
    fake = FakeHarness()
    runner.Runner("r1", execute=fake, sleep=lambda s: None, log=lambda m: None).run()
    efforts = sorted(c[c.index("--effort") + 1] for c in fake.calls if c[0] == "claude" and "--effort" in c
                     and "--max-turns" in c and c[c.index("--max-turns") + 1] == str(adapters.MAX_TURNS))
    assert efforts == ["high", "low"]
    names = [s["name"] for s in report.summarize(runner.read_rows(world.bench / "results" / "r1" / "attempts.jsonl"))]
    assert sorted(names) == ["Opus (high) @ claude-code", "Opus (low) @ claude-code"]


def test_status_defaults_to_the_run_started_last(world):
    import bench
    for run_id, created in (("2026-10-01-1958-model-smoke", "2026-10-01T19:58:01"),
                            ("2026-10-01-1958-model-quick", "2026-10-01T19:58:40")):
        d = world.bench / "results" / run_id
        d.mkdir(parents=True)
        (d / "run.json").write_text(json.dumps({"created": created}))
    assert bench._newest() == "2026-10-01-1958-model-quick"


def test_harness_skill_sync_is_not_the_agents_write(tmp_path):
    snap, root = tmp_path / "snap", tmp_path / "att"
    snap.mkdir()
    t = tasks.Task("vault-001", "vault", "p", "helm", [], True, "active", "", "")
    att = sandbox.prepare(root, snap, t)
    (att.upper / "03-rai" / "skills" / "synced" / "abc" / "pdf").mkdir(parents=True)
    (att.upper / "03-rai" / "skills" / "synced" / "abc" / "pdf" / "SKILL.md").write_text("x")
    (att.upper / "notes").mkdir()
    (att.upper / "notes" / "n.md").write_text("y")
    assert sandbox.FileView(att).changes() == ["notes/n.md"]
