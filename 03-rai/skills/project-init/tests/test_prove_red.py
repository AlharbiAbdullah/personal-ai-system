"""project-init v3, milestone M3: `project.py tdd red|green`, `prove-red` with its count guard,
and the lane rules I7 and I11 in `check`.

The fixture repo is the real tipcalc. fixtures/make_tipcalc.sh clones ~/projects/tipcalc (branch
master; TIPCALC_SOURCE overrides the path) with `git clone --no-local` into a temp dir, removes
origin, renames the branch to main, runs `uv lock`, and commits pytest plus the template
conftest. `main3` adds, straight on main, the fixed code with three linked tests. Every test
copies one of the two (leaving out .venv, whose editable install points at the original), builds
its branch on top, and runs the template project.py by path with the copy as cwd. The fixture
tests spawn the real `tipcalc` console script, which `uv run` puts on PATH.

The cases are the M3 table in 03-rai/skills/project-init/DESIGN.md, section 12; the
test names say which row. The wall-time row measures and prints.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
PROJECT_PY = SKILL / "templates" / "scripts" / "project.py"
MAKE_TIPCALC = TESTS / "fixtures" / "make_tipcalc.sh"
M2_SPECS = TESTS / "fixtures" / "tipcalc" / "specs"
TIPCALC_SOURCE = Path(os.environ.get("TIPCALC_SOURCE", Path.home() / "projects" / "tipcalc"))

CLI_MD = """# Capability: cli

## Requirement: Tip output
The CLI SHALL print the tip for the bill given as the first argument.

### Scenario: cli.tip-default
- GIVEN TIPCALC_DEFAULT_PERCENT is unset
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0

## Requirement: Usage errors
The CLI SHALL answer bad input with exit code 2 and no traceback.

### Scenario: cli.no-args
- WHEN the user runs `tipcalc` with no arguments
- THEN stderr holds a usage line and no traceback, and the exit code is 2

### Scenario: cli.bad-amount
- WHEN the user runs `tipcalc abc`
- THEN stderr holds `error: bill must be a number`, and the exit code is 2
"""

RUN_TIPCALC = """import os
import subprocess

import pytest


def tipcalc(*args: str, **env: str) -> subprocess.CompletedProcess[str]:
    full = {k: v for k, v in os.environ.items() if k != "TIPCALC_DEFAULT_PERCENT"}
    full.update(env)
    return subprocess.run(["tipcalc", *args], capture_output=True, text=True, check=False, env=full)
"""

TEST_CLI = (
    RUN_TIPCALC
    + """

@pytest.mark.spec("cli.tip-default")
def test_tip_default() -> None:
    r = tipcalc("100")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.0\\n"


@pytest.mark.spec("cli.no-args")
def test_no_args() -> None:
    r = tipcalc()
    assert r.returncode == 2
    assert "Traceback" not in r.stderr
"""
)

TEST_PARSE = """import pytest

from tipcalc import parse_amount


@pytest.mark.spec("cli.bad-amount")
def test_parse_rejects_text() -> None:
    with pytest.raises(ValueError, match="bill must be a number"):
        parse_amount("abc")
"""

SRC_OLD = """import os
import sys


def tip(bill: float, percent: float) -> float:
    return round(bill * percent / 100, 2)
"""

SRC_STUB = (
    SRC_OLD
    + """

def parse_amount(raw: str) -> float:
    raise NotImplementedError


def main() -> None:
    percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))
    bill = float(sys.argv[1])
    print(f"tip: {tip(bill, percent)}")
"""
)

SRC_FIXED = (
    SRC_OLD
    + """

def parse_amount(raw: str) -> float:
    try:
        return float(raw)
    except ValueError:
        raise ValueError("bill must be a number") from None


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: tipcalc BILL", file=sys.stderr)
        raise SystemExit(2)
    percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))
    print(f"tip: {tip(parse_amount(sys.argv[1]), percent)}")
"""
)

SRC_WITH_CONFIG = SRC_FIXED.replace(
    'percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))',
    "percent = default_percent()",
).replace("import sys\n", "import sys\n\nfrom tipcalc.config import default_percent\n")

CONFIG_PY = """import os

DEFAULT_PERCENT = 15.0


def default_percent() -> float:
    raw = os.environ.get("TIPCALC_DEFAULT_PERCENT", "")
    if not raw:
        return DEFAULT_PERCENT
    try:
        return float(raw)
    except ValueError:
        raise SystemExit("error: TIPCALC_DEFAULT_PERCENT must be a number") from None
"""

CONFIG_MD = """# Capability: config

## Requirement: The default percent knob
The CLI SHALL read the default tip percent from TIPCALC_DEFAULT_PERCENT, where empty means unset.

### Scenario: config.percent-empty
- GIVEN TIPCALC_DEFAULT_PERCENT is set to an empty string
- WHEN the default percent is read
- THEN it is 15.0

### Scenario: config.percent-invalid
- GIVEN TIPCALC_DEFAULT_PERCENT is `abc`
- WHEN the default percent is read
- THEN it exits with one `error:` line
"""

TEST_CONFIG = """import pytest

from tipcalc.config import default_percent


@pytest.mark.spec("config.percent-empty")
def test_percent_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIPCALC_DEFAULT_PERCENT", "")
    assert default_percent() == 15.0


@pytest.mark.spec("config.percent-invalid")
def test_percent_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TIPCALC_DEFAULT_PERCENT", "abc")
    with pytest.raises(SystemExit, match="error:"):
        default_percent()
"""


def gap_test(name: str, sid: str, args: str, env: str, assertion: str) -> str:
    return f'''

@pytest.mark.spec("{sid}")
@pytest.mark.xfail(strict=True, reason="{sid}: traceback today (gap entrypoint-hardening)")
def {name}() -> None:
    r = tipcalc({args}{env})
    {assertion}
'''


NO_TRACEBACK = 'assert "Traceback" not in r.stderr'
INIT_TEST_CLI = (
    RUN_TIPCALC
    + """

@pytest.mark.spec("cli.tip-default")
def test_tip_default() -> None:
    r = tipcalc("100")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.0\\n"
