"""Identity + Eval checks."""


import pytest

from conftest import hook_cmd, st
from sanity_checks.core import FAIL, PASS, WARN


BUDGET = ('IDENTITY_FILE_BUDGET = 4_096\nIDENTITY_TOTAL_BUDGET = 45056\n'
          'IDENTITY_BUDGET_EXEMPT = {"coding-format.md"}\n')


def _identity(w, rai=4, ana=1, size=100):
    w.write("helm/03-rai/hooks/session-start.py", BUDGET)
    for i in range(rai):
        w.write(f"helm/03-rai/identity/r{i}.md", "x" * size)
    for i in range(ana):
        w.write(f"helm/02-ana/identity/a{i}.md", "x" * size)


# ID-1 ──────────────────────────────────────────────────────────────────────────
def test_id_1_ok(w):
    _identity(w)
    assert st("ID-1").status == PASS


def test_id_1_fault_empty_file(w):
    _identity(w)
    w.write("helm/03-rai/identity/r0.md", "")
    assert st("ID-1").status == FAIL


def test_id_1_fault_dir_missing(w):
    _identity(w, ana=0)
    r = st("ID-1")
    assert r.status == FAIL and "ana:MISSING" in r.evidence


def test_id_1_fault_too_few(w):
    _identity(w, rai=2)
    assert st("ID-1").status == WARN


# ID-2: session-start, run exactly as registered ────────────────────────────────
def _session_start(w, body: str):
    w.settings({"SessionStart": [hook_cmd(w, "session-start")]})
    w.write("helm/03-rai/hooks/session-start.py", body)


def test_id_2_ok(w):
    _session_start(w, "print('=== Rai Identity Loaded ===\\n## Ai Steering Rules\\n## Memory')\n")
    assert st("ID-2").status == PASS


def test_id_2_ok_does_not_block_on_stdin(w):
    _session_start(w, "import sys\nsys.stdin.read()\nprint('Steering Identity Memory')\n")
    assert st("ID-2").status == PASS


def test_id_2_fault_blank(w):
    _session_start(w, "pass\n")
    assert st("ID-2").status == FAIL


def test_id_2_fault_crash(w):
    _session_start(w, "import sys\nsys.stderr.write('Traceback: boom\\n')\nsys.exit(1)\n")
    r = st("ID-2")
    assert r.status == FAIL and "boom" in r.evidence


def test_id_2_fault_internal_timeout(w):
    _session_start(w, "print('Rai identity load timed out (8s)')\n")
    r = st("ID-2")
    assert r.status == WARN and "8s timeout" in r.evidence


def test_id_2_fault_not_registered(w):
    w.settings({})
    assert st("ID-2").status == FAIL


def test_id_2_fault_sections_missing(w):
    _session_start(w, "print('something else entirely')\n")
    assert st("ID-2").status == WARN


# ID-3 ──────────────────────────────────────────────────────────────────────────
def test_id_3_ok(w):
    _identity(w)
    mt = max(p.stat().st_mtime for p in w.path("helm/03-rai/identity").glob("*.md"))
    w.json(".local/state/rai/runtime/identity-cache.json", {"max_mtime": mt})
    assert st("ID-3").status == PASS


def test_id_3_fault_unparseable(w):
    w.write(".local/state/rai/runtime/identity-cache.json", "{nope")
    assert st("ID-3").status == FAIL


def test_id_3_fault_drift(w):
    _identity(w)
    w.json(".local/state/rai/runtime/identity-cache.json", {"max_mtime": 1})
    assert st("ID-3").status == WARN


# ID-4 ──────────────────────────────────────────────────────────────────────────
def test_id_4_ok(w):
    _identity(w, size=3000)
    assert st("ID-4").status == PASS


def test_id_4_fault_file_over_4kb(w):
    _identity(w)
    w.write("helm/02-ana/identity/story.md", "x" * 5000)
    r = st("ID-4")
    assert r.status == WARN and "story.md" in r.evidence


def test_id_4_ok_exempt_rule_file(w):
    _identity(w)
    w.write("helm/03-rai/identity/coding-format.md", "x" * 5000)
    assert st("ID-4").status == PASS


def test_id_4_fault_total_over_budget(w):
    _identity(w, rai=12, ana=4, size=3000)  # 48,000B against 45,056B + 1,024B grace
    assert st("ID-4").status == WARN


# EVAL-1 ────────────────────────────────────────────────────────────────────────
GOLDEN = "helm/03-rai/semantic-memory/eval/golden.jsonl"


def _golden(w, rows=60, spec=1):
    w.jsonl(GOLDEN, [{"q": i} for i in range(rows)] + [{"kind": "freshness-spec"}] * spec)
    w.mkdir("helm/03-rai/semantic-memory/eval/reports")


def test_eval_1_ok(w):
    _golden(w)
    assert st("EVAL-1").status == PASS


def test_eval_1_fault_unparseable(w):
    _golden(w)
    w.write(GOLDEN, "{broken\n")
    assert st("EVAL-1").status == FAIL


@pytest.mark.parametrize("rows,spec", [(10, 1), (60, 0)])
def test_eval_1_fault_thin_or_malformed(w, rows, spec):
    _golden(w, rows=rows, spec=spec)
    assert st("EVAL-1").status == WARN


def test_eval_1_fault_missing(w):
    assert st("EVAL-1").status == WARN


def test_id_4_fault_budget_follows_session_start(w):
    """The budget comes from session-start.py: lowering it there makes ID-4 warn too."""
    _identity(w, size=3000)
    w.write("helm/03-rai/hooks/session-start.py", BUDGET.replace("45056", "10000"))
    assert st("ID-4").status == WARN


def test_id_4_fault_budget_unreadable(w):
    _identity(w)
    w.write("helm/03-rai/hooks/session-start.py", "print('no budget here')\n")
    r = st("ID-4")
    assert r.status == FAIL and "IDENTITY_FILE_BUDGET" in r.evidence
