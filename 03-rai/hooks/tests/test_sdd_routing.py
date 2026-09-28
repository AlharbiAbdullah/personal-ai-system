"""
test_sdd_routing.py — M10 / H27 memory routing: project-init repos keep their truth.

Covers lib/sdd_repo.py detection, and both Rai-memory writers (turn-capture.py live,
distill_session.py batch): the routing addendum and the code-side guard apply ONLY
when the session cwd sits in a repo holding `.project.toml`.

Hermetic: every model call is stubbed and every output path is a pytest tmp dir, so
nothing touches the live semantic-memory folders or runs `claude`.

Run: uv run --with pytest pytest 03-rai/hooks/tests/test_sdd_routing.py -q -p no:cacheprovider
"""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))  # bind `lib` to THIS checkout before the writers import it

from lib import claude_cli
from lib.sdd_repo import (
    POINTER_RE,
    has_pointer,
    leak_check,
    pointer_line,
    routing_rule,
    scenario_ids,
    sdd_repo,
    sdd_root,
    session_cwd,
    transcript_cwd,
)


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


tc = _load("turn_capture", HOOKS / "turn-capture.py")
ds = _load("distill_session", HOOKS / "scripts" / "distill_session.py")

GIT = ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
       "-c", "user.name=t", "-c", "user.email=t@t", "-c", "init.defaultBranch=main"]