"""
    + gap_test("test_no_args", "cli.no-args", "", "", NO_TRACEBACK)
    + gap_test("test_help", "cli.help", '"--help"', "", NO_TRACEBACK)
    + gap_test("test_bad_amount", "cli.bad-amount", '"abc"', "", NO_TRACEBACK)
)
INIT_TEST_CONFIG = (
    RUN_TIPCALC
    + gap_test(
        "test_percent_empty",
        "config.percent-empty",
        '"100"',
        ", TIPCALC_DEFAULT_PERCENT=''",
        NO_TRACEBACK,
    )
    + gap_test(
        "test_percent_invalid",
        "config.percent-invalid",
        '"100"',
        ", TIPCALC_DEFAULT_PERCENT='abc'",
        NO_TRACEBACK,
    )
)

# The trailers tdd red prints for the base case (cli.bad-amount went red with the stub).
RED_TRAILERS = "Red: cli.no-args: assert 1 == 2\nRed: cli.bad-amount: NotImplementedError"
BASE_TRAILERS = f"Spec: cli.no-args, cli.bad-amount\n{RED_TRAILERS}\nSpec-Guard: cli.tip-default"


def clean_env() -> dict[str, str]:
    drop = ("GIT_", "PYTEST_", "GITHUB_", "PROJECT_MERGE", "TIPCALC_")
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
        PYTHONDONTWRITEBYTECODE="1",
    )
    return env


class Repo:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.env: dict[str, str] = {}

    def run(
        self, *argv: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=self.path,
            capture_output=True,
            text=True,
            check=False,
            env={**clean_env(), **self.env, **(env or {})},
        )

    def git(self, *args: str) -> str:
        result = self.run("git", *args)
        assert result.returncode == 0, output(result)
        return result.stdout

    def read(self, rel: str) -> str:
        return (self.path / rel).read_text(encoding="utf-8")

    def write(self, rel: str, text: str) -> None:
        path = self.path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def edit(self, rel: str, old: str, new: str) -> None:
        text = self.read(rel)
        assert old in text, f"{old!r} not in {rel}"
        self.write(rel, text.replace(old, new, 1))

    def commit(self, message: str) -> str:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def branch(self, name: str) -> None:
        self.git("switch", "-q", "-c", name)

    def project(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, str(PROJECT_PY), *args)

    def pytest(self, *args: str) -> subprocess.CompletedProcess[str]:
        """The whole suite, as `mise run test` runs it (writes .cache/spec-results.json)."""
        return self.run("uv", "run", "--locked", "--quiet", "pytest", *args)

    def worktrees(self) -> list[str]:
        listing = self.git("worktree", "list", "--porcelain")
        return [line for line in listing.splitlines() if line.startswith("worktree ")]


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def copy_repo(template: Path, dest: Path) -> Repo:
    """A copy of a fixture repo without .venv (its editable install points at the template)."""
    shutil.copytree(template, dest, symlinks=True, ignore=shutil.ignore_patterns(".venv", ".cache"))
    repo = Repo(dest)
    repo.env["TMPDIR"] = str(dest.parent / "tmp")  # prove-red's temp worktrees land here
    (dest.parent / "tmp").mkdir(exist_ok=True)
    return repo


def write_base_case(repo: Repo) -> None:
    """The M3 base case: test_cli.py (tip-default, no-args), test_parse.py importing
    parse_amount, and the fixed src."""
    repo.write("specs/capabilities/cli.md", CLI_MD)
    repo.write("tests/test_cli.py", TEST_CLI)
    repo.write("tests/test_parse.py", TEST_PARSE)
    repo.write("src/tipcalc/__init__.py", SRC_FIXED)


@pytest.fixture(scope="session")
def tipcalc_main(tmp_path_factory: pytest.TempPathFactory) -> Path:
    if not (TIPCALC_SOURCE / ".git").exists():
        pytest.skip(f"no tipcalc repo at {TIPCALC_SOURCE} (set TIPCALC_SOURCE)")
    dest = tmp_path_factory.mktemp("m3") / "tipcalc"
    result = subprocess.run(
        ["sh", str(MAKE_TIPCALC), str(dest), str(TIPCALC_SOURCE)],
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(),
    )
    assert result.returncode == 0, output(result)
    repo = Repo(dest)
    assert repo.git("branch", "--format=%(refname:short)").split() == ["main"]
    assert repo.git("remote").strip() == ""
    assert len(repo.git("log", "--format=%H").split()) == 2
    assert "pytest" in repo.read("pyproject.toml")
    assert (dest / "uv.lock").is_file() and (dest / "tests" / "conftest.py").is_file()
    return dest


@pytest.fixture(scope="session")
def main3(tipcalc_main: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """main after the usage-errors fix landed: 3 scenarios, 3 linked tests, a tech-stack."""
    repo = copy_repo(tipcalc_main, tmp_path_factory.mktemp("main3") / "tipcalc")
    write_base_case(repo)
    shutil.copy2(M2_SPECS / "tech-stack.md", repo.path / "specs" / "tech-stack.md")
    repo.commit("fix(cli): usage errors\n\nMerged-By: mise run merge")
    return repo.path


@pytest.fixture
def fresh(tipcalc_main: Path, tmp_path: Path) -> Repo:
    return copy_repo(tipcalc_main, tmp_path / "tipcalc")


@pytest.fixture
def landed(main3: Path, tmp_path: Path) -> Repo:
    return copy_repo(main3, tmp_path / "tipcalc")


def base_case(repo: Repo, trailers: str = BASE_TRAILERS) -> None:
    repo.branch("fix/usage-errors")
    write_base_case(repo)
    repo.commit("fix(cli): usage errors\n\n" + trailers)


def assert_cleaned_up(repo: Repo) -> None:
    assert len(repo.worktrees()) == 1, repo.worktrees()
    left = [p.name for p in (repo.path.parent / "tmp").iterdir() if p.name.startswith("prove-red")]
    assert left == []  # uv keeps its own lock files in TMPDIR; those are not prove-red's


# ---------------------------------------------------------------- the M3 table


def test_base_case_red_on_the_old_code_and_guard_passes(fresh: Repo) -> None:
    """Row 1: cli.no-args red (assert 1 == 2), cli.bad-amount red (collection error),
    cli.tip-default passes as a Spec-Guard, exit 0. The collection error alone proves nothing
    about test_parse.py's body, so it runs once more with a stub for parse_amount, and fails
    there on NotImplementedError: no Red: trailer is needed (the commit here has none)."""
    base_case(fresh, "Spec: cli.no-args, cli.bad-amount\nSpec-Guard: cli.tip-default")
    assert fresh.pytest().returncode == 0  # all green at HEAD
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.no-args red (assert 1 == 2)" in out
    assert "ok    cli.bad-amount red (collection error; with stubs: NotImplementedError)" in out
    assert "ok    cli.tip-default guard: passes on the old code" in out
    assert "ok    test count 0 -> 3" in out
    assert "prove-red: ok; 2/2 red on base (1 assertion, 1 collection), guards 1/1 pass" in out
    assert "note" not in out  # the base's count ran in the base's own environment
    assert_cleaned_up(fresh)
    assert fresh.git("status", "--porcelain") == ""  # the repo itself is untouched


def test_new_module_is_gone_on_the_old_code(fresh: Repo) -> None:
    """Row 2: a fix adds NEW src/tipcalc/config.py and test_config.py imports it; config.* are
    red by collection error on the base, which only --no-overlay gives."""
    base_case(fresh)
    fresh.write("src/tipcalc/config.py", CONFIG_PY)
    fresh.write("src/tipcalc/__init__.py", SRC_WITH_CONFIG)
    fresh.write("specs/capabilities/config.md", CONFIG_MD)
    fresh.write("tests/test_config.py", TEST_CONFIG)
    fresh.commit("fix(config): read the knob\n\nSpec: config.percent-empty, config.percent-invalid")
    assert fresh.pytest().returncode == 0  # the config tests pass at HEAD
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    # (with stubs, tipcalc.config is an empty stub module and default_percent() raises)
    for sid in ("config.percent-empty", "config.percent-invalid"):
        assert f"ok    {sid} red (collection error; with stubs: NotImplementedError)" in out
    assert_cleaned_up(fresh)

    # Control: git's default (overlay) checkout keeps config.py in the "old" tree, and there
    # the config tests pass, so without --no-overlay prove-red would call them unproven.
    base = fresh.git("merge-base", "HEAD", "main").strip()
    tree = fresh.path.parent / "overlay"
    fresh.git("worktree", "add", "-q", "--detach", str(tree), "HEAD")
    overlay = Repo(tree)
    overlay.git("checkout", base, "--", "src")
    assert (tree / "src" / "tipcalc" / "config.py").is_file()
    # (test_parse.py does not import on the old code: one bad file must not stop the run)
    ran = overlay.pytest(
        "--continue-on-collection-errors", "--spec", "config.percent-empty,config.percent-invalid"
    )
    assert "2 passed, 2 deselected, 1 error" in ran.stdout, output(ran)
    fresh.git("worktree", "remove", "--force", str(tree))


def test_plan_project_init_guard_passes_and_gaps_xfail(fresh: Repo) -> None:
    """Row 3: plan/project-init with cli.tip-default (characterization) and 5 gaps."""
    fresh.branch("plan/project-init")
    for name in ("capabilities/cli.md", "capabilities/config.md", "roadmap.md", "tech-stack.md"):
        fresh.write(f"specs/{name}", (M2_SPECS / name).read_text(encoding="utf-8"))
    fresh.write("tests/test_cli.py", INIT_TEST_CLI)
    fresh.write("tests/test_config.py", INIT_TEST_CONFIG)
    fresh.commit("chore(init): project-init v3")
    ran = fresh.pytest()
    assert ran.returncode == 0 and "1 passed, 5 xfailed" in ran.stdout, output(ran)
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.tip-default guard: passes on the old code" in out
    for sid in ("cli.no-args", "cli.help", "cli.bad-amount"):
        assert f"ok    {sid} gap: xfails on the old code" in out
    for sid in ("config.percent-empty", "config.percent-invalid"):
        assert f"ok    {sid} gap: xfails on the old code" in out
    assert "0/0 red on base, guards 1/1 pass, gaps 5/5 xfail, tests 0 -> 6" in out
    assert_cleaned_up(fresh)


def test_mutated_test_pins_nothing_new(fresh: Repo) -> None:
    """Row 4: test_no_args mutated to assert returncode == 1 passes on the old code."""
    base_case(fresh)
    fresh.edit(
        "tests/test_cli.py",
        '    assert r.returncode == 2\n    assert "Traceback" not in r.stderr\n',
        "    assert r.returncode == 1\n",
    )
    fresh.commit("test(cli): weaker no-args check")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args passes on the old code: it pins nothing new" in out
    assert "ok    cli.bad-amount red (collection error; with stubs: NotImplementedError)" in out
    assert_cleaned_up(fresh)


def test_deleted_test_with_its_scenario_kept_fails(landed: Repo) -> None:
    """Row 5: test_tip_default deleted, scenario kept: spec-check exit 1 (and the count guard
    of prove-red sees the lost test too)."""
    landed.branch("chg/drop-tip-test")
    text = landed.read("tests/test_cli.py")
    start = text.index('@pytest.mark.spec("cli.tip-default")')
    end = text.index('@pytest.mark.spec("cli.no-args")')
    landed.write("tests/test_cli.py", text[:start] + text[end:])
    landed.commit("change(cli): drop a test")
    assert landed.pytest().returncode == 0
    result = landed.project("check")
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.tip-default: no linked test" in result.stdout
    proof = landed.project("prove-red")
    assert proof.returncode == 1, output(proof)
    assert "FAIL  tests disappeared: 2 collected at HEAD, 3 at the base" in proof.stdout


def test_removed_scenario_and_its_test_shrink_the_count(landed: Repo) -> None:
    """Row 6: scenario + test deleted in one commit with Spec-Removed: count 3 -> 2 allowed."""
    landed.branch("chg/drop-bad-amount")
    text = landed.read("specs/capabilities/cli.md")
    landed.write("specs/capabilities/cli.md", text[: text.index("### Scenario: cli.bad-amount")])
    (landed.path / "tests" / "test_parse.py").unlink()
    landed.commit("change(cli)!: stop parsing text bills\n\nSpec-Removed: cli.bad-amount")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    test count 3 -> 2 (1 linked only to removed ids)" in out
    assert "warn" not in out
    assert_cleaned_up(landed)
    assert landed.pytest().returncode == 0
    check = landed.project("check")
    assert check.returncode == 0, output(check)


def build_bad_amount(repo: Repo, src: str) -> None:
    repo.branch("fix/bad-amount")
    repo.write("specs/capabilities/cli.md", CLI_MD)
    repo.write("tests/test_parse.py", TEST_PARSE)
    repo.write("src/tipcalc/__init__.py", src)


def test_tdd_red_refuses_an_import_error(fresh: Repo) -> None:
    """Row 7: `tdd red cli.bad-amount` before any stub exists refuses, with the stub hint."""
    build_bad_amount(fresh, fresh.read("src/tipcalc/__init__.py"))
    result = fresh.project("tdd", "red", "cli.bad-amount")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.bad-amount: ImportError is the wrong red: "
        "add a stub that raises NotImplementedError"
    ) in out
    assert "nothing recorded" in out
    assert not (fresh.path / ".agent").exists()


def test_tdd_red_with_the_stub_then_green(fresh: Repo) -> None:
    """Row 8: with the stub, `tdd red cli.bad-amount` exits 0 and prints
    `Red: cli.bad-amount: NotImplementedError`; then green after the code."""
    build_bad_amount(fresh, SRC_STUB)
    result = fresh.project("tdd", "red", "cli.bad-amount")
    out = output(result)
    assert result.returncode == 0, out
    assert "Red: cli.bad-amount: NotImplementedError" in out.splitlines()
    record = fresh.path / ".agent" / "tdd" / "fix" / "bad-amount.json"
    assert '"reason": "NotImplementedError"' in record.read_text(encoding="utf-8")

    fresh.write("src/tipcalc/__init__.py", SRC_FIXED)
    green = fresh.project("tdd", "green", "cli.bad-amount")
    lines = output(green).splitlines()
    assert green.returncode == 0, lines
    assert "ok    cli.bad-amount: green, 1 passing" in lines
    assert lines[-2:] == ["Spec: cli.bad-amount", "Red: cli.bad-amount: NotImplementedError"]
    assert '"green": {' in record.read_text(encoding="utf-8")


def test_tdd_red_prints_the_assertion_and_green_needs_a_red_record(fresh: Repo) -> None:
    """The 5.4 trailer `Red: cli.no-args: assert 1 == 2`; green refuses an id never seen red,
    and red refuses a test that already passes."""
    fresh.branch("fix/no-args")
    fresh.write("specs/capabilities/cli.md", CLI_MD)
    fresh.write("tests/test_cli.py", TEST_CLI)
    result = fresh.project("tdd", "red", "cli.no-args")
    assert result.returncode == 0, output(result)
    assert "Red: cli.no-args: assert 1 == 2" in result.stdout.splitlines()
    refused = fresh.project("tdd", "green", "cli.tip-default")
    assert refused.returncode == 1, output(refused)
    assert "FAIL  cli.tip-default: no red record in .agent/tdd/fix/no-args.json" in refused.stdout
    passing = fresh.project("tdd", "red", "cli.tip-default")
    assert passing.returncode == 1, output(passing)
    assert "FAIL  cli.tip-default: passes already" in passing.stdout
    assert "or the code is here already" not in passing.stdout  # this branch wrote no code
    unknown = fresh.project("tdd", "red", "cli.nope")
    assert unknown.returncode == 1 and "cli.nope: no such scenario" in unknown.stdout


def test_tdd_red_on_code_the_branch_already_wrote_points_at_prove_red(fresh: Repo) -> None:
    """Run E: validate's in-scope finding on behaviour an earlier group wrote. tdd red runs
    the test on this branch's code, so it passes, and the refusal names validate's route
    (Spec: without Red:, then prove-red) instead of only asking for a stronger assertion."""
    base_case(fresh)  # fix/usage-errors: the code that makes cli.no-args pass, committed
    red = fresh.project("tdd", "red", "cli.no-args")
    out = output(red)
    assert red.returncode == 1, out
    assert "FAIL  cli.no-args: passes already" in out
    assert (
        "or the code is here already: when an earlier commit on fix/usage-errors wrote the "
        "behaviour of cli.no-args, its red shows only on the base. Commit the scenario and its "
        "test with `Spec:` and no `Red:` line, then run `mise run prove-red`"
    ) in out


TEST_NO_ARGS_FIRST_LINE = (
    RUN_TIPCALC
    + """

