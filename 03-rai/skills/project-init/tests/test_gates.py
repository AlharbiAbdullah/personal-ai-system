"""project-init v3, milestone M4: the git gates.

templates/githooks/{pre-commit,commit-msg,pre-push} are two-line shims into `project.py hook`,
templates/githooks/reference-transaction guards the default branch in plain sh, and
templates/gitleaks.toml holds the leak rules. fixtures/make_gates.sh renders them into the
tipcalc fixture on plan/project-init, before any hook is active.

`project.py selftest` is the M4 matrix (design section 12) run for real in a scratch clone with
a bare origin, so test_selftest_* check that every row comes back as specified, and that a gate
switched off makes the selftest fail. The other tests drive the hooks in a copy of the fixture,
for rules the matrix shows only once: which skips and xfails count as new, the feat lane before
approval, and `commit -a` (git's own temporary index).
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
PROJECT_PY = SKILL / "templates" / "scripts" / "project.py"
HOOKS = SKILL / "templates" / "githooks"
MAKE_GATES = TESTS / "fixtures" / "make_gates.sh"
TIPCALC_SOURCE = Path(os.environ.get("TIPCALC_SOURCE", Path.home() / "projects" / "tipcalc"))

# The M4 table (design section 12), as the selftest names its rows.
MATRIX = (
    "first commit in a fresh repo",
    "commit on main",
    "--no-verify commit on main",
    "branch -f main feat/x",
    "update-ref refs/heads/main feat/x",
    "reset --hard HEAD~1 on main",
    "fast-forward merge into main",
    "forged origin/main, then branch -f main origin/main",
    "origin re-pointed at a fake repo, then synced",
    "origin unreachable, branch -f main feat/x",
    "branch -m main away while main is packed",
    "recreate main at another commit",
    "pack-refs --all",
    "gc",
    "pull --ff-only to what origin holds",
    "reset --hard origin/main to what origin holds",
    "ff merge into main with PROJECT_MERGE=1",
    "push main to an empty origin",
    "push main once origin has it",
    "push main with PROJECT_MERGE=1",
    "push feat/x:main",
    "push -u origin feat/main-menu",
    "staged fake AWS key",
    "gitleaks missing",
    "staged .md with a vault path",
    "staged .md naming k8s/helm/01-base",
    "partially staged .py, ruff error in the staged copy",
    "partially staged .py, ty error in the staged copy",
    "specs/mission.md staged on feat/",
    "new bare @pytest.mark.skip",
    "message 'update stuff'",
    "feat(cli): x touching src without Spec:",
    "test tagged nope.nope",
    "scenario removed, its test kept",
    "scenario and test removed, no Spec-Removed:",
    "a commit from a worktree",
)
# Rows the selftest adds to the design's table: hardening found while building M4, and the
# sanctioned `git merge main` of a lane branch.
EXTRA = (
    "staged .md with a home path",
    "branch -m main away while main is loose",
    "origin_url forged by git replace, origin re-pointed, then synced",
    "push feat/x:main to a remote that has no main",
    "push . feat/x:main into this repo",
    "CHANGELOG.md staged on feat/",
    "edit a done change folder",
    # M15: I24 in pre-commit, a proof file against its README.md entry
    "a proof capture with its README.md entry",
    "a proof file edited by hand",
    "new strict xfail naming a gap id",
    "scenario added without a test",
    "scenario and test removed with Spec-Removed:",
    "git merge main into a lane branch",
    "a conflicted merge that also edits specs/mission.md",
    "a conflicted merge of main, resolved",
    # round 1 of the M4 review: every I16 path it found, and the rules it bent
    "recreate main at another commit (loose)",
    "delete main (branch -D)",
    "recreate main at origin's tip after deleting it",
    "origin's main moved outside merge (send-pack), then pull --ff-only",
    "origin's main moved outside merge (send-pack), then reset --hard origin/main",
    "push --no-verify . feat/x:main into this repo",
    "send-pack . feat/x:main into this repo",
    "push feat/x:main with default_branch edited in .project.toml",
    "new skip() imported from pytest without an id",
    "new pt.skip() with pytest imported as pt without an id",
    "new pytest.importorskip() without an id",
    "git's own subject 'Revert \"docs: notes\"'",
    "git's own subject 'fixup! docs: notes'",
    "feat(cli): x touching src, [paths] src edited in the working tree",
    "scenario added without a test on feat/ with no change folder",
    "a clean merge of two edits to one src file",
    "src edited by hand during a merge, no Spec:",
    "delete main while it is the only branch",
    "then create main at another commit",
    "reset --hard main to a commit without .githooks",
    "fast-forward main to a commit that weakens the guard",
    "commit on main with the guard emptied in the working tree",
    "branch -f main with the guard's x bit cleared",
    # round 2 of the M4 review
    "staged .md with a macOS home folder",
    "staged .md with $HOME/helm",
    "git's own subject 'Reapply \"docs: notes\"'",
    "message 'Revert \"update stuff\"'",
    "new skip in a conftest.py at the repo root",
    "new skip named by a string (getattr on pytest.mark)",
    "recreate main after every ref and reflog is gone",
    # round 3 of the M4 review: moves git makes without a ref transaction, a missing tool,
    # config that steers the guard's ls-remote, and the cleanup that decides a commit's subject
    "branch -M main on a lane branch",
    "the refused rename put feat/renamed back, still checked out",
    "a ref update after branch -C onto main",
    "put main back where the guard saw it",
    "branch -m onto a deleted main",
    "feat/renamed is still there after the refused rename",
    "branch -M main on a lane branch (guard emptied in the working tree)",
    "the refused rename put feat/renamed back, still checked out (guard emptied in the working tree)",
    "a ref update after branch -C onto main (guard emptied in the working tree)",
    "put main back where the guard saw it (guard emptied in the working tree)",
    "git -c remote.origin.uploadpack=<fake repo> branch -f main <forged Merged-By>",
    "remote.origin.uploadpack=<fake repo> in .git/config, branch -f main <forged>",
    "the same pull --ff-only with grep missing from PATH",
    "message '# update stuff' then 'docs: x' (-m keeps the comment line)",
    "--cleanup=verbatim with the first line '# update stuff'",
    "core.commentChar=f and --cleanup=strip drop the subject 'feat: x'",
    "message 'docs: notes' then a comment line",
    # the M11 remote trial: url.<base>.insteadOf, followed from the user's git config only
    "pull --ff-only through a url.<base>.insteadOf in the user's git config",
    "url.<fake repo>.insteadOf <origin> in .git/config, then synced",
    # rollout review R2: the guard reads ~/.gitconfig whatever GIT_CONFIG_GLOBAL names
    "GIT_CONFIG_GLOBAL names url.<fake repo>.insteadOf <origin>, then fetch main:main",
)
# M6: the Claude Code hooks (design 6.P5's pre-bash cases, session-start's cap, the launcher),
# which the selftest runs after the git matrix.
CLAUDE_HOOK_ROWS = (
    "pre-bash denies mise run merge",
    'pre-bash denies sh -c "PROJECT_MERGE=1 git merge x"',
    "pre-bash denies bash ./x.sh (x.sh sets PROJECT_MERGE=1)",
    "pre-bash denies git -c core.hooksPath=/dev/null commit",
    "pre-bash denies git -c core.hookspath=/dev/null commit",
    "pre-bash denies git -c hook.project-main-guard.enabled=false branch -f main x",
    "pre-bash denies git send-pack origin feat/x:main",
    "pre-bash denies gh api -X PUT repos/o/r/pulls/1/merge",
    "pre-bash denies gh api -X DELETE repos/o/r/branches/main/protection",
    "pre-bash denies cp /tmp/h .githooks/pre-commit",
    "pre-bash allows grep -n PROJECT_MERGE scripts/project.py",
    "pre-bash allows git config --get core.hooksPath",
    "pre-bash allows grep -- --no-verify specs/README.md",
    "pre-bash allows mise run test -- -k merge",
    "session-start with 12 lessons: 3 KB at most, the newest 5 in it",
    "pre-bash from a worktree runs that worktree's project.py",
    "pre-bash in the main checkout runs its own project.py",
    "session-start from a worktree runs that worktree's copy, on its branch",
    "pre-bash from a worktree still blocks mise run merge",
)
TIMING = re.compile(r" \(\d+\.\d s\)$")


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
        MISE_TRUSTED_CONFIG_PATHS=str(trusted),  # the hooks run `mise x` in the fixture
    )
    return env


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def load_project() -> ModuleType:
    spec = importlib.util.spec_from_file_location("project_gates_under_test", PROJECT_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    keep, sys.dont_write_bytecode = sys.dont_write_bytecode, True  # no __pycache__ in templates/
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = keep
    return module


class Repo:
    def __init__(self, path: Path, trusted: Path) -> None:
        self.path = path
        self.trusted = trusted

    def run(
        self, *argv: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=self.path,
            capture_output=True,
            text=True,
            check=False,
            env={**clean_env(self.trusted), **(env or {})},
            timeout=900,
        )

    def git(self, *args: str) -> str:
        result = self.run("git", *args)
        assert result.returncode == 0, output(result)
        return result.stdout

    def write(self, rel: str, text: str) -> None:
        path = self.path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def append(self, rel: str, text: str) -> None:
        with (self.path / rel).open("a", encoding="utf-8") as handle:
            handle.write(text)

    def commit(self, *args: str) -> subprocess.CompletedProcess[str]:
        """git commit with the hooks on."""
        return self.run("git", "commit", "-q", *args)

    def commit_unhooked(self, message: str) -> None:
        self.git("add", "-A")
        self.git("-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", message)

    def selftest(self) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, str(PROJECT_PY), "selftest")


@pytest.fixture(scope="session")
def gates(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not (TIPCALC_SOURCE / ".git").exists():
        pytest.skip(f"no tipcalc repo at {TIPCALC_SOURCE} (set TIPCALC_SOURCE)")
    dest = tmp_path_factory.mktemp("m4") / "tipcalc"
    result = subprocess.run(
        ["sh", str(MAKE_GATES), str(dest), str(TIPCALC_SOURCE)],
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(dest.parent),
    )
    assert result.returncode == 0, output(result)
    return dest


@pytest.fixture
def repo(gates: Path, tmp_path: Path) -> Repo:
    """A copy of the fixture (no .venv: its editable install points at the original) with the
    hooks on, on a lane branch."""
    dest = tmp_path / "tipcalc"
    shutil.copytree(gates, dest, symlinks=True, ignore=shutil.ignore_patterns(".venv", ".cache"))
    repo = Repo(dest, tmp_path)
    installed = repo.run(sys.executable, "scripts/project.py", "hook", "install")
    assert installed.returncode == 0, output(installed)
    repo.git("switch", "-q", "-c", "feat/gates")
    return repo


def test_templates_are_shims_and_sh() -> None:
    for name in ("pre-commit", "commit-msg", "pre-push"):
        path = HOOKS / name
        assert path.read_text(encoding="utf-8").splitlines() == [
            "#!/bin/sh",
            f'exec mise x -- uv run --script scripts/project.py hook {name} "$@"',
        ]
        assert os.access(path, os.X_OK)
    guard = HOOKS / "reference-transaction"
    assert os.access(guard, os.X_OK)
    text = guard.read_text(encoding="utf-8")
    assert text.startswith("#!/bin/sh\n") and "D={DEFAULT_BRANCH};" in text
    assert subprocess.run(["sh", "-n", str(guard)], check=False).returncode == 0
    mise = tomllib.loads((SKILL / "templates" / "mise.python.toml").read_text(encoding="utf-8"))
    postinstall = mise["hooks"]["postinstall"]
    assert postinstall.endswith("uv run --script scripts/project.py hook install")
    config = tomllib.loads((SKILL / "templates" / "gitleaks.toml").read_text(encoding="utf-8"))
    assert config["extend"] == {"useDefault": True}
    rules = {rule["id"] for rule in config["rules"]}
    assert rules == {"personal-path", "personal-home-path", "wiki-link"}


def test_selftest_runs_the_whole_matrix(gates: Path, tmp_path: Path) -> None:
    result = Repo(gates, tmp_path).selftest()
    text = output(result)
    assert result.returncode == 0, text
    rows = {TIMING.sub("", line[6:]) for line in text.splitlines() if line.startswith("ok    ")}
    missing = [name for name in (*MATRIX, *EXTRA, *CLAUDE_HOOK_ROWS) if name not in rows]
    assert not missing, text
    assert "FAIL" not in text
    assert text.rstrip().splitlines()[-1].startswith("selftest: ok (")


def test_selftest_fails_when_a_gate_is_off(repo: Repo) -> None:
    """The selftest reads the working tree: a reference-transaction that lets everything through
    must turn the main-guard rows into FAIL lines."""
    repo.write(".githooks/reference-transaction", "#!/bin/sh\nexit 0\n")
    result = repo.selftest()
    text = output(result)
    assert result.returncode == 1, text
    assert "FAIL  commit on main" in text
    assert "FAIL  branch -f main feat/x" in text
    assert "FAIL  recreate main at another commit" in text
    assert "ok    staged fake AWS key" in text  # the other gates still hold


DOC = '"""Tests."""\n\n'
TEST_HEAD = DOC + "import pytest\n"


def test_a_skip_head_already_had_is_not_new(repo: Repo) -> None:
    legacy = '\n\n@pytest.mark.skip\ndef test_legacy() -> None:\n    """Old."""\n'
    repo.write("tests/test_legacy.py", TEST_HEAD + legacy)
    repo.commit_unhooked("test: a legacy skip")
    added = '\n\ndef test_more() -> None:\n    """More."""\n'
    repo.append("tests/test_legacy.py", added)
    repo.git("add", "tests/test_legacy.py")
    result = repo.commit("-m", "test: more")
    assert result.returncode == 0, output(result)
    repo.append("tests/test_legacy.py", legacy.replace("legacy", "second"))
    repo.git("add", "tests/test_legacy.py")
    result = repo.commit("-m", "test: a second skip")
    assert result.returncode == 1
    assert "tests/test_legacy.py:15: a new skip needs a scenario id" in output(result)


@pytest.mark.parametrize(
    ("code", "problem"),
    [
        ('\n\ndef test_x() -> None:\n    pytest.skip("cli.tip-default: needs a network")\n', None),
        (
            (
                '\n\n@pytest.mark.xfail(strict=True, reason="cli.no-args: traceback")\n'
                'def test_x() -> None:\n    """Gap."""\n'
            ),
            None,
        ),
        (
            '\n\n@pytest.mark.skipif(True, reason="flaky")\ndef test_x() -> None:\n    """X."""\n',
            "a new skipif needs a scenario id",
        ),
        (
            (
                '\n\n@pytest.mark.xfail(reason="cli.no-args: traceback")\n'
                'def test_x() -> None:\n    """X."""\n'
            ),
            "a new xfail needs strict=True",
        ),
        (
            (
                '\n\n@pytest.mark.xfail(strict=True, reason="cli.tip-default: not a gap")\n'
                'def test_x() -> None:\n    """X."""\n'
            ),
            "a new xfail needs strict=True and a [gap] scenario id",
        ),
        ('\n\ndef test_x() -> None:\n    pytest.xfail("cli.no-args: later")\n', "pytest.xfail()"),
        # names resolve through imports and plain aliases
        (
            DOC + 'from pytest import skip\n\n\ndef test_x() -> None:\n    skip("later")\n',
            "a new skip() needs a scenario id",
        ),
        (
            DOC
            + 'from pytest import skip as later\n\n\ndef test_x() -> None:\n    later("later")\n',
            "a new skip() needs a scenario id",
        ),
        (
            '\nskip = pytest.skip\n\n\ndef test_x() -> None:\n    skip("later")\n',
            "a new skip() needs a scenario id",
        ),
        (
            DOC + 'import pytest as pt\n\n\ndef test_x() -> None:\n    pt.skip("later")\n',
            "a new skip() needs a scenario id",
        ),
        (
            DOC
            + 'from pytest import mark as m\n\n\n@m.skip\ndef test_x() -> None:\n    """X."""\n',
            "a new skip needs a scenario id",
        ),
        (
            '\n\ndef test_x() -> None:\n    pytest.importorskip("tipcalc_missing")\n',
            "a new importorskip() needs a scenario id",
        ),
        # what skip() and xfail() raise, raised by hand
        (
            DOC + "from _pytest.outcomes import Skipped\n\n\n"
            'def test_x() -> None:\n    raise Skipped("later")\n',
            "a new skip() needs a scenario id",
        ),
        (
            '\n\ndef test_x() -> None:\n    raise pytest.xfail.Exception("later")\n',
            "pytest.xfail()",
        ),
        ("\n\ndef test_x() -> None:\n    raise pytest.skip.Exception\n", "a new skip() needs"),
        (
            '\n\ndef test_x() -> None:\n    raise pytest.skip.Exception("cli.tip-default: net")\n',
            None,
        ),
        (
            (
                "\n\ndef test_x() -> None:\n"
                '    pytest.importorskip("tipcalc_missing", reason="cli.tip-default: extra")\n'
            ),
            None,
        ),
        (
            (
                DOC + 'import unittest\n\n\n@unittest.skipIf(True, "flaky")\n'
                'def test_x() -> None:\n    """X."""\n'
            ),
            "a new skipif needs a scenario id",
        ),
        (
            (
                DOC + "import unittest\n\n\nclass TestX(unittest.TestCase):\n"
                '    def test_x(self) -> None:\n        self.skipTest("later")\n'
            ),
            "a new skip() needs a scenario id",
        ),
        (
            (
                DOC + "from unittest import expectedFailure\n\n\n@expectedFailure\n"
                'def test_x() -> None:\n    """X."""\n'
            ),
            "a new xfail needs strict=True",
        ),
        # a marker named by a string: the reason rule cannot read it
        (
            '\n\n@getattr(pytest.mark, "sk" + "ip")\ndef test_x() -> None:\n    """X."""\n',
            "a skip or xfail named by a string",
        ),
        (
            (
                '\nNAME = "xf" + "ail"\n\n\n@pytest.mark.__getattr__(NAME)\n'
                'def test_x() -> None:\n    """X."""\n'
            ),
            "a skip or xfail named by a string",
        ),
        (
            (
                "\n\ndef test_x(request: pytest.FixtureRequest) -> None:\n"
                '    request.applymarker("xfail")\n'
            ),
            "a skip or xfail named by a string",
        ),
        (
            DOC + 'import math\n\nNAME = "p" + "i"\n\n\ndef test_x() -> None:\n'
            "    assert getattr(math, NAME) > 3\n",
            None,
        ),
    ],
)
def test_skip_and_xfail_forms(repo: Repo, code: str, problem: str | None) -> None:
    repo.write("tests/test_forms.py", code if code.startswith(DOC) else TEST_HEAD + code)
    repo.git("add", "tests/test_forms.py")
    result = repo.commit("-m", "test: forms")
    if problem is None:
        assert result.returncode == 0, output(result)
    else:
        assert result.returncode == 1
        assert problem in output(result)


def test_skips_outside_the_test_folders_count(repo: Repo) -> None:
    """A conftest.py at the repo root, or a plugin module, skips tests as well as a test file."""
    hook = (
        DOC + "import pytest\n\n\n"
        "def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:\n"
        '    """Skip them all."""\n'
        "    for item in items:\n"
        '        item.add_marker("skip")\n'
    )
    repo.write("conftest.py", hook)
    repo.git("add", "conftest.py")
    result = repo.commit("-m", "test: skip all")
    assert result.returncode == 1
    assert "conftest.py:9: a skip or xfail named by a string" in output(result)
    plugin = DOC + "import pytest\n\nLATER = pytest.mark.skip\n"
    repo.git("rm", "-q", "--cached", "conftest.py")
    repo.write("src/tipcalc/later.py", plugin)
    repo.git("add", "src/tipcalc/later.py")
    result = repo.commit("-m", "test: later")
    assert result.returncode == 1
    assert "src/tipcalc/later.py:5: a new skip needs a scenario id" in output(result)


def test_mark_imported_from_pytest_counts(repo: Repo) -> None:
    code = '"""Tests."""\n\nfrom pytest import mark\n\n\n@mark.skip\ndef test_x() -> None:\n'
    repo.write("tests/test_forms.py", code + '    """X."""\n')
    repo.git("add", "tests/test_forms.py")
    result = repo.commit("-m", "test: forms")
    assert result.returncode == 1
    assert "a new skip needs a scenario id" in output(result)


SCENARIO = "\n### Scenario: cli.{slug}\n- WHEN the user runs `tipcalc {slug}`\n- THEN it works\n"


def test_feat_scenarios_need_tests_once_approved(repo: Repo) -> None:
    """Talk writes scenarios before tests and approve commits them; after approval a scenario
    comes with its test in the same commit (I4, the drift rule)."""
    repo.git("switch", "-q", "-c", "feat/demo")
    requirements = "specs/changes/2026-09-24-demo/requirements.md"
    fields = "---\nchange: 2026-09-24-demo\nlane: feat\nstatus: {}\nroadmap: demo\n"
    repo.append("specs/capabilities/cli.md", SCENARIO.format(slug="demo"))
    repo.git("add", "-A")
    result = repo.commit("-m", "spec(demo): draft")  # no change folder yet: I4 holds
    assert result.returncode == 1
    assert "I4: scenario cli.demo is added in this commit" in output(result)
    repo.write(requirements, fields.format("draft") + 'title: "feat: demo"\n---\n')
    repo.git("add", "-A")
    result = repo.commit("-m", "spec(demo): draft")  # the open change: talk's window
    assert result.returncode == 0, output(result)
    repo.write(requirements, fields.format("approved") + 'title: "feat: demo"\n---\n')
    repo.git("add", "-A")
    result = repo.commit("-m", "spec(demo): approve")
    assert result.returncode == 0, output(result)
    repo.append("specs/capabilities/cli.md", SCENARIO.format(slug="demo-two"))
    repo.git("add", "-A")
    result = repo.commit("-m", "spec(demo): more")
    assert result.returncode == 1
    assert "I4: scenario cli.demo-two is added in this commit" in output(result)


def colocate(repo: Repo) -> None:
    """The fixture with its tests inside the package, as the tipcalc and orca trials keep them
    (src/tipcalc/tests, no testpaths): [paths] tests and the ruff rows name that folder, as
    render writes them for such a repo. Committed with the hooks off, as a render commit is."""
    repo.git("mv", "tests", "src/tipcalc/tests")
    for rel, old, new in (
        (".project.toml", 'tests = ["tests"]', 'tests = ["src/tipcalc/tests"]'),
        ("pyproject.toml", '"tests/**" =', '"src/tipcalc/tests/**" ='),
        ("pyproject.toml", '"tests/conftest.py"', '"src/tipcalc/tests/conftest.py"'),
    ):
        text = (repo.path / rel).read_text(encoding="utf-8")
        assert old in text, (rel, old)
        repo.write(rel, text.replace(old, new, 1))
    repo.commit_unhooked("test: keep the tests inside the package")


def test_tests_inside_the_source_root_are_tests_to_the_gates(repo: Repo) -> None:
    """Colocated tests (src/tipcalc/tests) are tests, not code: D4's `Spec:` rule leaves a feat/
    commit of them alone, and of a test_*.py beside the code too, while code beside them still
    needs the trailer. The whole selftest matrix, which writes its tests into the first test
    root, stays green (it failed D4 twice there)."""
    colocate(repo)
    test = (
        DOC + 'import pytest\n\n\n@pytest.mark.spec("cli.tip-default")\ndef test_more() -> None:\n'
    )
    repo.write("src/tipcalc/tests/test_more.py", test + '    """More."""\n')
    repo.write("src/tipcalc/test_beside.py", test + '    """Beside."""\n')
    repo.git("add", "-A")
    result = repo.commit("-m", "test(cli): two more")
    assert result.returncode == 0, output(result)
    repo.write("src/tipcalc/extra.py", '"""Extra."""\n')
    repo.git("add", "-A")
    result = repo.commit("-m", "feat(cli): extra")
    assert result.returncode == 1
    assert "needs a 'Spec: <ids>' trailer" in output(result)
    assert "it touches src/tipcalc/extra.py" in output(result)
    repo.git("rm", "-q", "--cached", "src/tipcalc/extra.py")
    (repo.path / "src/tipcalc/extra.py").unlink()
    result = repo.selftest()
    text = output(result)
    assert result.returncode == 0, text
    assert "FAIL" not in text
    assert text.rstrip().splitlines()[-1].startswith("selftest: ok (")


def test_a_test_beside_the_code_is_a_test_to_pre_commit(repo: Repo) -> None:
    """pre-commit reads a test_*.py beside the code as a test, as commit-msg and prove-red do:
    it carries the test of a scenario its commit adds (I4), its tags must name known ids, and
    a scenario removed while it is still tagged with it is refused. Only [paths] tests counted
    before, so the I4 commit was refused and the unknown id went through."""
    colocate(repo)
    test = DOC + 'import pytest\n\n\n@pytest.mark.spec("{sid}")\ndef test_{name}() -> None:\n'
    test += '    """{name}."""\n'
    repo.append("specs/capabilities/cli.md", SCENARIO.format(slug="double"))
    repo.write("src/tipcalc/test_double.py", test.format(sid="cli.double", name="double"))
    repo.git("add", "-A")
    result = repo.commit("-m", "test(cli): double")
    assert result.returncode == 0, output(result)
    repo.write("src/tipcalc/test_badtag.py", test.format(sid="nope.nope", name="badtag"))
    repo.git("add", "-A")
    result = repo.commit("-m", "test(cli): a bad tag")
    assert result.returncode == 1
    assert "src/tipcalc/test_badtag.py:6: unknown id 'nope.nope'" in output(result)
    repo.git("rm", "-q", "--cached", "src/tipcalc/test_badtag.py")
    (repo.path / "src/tipcalc/test_badtag.py").unlink()
    cli = (repo.path / "specs/capabilities/cli.md").read_text(encoding="utf-8")
    repo.write("specs/capabilities/cli.md", cli.replace(SCENARIO.format(slug="double"), ""))
    repo.git("add", "-A")
    result = repo.commit("-m", "spec(cli): drop double\n\nSpec-Removed: cli.double")
    assert result.returncode == 1
    assert (
        "I4: scenario cli.double is removed in this commit, but src/tipcalc/test_double.py:6 is "
        "still tagged with it"
    ) in output(result)


def test_a_test_folder_render_has_not_seen_gets_a_re_render_hint(repo: Repo) -> None:
    """The tests' per-file-ignores rows are written at render: a test folder made later has no
    row, nor has a first test_*.py beside the code, so their asserts fail S101 at pre-commit,
    and the refusal says a re-render adds the row."""
    test = DOC + '\ndef test_probe() -> None:\n    """Probe."""\n    assert True\n'
    repo.write("src/tipcalc/sub/tests/test_probe.py", test)
    repo.write("src/tipcalc/test_beside.py", test)
    repo.write("tests/test_probe.py", test)
    repo.git("add", "-A")
    result = repo.commit("-m", "test: probe")
    text = output(result)
    assert result.returncode == 1, text
    assert "src/tipcalc/sub/tests/test_probe.py:" in text and " S101 " in text
    assert "src/tipcalc/test_beside.py:" in text
    assert text.count("and this one came later. To add its row, re-render: init.py render") == 2
    assert "To add its row, re-render: init.py render (re-run /project-init)" in text
    assert "ruff check tests/test_probe.py" not in text  # tests/** has its row


def test_commit_all_is_checked_on_the_index_git_builds(repo: Repo) -> None:
    """`commit -a` and `commit <path>` hand the hooks a temporary index (GIT_INDEX_FILE)."""
    repo.append("specs/mission.md", "\nchanged\n")
    for args in (("-am", "docs: all"), ("-m", "docs: path", "specs/mission.md")):
        result = repo.commit(*args)
        assert result.returncode == 1, args
        assert "I1: specs/mission.md is staged on feat/gates" in output(result)


def test_hooks_fail_closed_without_mise(repo: Repo, tmp_path: Path) -> None:
    """The shims exec mise: on a machine without it, the commit is refused, not let through."""
    repo.append("README.md", "\nmore\n")
    repo.git("add", "README.md")
    git = shutil.which("git", path=clean_env(repo.trusted)["PATH"])
    assert git is not None
    bare = tmp_path / "bin"  # git alone on PATH: no mise, no uv
    bare.mkdir()
    (bare / "git").symlink_to(git)
    result = repo.run("git", "commit", "-q", "-m", "docs: more", env={"PATH": str(bare)})
    assert result.returncode != 0
    assert "mise" in output(result)
    assert repo.git("log", "-1", "--format=%s").strip() == "chore(init): project-init v3 gates"


def test_origin_sync_without_coreutils_timeout(repo: Repo, tmp_path: Path) -> None:
    """The guard confirms a sync with `git ls-remote` under coreutils' timeout when the machine
    has it; on one without it (macOS without coreutils) the sync still passes."""
    origin = tmp_path / "origin.git"
    repo.git("init", "-q", "--bare", "-b", "main", str(origin))
    toml = repo.path / ".project.toml"
    line = f'origin_url = "{origin}"'
    text, count = re.subn(r"(?m)^origin_url = .*$", line, toml.read_text(encoding="utf-8"))
    toml.write_text(text if count else f"{line}\n{text}", encoding="utf-8")
    repo.commit_unhooked("chore: origin")
    moved = repo.run("git", "branch", "-f", "main", "HEAD", env={"PROJECT_MERGE": "1"})
    assert moved.returncode == 0, output(moved)
    repo.git("remote", "add", "origin", str(origin))
    repo.git("push", "-q", "origin", "main")  # the bootstrap push
    other = tmp_path / "other"
    repo.git("clone", "-q", str(origin), str(other))
    (other / "README.md").write_text("moved on origin\n", encoding="utf-8")
    landed = "docs: moved\n\nMerged-By: mise run merge"
    for argv in (("commit", "-q", "-am", landed), ("push", "-q", "origin", "main")):
        done = repo.run("git", "-C", str(other), *argv)
        assert done.returncode == 0, output(done)
    tip = repo.git("-C", str(other), "rev-parse", "HEAD").strip()
    repo.git("switch", "-q", "main")
    bare = tmp_path / "bin"  # what the guard runs, without timeout or gtimeout
    bare.mkdir()
    path = clean_env(repo.trusted)["PATH"]
    for tool in ("git", "sh", "sed", "grep", "cut", "head", "tr"):
        found = shutil.which(tool, path=path)
        assert found is not None, tool
        (bare / tool).symlink_to(found)
    assert shutil.which("timeout", path=str(bare)) is None
    result = repo.run("git", "pull", "-q", "--ff-only", "origin", "main", env={"PATH": str(bare)})
    assert result.returncode == 0, output(result)
    assert repo.git("rev-parse", "main").strip() == tip


def test_hook_install_sets_the_gate_config_once(repo: Repo) -> None:
    """mise's postinstall runs `project.py hook install`; running it again changes nothing."""
    again = repo.run(sys.executable, "scripts/project.py", "hook", "install")
    assert again.returncode == 0, output(again)
    blob = repo.git("rev-parse", "HEAD:.githooks/reference-transaction").strip()
    expected = {
        "core.hooksPath": ".githooks",
        "receive.hideRefs": "refs/heads/main",
        "hook.project-main-guard.event": "reference-transaction",
    }
    for key, value in expected.items():
        assert repo.git("config", "--get-all", key).splitlines() == [value]
    command = repo.git("config", "--get-all", "hook.project-main-guard.command").splitlines()
    assert len(command) == 1
    assert f"cat-file blob {blob})" in command[0]
    record = repo.git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    main = repo.git("rev-parse", "main").strip()
    assert Path(record, "project-main-tip").read_text(encoding="utf-8") == f"{main}\n"