def git_init(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run([*GIT, "init", "-q", str(path)], check=True)
    return path


def sdd_repo_dir(path: Path, origin: str = "git@github.com:john/tipcalc.git") -> Path:
    git_init(path)
    (path / ".project.toml").write_text(
        f'standard = "sdd-1"\ndefault_branch = "main"\norigin_url = "{origin}"\n'
    )
    (path / "src" / "tipcalc").mkdir(parents=True)
    return path


# --- detection ---------------------------------------------------------------------------

def test_detects_repo_root_with_project_toml(tmp_path):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    assert sdd_root(repo) == repo.resolve()
    assert sdd_repo(repo) == "tipcalc"
    assert sdd_repo(str(repo)) == "tipcalc"


def test_detects_subdir_of_sdd_repo(tmp_path):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    assert sdd_root(repo / "src" / "tipcalc") == repo.resolve()
    assert sdd_repo(repo / "src" / "tipcalc") == "tipcalc"


def test_removed_cwd_inside_repo_still_detected(tmp_path):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    assert sdd_repo(repo / ".claude" / "worktrees" / "gone") == "tipcalc"


def test_repo_name_falls_back_to_folder_without_origin(tmp_path):
    repo = sdd_repo_dir(tmp_path / "calc-local", origin="")
    assert sdd_repo(repo) == "calc-local"


def test_linked_worktree_points_at_main_checkout(tmp_path):
    repo = sdd_repo_dir(tmp_path / "tipcalc", origin="")
    subprocess.run([*GIT, "-C", str(repo), "add", ".project.toml"], check=True)
    subprocess.run([*GIT, "-C", str(repo), "commit", "-qm", "init"], check=True)
    wt = tmp_path / "tipcalc-fix-crash"
    subprocess.run([*GIT, "-C", str(repo), "worktree", "add", "-q", str(wt), "-b", "fix/crash"],
                   check=True)
    assert sdd_root(wt) == wt.resolve()
    assert sdd_repo(wt) == "tipcalc"


@pytest.mark.parametrize("sub", ["", "03-rai", "03-rai/hooks"])
def test_helm_is_not_sdd(sub):
    helm = Path.home() / "helm"
    if not helm.is_dir():
        pytest.skip("no ~/helm on this machine")
    assert sdd_root(helm / sub) is None
    assert sdd_repo(helm / sub) == ""


def test_this_checkout_is_not_sdd():
    assert sdd_repo(HOOKS) == ""


def test_plain_git_repo_is_not_sdd(tmp_path):
    repo = git_init(tmp_path / "plain")
    (repo / "pkg").mkdir()
    assert sdd_repo(repo) == ""
    assert sdd_repo(repo / "pkg") == ""


def test_non_git_dir_is_not_sdd(tmp_path):
    d = tmp_path / "loose" / "notes"
    d.mkdir(parents=True)
    assert sdd_repo(d) == ""
    assert sdd_repo("") == ""
    assert sdd_repo(None) == ""


def test_walk_stops_at_nearest_git_toplevel(tmp_path):
    outer = sdd_repo_dir(tmp_path / "tipcalc")
    inner = git_init(outer / "vendor" / "other")  # a different repo nested inside
    assert sdd_repo(inner) == ""


def test_outside_git_only_the_cwd_counts(tmp_path):
    parent = tmp_path / "loose"
    (parent / "child").mkdir(parents=True)
    (parent / ".project.toml").write_text('standard = "sdd-1"\n')
    assert sdd_repo(parent) == "loose"
    assert sdd_repo(parent / "child") == ""


def _native_transcript(path: Path, cwd: str) -> Path:
    """Real line order: a `last-prompt` head with no cwd, then entries that carry it."""
    rows = [{"type": "last-prompt", "leafUuid": "u2", "sessionId": "s"},
            {"type": "mode", "mode": "default", "sessionId": "s"},
            {"type": "user", "cwd": cwd, "sessionId": "s",
             "message": {"role": "user", "content": "hi"}},
            {"type": "assistant", "cwd": "/elsewhere", "sessionId": "s",
             "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}]
    path.write_text("not json\n" + "\n".join(json.dumps(r) for r in rows) + "\n")
    return path


def test_transcript_cwd_reads_past_the_cwdless_head(tmp_path):
    t = _native_transcript(tmp_path / "t.jsonl", "/home/x/tipcalc")
    assert transcript_cwd(t) == "/home/x/tipcalc"  # the FIRST cwd, like the scanner
    assert transcript_cwd(tmp_path / "missing.jsonl") == ""
    assert transcript_cwd("") == "" and transcript_cwd(None) == "" and transcript_cwd(3) == ""


def test_session_cwd_prefers_json_then_transcript(tmp_path):
    t = _native_transcript(tmp_path / "t.jsonl", "/home/x/tipcalc")
    assert session_cwd({"cwd": "/a", "transcript_path": str(t)}) == "/a"
    # archived SessionEnd-hook captures carry cwd '': the hook read line 1 only (verify3)
    assert session_cwd({"cwd": "", "transcript_path": str(t)}) == "/home/x/tipcalc"
    assert session_cwd({"cwd": None, "transcript_path": str(t)}) == "/home/x/tipcalc"
    assert session_cwd({"cwd": "", "transcript_path": str(tmp_path / "gone.jsonl")}) == ""
    assert session_cwd({}) == ""


SPEC = """# Capability: cli

## Requirement: No crash on bad input
The CLI SHALL exit non-zero with a usage line when input is missing.

### Scenario: cli.no-args [gap: entrypoint-hardening]
- GIVEN no arguments

### Scenario: `cli.tip-default`
- GIVEN a bill
"""


def _repo_with_specs(tmp_path: Path) -> Path:
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    (repo / "specs" / "capabilities").mkdir(parents=True)
    (repo / "specs" / "capabilities" / "cli.md").write_text(SPEC)
    (repo / "src" / "tipcalc" / "cli.py").write_text("def main(): ...\n")
    (repo / "README.md").write_text("# tipcalc\n")
    return repo


def test_scenario_ids_from_specs(tmp_path):
    repo = _repo_with_specs(tmp_path)
    assert scenario_ids(repo) == {"cli.no-args", "cli.tip-default"}
    assert scenario_ids(tmp_path / "nowhere") == set()


def test_leak_check_flags_scenario_ids_and_repo_files(tmp_path):
    repo = _repo_with_specs(tmp_path)
    leaks = leak_check(repo)
    assert leaks("- scenario cli.no-args added, went red first")
    assert leaks("- fixed `src/tipcalc/cli.py` to guard argv")
    assert leaks(f"- see {repo}/specs/capabilities/cli.md")
    assert leaks("worked in tipcalc: covered cli.tip-default.")
    # generic words, bare file names, dirs, other repos and look-alikes are not leaks
    assert not leaks("- John prefers exit codes documented in the README")
    assert not leaks("- John prefers exit codes documented in README.md")
    assert not leaks("- ADRs live under project_memory/decisions/ (seen in tipcalc)")
    assert not leaks("- cli.no-argsx and and/or 12/5 are not repo specifics")
    assert not leaks("- see /etc/hosts and ../other/src/tipcalc/cli.py")
    assert not leaks("")
    assert not leak_check(None)("- scenario cli.no-args")


# --- pointer line ------------------------------------------------------------------------

def test_pointer_line_is_one_line_with_repo_stamped():
    assert pointer_line("tipcalc", "- worked in tipcalc-fix-x: hardened the CLI. Then more.\nx") \
        == "worked in tipcalc: hardened the CLI."
    assert pointer_line("tipcalc", "") == "worked in tipcalc: details live in the repo"
    assert pointer_line("tipcalc", "Worked in tipcalc — added usage errors") \
        == "worked in tipcalc: added usage errors"
    assert len(pointer_line("tipcalc", "a" * 500)) < 240
    assert pointer_line("tipcalc", "- worked in tipcalc:") == "worked in tipcalc: details live in the repo"
    assert pointer_line("tipcalc", "worked in tipcalc, fixing the parser") \
        == "worked in tipcalc: fixing the parser"


def test_pointer_line_drops_a_what_that_names_repo_specifics(tmp_path):
    leaks = leak_check(_repo_with_specs(tmp_path))
    assert pointer_line("tipcalc", "added scenario cli.no-args, then fixed it", leaks) \
        == "worked in tipcalc: details live in the repo"
    assert pointer_line("tipcalc", "hardened the CLI entrypoint.", leaks) \
        == "worked in tipcalc: hardened the CLI entrypoint."


def test_has_pointer_matches_only_this_repo():
    block = "- a lesson (seen in tipcalc)\n- worked in tipcalc: hardened the CLI"
    assert has_pointer(block, "tipcalc")
    assert has_pointer("worked in TipCalc: x", "tipcalc")
    assert not has_pointer(block, "tip")          # a prefix of the name is another repo
    assert not has_pointer(block, "ledger")
    assert not has_pointer("", "tipcalc")


def test_routing_rule_keeps_repo_choices_in_the_repo():
    rule = routing_rule("tipcalc")
    # a repo choice is never relabelled as John's preference (verify1 failure), whoever
    # made it: Rai, John delegating ("you pick") or John ordering a value ("use 2")
    assert "stays in the repo, whether Rai made it" in rule
    assert '("you pick")' in rule and '("use 2")' in rule
    assert 'never turn it into "John prefers' in rule
    assert '"(seen in tipcalc)"' in rule and '"worked in tipcalc: <' in rule


def test_routing_rule_keeps_preferences_john_states_himself():
    rule = routing_rule("tipcalc")
    # verify3: an unscoped "I prefer ..." said while working in the repo is still his
    assert "Keep it even though he said it while working here" in rule
    assert '"I prefer ..."' in rule
    assert "explicitly scopes" not in rule  # no longer needs "in all my repos" wording
    # verify3: no invented patterns inferred from Rai's actions or his approval
    assert "never infer a pattern, habit or expectation" in rule
    assert "an empty result besides the pointer is normal" in rule


# --- turn-capture (live writer) ----------------------------------------------------------

TURN = "USER: " + "please harden the entrypoint " * 20


def test_observer_prompt_unchanged_outside_sdd():
    p = tc.build_prompt(TURN)
    assert p == tc.OBSERVER_PROMPT + "\nEXCHANGE:\n" + TURN
    assert tc.OBSERVER_PROMPT.endswith("output exactly: SKIP\n")  # today's bytes, split in two
    assert "REPO RULE" not in p and "worked in" not in p


def test_observer_prompt_gets_addendum_in_sdd():
    p = tc.build_prompt(TURN, "tipcalc")
    assert p.startswith(tc.OBSERVER_PROMPT)
    assert "REPO RULE" in p and '"tipcalc"' in p and "- worked in tipcalc: ..." in p
    # the observer's "2-10 bullets" floor must not push it to invent a second bullet (verify3)
    assert "including its 2-bullet minimum" in p
    assert "a lone pointer bullet is a complete answer" in p
    assert "(only questions, diagnosis, plans or reading)" in p
    assert p.endswith("\nEXCHANGE:\n" + TURN)


def test_route_bullets_keeps_exactly_one_pointer_first():
    out = tc.route_bullets(
        ["- John wants red tests before code in every repo",
         "- worked in tipcalc: added usage-error handling",
         "- worked in tipcalc: second pointer"], "tipcalc")
    assert out[0] == "- worked in tipcalc: added usage-error handling"
    assert sum(bool(POINTER_RE.match(b)) for b in out) == 1
    assert out[1:] == ["- John wants red tests before code in every repo"]
    assert tc.route_bullets(["- a lesson (seen in tipcalc)"], "tipcalc")[0] \
        == "- worked in tipcalc: details live in the repo"


def test_route_bullets_drops_bullets_naming_repo_specifics(tmp_path):
    leaks = leak_check(_repo_with_specs(tmp_path))
    out = tc.route_bullets(
        ["- worked in tipcalc: added cli.no-args and fixed the crash",
         "- Usage errors exit 2 (argparse convention); scenario cli.no-args added",
         "- Guard lives in src/tipcalc/cli.py",
         "- John prefers exit codes documented in the README"], "tipcalc", leaks=leaks)
    assert out == ["- worked in tipcalc: details live in the repo",
                   "- John prefers exit codes documented in the README"]


def _transcript(tmp_path: Path) -> Path:
    t = tmp_path / "session.jsonl"
    rows = [
        {"type": "user", "message": {"role": "user", "content": "please harden the entrypoint " * 20}},
        {"type": "assistant", "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": "done " * 50}]}},
    ]
    t.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
    return t