@pytest.mark.spec("cli.no-args")
def test_no_args() -> None:
    r = tipcalc()
    assert r.stdout.splitlines()[0] == ""
    assert r.stderr.splitlines()[-1] == "usage: tipcalc BILL"
"""
)


def test_tdd_red_refuses_an_exception_the_test_itself_raises(fresh: Repo) -> None:
    """Run E: an IndexError from the test's own `splitlines()[0]` on empty output is no right
    red, and no Red: trailer is printed for it; the same check as an assertion is."""
    fresh.branch("fix/no-args")
    fresh.write("specs/capabilities/cli.md", CLI_MD)
    fresh.write("tests/test_cli.py", TEST_NO_ARGS_FIRST_LINE)
    result = fresh.project("tdd", "red", "cli.no-args")
    out = output(result)
    assert result.returncode == 1, out
    assert ("FAIL  cli.no-args: IndexError is the wrong red: the test's own code raised it") in out
    assert "Red: cli.no-args" not in out
    fresh.write(
        "tests/test_cli.py",
        TEST_NO_ARGS_FIRST_LINE.replace(
            'r.stdout.splitlines()[0] == ""', 'r.stdout.splitlines()[:1] == [""]'
        ),
    )
    again = fresh.project("tdd", "red", "cli.no-args")
    assert again.returncode == 0, output(again)
    assert "Red: cli.no-args: assert" in again.stdout


def test_i7_refactor_edits_an_existing_test(landed: Repo) -> None:
    """Row 9: refactor/x editing tests/test_cli.py without Test-Harness: fails I7; with the
    trailer the edit is listed for the human. A new test file needs no trailer."""
    landed.branch("refactor/tidy")
    landed.edit("tests/test_cli.py", "import os\n", '"""CLI tests."""\n\nimport os\n')
    sha = landed.commit("refactor(tests): docstring")
    landed.write("tests/test_more.py", "def test_more() -> None:\n    assert 1 + 1 == 2\n")
    landed.commit("test: one more")
    assert landed.pytest().returncode == 0
    result = landed.project("check")
    assert result.returncode == 1, output(result)
    assert f"FAIL  I7: commit {sha[:10]} edits tests/test_cli.py on refactor/tidy" in result.stdout
    assert "test_more.py" not in result.stdout

    landed.git("reset", "-q", "--soft", "HEAD~2")  # one commit for both, with the trailer
    landed.git("commit", "-q", "-m", "refactor(tests): docstring\n\nTest-Harness: name the module")
    trailer = landed.git("rev-parse", "HEAD").strip()
    result = landed.project("check")
    assert result.returncode == 0, output(result)
    assert (
        f"note  I7: {trailer[:10]} edits tests/test_cli.py (Test-Harness: name the module); "
        "merge shows this diff to a human"
    ) in result.stdout


def test_i7_counts_a_test_beside_the_code(landed: Repo) -> None:
    """A test_*.py beside the code is an existing test to I7, as it is to prove-red and the
    commit hooks: a refactor/ edit of it needs the Test-Harness: route too."""
    beside = '"""Beside."""\n\n\ndef test_beside() -> None:\n    assert 1 + 1 == 2\n'
    landed.write("src/tipcalc/test_beside.py", beside)
    landed.commit("test: a test beside the code\n\nMerged-By: mise run merge")
    landed.branch("refactor/tidy")
    landed.edit("src/tipcalc/test_beside.py", '"""Beside."""', '"""A test beside the code."""')
    sha = landed.commit("refactor(tests): docstring")
    assert landed.pytest().returncode == 0
    result = landed.project("check")
    assert result.returncode == 1, output(result)
    want = f"FAIL  I7: commit {sha[:10]} edits src/tipcalc/test_beside.py on refactor/tidy"
    assert want in result.stdout


def test_i11_new_runtime_dependency_needs_tech_stack(landed: Repo) -> None:
    """Row 10: pyproject gains pydantic-settings without a tech-stack edit: I11 exit 1."""
    sync = landed.run("uv", "sync", "--locked", "--quiet")
    assert sync.returncode == 0, output(sync)
    landed.branch("chore/deps-pydantic-settings")
    landed.edit("pyproject.toml", "dependencies = []", 'dependencies = ["pydantic-settings>=2"]')
    landed.commit("chore(deps): add pydantic-settings")
    # The lock is stale now, so the suite runs from the synced venv (tipcalc on PATH).
    venv_bin = landed.path / ".venv" / "bin"
    path = {"PATH": f"{venv_bin}{os.pathsep}{os.environ['PATH']}"}
    ran = landed.run(str(venv_bin / "python"), "-m", "pytest", env=path)
    assert ran.returncode == 0, output(ran)
    result = landed.project("check")
    assert result.returncode == 1, output(result)
    assert (
        "FAIL  I11: runtime dependency pydantic-settings added (pyproject.toml), but "
        "specs/tech-stack.md is unchanged on chore/deps-pydantic-settings" in result.stdout
    )
    landed.edit(
        "specs/tech-stack.md",
        "- Dependencies: none (standard library only).",
        "- Dependencies: pydantic-settings (env knobs, S-1).",
    )
    landed.commit("docs(stack): pydantic-settings")
    result = landed.project("check")
    assert result.returncode == 0, output(result)


def test_i11_ignores_a_version_bump(landed: Repo) -> None:
    landed.branch("chore/deps-bump")
    text = landed.read("pyproject.toml")
    pin = next(line for line in text.splitlines() if '"pytest>=' in line)
    landed.edit("pyproject.toml", pin, '    "pytest>=9",')
    landed.commit("chore(deps): relax pytest")
    result = landed.project("check")
    assert "I11" not in result.stdout, output(result)


def test_prove_red_wall_time(fresh: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """Row 11: prove-red wall time on the base case, measured and printed (target: 20 s warm)."""
    base_case(fresh)
    times = []
    for _ in range(2):
        start = time.perf_counter()
        result = fresh.project("prove-red")
        times.append(time.perf_counter() - start)
        assert result.returncode == 0, output(result)
    with capsys.disabled():
        print(
            f"\n[M3] prove-red wall time on tipcalc: first {times[0]:.2f} s, "
            f"warm {times[1]:.2f} s (target under 20 s warm)"
        )
    assert times[1] < 20


# ---------------------------------------------------------------- the rest of the 5.5 table


def test_guard_that_fails_on_the_old_code_broke(fresh: Repo) -> None:
    base_case(
        fresh,
        "Spec: cli.bad-amount\nRed: cli.bad-amount: NotImplementedError\n"
        "Spec-Guard: cli.tip-default, cli.no-args",
    )
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.no-args guard broke: tests/test_cli.py::test_no_args failed on the old code "
        "(assert 1 == 2)"
    ) in out


def test_gap_test_that_passes_on_the_old_code(fresh: Repo) -> None:
    fresh.branch("plan/project-init")
    for name in ("capabilities/cli.md", "capabilities/config.md", "roadmap.md", "tech-stack.md"):
        fresh.write(f"specs/{name}", (M2_SPECS / name).read_text(encoding="utf-8"))
    weak = INIT_TEST_CLI.replace(
        'r = tipcalc()\n    assert "Traceback" not in r.stderr',
        "r = tipcalc()\n    assert r.returncode != 0",
    )
    fresh.write("tests/test_cli.py", weak)
    fresh.write("tests/test_config.py", INIT_TEST_CONFIG)
    fresh.commit("chore(init): project-init v3")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.no-args gap test does not reproduce the gap: tests/test_cli.py::test_no_args "
        "passed (strict XPASS) on the old code"
    ) in out


def test_prove_red_cleans_up_when_setup_fails(fresh: Repo) -> None:
    base_case(fresh)
    fresh.edit("pyproject.toml", "dependencies = []", 'dependencies = ["pydantic-settings>=2"]')
    fresh.commit("chore(deps): no lock update")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  prove-red: uv sync --locked failed in the HEAD worktree" in out
    assert_cleaned_up(fresh)


def test_prove_red_on_main_and_with_a_bad_base(fresh: Repo) -> None:
    result = fresh.project("prove-red")
    assert result.returncode == 0, output(result)
    assert "nothing to prove, HEAD is the base" in result.stdout
    base_case(fresh)
    bad = fresh.project("prove-red", "--base", "nope")
    assert bad.returncode == 2 and "--base nope is not a commit" in bad.stderr
    explicit = fresh.project("prove-red", "--base", "main")
    assert explicit.returncode == 0, output(explicit)


def test_fix_lane_regression_test_beside_a_passing_one(fresh: Repo) -> None:
    """A fix/ regression test tagged with an existing, unchanged scenario: its Spec: trailer
    makes the id one to prove, and the older passing test on the same id does not spoil the red
    (tdd red accepts it too). On feat/ the same trailer adds nothing to prove."""
    fresh.write("specs/capabilities/cli.md", CLI_MD)
    fresh.write("tests/test_cli.py", TEST_CLI)
    fresh.write("tests/test_parse.py", TEST_PARSE)
    fresh.write("src/tipcalc/__init__.py", SRC_FIXED.replace("100, 2)", "100, 1)"))
    fresh.commit("fix(cli): usage errors\n\nMerged-By: mise run merge")  # main, rounding bug
    fresh.branch("fix/rounding")
    regression = (
        '\n\n@pytest.mark.spec("cli.tip-default")\ndef test_tip_rounds_to_cents() -> None:\n'
        '    assert tipcalc("10.25").stdout == "tip: 1.54\\n"\n'
    )
    fresh.write("tests/test_cli.py", TEST_CLI + regression)
    red = fresh.project("tdd", "red", "cli.tip-default")
    assert red.returncode == 0, output(red)
    assert "Red: cli.tip-default: assert 'tip: 1.5\\n' == 'tip: 1.54\\n'" in red.stdout
    fresh.write("src/tipcalc/__init__.py", SRC_FIXED)
    fresh.commit("fix(cli): round the tip to cents\n\nSpec: cli.tip-default")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.tip-default red (assert 'tip: 1.5\\n' == 'tip: 1.54\\n')" in out
    fresh.git("branch", "-m", "fix/rounding", "feat/rounding")
    feat = fresh.project("prove-red")
    assert feat.returncode == 0, output(feat)
    assert "cli.tip-default" not in feat.stdout
    assert "0/0 red on base" in feat.stdout


def test_prove_red_in_ci_on_a_detached_merge_commit(fresh: Repo) -> None:
    """CI checks out a detached commit and names the branch in GITHUB_HEAD_REF; the lane rules
    (here: plan/project-init characterization guards) follow that name."""
    fresh.branch("plan/project-init")
    for name in ("capabilities/cli.md", "capabilities/config.md", "roadmap.md", "tech-stack.md"):
        fresh.write(f"specs/{name}", (M2_SPECS / name).read_text(encoding="utf-8"))
    fresh.write("tests/test_cli.py", INIT_TEST_CLI)
    fresh.write("tests/test_config.py", INIT_TEST_CONFIG)
    fresh.commit("chore(init): project-init v3")
    fresh.git("switch", "-q", "--detach")
    ci = {
        "GITHUB_ACTIONS": "true",
        "GITHUB_HEAD_REF": "plan/project-init",
        "GITHUB_BASE_REF": "main",
    }
    result = fresh.run(sys.executable, str(PROJECT_PY), "prove-red", "--base", "main", env=ci)
    out = output(result)
    assert result.returncode == 0, out
    assert "prove-red plan/project-init:" in out
    assert "ok    cli.tip-default guard: passes on the old code" in out
    # Without the branch name, the characterization scenario must be red, and is not.
    bare = fresh.run(sys.executable, str(PROJECT_PY), "prove-red", "--base", "main")
    assert bare.returncode == 1, output(bare)
    assert "FAIL  cli.tip-default passes on the old code: it pins nothing new" in bare.stdout
    assert_cleaned_up(fresh)


SLOW_TEST = """import os
import time
from pathlib import Path