def guard_repo(tmp_path: Path, ref_format: str, *, pinned: bool) -> tuple[Repo, str, str]:
    """A repo with the rendered guard on, as `hook install` sets it (core.hooksPath, the pinned
    copy, the record of main), main at one commit and feat/x one ahead, checked out. pinned:
    the working tree's guard lets everything through, so the pinned copy alone holds."""
    path = tmp_path / ref_format
    path.mkdir()
    repo = Repo(path, tmp_path)
    made = repo.run("git", "init", "-q", "-b", "main", f"--ref-format={ref_format}", str(path))
    assert made.returncode == 0, output(made)
    repo.git("commit", "-q", "--allow-empty", "-m", "chore: one")
    guard = (HOOKS / "reference-transaction").read_text(encoding="utf-8")
    repo.write(".githooks/reference-transaction", guard.replace("{DEFAULT_BRANCH}", "main"))
    hook = path / ".githooks" / "reference-transaction"
    hook.chmod(0o755)
    blob = repo.git("hash-object", "-w", ".githooks/reference-transaction").strip()
    command = load_project().guard_command(blob)
    for key, value in (
        ("core.hooksPath", ".githooks"),
        ("hook.project-main-guard.event", "reference-transaction"),
        ("hook.project-main-guard.command", command),
    ):
        repo.git("config", key, value)
    common = repo.git("rev-parse", "--path-format=absolute", "--git-common-dir").strip()
    main = repo.git("rev-parse", "main").strip()
    Path(common, "project-main-tip").write_text(f"{main}\n", encoding="utf-8")
    repo.git("switch", "-q", "-c", "feat/x")
    repo.git("commit", "-q", "--allow-empty", "-m", "docs: two")
    if pinned:
        hook.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    return repo, main, repo.git("rev-parse", "feat/x").strip()