def _run_capture(tmp_path, monkeypatch, cwd, model_out, session_id="abcdef1234567890"):
    """One detached-worker capture; returns (prompt, every bullet in the daily log so far)."""
    seen = {}

    def fake_run(cmd, input=None, **kw):
        seen["prompt"] = input
        return subprocess.CompletedProcess(cmd, 0, stdout=model_out, stderr="")

    monkeypatch.setattr(tc, "DAILY_DIR", tmp_path / "daily")
    monkeypatch.setattr(tc, "DEBOUNCE_DIR", tmp_path / "debounce")
    monkeypatch.setattr(claude_cli, "effort_args", lambda level="high": [])
    monkeypatch.setattr(tc.subprocess, "run", fake_run)
    tc.capture(str(_transcript(tmp_path)), session_id, str(cwd))
    lines = [ln for day in sorted((tmp_path / "daily").glob("*.md"))
             for ln in day.read_text().splitlines()]
    return seen["prompt"], [ln for ln in lines if ln.startswith("- ")]


def _blocks(tmp_path) -> list[str]:
    return [ln for day in sorted((tmp_path / "daily").glob("*.md"))
            for ln in day.read_text().splitlines() if ln.startswith("### ")]


MODEL_BULLETS = ("- worked in tipcalc: hardened the CLI entrypoint\n"
                 "- John wants a failing test before every fix\n"
                 "- worked in tipcalc: again")