import pytest


@pytest.mark.spec("cli.no-args")
def test_slow_on_the_old_code() -> None:
    marker = os.environ.get("M3_MARKER")
    if marker:
        Path(marker).touch()
        time.sleep(60)
    assert marker, "red on the old code"
"""


def start_slow_run(repo: Repo) -> tuple[subprocess.Popen[str], Path]:
    """prove-red on a branch whose old-code run sleeps 60 s in a test; returns once the test
    runs. The script is started with this interpreter, so the pid is the script's."""
    base_case(repo)
    repo.write("tests/test_slow.py", SLOW_TEST)
    repo.commit("test(cli): slow\n\nSpec: cli.no-args")
    marker = repo.path.parent / "marker"
    started = time.monotonic()
    proc = subprocess.Popen(
        [sys.executable, str(PROJECT_PY), "prove-red"],
        cwd=repo.path,
        env={**clean_env(), **repo.env, "M3_MARKER": str(marker)},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    while not marker.exists():  # the run on the old code has reached the slow test
        assert proc.poll() is None, proc.communicate()
        assert time.monotonic() - started < 60
        time.sleep(0.1)
    return proc, marker


def working_in(folder: Path) -> list[int]:
    """pids of the processes whose working directory is inside folder (Linux /proc)."""
    pids = []
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                cwd = Path(os.readlink(entry / "cwd"))
            except OSError:
                continue
            if cwd == folder or folder in cwd.parents:
                pids.append(int(entry.name))
    return pids


@pytest.mark.parametrize("name", ["SIGTERM", "SIGHUP"])
def test_prove_red_cleans_up_when_terminated(fresh: Repo, name: str) -> None:
    """SIGTERM (CI cancelling a job) or SIGHUP (a closed terminal or SSH session) mid-run: the
    test processes die with it and the worktree is removed."""
    if not hasattr(signal, name):
        pytest.skip(f"no {name} here")
    number = getattr(signal, name)
    started = time.monotonic()
    proc, _ = start_slow_run(fresh)
    proc.send_signal(number)
    proc.communicate(timeout=30)
    assert proc.returncode == 128 + number
    assert time.monotonic() - started < 30  # it did not wait for the 60 s sleep
    assert_cleaned_up(fresh)


def test_prove_red_interrupted_exits_quietly(fresh: Repo) -> None:
    """Ctrl-C: exit 130 with one line, no traceback, and nothing left behind."""
    proc, _ = start_slow_run(fresh)
    proc.send_signal(signal.SIGINT)
    _, err = proc.communicate(timeout=30)
    assert proc.returncode == 130
    assert err == "project.py: interrupted\n"
    assert_cleaned_up(fresh)


@pytest.mark.skipif(not Path("/proc/self/cwd").exists(), reason="needs Linux /proc")
def test_killed_run_is_swept_by_the_next(fresh: Repo) -> None:
    """SIGKILL cannot be caught: the worktrees (HEAD's and the base's) stay and the tests keep
    running. The next run, even one with nothing to prove, kills those tests and removes the
    worktrees; a folder whose owner still runs, or that has no owner file, is left alone."""
    proc, _ = start_slow_run(fresh)
    proc.kill()
    proc.communicate(timeout=30)
    tmp = fresh.path.parent / "tmp"
    stale = next(p for p in tmp.iterdir() if p.name.startswith("prove-red-"))
    assert len(fresh.worktrees()) == 3
    assert working_in(stale)  # the orphaned uv and pytest

    live = tmp / "prove-red-live"
    live.mkdir()
    (live / "owner").write_text(f"{os.getpid()}\n", encoding="utf-8")
    fresh.git("worktree", "add", "-q", "--detach", str(live / "head"), "HEAD")
    ownerless = tmp / "prove-red-ownerless"
    ownerless.mkdir()
    fresh.git("worktree", "add", "-q", "--detach", str(ownerless / "head"), "HEAD")

    fresh.git("switch", "-q", "main")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "nothing to prove, HEAD is the base" in out
    assert f"note  removed {stale}: a prove-red run that was killed left it behind" in out
    assert not stale.exists()
    deadline = time.monotonic() + 10
    while working_in(stale) and time.monotonic() < deadline:  # SIGKILL lands asynchronously
        time.sleep(0.1)
    assert working_in(stale) == []
    assert sorted(fresh.worktrees()) == sorted(
        [f"worktree {fresh.path}", f"worktree {live / 'head'}", f"worktree {ownerless / 'head'}"]
    )


# ---------------------------------------------------------------- verifier round 1


def brownfield(tmp_path: Path, missing: str) -> Repo:
    """tipcalc master with a tests/ folder of its own on main, but no uv.lock ("lock") or no
    pytest ("pytest"): plan/project-init adds them, the spec plugin and the M2 specs."""
    if not (TIPCALC_SOURCE / ".git").exists():
        pytest.skip(f"no tipcalc repo at {TIPCALC_SOURCE} (set TIPCALC_SOURCE)")
    path = tmp_path / "tipcalc"
    (tmp_path / "tmp").mkdir()
    clone = ["git", "clone", "-q", "--no-local", "--branch", "master"]
    ran = subprocess.run(
        [*clone, str(TIPCALC_SOURCE), str(path)],
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(),
    )
    assert ran.returncode == 0, output(ran)
    repo = Repo(path)
    repo.env["TMPDIR"] = str(tmp_path / "tmp")
    repo.git("remote", "remove", "origin")
    repo.git("branch", "-m", "master", "main")
    repo.write(
        "tests/test_tip.py",
        "from tipcalc import tip\n\n\ndef test_tip() -> None:\n    assert tip(100, 15) == 15.0\n",
    )
    if missing == "pytest":
        assert repo.run("uv", "lock", "-q").returncode == 0
    repo.commit("test: a first test")
    repo.branch("plan/project-init")
    if missing == "lock":
        assert repo.run("uv", "lock", "-q").returncode == 0
    added = repo.run("uv", "add", "-q", "--dev", "pytest")
    assert added.returncode == 0, output(added)
    shutil.copy2(SKILL / "templates" / "tests" / "conftest.py", path / "tests" / "conftest.py")
    for name in ("capabilities/cli.md", "capabilities/config.md", "roadmap.md", "tech-stack.md"):
        repo.write(f"specs/{name}", (M2_SPECS / name).read_text(encoding="utf-8"))
    repo.write("tests/test_cli.py", INIT_TEST_CLI)
    repo.write("tests/test_config.py", INIT_TEST_CONFIG)
    repo.commit("chore(init): project-init v3")
    return repo


@pytest.mark.parametrize("missing", ["lock", "pytest"])
def test_brownfield_base_without_lock_or_pytest(tmp_path: Path, missing: str) -> None:
    """The G1 merge of plan/project-init passes (design 5.5) when main already has tests but no
    uv.lock, or no pytest: the count guard collects the base's tests in the base worktree with
    HEAD's environment, and says so."""
    repo = brownfield(tmp_path, missing)
    result = repo.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.tip-default guard: passes on the old code" in out
    assert "0/0 red on base, guards 1/1 pass, gaps 5/5 xfail, tests 1 -> 7" in out
    why = "the base has no uv.lock" if missing == "lock" else "pytest does not run in the base's"
    assert f"note  the base's tests were collected with HEAD's environment: {why}" in out
    assert_cleaned_up(repo)


def land(repo: Repo) -> None:
    """The base case, merged to main as merge would leave it."""
    base_case(repo)
    repo.git("switch", "-q", "main")
    repo.git("merge", "-q", "--ff-only", "fix/usage-errors")


def test_spec_guard_is_for_fix_lane_neighbours_only(fresh: Repo) -> None:
    """Spec-Guard: never lets an added or changed scenario skip its red proof: on feat/ and
    chg/ it is ignored, and on fix/ it does not cover a MODIFIED id."""
    land(fresh)
    fresh.branch("chg/exit-64")
    fresh.edit("specs/capabilities/cli.md", "and the exit code is 2", "and the exit code is 64")
    fresh.commit("change(cli): exit 64\n\nSpec-Guard: cli.no-args")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args passes on the old code: it pins nothing new" in out
    assert "warn  cli.no-args: Spec-Guard: ignored on chg/exit-64" in out
    assert "cli.no-args guard" not in out

    fresh.git("branch", "-m", "chg/exit-64", "fix/exit-64")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args passes on the old code: it pins nothing new" in out
    assert "warn  cli.no-args: Spec-Guard: ignored; the scenario is changed" in out

    fresh.git("switch", "-q", "main")
    fresh.branch("feat/version")
    fresh.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    fresh.write("tests/test_version.py", TAUTOLOGY)
    fresh.commit("feat(cli): version\n\nSpec-Guard: cli.version")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.version passes on the old code: it pins nothing new" in out
    assert "warn  cli.version: Spec-Guard: ignored on feat/version" in out


VERSION_MD = """
## Requirement: Version
The CLI SHALL report its version.

### Scenario: cli.version
- WHEN the user runs `tipcalc --version`
- THEN stdout is `tipcalc 0.1.0`
"""

TAUTOLOGY = """import pytest


@pytest.mark.spec("cli.version")
def test_version() -> None:
    assert True
"""


def test_a_subject_line_is_not_a_trailer(fresh: Repo) -> None:
    """A conventional `spec: ...` subject, or a prose paragraph that starts with `Spec:`, names
    no ids: only git's trailer block counts. The reworded scenario is MODIFIED, so it is proven
    from the diff alone (and its unchanged test pins nothing new)."""
    land(fresh)
    fresh.branch("chg/reword")
    fresh.edit("specs/capabilities/cli.md", "holds a usage line", "holds one usage line")
    fresh.commit(
        "spec: cli.tip-default wording is fine, reword cli.no-args\n\n"
        "Spec: cli.bad-amount is prose here.\nThe paragraph is prose, not trailers."
    )
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args passes on the old code: it pins nothing new" in out
    assert "cli.tip-default" not in out and "cli.bad-amount" not in out, out
    assert "warn" not in out, out


SRC_VERSION = (
    SRC_FIXED.replace(
        "def main() -> None:\n",
        'def main() -> None:\n    if sys.argv[1:] == ["--version"]:\n'
        '        print(f"tipcalc {__version__}")\n        return\n',
    )
    + '\n__version__ = "0.1.0"\n'
)

TEST_VERSION = """import subprocess

import pytest

from tipcalc import __version__


@pytest.mark.spec("cli.version")
def test_version() -> None:
    r = subprocess.run(["tipcalc", "--version"], capture_output=True, text=True, check=False)
    assert r.stdout == f"tipcalc {__version__}\\n"
"""

SMOKE = """

@pytest.mark.spec("cli.version")
def test_version_smoke() -> None:
    assert True
"""


def test_a_red_that_never_ran_the_body_runs_again_with_stubs(fresh: Repo) -> None:
    """A test file that imports a name new at HEAD does not even collect on the old code, so
    that red says nothing about the test bodies. They run once more with stubs for the names
    the old code lacks: the real test then fails on its assertion, and a tautology beside it
    passes, which no Red: trailer excuses (not even one tdd red printed before the tautology
    was added)."""
    land(fresh)
    fresh.branch("feat/version")
    fresh.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    fresh.write("src/tipcalc/__init__.py", SRC_VERSION)
    fresh.write("tests/test_version.py", TEST_VERSION + SMOKE)
    fresh.commit("feat(cli): version\n\nRed: cli.version: assert '' == 'tipcalc 0.1.0\\n'")
    assert fresh.pytest().returncode == 0
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.version: tests/test_version.py::test_version_smoke passed on the old code "
        "with stubs for the names it lacks, so it pins nothing new: without the stubs it failed "
        "there only because the new code is missing"
    ) in out

    fresh.write("tests/test_version.py", TEST_VERSION)
    fresh.git("commit", "-q", "-a", "--amend", "-m", "feat(cli): version")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.version red (collection error; with stubs: assert '' == 'tipcalc <stu" in out

    # An existence check passes against a stub too: tdd red refuses it, and prove-red agrees.
    fresh.write("tests/test_version.py", TEST_VERSION.replace(' == f"tipcalc', ' or f"tipcalc'))
    fresh.git("commit", "-q", "-a", "--amend", "-m", "feat(cli): version")
    result = fresh.project("prove-red")
    assert result.returncode == 1, output(result)
    assert "test_version passed on the old code with stubs" in result.stdout
    fresh.write("src/tipcalc/__init__.py", SRC_FIXED + '\n__version__ = "stub"\n')
    red = fresh.project("tdd", "red", "cli.version")
    assert red.returncode == 1 and "cli.version: passes already" in red.stdout, output(red)


def test_a_changed_scenario_with_an_unchanged_test_behind_a_new_import(landed: Repo) -> None:
    """A MODIFIED scenario whose test did not change, in a file that gains an import new at
    HEAD: red on the old code by the collection error only, and a pass with stubs. A Red:
    trailer written by hand does not change that."""
    landed.branch("fix/reword")
    landed.edit("specs/capabilities/cli.md", "holds a usage line", "holds one usage line")
    landed.write("src/tipcalc/__init__.py", SRC_VERSION)
    landed.edit(
        "tests/test_cli.py", "import pytest\n", "import pytest\n\nfrom tipcalc import __version__\n"
    )
    landed.commit("fix(cli): reword\n\nSpec: cli.no-args\nRed: cli.no-args: assert 1 == 2")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.no-args: tests/test_cli.py::test_no_args passed on the old code with stubs"
    ) in out


