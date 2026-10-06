"""
test_session_start_modes.py: session-start.py's two output modes.

Claude Code shows a SessionStart hook's output inline only up to 10,000 characters (measured
2026-10-02; past that it shows a 2 KB preview and a file path). So in Claude Code (no
RAI_HARNESS) the static parts load through ~/.claude/CLAUDE.md imports, and the hook prints only
the dynamic part, under CLAUDE_OUTPUT_BUDGET. Every other harness injects the output itself and
gets everything. The hook also keeps the generated imports file in step with the identity folders.

Hermetic: every path points into tmp_path; the orphan sweep, the embedding warmup and the
pending count are stubbed.

Run: uv run --with pytest pytest 03-rai/hooks/tests/test_session_start_modes.py -q -p no:cacheprovider
"""

import importlib.util
import signal
import sys
from datetime import date
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))


@pytest.fixture
def ss(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location("session_start_t", HOOKS / "session-start.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    signal.alarm(0)  # the hook arms an 8 s alarm at import
    rai = tmp_path / "helm" / "03-rai"
    ana = tmp_path / "helm" / "02-ana" / "identity"
    for d in (rai / "identity", ana, rai / "memory" / "state", rai / "semantic-memory" / "daily",
              tmp_path / "helm" / ".helm-index", rai / "skills", rai / "harness" / "claude-code",
              tmp_path / ".claude"):
        d.mkdir(parents=True)
    edge = rai / "harness" / "claude-code" / "user-instructions.md"
    edge.write_text("@~/helm/03-rai/AGENTS.md\n")
    (tmp_path / ".claude" / "CLAUDE.md").symlink_to(edge)
    (rai / "identity" / "working-memory.md").write_text("# Working Memory\nIDENT-RAI\n")
    (ana / "who-i-am.md").write_text("# Who I am\nIDENT-ANA\n")
    (rai / "memory" / "state" / "memory-block.md").write_text("## Memory (v3)\nMEM-BLOCK\n")
    (tmp_path / "helm" / ".helm-index" / "helm-index.md").write_text("# Helm index\nHELM-INDEX\n")
    daily = rai / "semantic-memory" / "daily" / f"{date.today().isoformat()}.md"
    daily.write_text("\n".join(f"- daily line {i} " + "x" * 120 for i in range(200)) + "\n- NEWEST-LINE\n")
    for name, value in {
        "PAI_DIR": rai, "IDENTITY_DIR": rai / "identity", "SKILLS_DIR": rai / "skills",
        "BRAIN_DIR": tmp_path / "helm", "TELOS_DIR": tmp_path / "helm" / "02-ana",
        "PENDING_DIR": rai / "semantic-memory" / "pending",
        "IDENTITY_CACHE": tmp_path / "identity-cache.json",
        "HELM_INDEX_PATH": tmp_path / "helm" / ".helm-index" / "helm-index.md",
        "IDENTITY_DIRS": [rai / "identity", ana],
        "MEMORY_BLOCK": rai / "memory" / "state" / "memory-block.md",
        "DAILY_DIR": rai / "semantic-memory" / "daily",
        "IMPORTS_FILE": rai / "harness" / "claude-code" / "identity-imports.md",
        "CLAUDE_EDGE": edge,
        "CLAUDE_MD": tmp_path / ".claude" / "CLAUDE.md",
    }.items():
        monkeypatch.setattr(mod, name, value)
    monkeypatch.setattr(mod, "_sweep_orphans_safe", lambda: {})
    monkeypatch.setattr(mod, "_warm_embeddings", lambda: None)
    monkeypatch.setattr(mod, "_count_pending", lambda: 0)
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    return mod


def run(ss, capsys, monkeypatch, harness=None):
    if harness:
        monkeypatch.setenv("RAI_HARNESS", harness)
    else:
        monkeypatch.delenv("RAI_HARNESS", raising=False)
    ss.main()
    return capsys.readouterr().out


def test_claude_code_gets_only_the_dynamic_part_within_budget(ss, capsys, monkeypatch):
    out = run(ss, capsys, monkeypatch)
    assert len(out) <= ss.CLAUDE_OUTPUT_BUDGET < 10_000
    for static in ("IDENT-RAI", "IDENT-ANA", "MEM-BLOCK", "HELM-INDEX"):
        assert static not in out  # these arrive through the CLAUDE.md imports
    assert "NEWEST-LINE" in out  # the daily tail keeps its newest lines
    assert "[rai]" in out and "identity=imported" in out


def test_other_harnesses_get_everything(ss, capsys, monkeypatch):
    out = run(ss, capsys, monkeypatch, harness="pi")
    for part in ("IDENT-RAI", "IDENT-ANA", "MEM-BLOCK", "HELM-INDEX", "NEWEST-LINE"):
        assert part in out


def test_imports_file_lists_every_static_part(ss, capsys, monkeypatch):
    run(ss, capsys, monkeypatch, harness="opencode")  # any harness keeps it current
    text = ss.IMPORTS_FILE.read_text()
    imports = [l[1:] for l in text.splitlines() if l.startswith("@")]
    assert [Path(p).name for p in imports] == ["working-memory.md", "who-i-am.md", "memory-block.md", "helm-index.md"]


def test_imports_file_follows_the_identity_folders(ss, capsys, monkeypatch):
    run(ss, capsys, monkeypatch)
    (ss.IDENTITY_DIR / "new-file.md").write_text("new")
    run(ss, capsys, monkeypatch)
    assert "new-file.md" in ss.IMPORTS_FILE.read_text()


def test_imports_use_home_relative_paths(ss, capsys, monkeypatch):
    monkeypatch.setattr(ss.Path, "home", classmethod(lambda cls: ss.BRAIN_DIR.parent))
    run(ss, capsys, monkeypatch)
    assert all(l.startswith("@~/") for l in ss.IMPORTS_FILE.read_text().splitlines() if l.startswith("@"))


def test_a_big_codemap_becomes_a_pointer_in_claude_code(ss, capsys, monkeypatch, tmp_path):
    cm = tmp_path / "repo" / ".codemap" / "codemap.md"
    cm.parent.mkdir(parents=True)
    cm.write_text("CODEMAP-BODY " * 1200)  # ~15 KB, under its own 20 KB cap
    monkeypatch.chdir(tmp_path / "repo")
    out = run(ss, capsys, monkeypatch)
    assert len(out) <= ss.CLAUDE_OUTPUT_BUDGET
    assert "CODEMAP-BODY" not in out and str(cm) in out


def test_a_machine_not_yet_relinked_gets_everything(ss, capsys, monkeypatch):
    ss.CLAUDE_MD.unlink()
    ss.CLAUDE_MD.symlink_to(ss.PAI_DIR / "AGENTS.md")  # the old link
    out = run(ss, capsys, monkeypatch)
    assert "IDENT-RAI" in out and "MEM-BLOCK" in out  # never silently lost


def test_a_removed_edge_is_never_recreated(ss, capsys, monkeypatch):
    import shutil
    shutil.rmtree(ss.IMPORTS_FILE.parent)
    out = run(ss, capsys, monkeypatch, harness="pi")
    assert not ss.IMPORTS_FILE.parent.exists() and "IDENT-RAI" in out


def test_the_cache_refreshes_in_claude_mode(ss, capsys, monkeypatch):
    run(ss, capsys, monkeypatch)
    assert ss.IDENTITY_CACHE.exists()


def test_huge_banners_still_fit(ss):
    head = ["=== start ===", "## BRAIN SANITY\n" + "\n".join("  x " + "y" * 900 for _ in range(40))]
    out = ss._fit_claude(head, None, "## Live log\n- a", "[rai] status")
    assert len(out) <= ss.CLAUDE_OUTPUT_BUDGET


def test_yesterdays_lines_keep_their_label(ss):
    daily = "## Live log (turn-capture)\n_2026-10-01 (yesterday):_\n- old one\n- old two\n\n- today one"
    out = ss._fit_claude(["=== start ==="], None, daily, "[rai] status")
    assert "(yesterday):_\n- old one" in out and out.index("(yesterday)") < out.index("- today one")
