"""project-init v3, milestone M5: the lifecycle commands of project.py.

change, backlog, approve, merge, abandon, doctor, status --merge and --audit, and release run
for real on the tipcalc fixture, with no remote. The remote path of merge (design D1, option 1)
is checked by `merge --dry-run` against a local bare origin and by a unit test of its plan,
because nothing here may create a GitHub repo.

The session fixture builds tipcalc with fixtures/make_gates.sh (branch plan/project-init), adds
what project-init renders beside the gates (the [tool.git-cliff] config from
templates/pyproject-additions.toml, the typed env contract, the mission one-liner as the
description), turns the hooks on, and lands plan/project-init with `project.py merge`: the G1
merge. Every other test works on a copy of that adopted repo. The M5 bullets of the design
(03-rai/skills/project-init/DESIGN.md, section 12) map to the tests named for them.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
PROJECT_PY = SKILL / "templates" / "scripts" / "project.py"
MAKE_GATES = TESTS / "fixtures" / "make_gates.sh"
PRODUCT_TEMPLATES = SKILL.parents[2] / "12-system" / "templates" / "sdd"
TIPCALC_SOURCE = Path(os.environ.get("TIPCALC_SOURCE", Path.home() / "projects" / "tipcalc"))
TODAY = datetime.now().astimezone().date().isoformat()
MERGED_BY = "Merged-By: mise run merge"
CHANGE = f"specs/changes/{TODAY}-split-bill"
ENV_EXAMPLE = """\
# Environment contract for tipcalc: every variable the app reads, typed. Copy to .env (gitignored).
# NAME | kind | type | required | default | notes          (an empty value means unset: the default applies)
# TIPCALC_DEFAULT_PERCENT | knob | float 0..100 | no | 15 | tip percent when none is given
#TIPCALC_DEFAULT_PERCENT=15
"""


def clean_env(trusted: Path) -> dict[str, str]:
    drop = ("GIT_", "PYTEST_", "GITHUB_", "PROJECT_MERGE", "TIPCALC_", "MISE_DISABLE_TOOLS")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop)}
    for key in ("VIRTUAL_ENV", "UV_PROJECT_ENVIRONMENT", "PYTHONPATH"):
        env.pop(key, None)
    env.update(
        GIT_CONFIG_GLOBAL=os.devnull,
        GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="Test Author",
        GIT_AUTHOR_EMAIL="author@example.com",
        GIT_COMMITTER_NAME="Test Author",
        GIT_COMMITTER_EMAIL="author@example.com",
        MISE_TRUSTED_CONFIG_PATHS=str(trusted),  # the hooks and merge run mise in the fixture
    )
    return env


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


class Repo:
    def __init__(self, path: Path, trusted: Path) -> None:
        self.path = path
        self.trusted = trusted

    def run(
        self, *argv: str, env: dict[str, str] | None = None, cwd: Path | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=cwd or self.path,
            capture_output=True,
            text=True,
            check=False,
            env={**clean_env(self.trusted), **(env or {})},
            timeout=900,
        )

    def git(self, *args: str, cwd: Path | None = None) -> str:
        result = self.run("git", *args, cwd=cwd)
        assert result.returncode == 0, output(result)
        return result.stdout

    def project(
        self, *args: str, cwd: Path | None = None, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return self.run(
            sys.executable, str(self.path / "scripts" / "project.py"), *args, cwd=cwd, env=env
        )

    def write(self, rel: str, text: str) -> None:
        path = self.path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def append(self, rel: str, text: str) -> None:
        with (self.path / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self, message: str, *extra: str, cwd: Path | None = None) -> None:
        """git add -A and commit with the hooks on."""
        self.git("add", "-A", cwd=cwd)
        result = self.run("git", "commit", "-q", "-m", message, *extra, cwd=cwd)
        assert result.returncode == 0, output(result)

    def head(self, ref: str = "HEAD") -> str:
        return self.git("rev-parse", ref).strip()

    def branch(self) -> str:
        return self.git("branch", "--show-current").strip()

    def show(self, ref: str, path: str) -> str:
        return self.git("show", f"{ref}:{path}")


@dataclass
class Adopted:
    path: Path
    g1: subprocess.CompletedProcess[str]
    old_main: str


@pytest.fixture(scope="session")
def adopted(tmp_path_factory: pytest.TempPathFactory) -> Adopted:
    return adopt(tmp_path_factory)


def adopt(tmp_path_factory: pytest.TempPathFactory) -> Adopted:
    """The adopted tipcalc repo the session fixture holds (test_proof.py builds its own)."""
    if not (TIPCALC_SOURCE / ".git").exists():
        pytest.skip(f"no tipcalc repo at {TIPCALC_SOURCE} (set TIPCALC_SOURCE)")
    base = tmp_path_factory.mktemp("m5")
    dest = base / "tipcalc"
    built = subprocess.run(
        ["sh", str(MAKE_GATES), str(dest), str(TIPCALC_SOURCE)],
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(base),
    )
    assert built.returncode == 0, output(built)
    repo = Repo(dest, base)
    additions = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    cliff = additions[additions.index("# CHANGELOG.md in Keep") :]
    pyproject = (dest / "pyproject.toml").read_text(encoding="utf-8")
    pyproject = re.sub(
        r'(?m)^description = ".*"$',
        'description = "Tiny CLI that prints the tip for a bill."',
        pyproject,
    )
    repo.write("pyproject.toml", pyproject + "\n" + cliff)
    repo.write(".env.example", ENV_EXAMPLE)
    repo.git("add", "-A")
    repo.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "chore(init): the rest")
    installed = repo.project("hook", "install")
    assert installed.returncode == 0, output(installed)
    old_main = repo.head("main")
    g1 = repo.project("merge")
    assert g1.returncode == 0, output(g1)
    return Adopted(dest, g1, old_main)


@pytest.fixture
def repo(adopted: Adopted, tmp_path: Path) -> Repo:
    """A copy of the adopted repo on main (no .venv: its editable install points at the
    original). The git config the hooks need travels in .git/config."""
    dest = tmp_path / "tipcalc"
    shutil.copytree(
        adopted.path, dest, symlinks=True, ignore=shutil.ignore_patterns(".venv", ".cache")
    )
    return Repo(dest, tmp_path)


def load_project_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("project_lifecycle_under_test", PROJECT_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in templates/
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = keep
    return module


# ---------------------------------------------------------------- the feat change used below

REQUIREMENTS = f"""\
---
change: "{TODAY}-split-bill"
lane: feat
status: draft                                   # draft | approved | done
roadmap: "split-bill"
title: "feat(cli): split the bill between people"   # becomes the squash commit + CHANGELOG line
---
## Why
Groups want each person's share of the bill and the tip.
## Scope
In: a --split flag. Out: uneven splits.
## Decisions
- `--split N` divides the bill plus the tip evenly. Rejected: a new command, it repeats parsing.
## Context
- argv parsing in `main()`.
## Rollback
revert: a new CLI option and nothing stored; a revert of the squash takes it away
"""
PLAN = """\
## G1 split | cli.split-bill | risk: low | parallel: yes
Files: src/tipcalc/__init__.py, tests/test_split.py
"""
VALIDATION = """\
## Review focus   (implied inputs the spec never named; each -> a scenario, or "none: <reason>")
- zero people -> none: out of scope, the backlog holds it
## Run it   (optional, feat only: what tests cannot reach, e.g. a real server; merge executes each row)
| command | exit | stdout contains | stderr contains |
|---|---|---|---|
| `uv run --locked tipcalc 100 --split 4` | 0 | each: 28.75 | |
## Human checks   (<=3; merge asks with a TTY, or records your --attest)
- The split output reads clearly.
"""
NO_CHECKS = "## Human checks   (none)\n"
SCENARIO = """
## Requirement: Split the bill
The CLI SHALL split the bill and the tip evenly between people when asked.

### Scenario: cli.split-bill
- WHEN the user runs `tipcalc 100 --split 4`
- THEN stdout is `tip: 15.0` then `each: 28.75`, and the exit code is 0
"""
TEST_SPLIT = """\
from __future__ import annotations

import pytest
from helpers import tipcalc


@pytest.mark.spec("cli.split-bill")
def test_split_bill() -> None:
    r = tipcalc("100", "--split", "4")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.0\\neach: 28.75\\n"
"""
SPLIT_CODE = """\
import os
import sys


def tip(bill: float, percent: float) -> float:
    return round(bill * percent / 100, 2)


def main() -> None:
    percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))
    bill = float(sys.argv[1])
    amount = tip(bill, percent)
    print(f"tip: {amount}")
    if len(sys.argv) > 3 and sys.argv[2] == "--split":
        print(f"each: {round((bill + amount) / int(sys.argv[3]), 2)}")