RECEIPT_MD = """
## Requirement: Receipt
The CLI SHALL total the bill and the tip.

### Scenario: cli.receipt
- WHEN a receipt is made for a bill of 100
- THEN its total is 115.0
"""

RECEIPT_STUB = """

class Receipt:
    def __init__(self, bill: float) -> None:
        self.bill = bill

    def total(self) -> float:
        raise NotImplementedError
"""

TEST_RECEIPT = """import pytest

from tipcalc import Receipt


@pytest.fixture
def receipt() -> Receipt:
    return Receipt(100)


@pytest.mark.spec("cli.receipt")
def test_receipt_total(receipt: Receipt) -> None:
    assert receipt.total() == 115.0
"""


def test_a_red_the_stubs_cannot_reach_needs_the_red_trailer(fresh: Repo) -> None:
    """A fixture that builds a class new at HEAD fails in setup on the old code, stubs or not
    (a stub class cannot be made). Only the Red: line tdd red printed, when the hand-written
    stub let the body run, carries that red."""
    land(fresh)
    fresh.branch("feat/receipt")
    fresh.write("specs/capabilities/cli.md", CLI_MD + RECEIPT_MD)
    fresh.write("tests/test_receipt.py", TEST_RECEIPT)
    fresh.write("src/tipcalc/__init__.py", SRC_FIXED + RECEIPT_STUB)
    red = fresh.project("tdd", "red", "cli.receipt")
    assert red.returncode == 0, output(red)
    assert "Red: cli.receipt: NotImplementedError" in red.stdout.splitlines()
    fresh.edit(
        "src/tipcalc/__init__.py",
        "raise NotImplementedError\n",
        "return self.bill + tip(self.bill, 15)\n",
    )
    fresh.commit("feat(cli): receipt\n\nSpec: cli.receipt")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.receipt: tests/test_receipt.py::test_receipt_total fails on the old code "
        "before its body reaches an assertion (collection error), so that red proves nothing; "
        "commit the 'Red: cli.receipt: <reason>' line that `mise run tdd -- red cli.receipt` "
        "prints"
    ) in out
    fresh.git(
        "commit",
        "-q",
        "--amend",
        "-m",
        "feat(cli): receipt\n\nSpec: cli.receipt\nRed: cli.receipt: NotImplementedError",
    )
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.receipt red (collection error); Red: NotImplementedError" in out