def test_capture_sdd_turn_writes_one_pointer(tmp_path, monkeypatch):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    prompt, bullets = _run_capture(tmp_path, monkeypatch, repo / "src", MODEL_BULLETS)
    assert "REPO RULE" in prompt
    assert bullets == ["- worked in tipcalc: hardened the CLI entrypoint",
                       "- John wants a failing test before every fix"]


def test_capture_plain_repo_turn_unchanged(tmp_path, monkeypatch):
    repo = git_init(tmp_path / "plain")
    prompt, bullets = _run_capture(tmp_path, monkeypatch, repo, MODEL_BULLETS)
    assert "REPO RULE" not in prompt
    assert bullets == MODEL_BULLETS.splitlines()


def test_route_bullets_drops_pointer_once_written():
    assert tc.route_bullets(["- worked in tipcalc: more", "- a lesson (seen in tipcalc)"],
                            "tipcalc", pointer_done=True) == ["- a lesson (seen in tipcalc)"]
    assert tc.route_bullets(["- worked in tipcalc: more"], "tipcalc", pointer_done=True) == []


def test_capture_sdd_session_writes_pointer_once_across_turns(tmp_path, monkeypatch):
    """verify1 open item: N captured turns of one session gave N pointers in the daily log."""
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    _run_capture(tmp_path, monkeypatch, repo, "- worked in tipcalc: diagnosed the crash")
    _, bullets = _run_capture(tmp_path, monkeypatch, repo / "src", MODEL_BULLETS)
    assert bullets == ["- worked in tipcalc: diagnosed the crash",
                       "- John wants a failing test before every fix"]
    assert len(_blocks(tmp_path)) == 2
    # a later turn whose only bullet is the pointer appends nothing at all
    _, bullets = _run_capture(tmp_path, monkeypatch, repo, "- worked in tipcalc: again")
    assert len(_blocks(tmp_path)) == 2
    assert sum(bool(POINTER_RE.match(b)) for b in bullets) == 1