"""


def talk(repo: Repo) -> None:
    """What talk writes for split-bill: the three files and the new scenario (uncommitted)."""
    repo.write(f"{CHANGE}/requirements.md", REQUIREMENTS)
    repo.write(f"{CHANGE}/plan.md", PLAN)
    repo.write(f"{CHANGE}/validation.md", VALIDATION)
    repo.append("specs/capabilities/cli.md", SCENARIO)


def compile_group(repo: Repo) -> None:
    """G1 on green: the tagged test and the code, one commit with its Spec: trailer."""
    repo.write("tests/test_split.py", TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", SPLIT_CODE)
    repo.commit("feat(cli): split the bill", "--trailer", "Spec: cli.split-bill")


def confident(repo: Repo, *groups: str) -> None:
    """validate's confidence line for each group (G1 by default), which merge wants for every
    group of a feat change (design C.5)."""
    for group in groups or ("G1",):
        why = "every scenario of the group has a passing test"
        result = repo.project("proof", "confidence", group, "high", "--", why)
        assert result.returncode == 0, output(result)


def chore_branch(repo: Repo, slug: str) -> None:
    """chore/<slug> with one docs commit on it."""
    started = repo.project("change", slug, "--lane", "chore")
    assert started.returncode == 0, output(started)
    repo.append("README.md", f"\nA note for {slug}.\n")
    repo.commit(f"docs: a note for {slug}")


def trailers(repo: Repo, ref: str) -> str:
    return repo.git("log", "-1", "--format=%(trailers:only,unfold)", ref)


# ---------------------------------------------------------------- G1: the adoption lands


def test_g1_merge_lands_the_adoption_branch(adopted: Adopted, tmp_path: Path) -> None:
    repo = Repo(adopted.path, tmp_path)
    text = output(adopted.g1)
    assert "guards 1/1 pass, gaps 5/5 xfail, tests 0 -> 6" in text
    assert "gate files ........ ok new with the adoption" in text
    assert "branch plan/project-init deleted" in text
    assert repo.branch() == "main"
    assert repo.git("branch", "--list", "plan/*").strip() == ""
    assert repo.git("status", "--porcelain").strip() == ""
    log = repo.git("log", "--first-parent", "--format=%s", "main").splitlines()
    assert log[0] == "chore(init): project-init v3 gates"
    assert repo.head("main~1") == adopted.old_main
    assert MERGED_BY in trailers(repo, "main")
    changelog = repo.show("main", "CHANGELOG.md")
    assert "## [Unreleased]\n\n### Added\n\n- initial tipcalc cli\n" in changelog
    assert "Features" not in changelog  # the project's config, not git-cliff's default
    audit = repo.project("status", "--audit")
    assert "audit main: ok (1 commit since adoption" in audit.stdout, output(audit)


# ---------------------------------------------------------------- change


def test_change_on_a_dirty_tree_lists_the_files(repo: Repo) -> None:
    repo.write("junk.txt", "x\n")
    repo.append("README.md", "\nedited\n")
    repo.write("specs/backlog/2026-01-01-parked.md", "an idea\n")  # untracked backlog: exempt
    result = repo.project("change", "split-bill")
    assert result.returncode == 1
    assert "the tree is dirty (2 files)" in result.stdout, output(result)
    assert "  junk.txt" in result.stdout
    assert "  README.md" in result.stdout
    assert "parked" not in result.stdout
    assert repo.branch() == "main"
    repo.git("checkout", "--", "README.md")
    (repo.path / "junk.txt").unlink()
    result = repo.project("change", "split-bill")
    assert result.returncode == 0, output(result)
    assert repo.git("status", "--porcelain").strip() == "?? specs/backlog/2026-01-01-parked.md"


def test_change_starts_feat_with_its_three_files_in_draft(repo: Repo) -> None:
    main = repo.head("main")
    result = repo.project("change", "split-bill", "--lane", "feat")
    assert result.returncode == 0, output(result)
    assert repo.branch() == "feat/split-bill"
    for name in ("requirements.md", "plan.md", "validation.md"):
        assert (repo.path / CHANGE / name).is_file()
    requirements = (repo.path / CHANGE / "requirements.md").read_text(encoding="utf-8")
    assert f'change: "{TODAY}-split-bill"' in requirements
    assert re.search(r"(?m)^status: draft\b", requirements)
    assert 'roadmap: "split-bill"' in requirements
    assert repo.git("log", "-1", "--format=%s").strip() == "spec(split-bill): start"
    assert repo.head("HEAD~1") == main
    assert repo.git("status", "--porcelain").strip() == ""


def test_a_second_change_while_one_is_open_is_refused(repo: Repo) -> None:
    assert repo.project("change", "split-bill").returncode == 0
    result = repo.project("change", "rounding", "--lane", "chg")
    assert result.returncode == 1
    assert "I8: a change is open (feat/split-bill)" in result.stdout, output(result)
    repo.git("switch", "-q", "main")
    result = repo.project("change", "rounding", "--lane", "chg")
    assert result.returncode == 1, output(result)
    assert "I8" in result.stdout
    assert repo.git("branch", "--list", "chg/*").strip() == ""


def test_an_empty_branch_checked_out_in_a_worktree_is_an_open_change(repo: Repo) -> None:
    result = repo.project("change", "typo", "--lane", "fix", "--hotfix")
    assert result.returncode == 0, output(result)
    assert "this checkout is untouched" in result.stdout  # no change is open here
    result = repo.project("change", "split-bill")
    assert result.returncode == 1
    assert "I8: a change is open (fix/typo)" in result.stdout, output(result)


def commit_tree(repo: Repo, onto: str, message: str, *merged: str) -> str:
    """A commit on top of onto with onto's tree (a merge of the merged commits into it when
    any are given, listed first), made with no hook: a branch from outside the tool."""
    parents = [arg for parent in (*merged, onto) for arg in ("-p", parent)]
    return repo.git("commit-tree", f"{onto}^{{tree}}", *parents, "-m", message).strip()


def test_a_branch_from_before_the_adoption_is_no_open_change(repo: Repo, adopted: Adopted) -> None:
    """Run B: a lane-named branch that forks before the adoption (a v2 chore/project-init that
    was never merged, an old feat/ branch) is no change `change` opened. I8 skips it, status
    and session-start say what `change` does, and a merge of main into it makes it a change."""
    old = commit_tree(repo, adopted.old_main, "chore: project init (memory, workflow, gates)")
    repo.git("branch", "chore/project-init", old)
    repo.git("branch", "feat/merged-long-ago", adopted.old_main)  # merged: never an open change
    status = repo.project("status")
    assert "[tipcalc] main | no open change" in status.stdout, output(status)
    assert "from before adoption: chore/project-init: not changes, so I8 skips them" in (
        status.stdout
    )
    assert "merged-long-ago" not in status.stdout
    start = repo.project("hook", "session-start")
    assert "[tipcalc] main | no open change |" in start.stdout, output(start)

    started = repo.project("change", "split-bill")
    assert started.returncode == 0, output(started)
    refused = repo.project("change", "rounding", "--lane", "chg")
    assert refused.returncode == 1
    assert "I8: a change is open (feat/split-bill);" in refused.stdout, output(refused)
    repo.git("switch", "-q", "main")
    status = repo.project("status")
    assert "[tipcalc] main | change open on feat/split-bill" in status.stdout, output(status)
    assert "next: finish feat/split-bill (`git switch feat/split-bill`" in status.stdout
    assert "next roadmap item" not in status.stdout  # change would refuse to start it
    start = repo.project("hook", "session-start")
    assert "[tipcalc] main | change open on feat/split-bill |" in start.stdout, output(start)
    assert "next: finish feat/split-bill first" in start.stdout

    repo.git("branch", "-D", "feat/split-bill")
    main = repo.head("main")
    merged = commit_tree(repo, main, "Merge branch 'main' into chore/project-init", old)
    repo.git("branch", "-f", "chore/project-init", merged)
    resumed = repo.project("change", "split-bill")
    assert resumed.returncode == 1
    assert "I8: a change is open (chore/project-init);" in resumed.stdout, output(resumed)
    assert "from before adoption" not in repo.project("status").stdout


def test_change_refuses_what_is_not_a_slug(repo: Repo) -> None:
    bad = ["split bill", "Split-Bill", "split_bill", "../evil", "split-", "split--bill", "x--g1"]
    for slug in [*bad, f"{TODAY}-split"]:
        result = repo.project("change", slug)
        assert result.returncode == 2, (slug, output(result))
    dated = repo.project("change", f"{TODAY}-split")
    assert "starts with a date; drop it" in dated.stderr, output(dated)
    assert repo.branch() == "main"
    assert repo.git("branch", "--list").strip() == "* main"


def test_hotfix_worktree_lands_with_merge_branch(repo: Repo) -> None:
    assert repo.project("change", "split-bill").returncode == 0
    main = repo.head("main")
    result = repo.project("change", "typo", "--lane", "fix", "--hotfix")
    assert result.returncode == 0, output(result)
    sibling = repo.path.parent / "tipcalc-fix-typo"
    assert sibling.is_dir()
    assert repo.git("branch", "--show-current", cwd=sibling).strip() == "fix/typo"
    assert repo.head("fix/typo") == main
    assert repo.branch() == "feat/split-bill"  # the open change is untouched
    assert "the change open here (feat/split-bill) is untouched" in result.stdout
    readme = (sibling / "README.md").read_text(encoding="utf-8")
    (sibling / "README.md").write_text(readme.replace("Tiny", "A tiny"), encoding="utf-8")
    repo.commit("fix(docs): readme wording", cwd=sibling)

    result = repo.project("merge", "--branch", "fix/typo")
    assert result.returncode == 0, output(result)
    assert repo.git("log", "-1", "--format=%s", "main").strip() == "fix(docs): readme wording"
    assert repo.head("main~1") == main
    assert MERGED_BY in trailers(repo, "main")
    assert not sibling.exists()
    assert repo.git("branch", "--list", "fix/*").strip() == ""
    assert "### Fixed\n\n- readme wording (docs)\n" in repo.show("main", "CHANGELOG.md")
    assert repo.branch() == "feat/split-bill"
    status = repo.project("status")
    assert "main moved: run git merge main" in status.stdout, output(status)


def test_lane_ratchet_only_gets_heavier(repo: Repo) -> None:
    assert repo.project("change", "rounding", "--lane", "chg").returncode == 0
    repo.append("README.md", "\nrounding\n")
    repo.commit("docs: rounding note")
    result = repo.project("change", "rounding", "--lane", "feat")
    assert result.returncode == 0, output(result)
    assert repo.branch() == "feat/rounding"
    assert (repo.path / f"specs/changes/{TODAY}-rounding/requirements.md").is_file()
    subject = repo.git("log", "-1", "--format=%s").strip()
    assert subject == "spec(rounding): ratchet chg to feat"
    result = repo.project("change", "rounding", "--lane", "chore")
    assert result.returncode == 1
    assert "a lane only gets heavier: feat/ to chore/ is refused" in result.stdout


# ---------------------------------------------------------------- backlog


def test_backlog_parks_an_idea_and_a_spike_gets_a_scratch_worktree(repo: Repo) -> None:
    result = repo.project("backlog", "percent", "rounding")
    assert result.returncode == 0, output(result)
    item = repo.path / f"specs/backlog/{TODAY}-percent-rounding.md"
    text = item.read_text(encoding="utf-8")
    assert text.startswith("---\nstatus: open ")
    assert "\n# percent rounding\n" in text
    status = repo.git("status", "--porcelain").strip()
    assert status == f"?? specs/backlog/{TODAY}-percent-rounding.md"  # never committed here
    again = repo.project("backlog", "percent", "rounding")
    assert again.returncode == 1

    result = repo.project("backlog", "cache", "idea", "--spike")
    assert result.returncode == 0, output(result)
    spike = repo.path.parent / "tipcalc-spike-cache-idea"
    assert spike.is_dir()
    assert repo.git("rev-parse", "HEAD", cwd=spike).strip() == repo.head("main")
    assert repo.git("branch", "--show-current", cwd=spike).strip() == ""  # detached
    text = (repo.path / f"specs/backlog/{TODAY}-cache-idea.md").read_text(encoding="utf-8")
    assert "# Spike: cache idea" in text
    assert f"git worktree remove --force {spike}" in text
    # parked ideas never block the next change
    assert repo.project("change", "split-bill").returncode == 0


# ---------------------------------------------------------------- approve and merge (feat)


def test_feat_change_from_approve_to_merge(repo: Repo) -> None:
    old_main = repo.head("main")
    old_changelog = repo.show("main", "CHANGELOG.md")
    assert repo.project("change", "split-bill").returncode == 0

    # approve: with lint errors (the templates are not filled yet)
    result = repo.project("approve")
    assert result.returncode == 1
    assert "unfilled placeholder {WHY}" in result.stdout, output(result)
    assert "approve: refused" in result.stdout

    # approve: clean
    talk(repo)
    result = repo.project("approve")
    assert result.returncode == 0, output(result)
    assert repo.git("log", "-1", "--format=%s").strip() == "spec(split-bill): approve"
    approved = trailers(repo, "HEAD")
    assert re.search(r"(?m)^Spec-Approved: sha256:[0-9a-f]{64}$", approved), approved
    assert "status: approved" in repo.show("HEAD", f"{CHANGE}/requirements.md")
    assert repo.git("status", "--porcelain").strip() == ""

    # --parallel: a worker branch for a `parallel: yes` group of the approved plan
    result = repo.project("change", "split-bill--g1", "--parallel")
    assert result.returncode == 0, output(result)
    assert repo.head("feat/split-bill--g1") == repo.head("feat/split-bill")
    assert repo.branch() == "feat/split-bill"
    confident(repo)  # validate's line; merge wants one per group

    # merge with a pending scenario
    result = repo.project("merge", "--attest")
    assert result.returncode == 1
    assert "not proven yet: cli.split-bill" in result.stdout, output(result)
    assert "cli.split-bill: no linked test" in result.stdout
    assert repo.head("main") == old_main

    # merge with a human check, no terminal and no --attest
    compile_group(repo)
    result = repo.project("merge")
    assert result.returncode == 1
    assert "human checks ...... FAIL 1 check and no terminal to ask in" in result.stdout
    assert "- The split output reads clearly." in result.stdout
    assert repo.head("main") == old_main

    # status --merge: the whole Definition of Done, read-only
    tip = repo.head()
    result = repo.project("status", "--merge")
    assert result.returncode == 0, output(result)
    assert "prove-red ......... ok 1/1 red on base (1 assertion)" in result.stdout
    assert "run it ............ ok 1/1 rows match" in result.stdout
    assert "human checks ...... for a human" in result.stdout
    assert "amended after approval .. ok none" in result.stdout
    assert "lane rules ........ ok I6 approve hash, I12 spec before code" in result.stdout
    assert "would land" in result.stdout
    assert repo.head() == tip
    assert repo.git("status", "--porcelain").strip() == ""

    # validate's close: a dismissed finding's reason in an empty commit (validate.md outcome 3)
    dismissed = "Dismissed: tests/test_split.py:4 split of 0 people: the CLI never asks for 0"
    repo.commit("test(split-bill): validate", "-m", dismissed, "--allow-empty")

    # merge --attest after green
    result = repo.project("merge", "--attest")
    assert result.returncode == 0, output(result)
    lines = result.stdout.rstrip().splitlines()
    assert lines[-2].startswith('  next .............. entrypoint-hardening "clear errors')
    assert "Still right? If not: /sdd replan" in lines[-2]
    assert lines[-1] == "  now ............... /clear"
    assert "branch feat/split-bill--g1 deleted" in result.stdout  # its work landed with it
    assert repo.branch() == "main"
    assert repo.git("branch", "--list", "feat/*").strip() == ""
    assert repo.git("status", "--porcelain").strip() == ""
    assert repo.head("main~1") == old_main  # one squash commit
    body = repo.git("log", "-1", "--format=%B", "main")
    assert body.startswith("feat(cli): split the bill between people\n")
    assert "Scenarios added: cli.split-bill" in body
    assert "prove-red against" in body and "cli.split-bill red (assert" in body
    assert "The split output reads clearly. (attested by Test Author, --attest)" in body
    # the branch is gone after the squash: its dismissal reasons live on in the squash body
    assert f"Findings dismissed at validate:\n  {dismissed}\n" in body
    assert body.rstrip().endswith(MERGED_BY)
    assert MERGED_BY in trailers(repo, "main")
    assert "- [x] split-bill: split the bill" in repo.show("main", "specs/roadmap.md")
    requirements = repo.show("main", f"{CHANGE}/requirements.md")
    assert re.search(r"(?m)^status: done\b", requirements)
    new_changelog = repo.show("main", "CHANGELOG.md")
    added = [
        line
        for line in new_changelog.splitlines()
        if line not in old_changelog.splitlines() and line.strip()
    ]
    assert added == ["- split the bill between people (cli)"]
    assert new_changelog.index("- split the bill") > new_changelog.index("## [Unreleased]")
    verify = repo.run("mise", "run", "verify")  # main after the merge passes its own gate
    assert verify.returncode == 0, output(verify)
    audit = repo.project("status", "--audit")
    assert "audit main: ok (2 commits since adoption" in audit.stdout, output(audit)


def test_the_squash_keeps_the_prose_of_the_commit_its_subject_comes_from(repo: Repo) -> None:
    """Run B: the squash deletes the branch, so the body of the commit the squash subject
    comes from (the P7 ship commit: the P5 results, N21) moves into the squash body. Its
    trailer block stays out, and so does a later commit's body."""
    assert repo.project("change", "rounding-note", "--lane", "chore").returncode == 0
    repo.append("README.md", "\nMoney is rounded to cents.\n")
    body = "P5 selftest: 12 of 13 checks green.\n- mise run doctor: green\nHappy path: 100 -> 15.0"
    repo.commit("docs: say where money is rounded", "-m", body, "--trailer", "Refs: rounding")
    repo.append("README.md", "\nA second note.\n")
    repo.commit("docs: a second note", "-m", "Second body, not the subject's.")
    merged = repo.project("merge")
    assert merged.returncode == 0, output(merged)
    message = repo.git("log", "-1", "--format=%B", "main")
    assert message.startswith(
        "docs: say where money is rounded\n\n"
        "P5 selftest: 12 of 13 checks green.\n- mise run doctor: green\n"
        "Happy path: 100 -> 15.0\n\nBranch: chore/rounding-note\n"
    ), message
    assert "Refs: rounding" not in message
    assert "Second body" not in message
    assert message.rstrip().endswith(MERGED_BY)


def test_merge_allow_lets_a_human_accept_a_failed_proof(repo: Repo) -> None:
    """merge -- --allow <id> --reason: the human-only escape for a prove-red FAIL, printed into
    the squash body."""
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    plain = VALIDATION.split("## Run it")[0] + "## Human checks   (none)\n"
    repo.write(f"{CHANGE}/validation.md", plain)
    assert repo.project("approve").returncode == 0
    old_output = TEST_SPLIT.replace(
        'assert r.stdout == "tip: 15.0\\neach: 28.75\\n"', 'assert r.stdout.startswith("tip: ")'
    )
    repo.write("tests/test_split.py", old_output)
    repo.commit("test(cli): split output starts with the tip")
    confident(repo)
    result = repo.project("merge")
    assert result.returncode == 1
    assert "cli.split-bill passes on the old code: it pins nothing new" in result.stdout
    result = repo.project("merge", "--allow", "cli.split-bill")
    assert result.returncode == 2
    assert "--allow needs --reason" in result.stderr
    result = repo.project("merge", "--reason", "no id named")
    assert result.returncode == 2
    assert "--reason goes with --allow <id>" in result.stderr
    why = "the split lands in the next change"
    result = repo.project("merge", "--allow", "cli.split-bill", "--reason", why)
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    assert "  allowed cli.split-bill passes on the old code" in body
    assert f"(allowed by Test Author: {why})" in body