@pytest.mark.parametrize("pinned", [False, True], ids=["tree", "pinned"])
@pytest.mark.parametrize("ref_format", ["files", "reftable"])
def test_guard_catches_renames_and_copies_onto_main(
    tmp_path: Path, ref_format: str, pinned: bool
) -> None:
    """git 2.55 writes main for `git branch -m/-M/-c/-C <x> main` without a ref transaction.
    With the files backend a rename first deletes main (old value unspecified) while its source's
    reflog waits in logs/refs/.tmp-renamed-log: the guard refuses that and puts the source back.
    reftable, and every copy, ask no hook: the guard's record of main trips at the next update
    (for a rename of the checked-out branch, the HEAD update in the same command) until main is
    back where the guard saw it."""
    repo, main, x = guard_repo(tmp_path, ref_format, pinned=pinned)

    def rev(ref: str) -> str:
        return repo.run("git", "rev-parse", "-q", "--verify", ref).stdout.strip()

    tripped = "moved without an update the guard saw"
    renamed = repo.run("git", "branch", "-M", "main")  # GitHub's quickstart line
    assert renamed.returncode != 0, output(renamed)
    assert "check git status" in output(renamed)
    if ref_format == "files":
        assert "git branch -m/-M onto it" in output(renamed)
        assert rev("main") == main
        assert "the rename had deleted feat/x already: it is back at" in output(renamed)
    else:
        assert tripped in output(renamed)
        assert f"then git branch feat/x {x}" in output(renamed)
        repo.git("update-ref", "refs/heads/main", main)
        repo.git("branch", "feat/x", x)
    assert rev("feat/x") == x
    assert repo.git("symbolic-ref", "HEAD").strip() == "refs/heads/feat/x"

    copied = repo.run("git", "branch", "-C", "feat/x", "main")
    assert copied.returncode == 0, output(copied)  # no hook runs: git cannot be stopped here
    assert rev("main") == x
    probe = repo.run("git", "branch", "probe")
    assert probe.returncode != 0
    assert tripped in output(probe)
    assert "(Branch: copied refs/heads/feat/x to refs/heads/main)" in output(probe)
    assert f"Put it back: git update-ref refs/heads/main {main}" in output(probe)
    problem = load_project().main_record_problem(repo.path, "main")
    assert problem is not None and "Branch: copied refs/heads/feat/x" in problem
    repo.git("update-ref", "refs/heads/main", main)  # putting it back is allowed
    assert load_project().main_record_problem(repo.path, "main") is None
    repo.git("branch", "probe")

    repo.git("update-ref", "-d", "refs/heads/main", main)  # a delete is recoverable
    onto = repo.run("git", "branch", "-m", "feat/x", "main")
    assert onto.returncode != 0
    if ref_format == "files":
        assert "main is missing here: no branch renames" in output(onto)
        assert rev("main") == ""
        assert rev("feat/x") == x
        log = repo.git("reflog", "show", "--format=%gs", "feat/x")
        assert "commit: docs: two" in log  # its reflog came back with it
    else:  # main is written; the HEAD update after it is where the guard gets a say
        assert tripped in output(onto)
        assert f"then git branch feat/x {x}" in output(onto)