def test_every_new_test_of_an_added_scenario_is_red(fresh: Repo) -> None:
    """One red test does not carry a tautology beside it: every new or changed test function of
    the id must fail on the old code (tdd red refuses it too). Tagging an older test with one
    more id is not a change."""
    base_case(fresh)
    tautology = '\n\n@pytest.mark.spec("cli.no-args")\ndef test_t() -> None:\n    assert True\n'
    fresh.write("tests/test_cli.py", TEST_CLI + tautology)
    fresh.commit("test(cli): one more")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.no-args: tests/test_cli.py::test_t passed on the old code, so it pins nothing "
        "new; every new or changed test of the scenario must fail there"
    ) in out

    fresh.write("src/tipcalc/__init__.py", SRC_OLD)
    red = fresh.project("tdd", "red", "cli.no-args")
    assert red.returncode == 1, output(red)
    assert "FAIL  cli.no-args: tests/test_cli.py::test_t passes already" in red.stdout


def test_retagging_an_older_test_is_not_a_change(landed: Repo) -> None:
    """fix/: a regression test for cli.no-args, and the older test_tip_default also tagged
    cli.no-args. The older test is unchanged apart from its tag, so it may pass."""
    landed.branch("fix/usage-line")
    text = TEST_CLI.replace(
        '@pytest.mark.spec("cli.tip-default")',
        '@pytest.mark.spec("cli.tip-default", "cli.no-args")',
    )
    regression = (
        '\n\n@pytest.mark.spec("cli.no-args")\ndef test_usage_names_the_bill() -> None:\n'
        '    assert "BILL AMOUNT" in tipcalc().stderr\n'
    )
    landed.write("tests/test_cli.py", text + regression)
    landed.write(
        "src/tipcalc/__init__.py",
        SRC_FIXED.replace("usage: tipcalc BILL", "usage: tipcalc BILL AMOUNT"),
    )
    landed.commit("fix(cli): name the amount\n\nSpec: cli.no-args")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.no-args red (assert 'BILL AMOUNT' in" in out


def test_conftest_that_imports_new_code(fresh: Repo) -> None:
    """A conftest.py that imports code new at HEAD stops pytest before any test on the old
    code: FAIL, with the file, the error and the fix."""
    base_case(fresh)
    text = fresh.read("tests/conftest.py")
    fresh.write("tests/conftest.py", text + "\n\nfrom tipcalc import parse_amount  # noqa: E402\n")
    fresh.commit("test: conftest import")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  prove-red: tests/conftest.py does not load (ImportError: cannot import name "
        "'parse_amount' from 'tipcalc') on the old code, so no test ran there and nothing is "
        "proven. A conftest.py may import only what the base already has: import new code "
        "inside the fixture that uses it"
    ) in out
    assert_cleaned_up(fresh)


# ---------------------------------------------------------------- verifier round 2

SMOKE_TEST = (
    "from tipcalc import tip\n\n\ndef test_tip_math() -> None:\n    assert tip(200, 10) == 20.0\n"
)


def test_count_guard_sees_a_test_outside_the_test_roots(landed: Repo) -> None:
    """The count guard collects the base as pytest does there, in a worktree at the base: a
    test in checks/ (outside the test roots in .project.toml) counts, and deleting it fails."""
    landed.write("checks/test_smoke.py", SMOKE_TEST)
    landed.commit("test: smoke\n\nMerged-By: mise run merge")
    assert "4 passed" in landed.pytest().stdout
    landed.branch("chg/drop-smoke")
    (landed.path / "checks" / "test_smoke.py").unlink()
    landed.commit("change: drop the smoke check")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  tests disappeared: 3 collected at HEAD, 4 at the base" in out
    assert_cleaned_up(landed)


def test_count_guard_uses_the_base_pytest_config(landed: Repo) -> None:
    """A branch that narrows python_files so a test is no longer collected: check has nothing
    to say (the test is linked to no scenario), but the base's own config collects 4 and HEAD's
    collects 3."""
    landed.write("tests/test_smoke.py", SMOKE_TEST)
    landed.commit("test: smoke\n\nMerged-By: mise run merge")
    landed.branch("chore/quiet")
    landed.edit(
        "pyproject.toml", "markers = [", 'python_files = ["test_c*.py", "test_p*.py"]\nmarkers = ['
    )
    landed.commit("chore: tidy the pytest config")
    ran = landed.pytest()
    assert ran.returncode == 0 and "3 passed" in ran.stdout, output(ran)
    assert landed.project("check").returncode == 0
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  tests disappeared: 3 collected at HEAD, 4 at the base" in out


TEST_VERSION_TABLE = """import subprocess

import pytest


@pytest.mark.spec("cli.version")
@pytest.mark.parametrize(
    ("args", "want"),
    [(["--version"], "tipcalc 0.1.0\\n")],
    ids=["version"],
)
def test_version(args: list[str], want: str) -> None:
    r = subprocess.run(["tipcalc", *args], capture_output=True, text=True, check=False)
    assert r.stdout == want
"""
TIP_ROW = '(["100"], "tip: 15.0\\n")'


def test_every_new_parametrized_case_is_red(landed: Repo) -> None:
    """A new table test: every case is new, so each must fail on the old code; a case that
    passes there rides on nothing (tdd red refuses it too)."""
    landed.branch("feat/version")
    landed.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    table = TEST_VERSION_TABLE.replace(
        '0.1.0\\n")],\n    ids=["version"]', f'0.1.0\\n"), {TIP_ROW}],\n    ids=["version", "tip"]'
    )
    assert 'ids=["version", "tip"]' in table
    landed.write("tests/test_version.py", table)
    red = landed.project("tdd", "red", "cli.version")
    assert red.returncode == 1, output(red)
    assert (
        "FAIL  cli.version: tests/test_version.py::test_version[tip] passes already" in red.stdout
    )
    landed.write("src/tipcalc/__init__.py", SRC_VERSION.replace("{__version__}", "0.1.0"))
    landed.commit("feat(cli): version")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.version: tests/test_version.py::test_version[tip] passed on the old code, so "
        "it pins nothing new; every new or changed test of the scenario must fail there"
    ) in out