def test_merge_refuses_code_committed_before_approve(repo: Repo) -> None:
    """I12: the approve commit comes before the first commit that touches src."""
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    repo.write("tests/test_split.py", TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", SPLIT_CODE)
    repo.git("add", "-A", "--", "src", "tests", "specs/capabilities")
    committed = repo.run(
        "git", "commit", "-q", "-m", "feat(cli): split early", "--trailer", "Spec: cli.split-bill"
    )
    assert committed.returncode == 0, output(committed)
    assert repo.project("approve").returncode == 0
    result = repo.project("merge", "--attest")
    assert result.returncode == 1
    assert "I12:" in result.stdout and "before the approve commit" in result.stdout, output(result)


def test_merge_refuses_code_from_before_the_change_folder(repo: Repo) -> None:
    """I12 on a branch that did not ratchet: code older than the change folder (a history
    written by hand) is refused like code older than approve."""
    repo.git("switch", "-q", "--no-track", "-c", "feat/split-bill", "main")
    repo.append("specs/capabilities/cli.md", SCENARIO)
    repo.write("tests/test_split.py", TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", SPLIT_CODE)
    repo.commit("feat(cli): split early", "--trailer", "Spec: cli.split-bill")
    code = repo.head()
    repo.write(f"{CHANGE}/requirements.md", REQUIREMENTS)
    repo.write(f"{CHANGE}/plan.md", PLAN)
    repo.write(f"{CHANGE}/validation.md", VALIDATION)
    repo.commit("spec(split-bill): start")
    result = repo.project("approve")
    assert result.returncode == 0, output(result)
    assert f"warn: {code[:10]} touched src before this approve; merge refuses it" in result.stdout
    result = repo.project("merge", "--attest")
    assert result.returncode == 1
    assert f"I12: {code[:10]} touches src before the change folder arrived" in result.stdout, (
        output(result)
    )


def test_code_from_before_a_ratchet_to_feat_is_put_to_a_human(repo: Repo) -> None:
    """chg/ work that ratchets to feat brings code older than its change folder, so older than
    approve. I12 cannot order it after an approve that did not exist yet, so approve names it
    and merge puts it to a human (G3), recording the answer in the squash body."""
    assert repo.project("change", "split-bill", "--lane", "chg").returncode == 0
    repo.append("specs/capabilities/cli.md", SCENARIO)
    repo.write("tests/test_split.py", TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", SPLIT_CODE)
    repo.commit("change(cli): split the bill", "--trailer", "Spec: cli.split-bill")
    early = repo.head()
    assert repo.project("change", "split-bill", "--lane", "feat").returncode == 0
    repo.write(f"{CHANGE}/requirements.md", REQUIREMENTS)
    repo.write(f"{CHANGE}/plan.md", PLAN)
    repo.write(f"{CHANGE}/validation.md", VALIDATION.split("## Human checks")[0] + NO_CHECKS)
    result = repo.project("approve")
    assert result.returncode == 0, output(result)
    note = "note: 1 commit touched src before the ratchet to feat, so this approval came after"
    assert note in result.stdout, output(result)
    assert f"({early[:10]} change(cli): split the bill)" in result.stdout
    confident(repo)
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    assert "human checks ...... FAIL 1 check and no terminal to ask in" in text, output(result)
    assert "- Code before approve: 1 commit touched src before the ratchet to feat" in text
    # I12 names the commits instead of a bare ok
    assert "I12: 1 commit touched the source before approve (before the ratchet" in text
    assert f"code before approve: {early[:10]} change(cli): split the bill" in text
    assert "I12 spec before code" not in text
    assert "src/tipcalc/__init__.py" in text  # the commit's stat, shown with the check
    result = repo.project("merge", "--attest")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    record = f"Code before approve (before the ratchet to feat): {early[:10]} change(cli): split"
    assert record in body, body
    assert "so G2 approved a spec written after this code" in body
    assert "(attested by Test Author, --attest)" in body


def test_merge_refuses_approved_checks_dropped_after_approve(repo: Repo) -> None:
    """G2 approved the whole change folder and validation.md's Human checks and Run it rows. A
    check that is gone at merge time, or a row that now asks less (a looser stdout), is shown
    with the diff and needs --reapprove (--gate-change is for gate files). Every spec file changed
    since approve, a new file in the change folder too, is listed in the output and the body."""
    main = repo.head("main")
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    assert repo.project("approve").returncode == 0
    compile_group(repo)
    confident(repo)
    row = "| `uv run --locked tipcalc 100 --split 4` | 0 | each: 28.75 | |\n"
    looser = "| `uv run --locked tipcalc 100 --split 4` | 0 | each: | |\n"
    check = "- The split output reads clearly.\n"
    repo.write(f"{CHANGE}/validation.md", VALIDATION.replace(row, looser).replace(check, ""))
    requirements = repo.path / CHANGE / "requirements.md"
    text = requirements.read_text(encoding="utf-8")
    requirements.write_text(text.replace("In: a --split flag.", "In: --split, --round."), "utf-8")
    repo.write(f"{CHANGE}/notes.md", "# Notes\n\nRounding comes later.\n")
    repo.commit("spec(split-bill): drop the checks")
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    step = (
        "amended after approval .. FAIL notes.md, requirements.md, validation.md changed; "
        "2 approved checks"
    )
    assert step in text, output(result)
    assert 'dropped: human check "The split output reads clearly."' in text
    assert "dropped: Run it row `uv run --locked tipcalc 100 --split 4` exit 0, stdout" in text
    assert "-- The split output reads clearly." in text  # the diff is shown
    assert "+In: --split, --round." in text
    assert "+Rounding comes later." in text
    assert "then merge -- --reapprove" in text
    assert repo.head("main") == main
    preview = repo.project("status", "--merge")
    assert preview.returncode == 0, output(preview)
    assert "amended after approval .. for a human" in preview.stdout
    assert "`! mise run merge -- --reapprove` after reading" in preview.stdout
    result = repo.project("merge", "--gate-change")
    assert result.returncode == 1, output(result)  # not a gate file: that flag does not do
    assert repo.head("main") == main
    result = repo.project("merge", "--reapprove")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    files = f"{CHANGE}/notes.md, {CHANGE}/requirements.md, {CHANGE}/validation.md"
    assert f"Spec files changed after approval: {files}" in body, body
    dropped = 'Dropped after approval (--reapprove by Test Author): human check "The split'
    assert dropped in body
    assert "amended after approval: ok (notes.md, requirements.md, validation.md changed;" in body


def test_the_approve_hash_covers_the_whole_change_folder(repo: Repo) -> None:
    """approve hashes every file in the change folder (a note beside the three files too) and
    every capability file: an edit to any of them after approve changes the hash."""
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    repo.write(f"{CHANGE}/notes.md", "# Notes\n")
    assert repo.project("approve").returncode == 0
    project = load_project_module()
    paths = project.spec_paths(repo.path, "HEAD", CHANGE)
    assert f"{CHANGE}/notes.md" in paths
    assert "specs/capabilities/cli.md" in paths
    before = project.spec_hash(repo.path, "HEAD", CHANGE)
    repo.write(f"{CHANGE}/notes.md", "# Notes\n\nchanged\n")
    repo.git("add", "-A")
    assert project.spec_hash(repo.path, "", CHANGE) != before


def test_merge_refuses_a_hand_written_approval(repo: Repo) -> None:
    """I6: status moves to approved only through approve, whose trailer hashes the spec."""
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    requirements = repo.path / CHANGE / "requirements.md"
    text = requirements.read_text(encoding="utf-8").replace("status: draft", "status: approved")
    requirements.write_text(text, encoding="utf-8")
    repo.commit("spec(split-bill): approve", "--trailer", "Spec-Approved: sha256:" + "0" * 64)
    compile_group(repo)
    result = repo.project("merge", "--attest")
    assert result.returncode == 1
    assert "I6: the Spec-Approved: hash of" in result.stdout, output(result)


def test_merge_asks_each_human_check_in_a_terminal(repo: Repo) -> None:
    """With a TTY, merge shows a Test-Harness: diff and asks y/N; no leaves everything as it
    was, yes lands with the answer recorded. util-linux `script` provides the terminal."""
    script = shutil.which("script")
    if script is None or not sys.platform.startswith("linux"):
        pytest.skip("needs util-linux script for a pseudo-terminal")
    assert repo.project("change", "harness", "--lane", "chore").returncode == 0
    cli = repo.path / "tests" / "test_cli.py"
    text = cli.read_text(encoding="utf-8")
    cli.write_text(text.replace('tipcalc("100")\n', 'tipcalc("100")  # harness: a note\n', 1))
    repo.commit("chore(tests): a harness note", "--trailer", "Test-Harness: a note, no assertion")
    main = repo.head("main")
    command = shlex.join([sys.executable, str(repo.path / "scripts" / "project.py"), "merge"])

    def merge_answering(answer: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [script, "-qec", command, "/dev/null"],
            cwd=repo.path,
            input=answer + "\n",
            capture_output=True,
            text=True,
            check=False,
            env=clean_env(repo.trusted),
            timeout=900,
        )

    result = merge_answering("n")
    assert result.returncode == 1, output(result)
    assert "# harness: a note" in result.stdout  # the diff, before the question
    assert "human check: Test-Harness" in result.stdout
    assert "merge: refused: a human check was not confirmed" in result.stdout
    assert repo.head("main") == main and repo.branch() == "chore/harness"
    result = merge_answering("y")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    assert "a note, no assertion (confirmed at the prompt by Test Author)" in body


def test_merge_refuses_a_gate_change_without_the_flag(repo: Repo) -> None:
    main = repo.head("main")
    assert repo.project("change", "hooks-note", "--lane", "chore").returncode == 0
    repo.append(".githooks/pre-commit", "# a note\n")
    repo.commit("chore(hooks): a note in pre-commit")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "gate files ........ FAIL changed: read the diff" in result.stdout, output(result)
    assert "changed: .githooks/pre-commit" in result.stdout
    assert "+# a note" in result.stdout  # the diff is shown
    assert repo.head("main") == main
    result = repo.project("merge", "--gate-change")
    assert result.returncode == 0, output(result)
    assert "# a note" in repo.show("main", ".githooks/pre-commit")


def test_merge_refuses_when_core_hookspath_is_unset(repo: Repo) -> None:
    main = repo.head("main")
    chore_branch(repo, "docs-note")
    repo.git("config", "--unset", "core.hooksPath")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "git config core.hooksPath is unset: run mise install" in result.stdout, output(result)
    assert repo.head("main") == main


def record_origin(repo: Repo, origin: Path) -> None:
    """What project-init's publish step leaves: a bare origin holding main, and its URL in
    .project.toml on main (committed the way merge commits, with the trailer)."""
    repo.git("init", "-q", "--bare", "-b", "main", str(origin))
    toml = repo.path / ".project.toml"
    text = re.sub(r"(?m)^origin_url = .*$", f'origin_url = "{origin}"', toml.read_text("utf-8"))
    toml.write_text(text, encoding="utf-8")
    repo.git("add", ".project.toml")
    message = "chore(init): record origin"
    record = repo.run(
        "git", "commit", "-q", "-m", message, "--trailer", MERGED_BY, env={"PROJECT_MERGE": "1"}
    )
    assert record.returncode == 0, output(record)
    repo.git("remote", "add", "origin", str(origin))
    repo.git("push", "-q", "origin", "main")  # the bootstrap push


def add_generated_ci(repo: Repo) -> None:
    """What render writes once a GitHub remote exists: .github/workflows/ci.yml (workflow ci,
    job verify), listed in .project.toml [generated]. Committed on main the way merge commits;
    before record_origin, so origin's main holds it too."""
    text = (SKILL / "templates" / "ci.yml").read_text(encoding="utf-8")
    values = {
        "NAME": "tipcalc",
        "DEFAULT_BRANCH": "main",
        "CI_JOB": "verify",
        "CI_NAME": "ci",
        "CHECKOUT_REF": "v5",
        "MISE_ACTION_REF": "v3",
    }
    for key, value in values.items():
        text = text.replace("{" + key + "}", value)
    repo.write(".github/workflows/ci.yml", text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    repo.append(".project.toml", f'\n[generated]\n".github/workflows/ci.yml" = "sha256:{digest}"\n')
    repo.git("add", "-A")
    added = repo.run(
        "git", "commit", "-q", "-m", "ci: the generated workflow", "--trailer", MERGED_BY,
        env={"PROJECT_MERGE": "1"},
    )  # fmt: skip
    assert added.returncode == 0, output(added)


def before_adoption(repo: Repo, adopted: Adopted, origin: Path | None = None) -> str:
    """Put the repo back to before its first merge (G1): main at the commit before project-init
    (no .project.toml), and plan/project-init one commit past it holding the adopted tree as the
    working tree has it, the way P7's ship commit leaves it. With origin: its URL recorded in
    that commit (P7's publish), and a bare origin holding main (the bootstrap push). Returns the
    branch's tip."""
    if origin is not None:
        toml = repo.path / ".project.toml"
        line = f'origin_url = "{origin}"'
        toml.write_text(re.sub(r"(?m)^origin_url = .*$", line, toml.read_text("utf-8")), "utf-8")
    repo.git("switch", "-q", "-c", "plan/project-init")
    repo.git("reset", "-q", "--soft", adopted.old_main)
    repo.git("add", "-A")
    repo.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "chore(init): project-init")
    moved = repo.run(
        "git", "update-ref", "refs/heads/main", adopted.old_main, env={"PROJECT_MERGE": "1"}
    )
    assert moved.returncode == 0, output(moved)
    if origin is not None:
        repo.git("init", "-q", "--bare", "-b", "main", str(origin))
        repo.git("remote", "add", "origin", str(origin))
        repo.git("push", "-q", "origin", "main")  # the bootstrap push: origin lacks main
    return repo.head()


def test_merge_dry_run_shows_the_remote_plan(repo: Repo, tmp_path: Path) -> None:
    """D1 option 1 without a network: origin is a local bare repo that .project.toml records,
    so merge plans a pull request; --dry-run prints its commands and writes nothing. gh merges
    on the server only, and merge syncs main itself once origin holds the merge commit."""
    add_generated_ci(repo)
    record_origin(repo, tmp_path / "origin.git")
    chore_branch(repo, "note")
    tip = repo.head()
    result = repo.project("merge", "--dry-run")
    assert result.returncode == 0, output(result)
    plan = [
        line.split("would run ......... ", 1)[1]
        for line in result.stdout.splitlines()
        if "would run" in line
    ]
    assert plan == [
        "git push -u origin chore/note",
        "gh pr create --base main --head chore/note --title 'docs: a note for note' --body-file -",
        "gh pr checks chore/note --json name,bucket,workflow,link",
        (
            f"gh pr merge chore/note --squash --match-head-commit {tip} "
            "--subject 'docs: a note for note' --body-file -"
        ),
        "gh pr view chore/note --json number,state,headRefOid,mergeCommit",
        "git ls-remote origin refs/heads/main",
        "git fetch -q origin refs/heads/main",
        "git push -q origin --delete chore/note",
    ]
    assert (
        "(and --required, every 10 s: waits on the required checks and the jobs of "
        ".github/workflows/ci.yml (verify); other checks only warn)"
    ) in result.stdout
    assert "(origin's main must be that merge commit, or a tip that holds it)" in result.stdout
    assert repo.head() == tip and repo.branch() == "chore/note"
    repo.git("remote", "set-url", "origin", str(tmp_path / "elsewhere.git"))
    result = repo.project("merge", "--dry-run")
    assert result.returncode == 1
    assert "origin is" in result.stdout and "re-run /project-init" in result.stdout


def test_merge_dry_run_names_the_close_commit_it_would_push(repo: Repo, tmp_path: Path) -> None:
    """A branch that gets a close commit lands that commit, so the plan cannot name a sha yet."""
    record_origin(repo, tmp_path / "origin.git")
    assert repo.project("change", "speed", "--lane", "refactor").returncode == 0
    code = repo.path / "src" / "tipcalc" / "__init__.py"
    head = "def tip(bill: float, percent: float) -> float:\n"
    text = code.read_text(encoding="utf-8")
    code.write_text(text.replace(head, head + "    # one multiply, one divide\n"), "utf-8")
    repo.commit("perf(cli): compute the tip in one expression")
    result = repo.project("merge", "--dry-run")
    assert result.returncode == 0, output(result)
    assert "would close ....... one commit on refactor/speed: CHANGELOG.md" in result.stdout
    assert "--match-head-commit '<close-commit>'" in result.stdout, result.stdout
    assert repo.head() not in result.stdout
    assert "waits on the required checks (no generated CI workflow)" in result.stdout


# A stand-in for gh that keeps a pull request's record in $GH_STATE and acts on the bare origin
# $GH_ORIGIN the way GitHub does: `pr merge` squashes the head onto main on the server (subject,
# then the body merge sends), and deletes the head branch only with $GH_DELETE_ON_MERGE (the
# repo setting). $GH_AFTER_MERGE lands one more commit on origin's main right after the squash:
# "merged" (a teammate's merge, with the trailer), "outside" (no trailer), or "rewrite" (main
# rewritten past the squash, which it no longer holds). `pr checks` prints $GH_CHECKS (or
# $GH_REQUIRED for --required) as its JSON, or gh's "no checks reported" error when that is
# empty. Every call is logged to $GH_LOG, and `pr create` keeps the body it was given.
FAKE_GH = """\
import json
import os
import subprocess
import sys

args = sys.argv[1:]
with open(os.environ["GH_LOG"], "a", encoding="utf-8") as log:
    log.write(" ".join(args) + "\\n")
path = os.environ["GH_STATE"]
state = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
origin = os.environ["GH_ORIGIN"]


def git(*argv, stdin=None):
    done = subprocess.run(
        ["git", "-C", origin, *argv], input=stdin, capture_output=True, text=True, check=True
    )
    return done.stdout.strip()


def value(flag):
    return args[args.index(flag) + 1]


def save():
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(state, handle)


pr = state.get("pr")
if args[:2] == ["pr", "view"]:
    if pr is None:
        sys.exit("no pull requests found for branch " + args[2])
    if "-q" in args:
        print(pr["reviewDecision"])
    else:
        print(json.dumps({key: pr.get(key) for key in value("--json").split(",")}))
elif args[:2] == ["pr", "create"]:
    body = sys.stdin.read()
    head = value("--head")
    pr = state["pr"] = {
        "body": body,
        "number": 7,
        "state": "OPEN",
        "head": head,
        "headRefOid": git("rev-parse", "refs/heads/" + head),
        "mergeCommit": None,
        "reviewDecision": os.environ.get("GH_REVIEW", ""),
    }
    save()
    print("https://example.invalid/o/r/pull/7")
elif args[:2] == ["pr", "checks"]:
    shown = os.environ.get("GH_REQUIRED" if "--required" in args else "GH_CHECKS", "")
    if not shown:
        kind = "required checks" if "--required" in args else "checks"
        sys.exit(f"no {kind} reported on the '{pr['head']}' branch")
    print(shown)
elif args[:2] == ["pr", "merge"]:
    body = sys.stdin.read()
    if git("rev-parse", "refs/heads/" + pr["head"]) != value("--match-head-commit"):
        sys.exit("head branch was modified")
    tree = git("rev-parse", "refs/heads/" + pr["head"] + "^{tree}")
    parent = git("rev-parse", "refs/heads/main")
    message = value("--subject") + "\\n\\n" + body
    commit = git("commit-tree", tree, "-p", parent, stdin=message)
    git("update-ref", "refs/heads/main", commit)
    after = os.environ.get("GH_AFTER_MERGE", "")
    if after:
        trailer = "" if after == "outside" else "\\n\\nMerged-By: mise run merge"
        base = parent if after == "rewrite" else commit
        later = git("commit-tree", tree, "-p", base, stdin=f"docs: a teammate's {after}{trailer}\\n")
        git("update-ref", "refs/heads/main", later)
    if os.environ.get("GH_DELETE_ON_MERGE"):
        git("update-ref", "-d", "refs/heads/" + pr["head"])
    pr.update(state="MERGED", mergeCommit={"oid": commit})
    save()
else:
    sys.exit(2)
"""
VERIFY = '[{"name": "verify", "bucket": "pass", "workflow": "ci", "link": ""}]'


def gh_env(tmp_path: Path, origin: Path, **values: str) -> dict[str, str]:
    """PATH with the fake gh first, and the GH_* variables it reads."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "gh"
    fake.write_text(f"#!{sys.executable}\n{FAKE_GH}", encoding="utf-8")
    fake.chmod(0o755)
    return {
        "PATH": f"{bin_dir}{os.pathsep}{clean_env(tmp_path)['PATH']}",
        "GH_LOG": str(tmp_path / "gh.log"),
        "GH_STATE": str(tmp_path / "gh.json"),
        "GH_ORIGIN": str(origin),
        **values,
    }


def gh_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "gh.log"
    return log.read_text(encoding="utf-8").splitlines() if log.exists() else []


def test_merge_lands_through_a_pull_request(repo: Repo, tmp_path: Path) -> None:
    """The remote path for real, with gh stood in for: push, PR, checks, squash-merge on
    origin (gh merges on the server only), then main synced to that merge commit and the
    branch deleted here and on origin."""
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    chore_branch(repo, "note")
    tip = repo.head()
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY)
    result = repo.project("merge", env=env)
    assert result.returncode == 0, output(result)
    calls = gh_calls(tmp_path)
    assert [call.split()[:2] for call in calls] == [
        ["pr", "view"],
        ["pr", "create"],
        ["pr", "checks"],
        ["pr", "checks"],
        ["pr", "merge"],
        ["pr", "view"],
    ]
    assert f"--match-head-commit {tip}" in calls[4]
    assert "--delete-branch" not in calls[4]  # gh would switch to main and pull it by itself
    assert calls[3].endswith("--required")
    landed = repo.git("rev-parse", "main", cwd=origin).strip()
    assert repo.head("main") == landed  # the sync
    body = repo.git("log", "-1", "--format=%B", "main")
    assert body.startswith("docs: a note for note\n\nBranch: chore/note\n")
    assert body.rstrip().endswith(MERGED_BY)
    assert f"main ({landed[:10]}): pull request #7 squash-merged on origin, synced here" in (
        result.stdout
    )
    assert "checks passed: verify (ci)" in result.stdout
    assert "deleted chore/note on origin" in result.stdout
    assert repo.branch() == "main"
    assert repo.git("branch", "--list", "chore/*").strip() == ""
    assert repo.git("ls-remote", "origin", "refs/heads/chore/note").strip() == ""
    audit = repo.project("status", "--audit")
    assert "audit main: ok" in audit.stdout, output(audit)


def test_the_first_merge_lands_through_a_pull_request(
    repo: Repo, adopted: Adopted, tmp_path: Path
) -> None:
    """Remote trial defects 1 and 4. At G1 main holds no .project.toml, so the main guard
    cannot confirm a sync from origin; merge confirms it itself (origin's main is the pull
    request's merge commit) and fast-forwards main under PROJECT_MERGE. A url.<base>.insteadOf
    in the user's git config (the trial's repro) rewrites origin's URL and origin_url alike."""
    origin = tmp_path / "origin.git"
    tip = before_adoption(repo, adopted, origin)
    rules = tmp_path / "gitconfig"
    rules.write_text(f'[url "file://{origin}"]\n\tinsteadOf = {origin}\n', encoding="utf-8")
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY, GH_DELETE_ON_MERGE="1")
    env["GIT_CONFIG_GLOBAL"] = str(rules)
    assert repo.git("remote", "get-url", "origin").strip() == str(origin)  # without the rule
    result = repo.project("merge", env=env)
    assert result.returncode == 0, output(result)
    calls = gh_calls(tmp_path)
    assert [call.split()[:2] for call in calls] == [
        ["pr", "view"],
        ["pr", "create"],
        ["pr", "checks"],
        ["pr", "checks"],
        ["pr", "merge"],
        ["pr", "view"],
    ]
    assert f"--match-head-commit {tip}" in calls[4]
    landed = repo.git("rev-parse", "main", cwd=origin).strip()
    assert repo.head("main") == landed
    assert repo.head("main~1") == adopted.old_main
    assert f'origin_url = "{origin}"' in repo.show("main", ".project.toml")
    assert repo.git("log", "-1", "--format=%B", "main").rstrip().endswith(MERGED_BY)
    assert repo.branch() == "main"
    assert repo.git("status", "--porcelain").strip() == ""
    assert repo.git("branch", "--list", "plan/*").strip() == ""
    assert "deleted plan/project-init on origin" not in result.stdout  # GitHub deleted it
    audit = repo.project("status", "--audit")
    assert "audit main: ok" in audit.stdout, output(audit)


def test_a_refused_first_sync_recovers_by_merging_again(
    repo: Repo, adopted: Adopted, tmp_path: Path
) -> None:
    """The pull request of G1 merged on origin, and a `git pull` of main here is refused (main
    records no origin_url yet): the guard says so and how to recover. `git reset --merge`
    undoes what the refused pull staged; merge run again on the branch finds the merged pull
    request and only syncs main."""
    origin = tmp_path / "origin.git"
    tip = before_adoption(repo, adopted, origin)
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY)
    repo.git("push", "-q", "-u", "origin", "plan/project-init")
    squash = ("--match-head-commit", tip, "--subject", "chore(init): project-init")
    for argv, stdin in (
        (("create", "--head", "plan/project-init"), ""),
        (("merge", "plan/project-init", *squash), f"Branch: plan/project-init\n\n{MERGED_BY}\n"),
    ):
        done = subprocess.run(
            [str(tmp_path / "bin" / "gh"), "pr", *argv],
            input=stdin,
            capture_output=True,
            text=True,
            check=False,
            env={**clean_env(repo.trusted), **env},
        )
        assert done.returncode == 0, output(done)
    landed = repo.git("rev-parse", "main", cwd=origin).strip()

    repo.git("switch", "-q", "main")
    pulled = repo.run("git", "pull", "-q", "--ff-only", "origin", "main")
    said = output(pulled)
    assert pulled.returncode != 0, said
    assert (
        "blocked: main moves only via 'mise run merge' (specs/README.md#gates), and this sync "
        "from origin is not confirmed: main's committed .project.toml records no origin_url yet"
    ) in said
    assert "check git status" in said
    assert "to recover: git reset --merge (it undoes this move's changes" in said
    assert "a human runs 'mise run merge' again on the branch whose pull request merged" in said
    assert repo.head("main") == adopted.old_main
    assert repo.git("status", "--porcelain", "--untracked-files=no").strip()  # pull staged it
    repo.git("reset", "-q", "--merge")
    assert repo.git("status", "--porcelain", "--untracked-files=no").strip() == ""
    repo.git("switch", "-q", "plan/project-init")

    result = repo.project("merge", env=env)
    assert result.returncode == 0, output(result)
    assert "pull request #7 had merged on origin already" in result.stdout
    assert [call.split()[:2] for call in gh_calls(tmp_path)][2:] == [["pr", "view"]]
    assert repo.head("main") == landed
    assert repo.branch() == "main"
    assert repo.git("status", "--porcelain").strip() == ""
    assert "deleted plan/project-init on origin" in result.stdout
    audit = repo.project("status", "--audit")
    assert "audit main: ok" in audit.stdout, output(audit)


def test_a_sync_never_carries_a_commit_that_skipped_merge(repo: Repo, tmp_path: Path) -> None:
    """Rollout review R1. origin's main holds a commit that reached it around merge (a merge in
    GitHub's UI: no Merged-By trailer) and main here lacks. The pull request squash-merges on
    top of it, and merge refuses to sync main, naming that commit, as the main guard refuses a
    pull of it; main stays put. The recovery it names works: a human who checked the commit
    syncs main by hand and deletes the branch, and the audit keeps naming the commit."""
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    other = tmp_path / "other"
    repo.git("clone", "-q", str(origin), str(other))
    (other / "OUTSIDE.md").write_text("outside\n", encoding="utf-8")
    for argv in (("add", "OUTSIDE.md"), ("commit", "-q", "-m", "docs: outside"), ("push", "-q")):
        done = repo.run("git", "-C", str(other), *argv)
        assert done.returncode == 0, output(done)
    outside = repo.git("-C", str(other), "rev-parse", "HEAD").strip()
    main = repo.head("main")
    chore_branch(repo, "note")
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY)
    result = repo.project("merge", env=env)
    assert result.returncode == 1, output(result)
    landed = repo.git("rev-parse", "main", cwd=origin).strip()
    assert repo.git("rev-parse", "main~1", cwd=origin).strip() == outside  # merged on origin
    said = " ".join(result.stdout.split())
    assert (
        "land: origin's main holds 1 commit that did not land through 'mise run merge' (no "
        f"'{MERGED_BY}' trailer): {outside[:10]}, so main here stays at {main[:10]}. The pull "
        "request merged on origin. To recover: a human who checked those commits syncs main by "
        "hand (on main: PROJECT_MERGE=1 git pull --ff-only origin main; status --audit keeps "
        "naming them), then deletes chore/note (git branch -D chore/note, and git push origin "
        "--delete chore/note if origin still has it)"
    ) in said, output(result)
    assert repo.head("main") == main
    assert repo.branch() == "chore/note"

    repo.git("switch", "-q", "main")
    pulled = repo.run(
        "git", "pull", "-q", "--ff-only", "origin", "main", env={"PROJECT_MERGE": "1"}
    )
    assert pulled.returncode == 0, output(pulled)
    repo.git("branch", "-D", "chore/note")
    repo.git("push", "-q", "origin", "--delete", "chore/note")
    assert repo.head("main") == landed
    assert repo.git("status", "--porcelain").strip() == ""
    audit = repo.project("status", "--audit")
    assert f'WARN  {outside[:10]} "docs: outside" on main has no' in audit.stdout, output(audit)