def test_commit_subject_under_every_cleanup() -> None:
    """commit-msg cannot see --cleanup, so it judges each subject git may store: the first line
    that is not a comment (strip), and the first line at all (whitespace, the default for -m and
    -F, verbatim and scissors). core.commentChar decides what a comment line is."""
    project = load_project()
    assert project.message_subjects("docs: x\n\n# a comment\n") == ["docs: x"]
    assert project.message_subjects("\n# update stuff\n\ndocs: x\n") == [
        "# update stuff",
        "docs: x",
    ]
    assert project.message_subjects("feat: x\n\nupdate stuff\n", "f") == [
        "feat: x",
        "update stuff",
    ]
    assert project.message_subjects("; a note\n\ndocs: x\n", ";") == ["; a note", "docs: x"]
    editor = "docs: x\n\n# Please enter the commit message\n# ------------------------ >8 ---"
    editor += "---------------------\ndiff --git a/x b/x\n"
    assert project.message_subjects(editor) == ["docs: x"]
    assert project.message_text(editor) == "docs: x\n"
    assert project.message_text("docs: x\n; c\n# kept\n", ";") == "docs: x\n# kept\n"


def fresh_render(repo: Repo) -> dict[str, str]:
    """The adoption branch before its ship commit (P5): the gate files rendered, not committed,
    and .project.toml [generated] recording the sha256 of each hook as project-init wrote it."""
    repo.git("reset", "-q", "--soft", "main")  # the render, staged; HEAD has no .githooks
    hooks = {}
    for name in ("pre-commit", "commit-msg", "pre-push", "reference-transaction"):
        data = (repo.path / ".githooks" / name).read_bytes()
        hooks[f".githooks/{name}"] = "sha256:" + hashlib.sha256(data).hexdigest()
    lines = "".join(f'"{path}" = "{digest}"\n' for path, digest in hooks.items())
    repo.append(".project.toml", f"\n[generated]\n{lines}")
    installed = repo.run(sys.executable, "scripts/project.py", "hook", "install")
    assert installed.returncode == 0, output(installed)
    return hooks