def test_a_new_row_of_an_older_table_test_is_red(landed: Repo) -> None:
    """A changed table test keeps its older rows, which may pass on the old code; each new row
    must fail there. (tdd red cannot tell an older row from a new one, so only prove-red, which
    collects the base, checks each new row of a changed test.)"""
    landed.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    landed.write("tests/test_version.py", TEST_VERSION_TABLE)
    landed.write("src/tipcalc/__init__.py", SRC_VERSION.replace("{__version__}", "0.1.0"))
    landed.commit("feat(cli): version\n\nMerged-By: mise run merge")
    landed.branch("fix/short-flag")
    short = '(["-V"], "tipcalc 0.1.0\\n")'
    landed.edit("tests/test_version.py", '0.1.0\\n")],', f'0.1.0\\n"), {short}],')
    landed.edit("tests/test_version.py", 'ids=["version"]', 'ids=["version", "short"]')
    landed.edit("src/tipcalc/__init__.py", '== ["--version"]', 'in (["--version"], ["-V"])')
    landed.commit("fix(cli): -V prints the version\n\nSpec: cli.version")
    assert landed.pytest().returncode == 0
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.version red (assert '' == 'tipcalc 0.1.0\\n')" in out

    landed.edit("tests/test_version.py", f"{short}],", f"{short}, {TIP_ROW}],")
    landed.edit("tests/test_version.py", '"short"]', '"short", "tip"]')
    landed.commit("test(cli): one more row")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.version: tests/test_version.py::test_version[tip] passed on the old code" in out
    )


ASSIGNED = """

def _smoke() -> None:
    assert True


test_version_smoke = pytest.mark.spec("cli.version")(_smoke)
"""


def test_a_test_made_by_assignment_is_new_too(landed: Repo) -> None:
    """`test_x = pytest.mark.spec(id)(fn)` defines a test without a def: in a new file, or new
    in an older file, it is a new test and must fail on the old code like any other."""
    landed.branch("feat/version")
    landed.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    landed.write("tests/test_version.py", TEST_VERSION_TABLE + ASSIGNED)
    landed.write("src/tipcalc/__init__.py", SRC_VERSION.replace("{__version__}", "0.1.0"))
    landed.commit("feat(cli): version")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.version: tests/test_version.py::test_version_smoke passed on the old" in out

    landed.git("switch", "-q", "main")
    landed.branch("fix/usage-line")
    regression = (
        '\n\n@pytest.mark.spec("cli.no-args")\ndef test_usage_names_the_bill() -> None:\n'
        '    assert "BILL AMOUNT" in tipcalc().stderr\n'
    )
    assigned = ASSIGNED.replace("test_version_smoke", "test_no_args_smoke").replace(
        "cli.version", "cli.no-args"
    )
    landed.write("tests/test_cli.py", TEST_CLI + regression + assigned)
    red = landed.project("tdd", "red", "cli.no-args")
    assert red.returncode == 1, output(red)
    assert "FAIL  cli.no-args: tests/test_cli.py::test_no_args_smoke passes already" in red.stdout
    landed.edit("src/tipcalc/__init__.py", "usage: tipcalc BILL", "usage: tipcalc BILL AMOUNT")
    landed.commit("fix(cli): name the amount\n\nSpec: cli.no-args")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args: tests/test_cli.py::test_no_args_smoke passed on the old code" in out


def test_every_gap_is_proven_on_every_branch(fresh: Repo) -> None:
    """Design 5.5 runs every gap, not only the gaps a branch adds: after plan/project-init
    lands, a later branch lists the 5 gaps, and a gap test it weakens fails prove-red even
    though its scenario did not change."""
    fresh.branch("plan/project-init")
    for name in ("capabilities/cli.md", "capabilities/config.md", "roadmap.md", "tech-stack.md"):
        fresh.write(f"specs/{name}", (M2_SPECS / name).read_text(encoding="utf-8"))
    fresh.write("tests/test_cli.py", INIT_TEST_CLI)
    fresh.write("tests/test_config.py", INIT_TEST_CONFIG)
    fresh.commit("chore(init): project-init v3")
    fresh.git("switch", "-q", "main")
    fresh.git("merge", "-q", "--ff-only", "plan/project-init")
    fresh.branch("chg/readme")
    fresh.edit("README.md", "tipcalc", "tipcalc, a tip calculator")
    fresh.commit("docs: say what it is")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "0/0 red on base, guards 0/0 pass, gaps 5/5 xfail, tests 6 -> 6" in out

    fresh.edit(
        "tests/test_cli.py",
        'r = tipcalc()\n    assert "Traceback" not in r.stderr',
        "r = tipcalc()\n    assert r.returncode != 0",
    )
    fresh.commit("test(cli): looser")
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert "FAIL  cli.no-args gap test does not reproduce the gap" in out


OPTIONAL_IMPORT = """
try:
    from tipcalc._speedups import fast_tip
except ImportError:
    fast_tip = None


def hook() -> object:
    return getattr(sys.modules[__name__], "tip_hook", None)
"""


def test_the_stubs_leave_the_old_code_alone(landed: Repo) -> None:
    """The stubs stand in only for names a test asks for. The old code's own imports and
    lookups behave as they always did: its optional import still fails and its getattr still
    finds no hook, so tip() still works, and a new test that only checks tip() passes with the
    stubs, pinning nothing new."""
    landed.edit(
        "src/tipcalc/__init__.py",
        "def tip(bill: float, percent: float) -> float:\n",
        OPTIONAL_IMPORT
        + "\n\ndef tip(bill: float, percent: float) -> float:\n"
        + "    if fast_tip is not None or hook() is not None:\n"
        + "        raise RuntimeError('no speedups here')\n",
    )
    landed.commit("perf: optional speedups\n\nMerged-By: mise run merge")
    assert landed.pytest().returncode == 0
    landed.branch("feat/version")
    landed.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    landed.edit("src/tipcalc/__init__.py", "import sys\n", 'import sys\n\n__version__ = "0.1.0"\n')
    landed.write(
        "tests/test_version.py",
        "import pytest\n\nfrom tipcalc import __version__, tip\n\n\n"
        '@pytest.mark.spec("cli.version")\ndef test_tip_still_works() -> None:\n'
        "    assert tip(100, 15) == 15.0\n",
    )
    landed.commit("feat(cli): version")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.version: tests/test_version.py::test_tip_still_works passed on the old code "
        "with stubs"
    ) in out


def test_a_base_that_does_not_collect_is_a_warning(landed: Repo) -> None:
    """A base whose pytest config is broken collects nothing, in its own environment or in
    HEAD's. The branch that repairs it cannot change the base, so the count guard compares with
    0 and says why, instead of blocking the only way out."""
    landed.edit("pyproject.toml", 'addopts = "', 'addopts = "--no-such-flag ')
    landed.commit("chore: break the pytest config\n\nMerged-By: mise run merge")
    landed.branch("chore/repair-addopts")
    landed.edit("pyproject.toml", 'addopts = "--no-such-flag ', 'addopts = "')
    landed.commit("chore: repair the pytest config")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert (
        "warn  the count guard compares with 0: the base's tests collect neither in its own "
        "environment nor in HEAD's (pytest --collect-only failed on the base's tests and code"
    ) in out
    assert "ok    test count 0 -> 3" in out
    assert_cleaned_up(landed)


# ---------------------------------------------------------------- M3 fix round 1

THOUSANDS_MD = """
## Requirement: Thousands separators
The CLI SHALL accept a bill written with thousands separators.

### Scenario: cli.thousands
- WHEN the user runs `tipcalc 1,000`
- THEN stdout is `tip: 150.0` and the exit code is 0
"""

TEST_THOUSANDS = """import pytest

from tipcalc import parse_amount


@pytest.mark.spec("cli.thousands")
def test_thousands() -> None:
    assert parse_amount("1,000") == 1000.0
"""