def test_a_merge_that_lands_on_origin_in_between_syncs_along(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rollout finding B. Another merge lands on origin's main between this pull request's
    squash and the sync. origin's tip then holds the merge commit, and each first-parent commit
    since carries Merged-By: merge syncs main to that tip."""
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    chore_branch(repo, "race-note")
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY, GH_AFTER_MERGE="merged")
    _, code = run_in_process(repo, monkeypatch, env, "merge")
    out = capsys.readouterr().out
    assert code == 0, out
    tip = repo.git("rev-parse", "main", cwd=origin).strip()
    squash = repo.git("rev-parse", "main~1", cwd=origin).strip()
    assert repo.head("main") == tip
    assert f"main ({squash[:10]}): pull request #7 squash-merged on origin, synced here" in out
    assert (
        f"origin's main had moved on to {tip[:10]} (1 more commit, each with the Merged-By "
        "trailer): main here is there too"
    ) in out
    assert repo.branch() == "main"
    assert repo.git("status", "--porcelain").strip() == ""
    assert repo.git("branch", "--list", "chore/*").strip() == ""
    audit = repo.project("status", "--audit")
    assert "audit main: ok" in audit.stdout, output(audit)


def test_a_sync_past_the_merge_needs_every_commit_merged(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Rollout findings B, C and the hook's recovery. A commit that skipped merge lands on
    origin's main right after the squash: merge refuses to sync and names the manual recovery,
    with the branch delete for 'if origin still has it'. A human `git pull` of it is refused by
    the main guard with the same by-hand step under 'to recover:'. When origin's main no longer
    holds the merge commit at all, merge names both ways out."""
    project = load_project_module()
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    main = repo.head("main")
    chore_branch(repo, "note")
    env = gh_env(tmp_path, origin, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY, GH_AFTER_MERGE="outside")
    _, code = run_in_process(repo, monkeypatch, env, "merge")
    out = " ".join(capsys.readouterr().out.split())
    assert code == 1, out
    outside = repo.git("rev-parse", "main", cwd=origin).strip()
    assert (
        "land: origin's main holds 1 commit that did not land through 'mise run merge' (no "
        f"'{MERGED_BY}' trailer): {outside[:10]}, so main here stays at {main[:10]}. The pull "
        f"request merged on origin. To recover: {project.sync_by_hand('main')}, then deletes "
        "chore/note (git branch -D chore/note, and git push origin --delete chore/note if "
        "origin still has it)"
    ) in out, out
    assert repo.head("main") == main

    repo.git("switch", "-q", "main")
    pulled = repo.run("git", "pull", "-q", "--ff-only", "origin", "main")
    said = " ".join(output(pulled).split())
    assert pulled.returncode != 0, said
    assert (
        "blocked: origin's main holds commits that did not land through 'mise run merge' (no "
        f"Merged-By trailer): {outside[:7]}"
    ) in said
    assert (
        "to recover: git reset --merge (it undoes this move's changes to the index and files; "
        f"your own edits stay). Then {project.sync_by_hand('main')}"
    ) in said
    assert repo.head("main") == main
    repo.git("reset", "-q", "--merge")
    assert repo.git("status", "--porcelain").strip() == ""
    repo.git("branch", "-D", "chore/note")

    other = tmp_path / "other"
    other.mkdir()
    origin2 = other / "origin.git"
    repo.git("remote", "remove", "origin")
    record_origin(repo, origin2)
    main = repo.head("main")
    chore_branch(repo, "gone")
    env = gh_env(other, origin2, GH_CHECKS=VERIFY, GH_REQUIRED=VERIFY, GH_AFTER_MERGE="rewrite")
    _, code = run_in_process(repo, monkeypatch, env, "merge")
    out = " ".join(capsys.readouterr().out.split())
    assert code == 1, out
    tip = repo.git("rev-parse", "main", cwd=origin2).strip()
    assert f"land: origin's main is {tip[:10]}, which does not hold the pull request's merge" in out
    assert "a human runs `! mise run merge` again on chore/gone later" in out
    assert (
        "If origin's main was rewritten, to recover: a human who checked origin's main syncs "
        "main by hand (on main: PROJECT_MERGE=1 git pull --ff-only origin main), then deletes "
        "chore/gone (git branch -D chore/gone, and git push origin --delete chore/gone if "
        "origin still has it)"
    ) in out
    assert repo.head("main") == main


def test_merge_asks_origin_the_way_the_main_guard_does(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rollout findings A and E, merge's side. The confirm and fetch of a sync run as the main
    guard runs its own git (guard_env): git -c, GIT_CONFIG_*, XDG_CONFIG_HOME and GIT_SSH* are
    dropped, and core.sshCommand comes from the user's or the system's config only. So an
    insteadOf rule in a GIT_CONFIG_GLOBAL file cannot point the sync at a repo whose main holds
    a forged Merged-By commit: merge syncs to the pull request's real merge commit."""
    project = load_project_module()
    monkeypatch.setattr(project, "SYNC_TRIES", 1)
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    tree = repo.git("rev-parse", "main^{tree}").strip()
    oid = repo.git("commit-tree", tree, "-p", "main", "-m", f"docs: x\n\n{MERGED_BY}").strip()
    repo.git("push", "-q", str(origin), f"{oid}:refs/heads/side")
    repo.git("update-ref", "refs/heads/main", oid, cwd=origin)
    other = tmp_path / "other.git"
    repo.git("clone", "-q", "--bare", str(origin), str(other))
    forged = repo.git("commit-tree", tree, "-p", oid, "-m", f"forged\n\n{MERGED_BY}", cwd=other)
    repo.git("update-ref", "refs/heads/main", forged.strip(), cwd=other)
    rules = tmp_path / "evil.gitconfig"
    rules.write_text(f'[url "file://{other}"]\n\tinsteadOf = {origin}\n', encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()
    evil = {
        "HOME": str(home),
        "GIT_CONFIG_GLOBAL": str(rules),
        "GIT_SSH_COMMAND": "false",
        "GIT_SSH": "false",
        "GIT_SSH_VARIANT": "simple",
        "XDG_CONFIG_HOME": str(tmp_path),
        "GIT_CONFIG_PARAMETERS": "'core.sshcommand'='false'",
        "GIT_CONFIG_COUNT": "0",
    }
    env = {**clean_env(repo.trusted), **evil}
    got = project.guard_env(repo.path, env)
    assert set(project.GUARD_UNSET) & set(got) == {"GIT_SSH_COMMAND"}
    assert got["GIT_SSH_COMMAND"] == "ssh" and got["HOME"] == str(home)
    repo.git("config", "core.sshCommand", "false")  # the repo's own: never taken
    (home / ".gitconfig").write_text("[core]\n\tsshCommand = ssh -i deploy_key\n", "utf-8")
    assert project.guard_env(repo.path, env)["GIT_SSH_COMMAND"] == "ssh -i deploy_key"
    (home / "keys.gitconfig").write_text("[core]\n\tsshCommand = ssh -i work_key\n", "utf-8")
    (home / ".gitconfig").write_text("[include]\n\tpath = keys.gitconfig\n", "utf-8")
    assert project.guard_env(repo.path, env)["GIT_SSH_COMMAND"] == "ssh -i work_key"
    repo.git("config", "--unset", "core.sshCommand")

    for key, value in env.items():
        monkeypatch.setenv(key, value)
    plan = project.remote_plan("chore/x", "main", "docs: x", oid, False)[-3:-1]
    problem, notes = project.sync_merged(repo.path, "chore/x", "main", env, (plan[0], plan[1]), oid)
    assert problem is None, problem
    assert repo.head("main") == oid
    assert notes == []


def test_a_failed_fetch_of_a_later_tip_is_named(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """origin's main moved past the merge commit, and the fetch of that tip fails: merge
    says the fetch failed, with what git said, and never that origin lost the merge commit."""
    project = load_project_module()
    monkeypatch.setattr(project, "SYNC_TRIES", 1)
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    tree = repo.git("rev-parse", "main^{tree}").strip()
    oid = repo.git("commit-tree", tree, "-p", "main", "-m", f"docs: x\n\n{MERGED_BY}").strip()
    later = repo.git("commit-tree", tree, "-p", oid, "-m", f"docs: y\n\n{MERGED_BY}").strip()
    repo.git("push", "-q", str(origin), f"{later}:refs/heads/side")
    repo.git("update-ref", "refs/heads/main", later, cwd=origin)
    env = clean_env(repo.trusted)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    main = repo.head("main")
    confirm = project.remote_plan("chore/x", "main", "docs: x", oid, False)[-3]
    fetch = ["sh", "-c", "echo 'fatal: the network went away' >&2; exit 128"]
    problem, notes = project.sync_merged(repo.path, "chore/x", "main", env, (confirm, fetch), oid)
    assert problem is not None and notes == [], problem
    assert (
        f"git fetch origin main did not bring its tip {later[:10]}, so whether that holds the "
        f"pull request's merge commit {oid[:10]} is unknown: fatal: the network went away"
    ) in problem
    assert "does not hold" not in problem
    assert repo.head("main") == main


def run_in_process(
    repo: Repo, monkeypatch: pytest.MonkeyPatch, env: dict[str, str], *argv: str
) -> tuple[ModuleType, int]:
    """project.py run in this process, so a test can shorten its waits: CHECKS_REGISTER and
    CHECKS_POLL are 0, and origin's default branch is looked at once (SYNC_TRIES). os.environ
    becomes what repo.project() would pass."""
    module = load_project_module()
    monkeypatch.setattr(module, "CHECKS_REGISTER", 0)
    monkeypatch.setattr(module, "CHECKS_POLL", 0)
    monkeypatch.setattr(module, "SYNC_TRIES", 1)
    wanted = {**clean_env(repo.trusted), **env}
    for key in list(os.environ):
        if key not in wanted:
            monkeypatch.delenv(key)
    for key, value in wanted.items():
        monkeypatch.setenv(key, value)
    monkeypatch.chdir(repo.path)
    args = module.build_parser().parse_args(list(argv))
    return module, int(args.func(module.load_context(repo.path), args))


def test_merge_refuses_a_pull_request_without_ci_unless_a_human_says_why(
    repo: Repo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Remote trial defect 5: the generated workflow's job never shows up on the pull request
    (Actions off, a workflow GitHub rejected). merge refuses, and names the human-only
    --without-ci; with it the pull request lands, and the squash body records who and why."""
    add_generated_ci(repo)
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    chore_branch(repo, "note")
    main = repo.head("main")
    env = gh_env(tmp_path, origin)  # no checks reported, required or not
    _, code = run_in_process(repo, monkeypatch, env, "merge")
    out = capsys.readouterr().out
    assert code == 1, out
    assert (
        "FAIL  land: the pull request shows no check from .github/workflows/ci.yml (verify) after "
        "0 min: GitHub Actions may be off for this repo"
    ) in out
    assert '`! mise run merge -- --without-ci "<why>"`' in out
    assert repo.head("main") == main
    assert repo.git("rev-parse", "main", cwd=origin).strip() == main  # nothing merged
    assert [call.split()[:2] for call in gh_calls(tmp_path)][-1] == ["pr", "checks"]

    _, code = run_in_process(repo, monkeypatch, env, "merge", "--without-ci", "Actions are off")
    out = capsys.readouterr().out
    assert code == 0, out
    assert "--without-ci: verify never reported; the squash body says why" in out
    body = repo.git("log", "-1", "--format=%B", "main")
    assert (
        "\n\nLanded without CI (--without-ci, by Test Author): Actions are off. verify never "
        f"reported on the pull request.\n\n{MERGED_BY}\n"
    ) in body
    assert repo.head("main") == repo.git("rev-parse", "main", cwd=origin).strip()


def test_merge_waits_only_on_the_checks_that_gate_it() -> None:
    """helios: its own CI's Backend job is red on main already. merge waits on the required
    checks and the jobs of the generated workflow (sdd.yml's sdd); any other check only warns."""
    project = load_project_module()
    ci = project.Workflow(".github/workflows/sdd.yml", "ci", ["sdd"])

    def check(name: str, bucket: str, workflow: str) -> object:
        return project.Check(name, bucket, workflow, f"https://example.invalid/{name}")

    backend, frontend = check("Backend", "fail", "CI"), check("Frontend", "pass", "CI")
    judge = project.judge_checks
    verdict = judge([backend, frontend, check("sdd", "pending", "ci")], [], ci, 1.0, "")
    assert not verdict.done and verdict.waiting == "sdd (ci)"
    verdict = judge([backend, frontend, check("sdd", "pass", "ci")], [], ci, 1.0, "")
    assert verdict.done and verdict.problem is None, verdict
    assert verdict.notes[0] == "checks passed: sdd (ci)"
    assert verdict.notes[1] == (
        "warning: Backend (CI) fail, a check this merge does not wait on (neither required nor "
        "a job of the generated workflow): https://example.invalid/Backend"
    )
    verdict = judge([backend, check("sdd", "fail", "ci")], [], ci, 1.0, "")
    assert verdict.problem == "checks failed: sdd (ci) fail (https://example.invalid/sdd)"
    # a check a ruleset requires gates too, red legacy job or not
    verdict = judge([backend, check("sdd", "pass", "ci")], [backend], ci, 1.0, "")
    assert verdict.problem == "checks failed: Backend (CI) fail (https://example.invalid/Backend)"
    # a job named like the generated one in another workflow is not it
    verdict = judge([check("sdd", "fail", "CI"), check("sdd", "pass", "ci")], [], ci, 1.0, "")
    assert verdict.done and verdict.problem is None, verdict
    # the generated job never reports: wait CHECKS_REGISTER, then refuse unless --without-ci
    register = project.CHECKS_REGISTER
    verdict = judge([backend], [], ci, 1.0, "")
    assert not verdict.done and verdict.waiting == "sdd (not reported yet)"
    verdict = judge([backend], [], ci, register, "")
    assert verdict.done and verdict.problem is not None and "--without-ci" in verdict.problem
    verdict = judge([backend], [], ci, register, "Actions are off")
    assert verdict.done and verdict.problem is None and verdict.unreported == ["sdd"]
    # a workflow whose jobs could not be read: a check of any job of it will do
    unread = project.Workflow(".github/workflows/sdd.yml", "ci", [])
    verdict = judge([backend, check("lint", "pass", "ci")], [], unread, register, "")
    assert (
        verdict.done and verdict.problem is None and verdict.notes[0] == "checks passed: lint (ci)"
    )
    verdict = judge([backend], [], unread, register, "")
    assert verdict.problem is not None and "(any job)" in verdict.problem
    # no generated workflow: the required checks alone; none at all lands with a note
    verdict = judge([backend], [], None, register, "")
    assert verdict.problem is None
    assert verdict.notes[0] == "no check gates this pull request: no generated CI, none required"


def test_wait_for_checks_polls_until_the_gating_checks_finish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    project = load_project_module()
    ci = project.Workflow(".github/workflows/ci.yml", "ci", ["verify"])
    looks = iter(["pending", "pending", "pass"])
    seen: list[bool] = []

    def pr_checks(_root: Path, _env: object, _branch: str, *, required: bool) -> object:
        seen.append(required)
        if required:
            return []
        return [project.Check("verify", next(looks), "ci", "")]

    monkeypatch.setattr(project, "generated_ci", lambda _root: ci)
    monkeypatch.setattr(project, "pr_checks", pr_checks)
    monkeypatch.setattr(project, "CHECKS_POLL", 0)
    notes: list[str] = []
    problem, unreported = project.wait_for_checks(tmp_path, {}, "chore/x", "", notes)
    assert (problem, unreported) == (None, [])
    assert notes == ["checks passed: verify (ci)"]
    assert seen == [False, True] * 3
    assert capsys.readouterr().out.count("waiting on verify (ci)") == 1  # said once
    monkeypatch.setattr(project, "pr_checks", lambda *_a, **_k: "boom")
    problem, _ = project.wait_for_checks(tmp_path, {}, "chore/x", "", [])
    assert problem == "gh pr checks failed 3 times in a row: boom"


def test_workflow_jobs_reads_the_rendered_ci() -> None:
    project = load_project_module()
    text = (SKILL / "templates" / "ci.yml").read_text(encoding="utf-8")
    sdd = text.replace("{CI_JOB}", "sdd").replace("{CI_NAME}", "sdd")
    assert project.workflow_jobs(sdd) == ("sdd", ["sdd"])
    own = "name: CI\non: [push]\njobs:\n  backend:\n    runs-on: x\n    steps:\n      - name: y\n"
    assert project.workflow_jobs(own + "  frontend:\n    name: Front end\n") == (
        "CI",
        ["backend", "Front end"],
    )


def test_with_record_goes_before_the_trailer() -> None:
    project = load_project_module()
    body = f"Branch: chore/x\n\nDefinition of Done:\n  tree: ok\n\n{MERGED_BY}\n"
    assert project.with_record(body, "Landed without CI.") == (
        f"Branch: chore/x\n\nDefinition of Done:\n  tree: ok\n\nLanded without CI.\n\n{MERGED_BY}\n"
    )


def test_origin_is_compared_after_url_rewrites(repo: Repo, tmp_path: Path) -> None:
    """Remote trial defect 4: origin_url and origin's URL are both compared after git's
    url.<base>.insteadOf, in merge's land step (and doctor) and in the main guard. A rule in the
    user's git config is followed; one in the repo's own config is refused by both, since it
    could send the guard's `ls-remote origin` to another repo."""
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    rules = tmp_path / "gitconfig"
    rules.write_text(f'[url "file://{origin}"]\n\tinsteadOf = {origin}\n', encoding="utf-8")
    env = {"GIT_CONFIG_GLOBAL": str(rules)}
    other = tmp_path / "other"
    repo.git("clone", "-q", str(origin), str(other))

    def origin_moves(note: str) -> str:
        (other / "README.md").write_text(f"{note}\n", encoding="utf-8")
        for argv in (("commit", "-q", "-am", f"docs: {note}\n\n{MERGED_BY}"), ("push", "-q")):
            done = repo.run("git", "-C", str(other), *argv)
            assert done.returncode == 0, output(done)
        return repo.git("-C", str(other), "rev-parse", "HEAD").strip()

    doctor_run = ("mise", "x", "--", sys.executable, "scripts/project.py", "doctor")
    result = repo.run(*doctor_run, env=env)
    assert "ok    origin: the origin_url .project.toml records" in result.stdout, output(result)
    assert repo.run("git", "remote", "get-url", "origin", env=env).stdout.startswith("file://")
    tip = origin_moves("moved")
    # the guard reads ~/.gitconfig whatever GIT_CONFIG_GLOBAL names: HOME holds the same rule
    home = tmp_path / "home"
    home.mkdir()
    shutil.copy(rules, home / ".gitconfig")
    pulled = repo.run(
        "git", "pull", "-q", "--ff-only", "origin", "main", env={**env, "HOME": str(home)}
    )
    assert pulled.returncode == 0, output(pulled)
    assert repo.head("main") == tip

    rules.write_text("", encoding="utf-8")
    repo.git("config", f"url.file://{origin}.insteadOf", str(origin))
    result = repo.run(*doctor_run)
    assert result.returncode == 1
    assert (
        f"FAIL  this repo's own git config rewrites origin_url '{origin}' (url.<base>.insteadOf "
        f"'{origin}'): main's guard follows only the rewrites in your user or system git config"
    ) in result.stdout, output(result)
    main = repo.head("main")
    origin_moves("moved again")
    pulled = repo.run("git", "pull", "-q", "--ff-only", "origin", "main")
    said = output(pulled)
    assert pulled.returncode != 0, said
    assert "this sync from origin is not confirmed: this repo's own git config rewrites" in said
    assert "to recover: git reset --merge, then move that url.<base>.insteadOf rule" in said
    assert repo.head("main") == main


def test_the_guard_follows_only_the_users_own_git_config(repo: Repo, tmp_path: Path) -> None:
    """Rollout review R2. A url.<base>.insteadOf rule can point origin at another repo whose
    main holds a commit with a forged Merged-By trailer. The main guard follows such a rule
    from ~/.gitconfig, the file a person keeps (HOME here). It reads that file whatever
    GIT_CONFIG_GLOBAL or GIT_CONFIG_SYSTEM name, so the same rule in a file one of them names,
    or in git -c, gets the pull refused: the guard asks the real origin."""
    origin = tmp_path / "origin.git"
    record_origin(repo, origin)
    other = tmp_path / "other.git"
    repo.git("clone", "-q", "--bare", str(origin), str(other))
    tree = repo.git("rev-parse", "main^{tree}", cwd=other).strip()
    message = f"docs: forged\n\n{MERGED_BY}"
    forged = repo.git("commit-tree", tree, "-p", "main", "-m", message, cwd=other).strip()
    repo.git("update-ref", "refs/heads/main", forged, cwd=other)
    rule = f'[url "file://{other}"]\n\tinsteadOf = {origin}\n'
    named = tmp_path / "named.gitconfig"
    named.write_text(rule, encoding="utf-8")
    nobody = tmp_path / "nobody"  # a HOME without a .gitconfig
    nobody.mkdir()
    main = repo.head("main")
    pull = ("git", "pull", "-q", "--ff-only", "origin", "main")
    for label, env in (
        ("GIT_CONFIG_GLOBAL", {"GIT_CONFIG_GLOBAL": str(named)}),
        ("GIT_CONFIG_SYSTEM", {"GIT_CONFIG_SYSTEM": str(named), "GIT_CONFIG_NOSYSTEM": "0"}),
        ("git -c", {}),
    ):
        argv = pull if env else ("git", "-c", f"url.file://{other}.insteadOf={origin}", *pull[1:])
        pulled = repo.run(*argv, env={**env, "HOME": str(nobody)})
        said = output(pulled)
        assert pulled.returncode != 0, f"{label}: {said}"
        assert "blocked: main moves only via 'mise run merge' (specs/README.md#gates)" in said
        assert repo.head("main") == main, label
    assert repo.git("status", "--porcelain").strip() == ""

    # rollout finding E: the same rule in $XDG_CONFIG_HOME/git/config, which the pull follows
    xdg = tmp_path / "xdg"
    (xdg / "git").mkdir(parents=True)
    (xdg / "git" / "config").write_text(rule, encoding="utf-8")
    env = {k: v for k, v in clean_env(repo.trusted).items() if k != "GIT_CONFIG_GLOBAL"}
    env.update(HOME=str(nobody), XDG_CONFIG_HOME=str(xdg))
    pulled = subprocess.run(
        list(pull), cwd=repo.path, capture_output=True, text=True, check=False, env=env
    )
    said = output(pulled)
    assert pulled.returncode != 0, f"XDG_CONFIG_HOME: {said}"
    assert "blocked: main moves only via 'mise run merge' (specs/README.md#gates)" in said
    assert repo.head("FETCH_HEAD") == forged  # the pull itself followed the rule
    assert repo.head("main") == main
    assert repo.git("status", "--porcelain").strip() == ""

    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(rule, encoding="utf-8")
    env = {"HOME": str(home), "GIT_CONFIG_GLOBAL": str(home / ".gitconfig")}
    pulled = repo.run(*pull, env=env)
    assert pulled.returncode == 0, output(pulled)
    assert repo.head("main") == forged  # the rule a person keeps is theirs to trust


def fake_ssh(folder: Path, target: Path) -> Path:
    """A stand-in for ssh at <folder>/ssh: whatever host and path git asks for, it runs the
    git command asked for (upload-pack, receive-pack) on target."""
    folder.mkdir()
    script = folder / "ssh"
    script.write_text(
        "#!/bin/sh\nfor last; do :; done\ncmd=${last%% *}\n"
        f"exec git \"${{cmd#git-}}\" '{target}'\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return script


def test_the_guard_asks_origin_over_the_users_own_ssh(repo: Repo, tmp_path: Path) -> None:
    """Rollout finding A. With an ssh origin, GIT_SSH_COMMAND, GIT_SSH or this repo's own
    core.sshCommand sends a pull to another repo, whose main holds a forged Merged-By commit.
    The main guard unsets the GIT_SSH* variables and takes core.sshCommand only from the
    user's or the system's git config (HOME here), so it asks the real origin, and each of
    those pulls is refused. The user's own core.sshCommand is followed."""
    url = "ssh://git@git.example.invalid/o/tipcalc.git"
    origin = tmp_path / "origin.git"
    other = tmp_path / "other.git"
    good = fake_ssh(tmp_path / "good", origin)
    evil = fake_ssh(tmp_path / "evil", other)
    toml = repo.path / ".project.toml"
    line = f'origin_url = "{url}"'
    toml.write_text(re.sub(r"(?m)^origin_url = .*$", line, toml.read_text("utf-8")), "utf-8")
    repo.git("add", ".project.toml")
    recorded = repo.run(
        "git", "commit", "-q", "-m", "chore(init): record origin", "--trailer", MERGED_BY,
        env={"PROJECT_MERGE": "1"},
    )  # fmt: skip
    assert recorded.returncode == 0, output(recorded)
    repo.git("init", "-q", "--bare", "-b", "main", str(origin))
    repo.git("remote", "add", "origin", url)
    pushed = repo.run("git", "push", "-q", "origin", "main", env={"GIT_SSH_COMMAND": str(good)})
    assert pushed.returncode == 0, output(pushed)  # the bootstrap push
    repo.git("clone", "-q", "--bare", str(origin), str(other))
    tree = repo.git("rev-parse", "main^{tree}").strip()
    message = f"docs: forged\n\n{MERGED_BY}"
    forged = repo.git("commit-tree", tree, "-p", "main", "-m", message, cwd=other).strip()
    repo.git("update-ref", "refs/heads/main", forged, cwd=other)
    home = tmp_path / "home"
    home.mkdir()
    (home / ".gitconfig").write_text(f"[core]\n\tsshCommand = {good}\n", encoding="utf-8")
    main = repo.head("main")
    pull = ("git", "pull", "-q", "--ff-only", "origin", "main")
    for label, env in (
        ("GIT_SSH_COMMAND", {"GIT_SSH_COMMAND": str(evil)}),
        ("GIT_SSH", {"GIT_SSH": str(evil)}),
        ("core.sshCommand in .git/config", {}),
    ):
        if not env:
            repo.git("config", "core.sshCommand", str(evil))
        pulled = repo.run(*pull, env={"HOME": str(home), **env})
        said = output(pulled)
        assert pulled.returncode != 0, f"{label}: {said}"
        assert "blocked: main moves only via 'mise run merge' (specs/README.md#gates)" in said
        assert repo.head("FETCH_HEAD") == forged, label  # the pull itself reached the fake
        assert repo.head("main") == main, label
    repo.git("config", "--unset", "core.sshCommand")
    assert repo.git("status", "--porcelain").strip() == ""

    message = f"docs: merged\n\n{MERGED_BY}"
    merged = repo.git("commit-tree", tree, "-p", "main", "-m", message, cwd=origin).strip()
    repo.git("update-ref", "refs/heads/main", merged, cwd=origin)
    env = {"HOME": str(home), "GIT_CONFIG_GLOBAL": str(home / ".gitconfig")}
    pulled = repo.run(*pull, env=env)
    assert pulled.returncode == 0, output(pulled)
    assert repo.head("main") == merged  # the user's own core.sshCommand reached origin

    # the user's core.sshCommand in a file ~/.gitconfig includes is theirs too
    (home / "ssh.gitconfig").write_text(f"[core]\n\tsshCommand = {good}\n", encoding="utf-8")
    (home / ".gitconfig").write_text("[include]\n\tpath = ssh.gitconfig\n", encoding="utf-8")
    message = f"docs: merged again\n\n{MERGED_BY}"
    again = repo.git("commit-tree", tree, "-p", merged, "-m", message, cwd=origin).strip()
    repo.git("update-ref", "refs/heads/main", again, cwd=origin)
    pulled = repo.run(*pull, env=env)
    assert pulled.returncode == 0, output(pulled)
    assert repo.head("main") == again

    # GIT_SSH_COMMAND alone reaches origin for git, never for the guard: the refusal says how
    # to recover instead of only 'retry online'
    (home / ".gitconfig").write_text("", encoding="utf-8")
    message = f"docs: merged once more\n\n{MERGED_BY}"
    later = repo.git("commit-tree", tree, "-p", again, "-m", message, cwd=origin).strip()
    repo.git("update-ref", "refs/heads/main", later, cwd=origin)
    pulled = repo.run(*pull, env={**env, "GIT_SSH_COMMAND": str(good)})
    said = " ".join(output(pulled).split())
    assert pulled.returncode != 0, said
    assert "blocked: cannot reach origin to confirm main" in said
    assert "to recover: git reset --merge" in said
    assert "it ignores GIT_SSH_COMMAND and this repo's own core.sshCommand" in said
    assert "git config --global core.sshCommand '<command>'" in said
    assert "PROJECT_MERGE=1 git pull --ff-only origin main" in said
    assert repo.head("main") == again
    repo.git("reset", "-q", "--merge")


def test_remote_plan_waits_for_a_review_in_the_team_tier() -> None:
    project = load_project_module()
    solo = project.remote_plan("feat/x", "main", "feat: x", "abc123", False)
    team = project.remote_plan("feat/x", "main", "feat: x", "abc123", True)
    assert [argv[:3] for argv in solo] == [
        ["git", "push", "-u"],
        ["gh", "pr", "create"],
        ["gh", "pr", "checks"],
        ["gh", "pr", "merge"],
        ["gh", "pr", "view"],
        ["git", "ls-remote", "origin"],
        ["git", "fetch", "-q"],
        ["git", "push", "-q"],
    ]
    assert team[3] == [
        "gh",
        "pr",
        "view",
        "feat/x",
        "--json",
        "reviewDecision",
        "-q",
        ".reviewDecision",
    ]
    merge = team[4]
    assert merge[:5] == ["gh", "pr", "merge", "feat/x", "--squash"]
    assert "--delete-branch" not in merge
    assert merge[merge.index("--match-head-commit") + 1] == "abc123"


# ---------------------------------------------------------------- status --audit, abandon


def test_status_audit_warns_about_a_commit_that_skipped_merge(repo: Repo) -> None:
    repo.append("README.md", "\nsneaky\n")
    repo.git("add", "README.md")
    forced = repo.run("git", "commit", "-q", "-m", "docs: sneaky", env={"PROJECT_MERGE": "1"})
    assert forced.returncode == 0, output(forced)
    sha = repo.head("main")
    result = repo.project("status", "--audit")
    assert result.returncode == 0, output(result)
    assert (
        f"WARN  {sha[:10]} \"docs: sneaky\" on main has no '{MERGED_BY}' trailer" in result.stdout
    )
    assert "audit main: 1 of 2 commits since adoption" in result.stdout


def test_abandon_tags_reports_and_deletes(repo: Repo) -> None:
    main = repo.head("main")
    assert repo.project("change", "split-bill").returncode == 0
    tip = repo.head()
    result = repo.project("abandon", "not worth it")
    assert result.returncode == 0, output(result)
    assert repo.git("rev-parse", "abandoned/split-bill^{commit}").strip() == tip
    assert repo.git("branch", "--list", "feat/*").strip() == ""
    assert repo.branch() == "main"
    assert repo.head("main~1") == main
    report = f"specs/backlog/{TODAY}-split-bill.md"
    text = repo.show("main", report)
    assert "not worth it" in text and "abandoned/split-bill" in text
    assert text.startswith("---\nstatus: open ")
    assert (repo.path / report).is_file()
    assert (
        repo.git("log", "-1", "--format=%s", "main").strip() == "docs(backlog): abandon split-bill"
    )
    assert MERGED_BY in trailers(repo, "main")
    assert repo.git("status", "--porcelain").strip() == ""
    audit = repo.project("status", "--audit")
    assert "audit main: ok" in audit.stdout, output(audit)


# ---------------------------------------------------------------- doctor


def doctor(repo: Repo) -> subprocess.CompletedProcess[str]:
    """Through `mise x`, as `mise run doctor` runs it: gitleaks and git-cliff on PATH."""
    return repo.run("mise", "x", "--", sys.executable, "scripts/project.py", "doctor")


def test_doctor_checks_the_typed_env_contract(repo: Repo) -> None:
    repo.write(".env", "TIPCALC_DEFAULT_PERCENT=\n")
    result = doctor(repo)
    assert "ok    env TIPCALC_DEFAULT_PERCENT: empty: default 15 applies" in result.stdout
    assert result.returncode == 0, output(result)
    # Run C: the contract reads empty as unset (H17), but open gaps say the app does not yet
    assert (
        "warn  env TIPCALC_DEFAULT_PERCENT: empty, which the contract reads as unset, but the app "
        "may not yet: open gap scenarios name it (config.percent-empty [gap: "
        "entrypoint-hardening], config.percent-invalid [gap: entrypoint-hardening]). Unset it "
        "(`env -u TIPCALC_DEFAULT_PERCENT`) until that gap is closed"
    ) in result.stdout, output(result)
    repo.write(".env", "TIPCALC_DEFAULT_PERCENT=20\n")
    result = doctor(repo)
    assert "ok    env TIPCALC_DEFAULT_PERCENT: 20 (float 0..100)" in result.stdout, output(result)
    assert "open gap scenarios" not in result.stdout
    assert "ok    gitleaks: 8.30.1" in result.stdout
    assert "ok    git gates:" in result.stdout

    repo.write(".env", "TIPCALC_DEFAULT_PERCENT=abc_knob_value\n")
    result = doctor(repo)
    assert result.returncode == 1
    assert "FAIL  env TIPCALC_DEFAULT_PERCENT: the value is not a float" in result.stdout
    assert "abc_knob_value" not in output(result)  # a secret in a knob's slot stays hidden

    repo.write(".env", "TIPCALC_DEFAULT_PERCENT=150\n")
    result = doctor(repo)
    assert "FAIL  env TIPCALC_DEFAULT_PERCENT: the value is outside 0..100" in result.stdout

    repo.write(".env", "AWS_SECRET_ACCESS_KEY=undeclared_value_never_printed\n")
    result = doctor(repo)
    assert result.returncode == 0, output(result)
    assert "warn  env AWS_SECRET_ACCESS_KEY: in .env but not in the .env.example contract" in (
        result.stdout
    )
    assert "undeclared_value_never_printed" not in output(result)

    repo.append(".env.example", "# STRIPE_KEY | secret | str | yes | - | op:// pointer\n")
    repo.write(".env", "STRIPE_KEY=sk_test_value_never_printed\n")
    result = doctor(repo)
    assert result.returncode == 1
    assert "FAIL  env STRIPE_KEY: secret, not an op:// pointer" in result.stdout
    assert "sk_test_value_never_printed" not in output(result)
    repo.write(".env", "STRIPE_KEY=op://Private\n")
    result = doctor(repo)
    assert "FAIL  env STRIPE_KEY: secret, not an op:// pointer" in result.stdout
    repo.write(".env", "STRIPE_KEY=op://Private/stripe/credential\n")
    result = doctor(repo)
    assert "ok    env STRIPE_KEY: secret, an op:// pointer" in result.stdout
    assert result.returncode == 0, output(result)
    repo.append(".env.example", "# QWEN_API_KEY | secret | str | no | - | op:// pointer\n")
    result = doctor(repo)
    assert result.returncode == 0, output(result)
    assert (
        "ok    env QWEN_API_KEY: secret, unset: optional (required no); its op:// pointer in .env "
        "turns it on"
    ) in result.stdout

    # a note that names where the read was: stale once a feature moves the read elsewhere
    repo.append(
        ".env.example", "# TIPCALC_GONE | knob | str | no | - | read in src/tipcalc/x.py:9\n"
    )
    result = doctor(repo)
    assert (
        "warn  env TIPCALC_GONE: .env.example says it is read in src/tipcalc/x.py, which no "
        "longer names it" in result.stdout
    ), output(result)
    assert "env TIPCALC_DEFAULT_PERCENT: .env.example says" not in result.stdout


def test_a_read_in_note_is_stale_when_its_file_no_longer_names_the_variable(
    tmp_path: Path,
) -> None:
    project = load_project_module()
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "config.py").write_text('KEY = "TIPCALC_DEFAULT_PERCENT"\n', "utf-8")
    (tmp_path / "src" / "main.py").write_text("print('tip')\n", "utf-8")
    rows, _ = project.env_contract(
        "# TIPCALC_DEFAULT_PERCENT | knob | float | no | 15 | read in src/main.py:10, "
        "src/config.py\n# OTHER | knob | str | no | - | the default tip; set by hand\n"
    )
    assert project.stale_read_notes(tmp_path, rows[0]) == ["src/main.py"]
    assert project.stale_read_notes(tmp_path, rows[1]) == []


def test_a_read_in_note_matches_pydantic_settings_fields(tmp_path: Path) -> None:
    """orca re-check defect 4: a pydantic-settings model names ANTHROPIC_API_KEY as the field
    anthropic_api_key (case_sensitive=False), and ORCA_DEBUG as `debug` under
    env_prefix="ORCA_". Neither note is stale; a file that names neither still is."""
    project = load_project_module()
    (tmp_path / "config.py").write_text(
        "from pydantic_settings import BaseSettings, SettingsConfigDict\n\n\n"
        "class Settings(BaseSettings):\n"
        '    model_config = SettingsConfigDict(env_prefix="ORCA_", env_ignore_empty=True)\n'
        "    anthropic_api_key: str | None = None\n"
        "    debug: bool = False\n",
        "utf-8",
    )
    (tmp_path / "other.py").write_text("DEBUGGER = 1\ndebug_level = 2\n", "utf-8")
    rows, _ = project.env_contract(
        "# ANTHROPIC_API_KEY | secret | str | no | - | read in config.py\n"
        "# ORCA_DEBUG | knob | bool | no | false | read in config.py, other.py\n"
        "# ORCA_GONE | knob | str | no | - | read in config.py\n"
    )
    assert [project.stale_read_notes(tmp_path, row) for row in rows] == [
        [],
        ["other.py"],
        ["config.py"],
    ]
    # a whole word, and a lower-case one only for a settings field: `import sys` and
    # `def main` in plain code name neither SYS nor MAIN, and `import` does not name PORT
    (tmp_path / "cli.py").write_text(
        "import sys\n\n\ndef main() -> None:\n    sys.exit()\n", "utf-8"
    )
    rows, _ = project.env_contract(
        "".join(f"# {name} | knob | str | no | - | read in cli.py\n" for name in ("PORT", "SYS"))
        + "# MAIN | knob | str | no | - | read in cli.py\n"
    )
    assert [project.stale_read_notes(tmp_path, row) for row in rows] == [["cli.py"]] * 3
    # a settings model on a base of the project's own (defined in another file) is one too
    (tmp_path / "sub_settings.py").write_text(
        "from app.base import AppSettings\n\n\nclass Settings(AppSettings):\n    port: int\n",
        "utf-8",
    )
    rows, _ = project.env_contract("# PORT | knob | int | no | - | read in sub_settings.py\n")
    assert project.stale_read_notes(tmp_path, rows[0]) == []


def test_doctor_and_merge_see_main_moved_by_a_copy(repo: Repo) -> None:
    """git branch -C <x> main runs no hook, so the guard's record of main (hook install wrote
    it, merge moved it) is what shows the move: doctor and merge FAIL until main is put back."""
    main = repo.head("main")
    chore_branch(repo, "copied")
    copied = repo.run("git", "branch", "-C", "chore/copied", "main")
    assert copied.returncode == 0, output(copied)
    result = doctor(repo)
    assert result.returncode == 1
    moved = repo.head("main")[:10]
    line = f"FAIL  main is at {moved}, but the main guard last saw it at {main[:10]}"
    assert line in result.stdout, output(result)
    assert "(Branch: copied refs/heads/chore/copied to refs/heads/main)" in result.stdout
    assert f"put it back: git update-ref refs/heads/main {main}" in result.stdout
    result = repo.project("merge")
    assert result.returncode == 1
    assert "hooks ............. FAIL" in result.stdout, output(result)
    assert repo.run("git", "commit", "-q", "--allow-empty", "-m", "docs: x").returncode != 0
    repo.git("update-ref", "refs/heads/main", main)
    result = doctor(repo)
    assert "the guard's record of main matches it" in result.stdout, output(result)


def test_doctor_and_session_start_see_an_origin_merge_would_refuse(
    repo: Repo, tmp_path: Path
) -> None:
    """A clone whose origin .project.toml does not record: doctor fails and session start
    warns up front, not only merge's land step after the work is done."""
    result = doctor(repo)
    assert "ok    origin: none, so merge squashes onto main locally" in result.stdout
    other = tmp_path / "elsewhere.git"
    repo.git("init", "-q", "--bare", "-b", "main", str(other))
    repo.git("remote", "add", "origin", str(other))
    result = doctor(repo)
    assert result.returncode == 1
    line = f"FAIL  origin is {other}, but .project.toml records origin_url = ''"
    assert line in result.stdout, output(result)
    payload = '{"session_id": "t", "hook_event_name": "SessionStart", "source": "startup"}'
    start = subprocess.run(
        [sys.executable, "scripts/project.py", "hook", "session-start"],
        input=payload,
        cwd=repo.path,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(repo.trusted),
        timeout=300,
    )
    assert f"WARNING: merge will refuse to land: origin is {other}" in start.stdout, output(start)


def test_doctor_fails_on_gate_config_that_is_off(repo: Repo) -> None:
    repo.git("config", "--unset", "receive.hideRefs")
    result = doctor(repo)
    assert result.returncode == 1
    assert "FAIL  git config receive.hideRefs is unset: run mise install" in result.stdout


BASELINE = """\
# project-init baseline: shrink only. The lint debt found at adoption (N3): fix a file's findings,
# then delete its row. doctor fails when this block grows.
"src/tipcalc/__init__.py" = ["E501", "F401"]
"tests/test_cli.py" = [
    "ANN201",
    "S101",
]
"""
OWN_ROW = '"tests/**" = ["S101", "S603", "S607"]\n'  # the project's own row, above the block


def put_baseline(repo: Repo, block: str, own: str = "") -> None:
    """pyproject.toml with block where render puts the ruff baseline: after the project's own
    rows of [tool.ruff.lint.per-file-ignores] (own adds one more of those)."""
    path = repo.path / "pyproject.toml"
    text = path.read_text(encoding="utf-8")
    start = text.find("# project-init baseline")
    if start >= 0:  # replace the block: it runs up to the next table
        end = text.find("\n[", start)
        text = text[:start] + text[end + 1 :]
        text = text.replace(OWN_ROW, OWN_ROW + "\n", 1) if end >= 0 else text
    head, sep, tail = text.partition(OWN_ROW)
    assert sep, "the fixture's per-file-ignores row moved"
    path.write_text(head + OWN_ROW + own + block + tail.lstrip("\n"), encoding="utf-8")


def n3_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [line for line in result.stdout.splitlines() if " N3: " in line]


def test_doctor_holds_the_ruff_baseline_to_the_rows_render_wrote(
    repo: Repo, adopted: Adopted
) -> None:
    """helios: on the adoption branch, before G1, main has no baseline (no .project.toml at
    all), and comparing with main's pyproject counted all 426 rows as growth. The reference is
    the block as render wrote it: the first commit on the branch that holds it (main's block
    once G1 landed it). Growth counts per file, and only the block's rows count."""
    put_baseline(repo, BASELINE)
    tip = before_adoption(repo, adopted)[:10]
    result = doctor(repo)
    assert n3_lines(result) == [
        f"ok    N3: the ruff baseline did not grow (2 files, against {tip})"
    ], output(result)
    grown = BASELINE.replace('["E501", "F401"]', '["E501", "E741"]')
    put_baseline(repo, grown + '"src/tipcalc/extra.py" = ["E501"]\n', own='"docs/**" = ["E501"]\n')
    result = doctor(repo)
    assert result.returncode == 1
    fix = "it only shrinks, so fix the findings instead"
    assert n3_lines(result) == [
        f"FAIL  N3: the ruff baseline grew: src/tipcalc/__init__.py gains E741 (against {tip}); {fix}",
        f"FAIL  N3: the ruff baseline grew: src/tipcalc/extra.py gains E501 (against {tip}); {fix}",
    ], output(result)


def test_doctor_holds_the_ruff_baseline_to_main_once_adopted(repo: Repo) -> None:
    put_baseline(repo, BASELINE)
    repo.git("add", "pyproject.toml")
    landed = repo.run(
        "git", "commit", "-q", "-m", "chore: the baseline", "--trailer", MERGED_BY,
        env={"PROJECT_MERGE": "1"},
    )  # fmt: skip
    assert landed.returncode == 0, output(landed)
    chore_branch(repo, "lint")
    shrunk = BASELINE[: BASELINE.index('"tests/test_cli.py"')]
    put_baseline(repo, shrunk)
    result = doctor(repo)
    assert n3_lines(result) == [
        "ok    N3: the ruff baseline did not grow (1 file, against main)"
    ], output(result)
    put_baseline(repo, shrunk.replace('"F401"]', '"F401", "E741"]'))
    result = doctor(repo)
    assert n3_lines(result) == [
        (
            "FAIL  N3: the ruff baseline grew: src/tipcalc/__init__.py gains E741 (against main); "
            "it only shrinks, so fix the findings instead"
        )
    ], output(result)


def test_doctor_reads_the_render_before_its_commit(
    repo: Repo, adopted: Adopted, tmp_path: Path
) -> None:
    """helios: between render and the ship commit, .project.toml and the baseline exist only in
    the working tree. doctor reads origin_url there (it failed on origin_url = '' from the
    committed copies, which had none), and takes the block as render's own. With no origin,
    an empty origin_url is fine."""
    moved = repo.run(
        "git", "update-ref", "refs/heads/main", adopted.old_main, env={"PROJECT_MERGE": "1"}
    )
    assert moved.returncode == 0, output(moved)
    repo.git("switch", "-q", "-c", "plan/project-init")  # the adopted files: all uncommitted
    repo.git("reset", "-q")
    origin = tmp_path / "origin.git"
    repo.git("init", "-q", "--bare", "-b", "main", str(origin))
    repo.git("remote", "add", "origin", str(origin))
    toml = repo.path / ".project.toml"
    text = toml.read_text(encoding="utf-8")
    toml.write_text(text.replace('origin_url = ""', f'origin_url = "{origin}"'), "utf-8")
    put_baseline(repo, BASELINE)
    result = doctor(repo)
    out = output(result)
    assert "ok    origin: the origin_url .project.toml records, so merge opens a pull" in out
    assert "records origin_url = ''" not in out
    assert n3_lines(result) == [
        "ok    N3: the ruff baseline is render's, not committed yet: nothing to compare with"
    ], out
    toml.write_text(text, encoding="utf-8")
    repo.git("remote", "remove", "origin")
    result = doctor(repo)
    assert "ok    origin: none, so merge squashes onto main locally" in output(result)


# ---------------------------------------------------------------- release


def test_release_dry_run_with_distribution_none(repo: Repo) -> None:
    result = repo.project("release", "minor", "--dry-run")
    assert result.returncode == 1
    assert result.stdout.strip() == "no release for distribution: none"
    result = repo.project("release", "minor")
    assert result.returncode == 1
    assert "no release for distribution: none" in result.stdout


def test_release_of_a_git_distribution(repo: Repo) -> None:
    """Distribution git: the dry run bumps nothing and builds to a temp dir; the release
    itself lands a version commit on main (Merged-By) and tags it."""
    started = repo.project("change", "distribute", "--lane", "chore")
    assert started.returncode == 0, output(started)
    stack = repo.path / "specs/tech-stack.md"
    stack.write_text(
        stack.read_text("utf-8").replace("## Distribution\nnone", "## Distribution\ngit"), "utf-8"
    )
    repo.commit("docs(stack): installed from the repo")
    landed = repo.project("merge")
    assert landed.returncode == 0, output(landed)
    result = repo.project("release", "minor", "--dry-run")
    assert result.returncode == 0, output(result)
    assert "version ........... 0.1.0 -> 0.2.0" in result.stdout
    assert "no release tag yet, so nothing to bump from; this first release is v0.2.0" in (
        result.stdout
    )
    assert re.search(r"build \.+ tipcalc-0\.1\.0\S*(whl|tar\.gz)", result.stdout), result.stdout
    assert repo.git("status", "--porcelain").strip() == ""
    main = repo.head("main")
    result = repo.project("release", "minor")
    assert result.returncode == 0, output(result)
    assert repo.head("main~1") == main
    assert repo.git("log", "-1", "--format=%s", "main").strip() == "chore(release): v0.2.0"
    assert MERGED_BY in trailers(repo, "main")
    assert repo.git("rev-parse", "v0.2.0^{commit}").strip() == repo.head("main")
    assert 'version = "0.2.0"' in repo.show("main", "pyproject.toml")
    changelog = repo.show("main", "CHANGELOG.md")
    assert re.search(r"(?m)^## \[0\.2\.0\] - \d{4}-\d{2}-\d{2}$", changelog), changelog
    assert repo.branch() == "main"
    assert repo.git("branch", "--list", "release/*").strip() == ""


# ---------------------------------------------------------------- units


def test_the_change_templates_are_the_product_templates() -> None:
    project = load_project_module()
    for name, text in project.CHANGE_TEMPLATES.items():
        assert text == (PRODUCT_TEMPLATES / name).read_text(encoding="utf-8"), name
    assert project.BACKLOG_TEMPLATE == (PRODUCT_TEMPLATES / "backlog.md").read_text("utf-8")


def test_env_contract_rows_and_verdicts() -> None:
    project = load_project_module()
    rows, problems = project.env_contract(
        ENV_EXAMPLE
        + "# FLAG | knob | bool | no | - | x\n# COUNT | knob | int 1..5 | yes | - | x\n"
        + "# BAD | kind | str | no | - | x\n"
    )
    assert [row.name for row in rows] == ["TIPCALC_DEFAULT_PERCENT", "FLAG", "COUNT"]
    assert problems == [".env.example:7: kind is knob, secret or flag, not 'kind'"]
    percent, flag, count = rows
    assert project.judge_env(percent, None) == ("ok", "unset: default 15 applies")
    assert project.judge_env(percent, "") == ("ok", "empty: default 15 applies")
    # H17: only "" is empty, as env_ignore_empty reads it; spaces reach the app, which exits 2
    assert project.judge_env(percent, "  ") == ("FAIL", "the value is not a float")
    assert project.judge_env(percent, "12.5") == ("ok", "12.5 (float 0..100)")
    assert project.judge_env(flag, "maybe")[0] == "FAIL"
    assert project.judge_env(flag, "yes")[0] == "ok"
    assert project.judge_env(count, "") == (
        "warn",
        "empty, required and without a default: set it in .env",
    )
    assert project.judge_env(count, "7") == ("FAIL", "the value is outside 1..5")
    assert project.judge_env(count, "2.5") == ("FAIL", "the value is not an int")
    text = project.env_contract("# NOTE | knob | str | no | - | x\n")[0][0]
    assert project.judge_env(text, "free text") == ("ok", "set (str)")
    # orca re-check defect 1: the required column holds for secrets too
    needed, optional = project.env_contract(
        "# STRIPE_KEY | secret | str | yes | - | x\n# QWEN_API_KEY | secret | str | no | - | x\n"
    )[0]
    assert project.judge_env(needed, None)[0] == "FAIL"
    for value, unset in ((None, "unset"), ("", "empty")):
        assert project.judge_env(optional, value) == (
            "ok",
            f"secret, {unset}: optional (required no); its op:// pointer in .env turns it on",
        )
    assert project.judge_env(optional, "sk_live_x")[0] == "FAIL"  # set: still an op:// pointer
    assert project.judge_env(optional, "op://Private/qwen/credential")[0] == "ok"
    assert project.op_pointer("op://Private/stripe/credential")
    assert project.op_pointer("op://My Vault/stripe/api/credential")  # a section; names with spaces
    for bad in (
        "op://",
        "op://x",
        "op://x/y",
        "op://x//z",
        "op:/x/y/z",
        "sk_live_x",
        " op://a/b/c",
        "op://a/b/c <pasted after it>",
        "op://a/b/c/d/e",
        "op://a/b/c?x",
        "op://a/b/ c",
    ):
        assert not project.op_pointer(bad), bad
    assert project.op_pointer("op://Private/ssh key/private key?ssh-format=openssh")
    assert project.dotenv("export A='x'\nB=y # note\n# C=z\nD=\n") == {"A": "x", "B": "y", "D": ""}


def test_roadmap_close_ticks_or_adds_unplanned() -> None:
    project = load_project_module()
    text = "# Roadmap\n\n## Phase 1: a\n- [ ] one: first\n- [ ] two: second\n\n## Later\n- [ ] l: later\n"
    ticked, note = project.roadmap_close(text, "two", "feat: second")
    assert "- [x] two: second" in ticked and note == "ticked two"
    assert project.roadmap_close_problem(text, ticked, "two") is None
    added, note = project.roadmap_close(text, "new", "feat(cli): a new thing")
    assert "- [ ] two: second\n- [x] new: a new thing (unplanned)\n" in added
    assert project.roadmap_close_problem(text, added, "new") is None
    _, note = project.roadmap_close("## Phase 1: a\n- [x] a: x\n- [ ] b: y\n", "b", "feat: y")
    assert note == "ticked b (Phase 1: a: done)"


def test_status_line_and_run_it_rows() -> None:
    project = load_project_module()
    text = '---\nstatus: "approved"   # x\n---\n'
    assert project.with_status(text, "approved", "done") == '---\nstatus: "done"   # x\n---\n'
    assert project.with_status(text, "draft", "approved") is None
    row = "| `uv run --locked tipcalc 100 --split 4` | 0 | each: 28.75 | |\n"
    extra = row + "| `echo a \\| b` | 1 | a \\| b | |\n"
    rows = project.run_it_rows(VALIDATION.replace(row, extra))
    assert [row[1:] for row in rows] == [
        ("uv run --locked tipcalc 100 --split 4", "0", "each: 28.75", ""),
        ("echo a | b", "1", "a | b", ""),
    ]


# ---------------------------------------------------------------- v3.1 M12: the trunk map

TRUNK_SECTION = "\n## Trunk\n- src/tipcalc/__init__.py: the entrypoint every command runs through\n"
ENTRY_NOTE = "    # the entrypoint every command runs through\n"


def replace_in(repo: Repo, rel: str, old: str, new: str) -> None:
    text = (repo.path / rel).read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {rel}"
    repo.write(rel, text.replace(old, new, 1))


def test_merge_asks_for_the_trunk_diff_and_the_trunk_only_grows_freely(repo: Repo) -> None:
    """I19, I20 and the review tiers (design A.3, A.4): merge prints the branch diff limited to
    trunk files and needs a human to confirm reading it (--read-trunk without a terminal); the
    squash body records who. A branch that touches no trunk file asks nothing. Adding a Trunk
    entry is free; changing or removing one is a gate change."""
    main = repo.head("main")
    assert repo.project("change", "trunk-map", "--lane", "chore").returncode == 0
    repo.append("specs/tech-stack.md", TRUNK_SECTION)
    repo.commit("docs(specs): the trunk map")
    repo.write("junk.txt", "x\n")  # a dirty tree: merge stops after the cheap checks
    result = repo.project("merge")
    assert result.returncode == 1
    assert "  trunk ............. ok none" in result.stdout, output(result)
    assert "review depth  trunk: READ  0 files" in result.stdout
    (repo.path / "junk.txt").unlink()

    replace_in(
        repo,
        "src/tipcalc/__init__.py",
        "def main() -> None:\n",
        "def main() -> None:\n" + ENTRY_NOTE,
    )
    repo.commit("chore(cli): say what main is")
    result = repo.project("merge")
    assert result.returncode == 1
    text = result.stdout
    assert (
        "  trunk ............. FAIL 1 trunk file and no terminal to ask in: read the diff, then "
        "`! mise run merge -- --read-trunk`"
    ) in text, output(result)
    assert "- src/tipcalc/__init__.py (the entrypoint every command runs through)" in text
    assert "+" + ENTRY_NOTE.rstrip("\n") in text  # the trunk diff, in full
    assert (
        "review depth  trunk: READ  1 file  +1 -0  src/tipcalc/__init__.py (the entrypoint every "
        "command runs through)"
    ) in text
    assert "              leaf:  SKIM  1 file  +3 -0" in text
    assert repo.head("main") == main

    preview = repo.project("status", "--merge")
    assert preview.returncode == 0, output(preview)
    assert "  trunk ............. for a human 1 trunk file" in preview.stdout
    assert preview.stdout.rstrip().splitlines()[-1] == (
        "ready for a human: `! mise run merge -- --read-trunk` after reading the trunk diff"
    )
    result = repo.project("merge", "--read-trunk")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    assert "Trunk read by Test Author (--read-trunk): src/tipcalc/__init__.py" in body
    assert "Review depth:\n  trunk: READ  1 file  +1 -0  src/tipcalc/__init__.py" in body

    # adding an entry is free; changing (or removing) one is a gate change
    assert repo.project("change", "trunk-grows", "--lane", "chore").returncode == 0
    repo.append("specs/tech-stack.md", "- src/tipcalc/config.py: settings every module reads\n")
    repo.commit("docs(specs): config is trunk")
    repo.write("junk.txt", "x\n")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "  gate files ........ ok unchanged" in result.stdout, output(result)
    (repo.path / "junk.txt").unlink()
    replace_in(
        repo, "specs/tech-stack.md", "the entrypoint every command runs through", "the entrypoint"
    )
    repo.commit("docs(specs): a shorter why")
    result = repo.project("merge")
    assert result.returncode == 1
    assert "  gate files ........ FAIL changed: read the diff" in result.stdout, output(result)
    assert (
        "changed: specs/tech-stack.md ## Trunk (removed or changed: src/tipcalc/__init__.py)"
    ) in result.stdout
    assert "-- src/tipcalc/__init__.py: the entrypoint every command runs through" in result.stdout
    result = repo.project("merge", "--gate-change")
    assert result.returncode == 0, output(result)


def test_i18_a_trunk_file_the_plan_called_leaf(repo: Repo) -> None:
    """I18 (design A.3): each trunk file in a feat diff sits in the Files: of a risk: high
    group; otherwise merge refuses, and the plan edit that fixes it shows as amended after
    approval."""
    assert repo.project("change", "split-bill").returncode == 0
    repo.append("specs/tech-stack.md", TRUNK_SECTION)
    repo.commit("docs(specs): the trunk map")
    talk(repo)
    leaf_plan = PLAN.replace(
        "Files: src/tipcalc/__init__.py, tests/test_split.py", "Files: tests/test_split.py"
    )
    repo.write(f"{CHANGE}/plan.md", leaf_plan)
    assert repo.project("approve").returncode == 0
    compile_group(repo)  # it writes src/tipcalc/__init__.py: trunk
    confident(repo)
    result = repo.project("merge", "--attest", "--read-trunk")
    assert result.returncode == 1
    assert "  trunk in plan ..... FAIL 1 trunk file outside a risk: high group" in result.stdout, (
        output(result)
    )
    assert (
        "src/tipcalc/__init__.py: the plan said leaf, the diff touched trunk (the entrypoint "
        f"every command runs through): add it to a risk: high group's Files: in {CHANGE}/plan.md"
    ) in result.stdout
    repo.write(f"{CHANGE}/plan.md", PLAN.replace("risk: low", "risk: high"))
    repo.commit("spec(split-bill): G1 touches trunk")
    result = repo.project("merge", "--attest", "--read-trunk")
    assert result.returncode == 0, output(result)
    assert "  trunk in plan ..... ok 1 trunk file, each in a risk: high group" in result.stdout
    assert "  amended after approval .. ok plan.md changed" in result.stdout
    body = repo.git("log", "-1", "--format=%B", "main")
    assert f"Spec files changed after approval: {CHANGE}/plan.md" in body


def test_doctor_warns_when_the_trunk_map_is_missing(repo: Repo) -> None:
    result = doctor(repo)
    assert (
        "warn  specs/tech-stack.md has no ## Trunk section: every path counts as leaf, so merge "
        "asks no one to read a diff; add one (specs/README.md#formats)"
    ) in result.stdout, output(result)
    repo.append("specs/tech-stack.md", TRUNK_SECTION + "- tests/**:\n")
    result = doctor(repo)
    assert "ok    trunk: 1 entry in specs/tech-stack.md" in result.stdout, output(result)
    assert "FAIL  specs/tech-stack.md:" in result.stdout  # the entry without its why
    assert "no ## Trunk section" not in result.stdout


# ---------------------------------------------------------------- v3.1 M14: rollback and flags

SPLIT_FLAG = "TIPCALC_FLAG_SPLIT"
SPLIT_OFF = f"""
### Scenario: cli.split-off [flag-off: {SPLIT_FLAG}]
- GIVEN {SPLIT_FLAG} is unset
- WHEN the user runs `tipcalc 100 --split 4`
- THEN stdout is `tip: 15.0` alone, and the exit code is 0
"""
TEST_SPLIT_FLAG = (
    TEST_SPLIT.replace(
        'tipcalc("100", "--split", "4")',
        f'tipcalc("100", "--split", "4", env={{"{SPLIT_FLAG}": "1"}})',
    )
    + """

@pytest.mark.spec("cli.split-off")
def test_split_off() -> None:
    r = tipcalc("100", "--split", "4")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.0\\n"
"""
)
SPLIT_FLAG_CODE = SPLIT_CODE.replace(
    '    if len(sys.argv) > 3 and sys.argv[2] == "--split":\n',
    f'    split = os.environ.get("{SPLIT_FLAG}", "") in ("1", "true", "yes", "on")\n'
    '    if split and len(sys.argv) > 3 and sys.argv[2] == "--split":\n',
)
NO_RUN_IT = VALIDATION.split("## Run it")[0] + NO_CHECKS


def land_flag_change(repo: Repo) -> subprocess.CompletedProcess[str]:
    """split-bill as a flag: change, from change to merge: its flag row, a [flag-off] guard,
    the code behind the flag. The merge's result."""
    assert repo.project("change", "split-bill").returncode == 0
    repo.append(".env.example", f"# {SPLIT_FLAG} | flag | bool | no | 0 | --split (split-bill)\n")
    repo.commit("chore(env): the split-bill flag, off")
    talk(repo)
    text = (repo.path / CHANGE / "requirements.md").read_text(encoding="utf-8")
    repo.write(
        f"{CHANGE}/requirements.md",
        text.split("## Rollback")[0] + f"## Rollback\nflag: {SPLIT_FLAG}\n",
    )
    repo.write(
        f"{CHANGE}/plan.md", PLAN.replace("cli.split-bill |", "cli.split-bill cli.split-off |")
    )
    repo.write(f"{CHANGE}/validation.md", NO_RUN_IT)
    repo.append("specs/capabilities/cli.md", SPLIT_OFF)
    result = repo.project("approve")
    assert result.returncode == 0, output(result)
    repo.write("tests/test_split.py", TEST_SPLIT_FLAG)
    repo.write("src/tipcalc/__init__.py", SPLIT_FLAG_CODE)
    repo.commit("feat(cli): split the bill behind a flag", "--trailer", "Spec: cli.split-bill")
    confident(repo)
    return repo.project("merge")


def test_a_flag_change_lands_with_its_launch_item(repo: Repo) -> None:
    """Design B.2: a flag: change has its flag row and a [flag-off] guard, which prove-red wants
    to pass on the old code; merge's close commit adds the launch backlog item, and the squash
    body records the Rollback line."""
    result = land_flag_change(repo)
    assert result.returncode == 0, output(result)
    launch = f"specs/backlog/{TODAY}-launch-split-bill.md"
    assert "guards 1/1 pass" in result.stdout
    assert f"{launch} (launch: flip {SPLIT_FLAG} on" in result.stdout
    item = repo.show("main", launch)
    assert item.startswith("---\nstatus: open ")
    assert (
        f"Flip {SPLIT_FLAG} on, then remove the flag, its off path and its [flag-off: "
        f"{SPLIT_FLAG}] scenarios"
    ) in item
    assert f"{CHANGE}" in item
    body = repo.git("log", "-1", "--format=%B", "main")
    assert f"Rollback: flag: {SPLIT_FLAG}" in body
    assert "cli.split-off flag-off guard: passes on the old code" in body


def test_a_one_way_change_asks_its_own_human_check(repo: Repo) -> None:
    """Design B.3: merge asks "I read the one-way part: <what>" like any Human check (--attest
    without a terminal), outside validation.md's cap; the squash body keeps the one-way line."""
    what = "the split output becomes a format other tools parse"
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    text = (repo.path / CHANGE / "requirements.md").read_text(encoding="utf-8")
    repo.write(
        f"{CHANGE}/requirements.md",
        text.split("## Rollback")[0] + f"## Rollback\none-way: {what}\n",
    )
    repo.write(f"{CHANGE}/plan.md", PLAN.replace("risk: low", "risk: high"))
    repo.write(f"{CHANGE}/validation.md", VALIDATION.split("## Human checks")[0] + NO_CHECKS)
    assert repo.project("approve").returncode == 0
    compile_group(repo)
    confident(repo)
    result = repo.project("merge")
    assert result.returncode == 1
    assert "human checks ...... FAIL 1 check and no terminal to ask in" in result.stdout, output(
        result
    )
    assert f"- I read the one-way part: {what}" in result.stdout
    result = repo.project("merge", "--attest")
    assert result.returncode == 0, output(result)
    body = repo.git("log", "-1", "--format=%B", "main")
    assert f"Rollback: one-way: {what}" in body
    assert f"- I read the one-way part: {what} (attested by Test Author, --attest)" in body


# ---------------------------------------------------------------- v3.1 M16: launch


def test_a_launch_marks_its_roadmap_item() -> None:
    """Design D.2: a branch whose slug is launch-<slug> launches the roadmap item <slug>; its
    merge appends ` (launched <date>)` to that ticked item, which still reads as the same item.
    An item not ticked, missing or launched already cannot be marked."""
    project = load_project_module()
    assert project.launch_target("launch-split-bill") == "split-bill"
    for slug in ("split-bill", "launch", "launch-", "launcher-x", None):
        assert project.launch_target(slug) is None, slug
    text = "## Phase 1: a\n- [x] one: first\n- [ ] two: second\n"
    marked, problem = project.roadmap_launch(text, "one", "2026-09-26")
    assert problem is None
    assert marked == "## Phase 1: a\n- [x] one: first (launched 2026-09-26)\n- [ ] two: second\n"
    assert project.roadmap_items(marked) == {"one": True, "two": False}
    assert project.roadmap_launch_problem(text, marked, "one") is None
    for slug, why in (
        ("two", "'two' is not ticked yet: its change merges first"),
        ("three", "has no item 'three' to mark launched"),
    ):
        unchanged, problem = project.roadmap_launch(text, slug, "2026-09-26")
        assert unchanged == text and why in (problem or ""), problem
    problem = project.roadmap_launch(marked, "one", "2026-09-27")[1]
    assert "'one' is launched already" in (problem or ""), problem


def test_status_lists_the_items_not_launched_flags_first(tmp_path: Path) -> None:
    """Design D.2: status on the default branch lists the ticked roadmap items without the
    launched mark, those with a live flag first (a flag row whose notes name the item or one of
    its changes, or the flag a change's Rollback line names), at most 4 below one line."""
    project = load_project_module()
    assert project.launch_lines([]) == []
    assert project.launch_lines([("a", [])]) == [
        "launch: 1 merged roadmap item is not launched yet (next: /sdd launch a)",
        "  a",
    ]
    items = [("a", []), ("b", ["APP_FLAG_B"]), ("c", []), ("d", ["X", "Y"]), ("e", []), ("f", [])]
    assert project.launch_lines(items) == [
        (
            "launch: 6 merged roadmap items are not launched yet, the first 4 below "
            "(next: /sdd launch b)"
        ),
        "  b (flag APP_FLAG_B)",
        "  d (flags X, Y)",
        "  a",
        "  c",
    ]
    roadmap = (
        "# Roadmap\n\n## Phase 1: one\n- [x] done-long-ago: x (launched 2026-01-01)\n"
        "- [x] cards: y\n- [x] export: z\n- [ ] later: w\n"
    )
    (tmp_path / "specs").mkdir()
    (tmp_path / "specs/roadmap.md").write_text(roadmap, encoding="utf-8")
    (tmp_path / ".env.example").write_text(
        "# NAME | kind | type | required | default | notes\n"
        "# APP_FLAG_CSV | flag | bool | no | 0 | csv output (change 2026-09-20-export)\n"
        "# APP_KNOB | knob | int | no | 1 | export batch size\n",
        encoding="utf-8",
    )
    assert project.unlaunched_items(tmp_path, {}) == [("cards", []), ("export", ["APP_FLAG_CSV"])]


def test_a_launch_lane_marks_its_roadmap_item_launched(repo: Repo) -> None:
    """Design D.1 and D.2: once a flag: change lands, status on main lists its roadmap item as
    not launched, with its live flag. The launch file edited on main rides into the launch lane,
    chg/launch-<slug>, which keeps the new behaviour on for good and removes the flag, its off
    path and its [flag-off] scenario. Its merge appends ` (launched <date>)` to the item, and
    the squash keeps the launch record from the commit body."""
    result = land_flag_change(repo)
    assert result.returncode == 0, output(result)
    status = repo.project("status")
    assert (
        "launch: 1 merged roadmap item is not launched yet (next: /sdd launch split-bill)"
    ) in status.stdout, output(status)
    assert f"  split-bill (flag {SPLIT_FLAG})" in status.stdout

    launch = f"specs/backlog/{TODAY}-launch-split-bill.md"
    checklist = "\n## Launch checklist\n- [x] split a bill end to end with the flag on\n"
    repo.append(launch, checklist)  # tracked on main: an edited backlog file waits, too
    result = repo.project("change", "launch-split-bill", "--lane", "chg")
    assert result.returncode == 0, output(result)
    assert checklist in (repo.path / launch).read_text(encoding="utf-8")

    repo.git("rm", "-q", "-f", "--", launch)
    repo.write(".env.example", ENV_EXAMPLE)
    cli = (repo.path / "specs/capabilities/cli.md").read_text(encoding="utf-8")
    repo.write("specs/capabilities/cli.md", cli.replace(SPLIT_OFF, ""))
    repo.write("tests/test_split.py", TEST_SPLIT)
    repo.write("src/tipcalc/__init__.py", SPLIT_CODE)
    record = "Launch of split-bill: 4 lenses, no finding open; the checklist is done."
    repo.commit(
        f"change(cli): split the bill without a flag\n\n{record}",
        "--trailer",
        "Spec: cli.split-bill",
        "--trailer",
        "Spec-Removed: cli.split-off",
    )
    preview = repo.project("status", "--merge")
    assert "roadmap marked split-bill launched" in preview.stdout, output(preview)
    result = repo.project("merge")
    assert result.returncode == 0, output(result)
    assert "marked split-bill launched" in result.stdout
    roadmap = repo.show("main", "specs/roadmap.md")
    line = f"- [x] split-bill: split the bill and the tip between people (launched {TODAY})"
    assert line in roadmap.splitlines(), roadmap
    assert launch not in repo.git("ls-tree", "-r", "--name-only", "main").split()
    assert record in repo.git("log", "-1", "--format=%B", "main")
    status = repo.project("status")
    assert "not launched" not in status.stdout, output(status)


def test_a_launch_without_a_flag_lands_as_a_chore(repo: Repo) -> None:
    """Design D.1: with no flag, the launch lane is chore/launch-<slug>. Its one commit is empty
    when the launch file was never committed, and its body is the launch record; its merge marks
    the item launched."""
    assert repo.project("change", "split-bill").returncode == 0
    talk(repo)
    repo.write(f"{CHANGE}/validation.md", NO_RUN_IT)
    assert repo.project("approve").returncode == 0
    compile_group(repo)
    confident(repo)
    result = repo.project("merge")
    assert result.returncode == 0, output(result)
    status = repo.project("status")
    assert "(next: /sdd launch split-bill)\n  split-bill\n" in status.stdout, output(status)

    assert repo.project("backlog", "launch-split-bill").returncode == 0
    launch = repo.path / f"specs/backlog/{TODAY}-launch-split-bill.md"
    result = repo.project("change", "launch-split-bill", "--lane", "chore")
    assert result.returncode == 0, output(result)
    launch.unlink()  # never committed: the launch commit is empty
    record = "Launch of split-bill: 4 lenses, 1 finding dismissed; the checklist is done."
    committed = repo.run(
        "git", "commit", "-q", "--allow-empty", "-m", "chore(launch): split-bill", "-m", record
    )
    assert committed.returncode == 0, output(committed)
    result = repo.project("merge")
    assert result.returncode == 0, output(result)
    roadmap = repo.show("main", "specs/roadmap.md").splitlines()
    line = f"- [x] split-bill: split the bill and the tip between people (launched {TODAY})"
    assert line in roadmap, roadmap
    body = repo.git("log", "-1", "--format=%B", "main")
    assert body.startswith("chore(launch): split-bill\n") and record in body