def test_capture_sdd_pointer_is_per_session_and_per_repo(tmp_path, monkeypatch):
    tip = sdd_repo_dir(tmp_path / "tipcalc")
    ledger = sdd_repo_dir(tmp_path / "ledger", origin="git@github.com:john/ledger.git")
    _run_capture(tmp_path, monkeypatch, tip, "- worked in tipcalc: a")
    _run_capture(tmp_path, monkeypatch, tip, "- worked in tipcalc: b", session_id="0123456789ab")
    _, bullets = _run_capture(tmp_path, monkeypatch, ledger, "- worked in ledger: c")
    assert bullets == ["- worked in tipcalc: a", "- worked in tipcalc: b", "- worked in ledger: c"]


def test_capture_sdd_turn_drops_leaking_bullets(tmp_path, monkeypatch):
    repo = _repo_with_specs(tmp_path)
    _, bullets = _run_capture(tmp_path, monkeypatch, repo,
                              "- worked in tipcalc: hardened the CLI\n"
                              "- scenario cli.no-args went red, then green\n"
                              "- John prefers exit codes documented in the README")
    assert bullets == ["- worked in tipcalc: hardened the CLI",
                       "- John prefers exit codes documented in the README"]


def test_capture_sdd_skip_writes_nothing(tmp_path, monkeypatch):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    prompt, _ = _run_capture(tmp_path, monkeypatch, repo, "- worked in tipcalc: a")
    assert "output exactly: SKIP" in prompt.split("REPO RULE", 1)[1]
    _run_capture(tmp_path, monkeypatch, repo, "SKIP", session_id="0123456789ab")
    assert len(_blocks(tmp_path)) == 1


# --- distill_session (batch writer) ------------------------------------------------------

MODEL_DISTILL = {
    "session_id": "x", "date": "2026-09-24",
    "summary": "John hardened the tipcalc entrypoint. Usage errors now exit 2.",
    "decisions": [{"content": "John runs red-first TDD in every repo (seen in tipcalc)",
                   "confidence": "high", "evidence": ["red first"]},
                  {"content": "John picks exit code 2 for usage errors (seen in tipcalc)",
                   "category": "technical", "evidence": ["Use 2, same as argparse."]},
                  {"content": "worked in tipcalc: stray pointer", "evidence": []}],
    "facts": [{"content": "tipcalc reads TIP_PERCENT", "category": "project", "evidence": []},
              {"content": "John wants red tests first (seen in tipcalc)",
               "category": "preference", "evidence": []}],
    "preferences": [{"content": "Rai should propose the scenario before code", "evidence": []}],
}


def test_distill_note_only_for_sdd():
    assert ds.sdd_note("") == ""
    note = ds.sdd_note("tipcalc")
    assert "REPO RULE" in note and '"summary" is that one pointer line' in note
    assert '"preferences" hold every preference or standing rule John states himself' in note
    assert ds.PROMPT.replace("__SDD__", "").count("REPO RULE") == 0


def _run_distill(tmp_path, monkeypatch, cwd, transcript_path=None, model=None):
    prompts = []

    def fake_run_claude(prompt, **kw):
        prompts.append(prompt)
        return json.dumps(model or MODEL_DISTILL)

    session = {
        "session_id": "sess-1", "timestamp": "2026-09-24T10:00:00Z", "cwd": str(cwd),
        "messages": [
            {"type": "user", "message": {"content": "harden the entrypoint please " * 10}},
            {"type": "assistant", "message": {"content": "hardened; usage errors exit 2 " * 10}},
        ],
    }
    if transcript_path is not None:
        session["transcript_path"] = str(transcript_path)
    sj, out = tmp_path / "sess-1.json", tmp_path / "sess-1.distill.json"
    sj.write_text(json.dumps(session))
    monkeypatch.setattr(ds, "run_claude", fake_run_claude)
    monkeypatch.setattr(sys, "argv", ["distill_session.py", "--session-json", str(sj), "--out", str(out)])
    assert ds.main() == 0
    return prompts, json.loads(out.read_text())