def test_fix_lane_red_from_an_exception_the_old_code_raises(landed: Repo) -> None:
    """A fix/ regression test that meets the ValueError the existing parse_amount raises is red
    for the right reason (design 5.5: failed is red; 5.4 names only ImportError, NameError,
    SyntaxError and fixture or collection errors as wrong). tdd red records it with the
    exception as the Red: reason, and prove-red proves it without any trailer; the exception
    type is named once."""
    landed.branch("fix/thousands")
    landed.write("specs/capabilities/cli.md", CLI_MD + THOUSANDS_MD)
    landed.write("tests/test_thousands.py", TEST_THOUSANDS)
    red = landed.project("tdd", "red", "cli.thousands")
    assert red.returncode == 0, output(red)
    assert "Red: cli.thousands: ValueError: bill must be a number" in red.stdout.splitlines()
    landed.edit(
        "src/tipcalc/__init__.py", "return float(raw)", 'return float(raw.replace(",", ""))'
    )
    green = landed.project("tdd", "green", "cli.thousands")
    assert green.returncode == 0, output(green)
    landed.commit("fix(cli): accept thousands separators\n\nSpec: cli.thousands")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.thousands red (ValueError: bill must be a number)\n" in out
    assert "ValueError: ValueError" not in out
    assert "prove-red: ok; 1/1 red on base (1 exception)" in out

    # A test that swallows that exception still pins nothing new.
    landed.write(
        "tests/test_thousands.py",
        TEST_THOUSANDS.replace(
            '    assert parse_amount("1,000") == 1000.0\n',
            '    try:\n        parse_amount("1,000")\n    except ValueError:\n        pass\n',
        ),
    )
    landed.git("commit", "-q", "-a", "--amend", "--no-edit")
    result = landed.project("prove-red")
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.thousands passes on the old code: it pins nothing new" in result.stdout


TEST_VERSION_CALL = """import pytest

import tipcalc


@pytest.mark.spec("cli.version")
def test_version() -> None:
    assert tipcalc.version() == "0.1.0"
"""


def test_a_name_the_module_lacks_is_still_the_wrong_red(landed: Repo) -> None:
    """`tipcalc.version()` before version exists is the attribute form of an ImportError: tdd
    red refuses it with the stub hint. With the stub it records NotImplementedError, and
    prove-red proves the red through its run with stubs."""
    landed.branch("feat/version")
    landed.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    landed.write("tests/test_version.py", TEST_VERSION_CALL)
    refused = landed.project("tdd", "red", "cli.version")
    assert refused.returncode == 1, output(refused)
    assert (
        "FAIL  cli.version: AttributeError is the wrong red: add a stub that raises "
        "NotImplementedError"
    ) in refused.stdout
    landed.write(
        "src/tipcalc/__init__.py",
        SRC_FIXED + "\n\ndef version() -> str:\n    raise NotImplementedError\n",
    )
    red = landed.project("tdd", "red", "cli.version")
    assert red.returncode == 0, output(red)
    assert "Red: cli.version: NotImplementedError" in red.stdout.splitlines()
    landed.edit("src/tipcalc/__init__.py", "raise NotImplementedError", 'return "0.1.0"')
    landed.commit("feat(cli): version")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert (
        "ok    cli.version red (AttributeError: module 'tipcalc' has no attribute 'version'; "
        "with stubs: NotImplementedError)"
    ) in out


REGRESSION_BILL_AMOUNT = (
    '\n\n@pytest.mark.spec("cli.no-args")\ndef test_usage_names_the_bill() -> None:\n'
    '    assert "BILL AMOUNT" in tipcalc().stderr\n'
)


def test_a_moved_test_file_keeps_its_older_tests(landed: Repo) -> None:
    """fix/: tests/test_cli.py moves to tests/cli/ (a plain mv, not yet staged, for tdd red)
    and gains a regression test. The moved test_no_args is the base's code in another file, so
    it may pass on the old code like any older test; the new test must be red. Editing the
    moved test makes it a changed test, which must be red again."""
    landed.branch("fix/usage-line")
    (landed.path / "tests" / "cli").mkdir()
    (landed.path / "tests" / "test_cli.py").rename(landed.path / "tests" / "cli" / "test_cli.py")
    landed.write("tests/cli/test_cli.py", TEST_CLI + REGRESSION_BILL_AMOUNT)
    red = landed.project("tdd", "red", "cli.no-args")
    assert red.returncode == 0, output(red)
    assert "Red: cli.no-args: assert 'BILL AMOUNT' in 'usage: tipcalc BILL\\n'" in red.stdout
    landed.edit("src/tipcalc/__init__.py", "usage: tipcalc BILL", "usage: tipcalc BILL AMOUNT")
    landed.commit("fix(cli): name the amount\n\nSpec: cli.no-args")
    assert landed.git("diff", "--name-status", "-M", "main", "--", "tests").startswith("R")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.no-args red (assert 'BILL AMOUNT' in 'usage: tipcalc BILL\\n')" in out
    assert "ok    test count 3 -> 4" in out

    landed.edit(
        "tests/cli/test_cli.py",
        '    assert "Traceback" not in r.stderr\n',
        '    assert "Traceback" not in r.stderr\n    assert r.stderr\n',
    )
    landed.git("commit", "-q", "-a", "--amend", "--no-edit")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.no-args: tests/cli/test_cli.py::test_no_args passed on the old code, so it "
        "pins nothing new"
    ) in out


def test_prove_red_reads_the_committed_paths(fresh: Repo) -> None:
    """prove-red judges the committed HEAD, so the source roots it swaps for the old code come
    from the .project.toml that HEAD and the merge-base hold, not from an uncommitted edit."""
    base_case(fresh)
    fresh.write(".project.toml", '[paths]\nsrc = ["docs"]\n')
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.no-args red (assert 1 == 2)" in out
    assert "warn  prove-red judges the committed HEAD" not in out  # untracked, so no warning
    assert_cleaned_up(fresh)


def colocate(repo: Repo) -> None:
    """The base case landed with its tests inside the package, as orca keeps them:
    src/tipcalc/tests is a package of its own (tipcalc.tests), .project.toml names it the test
    root, and the spec plugin moves to the root conftest.py so that pytest loads it there."""
    land(repo)
    repo.write("src/tipcalc/tests/__init__.py", "")
    repo.git("mv", "tests/conftest.py", "conftest.py")
    for name in ("test_cli.py", "test_parse.py"):
        repo.git("mv", f"tests/{name}", f"src/tipcalc/tests/{name}")
    repo.write(".project.toml", '[paths]\nsrc = ["src"]\ntests = ["src/tipcalc/tests"]\n')
    repo.commit("test: keep the tests inside the package")


def test_tests_inside_the_source_root_run_on_the_old_code(fresh: Repo) -> None:
    """Tests inside a source root are HEAD's tests, not old code: prove-red keeps them when it
    swaps src for the base, so a new test in src/tipcalc/tests is red there (it recorded
    `notrun` before). The stubs reach the names the old code lacks for a test module inside
    the package too, while pytest's own lookups on that module still miss: a stub for its
    pytest_generate_tests made a false NotImplementedError red at collection. A loose
    test_*.py beside the code counts the same way."""
    colocate(fresh)
    assert fresh.pytest().returncode == 0
    fresh.branch("feat/version")
    fresh.write("specs/capabilities/cli.md", CLI_MD + VERSION_MD)
    fresh.write("src/tipcalc/__init__.py", SRC_VERSION)
    fresh.write("src/tipcalc/tests/test_version.py", TEST_VERSION)
    fresh.commit("feat(cli): version\n\nSpec: cli.version")
    assert fresh.pytest().returncode == 0
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.version red (collection error; with stubs: assert '' == 'tipcalc <stu" in out
    assert "notrun" not in out

    fresh.git("mv", "src/tipcalc/tests/test_version.py", "src/tipcalc/test_version.py")
    fresh.git("commit", "-q", "--amend", "--no-edit")
    assert fresh.pytest().returncode == 0
    result = fresh.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.version red (collection error; with stubs: assert '' == 'tipcalc <stu" in out
    assert_cleaned_up(fresh)


# ---------------------------------------------------------------- v3.1 M14: flag-off guards

FLAG_OFF_MD = """
## Requirement: Strict amounts behind a flag
The CLI SHALL refuse a bill with more than two decimals when TIPCALC_FLAG_STRICT is on.

### Scenario: cli.strict-off [flag-off: TIPCALC_FLAG_STRICT]
- GIVEN TIPCALC_FLAG_STRICT is unset
- WHEN the user runs `tipcalc 100.123`
- THEN stdout is `tip: 15.02` and the exit code is 0
"""

TEST_STRICT_OFF = (
    RUN_TIPCALC
    + """

@pytest.mark.spec("cli.strict-off")
def test_strict_off() -> None:
    r = tipcalc("100.123")
    assert r.returncode == 0
    assert r.stdout == "tip: 15.02\\n"
"""
)


def test_a_flag_off_scenario_is_a_guard_that_passes_on_the_old_code(landed: Repo) -> None:
    """I22 (design B.2): a [flag-off] scenario pins the old behaviour with the flag off, so
    prove-red wants it to pass on the old code, although the branch adds it."""
    landed.branch("feat/strict")
    landed.write("specs/capabilities/cli.md", CLI_MD + FLAG_OFF_MD)
    landed.write("tests/test_strict.py", TEST_STRICT_OFF)
    landed.commit("feat(cli): strict amounts behind a flag")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 0, out
    assert "ok    cli.strict-off flag-off guard: passes on the old code" in out
    assert "prove-red: ok; 0/0 red on base, guards 1/1 pass" in out

    # the off path changed: the test pins what the new code prints with the flag off
    landed.write("tests/test_strict.py", TEST_STRICT_OFF.replace("tip: 15.02", "tip: 15.1"))
    landed.commit("test(cli): the off path rounds the bill first")
    result = landed.project("prove-red")
    out = output(result)
    assert result.returncode == 1, out
    assert (
        "FAIL  cli.strict-off flag-off guard broke: the old behaviour changed with the flag off: "
        "tests/test_strict.py::test_strict_off failed on the old code"
    ) in out