def test_a_fresh_render_passes_the_hook_checks_before_its_ship_commit(repo: Repo) -> None:
    """P5 runs doctor on plan/project-init before P7 commits the render: a hook that HEAD lacks
    passes while it is the file [generated] records, staged or untracked; an edited one fails."""
    repo.git("switch", "-q", "plan/project-init")
    fresh_render(repo)
    project = load_project()

    def problems() -> list[str]:
        return project.gate_setup_problems(project.load_context(repo.path))

    assert problems() == []
    result = repo.run(sys.executable, "scripts/project.py", "doctor")
    text = output(result)
    assert "ok    git gates: core.hooksPath, receive.hideRefs and the pinned main guard" in text
    assert "is not committed" not in text
    repo.git("reset", "-q")  # untracked now
    assert problems() == []
    hook = repo.path / ".githooks" / "pre-commit"
    rendered = hook.read_bytes()
    repo.append(".githooks/pre-commit", "exit 0\n")
    assert problems() == [
        ".githooks/pre-commit differs from what project-init rendered (.project.toml [generated])"
    ]
    repo.git("add", ".githooks/pre-commit")
    hook.write_bytes(rendered)
    assert problems() == [".githooks/pre-commit as staged differs from what project-init rendered"]
    repo.git("rm", "-q", "--cached", "-f", ".githooks/pre-commit")
    toml = repo.path / ".project.toml"
    toml.write_text(
        re.sub(r'(?m)^"\.githooks/pre-push" = .*\n', "", toml.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    assert problems() == [
        ".githooks/pre-push is not committed, and .project.toml [generated] does not record it"
    ]


@pytest.mark.parametrize(
    ("user", "own", "expected"),
    [
        ("https://h/o/", "https://h/", ""),  # the user's rule is longer: git follows it
        ("https://h/", "https://h/o/", "https://h/o/"),  # the repo's own rule is longer
        ("https://h/", "https://h/", "https://h/"),  # a tie counts as the repo's own
        ("", "", ""),
        ("", "ssh://x/", ""),  # a rule that does not match the URL
    ],
    ids=["user-longer", "own-longer", "tie", "none", "no-match"],
)
def test_guard_and_merge_agree_on_the_insteadof_rule_git_applies(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, user: str, own: str, expected: str
) -> None:
    """git rewrites a URL by the longest matching url.<base>.insteadOf. The main guard (sh) and
    project.py's land step name that rule when the repo's own config sets it (they refuse such
    a sync) and follow it when the user's config does."""
    path = tmp_path / "r"
    subprocess.run(["git", "init", "-q", str(path)], check=True, env=clean_env(tmp_path))
    config = tmp_path / "gitconfig"
    config.write_text(f'[url "git@user:"]\n\tinsteadOf = {user}\n' if user else "", "utf-8")
    repo = Repo(path, tmp_path)
    if own:
        repo.git("config", "url.git@own:.insteadOf", own)
    url = "https://h/o/r.git"
    text = (HOOKS / "reference-transaction").read_text(encoding="utf-8")
    found = re.search(r"(?ms)^own_rewrite\(\) \{.*?^\}\n", text)
    assert found is not None
    script = found.group(0) + 'own_rewrite "$1"\n'
    env = {"GIT_CONFIG_GLOBAL": str(config)}
    guard = repo.run("sh", "-c", script, "own_rewrite", url, env=env)
    assert guard.returncode == 0, output(guard)
    assert guard.stdout == expected
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    assert load_project().own_rewrite(path, url) == (expected or None)