def test_distill_sdd_session_keeps_pointer_and_personal_only(tmp_path, monkeypatch):
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    prompts, d = _run_distill(tmp_path, monkeypatch, repo)
    assert all("REPO RULE" in p and '"decisions" is always []' in p for p in prompts)
    assert d["summary"] == "worked in tipcalc: John hardened the tipcalc entrypoint."
    assert d["sdd_repo"] == "tipcalc"
    assert [f["content"] for f in d["facts"]] == ["John wants red tests first (seen in tipcalc)"]
    assert d["decisions"] == []  # the repo's ADRs own them, whatever category the model used
    assert [p["content"] for p in d["preferences"]] == ["Rai should propose the scenario before code"]
    items = [d["summary"]] + [i["content"] for k in ("decisions", "facts", "preferences")
                              for i in d[k]]
    assert sum(bool(POINTER_RE.match(s)) for s in items) == 1


def test_distill_plain_session_unchanged(tmp_path, monkeypatch):
    repo = git_init(tmp_path / "plain")
    prompts, d = _run_distill(tmp_path, monkeypatch, repo)
    assert all("REPO RULE" not in p for p in prompts)
    assert "sdd_repo" not in d
    assert d["summary"] == MODEL_DISTILL["summary"]
    assert d["facts"] == MODEL_DISTILL["facts"] and d["decisions"] == MODEL_DISTILL["decisions"]


def test_distill_sessionend_json_with_empty_cwd_still_routes(tmp_path, monkeypatch):
    """verify3: archived SessionEnd-hook captures carry cwd '' (line 1 of a real transcript
    has no cwd), so the distiller resolves the cwd from the native transcript before applying
    the rule."""
    repo = sdd_repo_dir(tmp_path / "tipcalc")
    t = _native_transcript(tmp_path / "native.jsonl", str(repo / "src"))
    prompts, d = _run_distill(tmp_path, monkeypatch, "", transcript_path=t)
    assert all("REPO RULE" in p for p in prompts)
    assert d["sdd_repo"] == "tipcalc" and d["decisions"] == []
    assert d["summary"].startswith("worked in tipcalc: ")


def test_distill_sessionend_json_plain_repo_unchanged(tmp_path, monkeypatch):
    plain = git_init(tmp_path / "plain")
    t = _native_transcript(tmp_path / "native.jsonl", str(plain))
    prompts, d = _run_distill(tmp_path, monkeypatch, "", transcript_path=t)
    assert all("REPO RULE" not in p for p in prompts)
    assert "sdd_repo" not in d and d["summary"] == MODEL_DISTILL["summary"]


def test_distill_sdd_drops_items_and_evidence_naming_repo_specifics(tmp_path, monkeypatch):
    repo = _repo_with_specs(tmp_path)
    model = dict(MODEL_DISTILL, summary="Added scenario cli.no-args. More.", facts=[
        {"content": "Scenario cli.no-args guards a bare call", "category": "technical",
         "evidence": []},
        {"content": "Write the failing test before the fix (seen in tipcalc)",
         "category": "technical",
         "evidence": ["went red on cli.no-args", "watch its test fail, then fix"]}],
        preferences=[{"content": "John prefers exit codes documented in the README",
                      "evidence": ["I prefer exit codes documented in the README."]},
                     {"content": "Keep the guard in src/tipcalc/cli.py", "evidence": []}])
    _, d = _run_distill(tmp_path, monkeypatch, repo, model=model)
    assert d["summary"] == "worked in tipcalc: details live in the repo"
    assert d["facts"] == [{"content": "Write the failing test before the fix (seen in tipcalc)",
                           "category": "technical",
                           "evidence": ["watch its test fail, then fix"]}]
    assert d["preferences"] == [{"content": "John prefers exit codes documented in the README",
                                 "evidence": ["I prefer exit codes documented in the README."]}]
