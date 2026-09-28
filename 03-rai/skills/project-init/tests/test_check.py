"""project-init v3, milestone M2: `project.py check` and `status`, and the conftest spec plugin.

Each test works on a throwaway copy of a tipcalc repo built from tests/fixtures/:
- fixtures/tipcalc: main right after adoption (1 characterization scenario, 5 gaps);
- fixtures/feat1: the entrypoint-hardening change laid over it on feat/entrypoint-hardening.
fixtures/tipcalc carries the rendered [tool.git-cliff] config and the CHANGELOG.md it writes for
the adoption history, so a close commit can be checked against what merge would add.
Dotfiles are stored without their dot (gitignore, project.toml, mise.fixture.toml and its
mise.fixture.lock, AGENTS.fixture.md) so they never act on this vault; build() renames them.
The tests run the real pytest with the template conftest (which writes
.cache/spec-results.json), then the template project.py. Cases (a) to (j) are the M2 table in
03-rai/skills/project-init/DESIGN.md, section 12. The fixture repos run on the
pytest this suite runs on; test_pytest_majors repeats the core cases on pytest 8 and 9 (in
venvs uv builds), so a pytest release cannot flip the result unnoticed.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
PROJECT_PY = SKILL / "templates" / "scripts" / "project.py"
CONFTEST = SKILL / "templates" / "tests" / "conftest.py"
FIXTURES = TESTS / "fixtures"
RENAMES = {
    "gitignore": ".gitignore",
    "project.toml": ".project.toml",
    "mise.fixture.toml": "mise.toml",
    "mise.fixture.lock": "mise.lock",
    "AGENTS.fixture.md": "AGENTS.md",
}
FEAT = "feat/entrypoint-hardening"
CHANGE = "specs/changes/2026-09-24-entrypoint-hardening"
TOOL_TRAILER = "Merged-By: mise run merge"
NEW_SCENARIO = """
### Scenario: cli.negative-amount
- WHEN the user runs `tipcalc -5`
- THEN stderr holds one `error:` line and no traceback, and the exit code is 2
"""


def clean_env() -> dict[str, str]:
    drop = ("GIT_", "PYTEST_", "GITHUB_", "PROJECT_MERGE")
    env = {k: v for k, v in os.environ.items() if not k.startswith(drop)}
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

    def run(
        self, *argv: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(argv),
            cwd=self.path,
            capture_output=True,
            text=True,
            check=False,
            env={**clean_env(), **(env or {})},
        )

    def git(self, *args: str) -> str:
        result = self.run("git", *args)
        assert result.returncode == 0, result.stderr
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

    def append(self, rel: str, text: str) -> None:
        self.write(rel, self.read(rel) + text)

    def commit(self, message: str) -> None:
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def pytest(self, *args: str) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, "-m", "pytest", *args)

    def project(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return self.run(sys.executable, "scripts/project.py", *args, env=env)

    def check(
        self, *args: str, env: dict[str, str] | None = None
    ) -> subprocess.CompletedProcess[str]:
        return self.project("check", *args, env=env)

    def results(self) -> dict[str, object]:
        return json.loads(self.read(".cache/spec-results.json"))


def output(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def build(dest: Path) -> Repo:
    shutil.copytree(FIXTURES / "tipcalc", dest)
    for old, new in RENAMES.items():
        (dest / old).rename(dest / new)
    (dest / "scripts").mkdir()
    shutil.copy2(PROJECT_PY, dest / "scripts" / "project.py")
    shutil.copy2(CONFTEST, dest / "tests" / "conftest.py")
    repo = Repo(dest)
    repo.git("init", "-q", "-b", "main")
    repo.commit(f"chore(init): project-init v3\n\n{TOOL_TRAILER}")
    return repo


@pytest.fixture(scope="session")
def base_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    repo = build(tmp_path_factory.mktemp("base") / "tipcalc")
    result = repo.pytest()
    assert result.returncode == 0, output(result)
    return repo.path


@pytest.fixture(scope="session")
def feat_template(base_template: Path, tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("feat") / "tipcalc"
    shutil.copytree(base_template, path, symlinks=True)
    repo = Repo(path)
    repo.git("switch", "-q", "-c", FEAT)
    shutil.copytree(FIXTURES / "feat1", path, dirs_exist_ok=True)
    repo.commit("spec(entrypoint-hardening): draft")
    return path


@pytest.fixture
def repo(base_template: Path, tmp_path: Path) -> Repo:
    shutil.copytree(base_template, tmp_path / "tipcalc", symlinks=True)
    return Repo(tmp_path / "tipcalc")


@pytest.fixture
def feat(feat_template: Path, tmp_path: Path) -> Repo:
    shutil.copytree(feat_template, tmp_path / "tipcalc", symlinks=True)
    return Repo(tmp_path / "tipcalc")


def approve(feat: Repo) -> None:
    feat.edit(f"{CHANGE}/requirements.md", "status: draft ", "status: approved ")


# ---------------------------------------------------------------- the M2 table, (a) to (j)


def test_a_scenario_without_a_test_on_main_fails(repo: Repo) -> None:
    text = repo.read("tests/test_cli.py")
    start = text.index('@pytest.mark.spec("cli.no-args")')
    end = text.index('@pytest.mark.spec("cli.help")')
    repo.write("tests/test_cli.py", text[:start] + text[end:])
    assert repo.pytest().returncode == 0
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.no-args: no linked test" in result.stdout


def test_b_test_tagged_with_an_unknown_id_fails(repo: Repo) -> None:
    repo.append(
        "tests/test_cli.py",
        '\n\n@pytest.mark.spec("nope.nope")\ndef test_nope() -> None:\n'
        '    assert tipcalc("100").returncode == 0\n',
    )
    assert repo.pytest().returncode == 0
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  nope.nope: unknown id, tagged on tests/test_cli.py::test_nope" in result.stdout


def test_c_skip_on_a_linked_test_fails(repo: Repo) -> None:
    repo.edit(
        "tests/test_cli.py",
        '@pytest.mark.spec("cli.tip-default")\n',
        '@pytest.mark.spec("cli.tip-default")\n'
        '@pytest.mark.skip(reason="cli.tip-default: later")\n',
    )
    assert repo.pytest().returncode == 0
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.tip-default: skip on a linked test" in result.stdout


def test_d_gap_with_a_strict_xfail_passes(repo: Repo) -> None:
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "FAIL" not in result.stdout
    assert "6 scenarios; 1 proven, 5 gaps, 0 pending" in result.stdout


def test_d_gap_whose_test_xpasses_fails(repo: Repo) -> None:
    repo.edit(
        "src/tipcalc/__init__.py",
        "    bill = float(sys.argv[1])\n",
        "    if len(sys.argv) < 2:\n"
        '        print("usage: tipcalc BILL", file=sys.stderr)\n'
        "        raise SystemExit(2)\n"
        "    bill = float(sys.argv[1])\n",
    )
    assert repo.pytest().returncode == 1  # a strict XPASS fails the run
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert (
        "FAIL  cli.no-args: tests/test_cli.py::test_no_args passes now (strict XPASS)"
        in result.stdout
    )


def test_d_gap_slug_missing_from_the_roadmap_fails(repo: Repo) -> None:
    repo.edit(
        "specs/roadmap.md",
        "- [ ] entrypoint-hardening: clear errors instead of tracebacks\n",
        "",
    )
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.no-args: gap slug 'entrypoint-hardening' is not in specs/roadmap.md" in (
        result.stdout
    )


def test_e_pending_scenario_passes_on_a_branch_with_an_open_change(feat: Repo) -> None:
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert f"pend  cli.negative-amount: no linked test (added on {FEAT})" in result.stdout
    assert "1 added, 5 modified, 0 removed since main" in result.stdout


def test_e_the_same_pending_scenario_fails_on_main(repo: Repo) -> None:
    repo.append("specs/capabilities/cli.md", NEW_SCENARIO)
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.negative-amount: no linked test" in result.stdout


def test_f_review_focus_row_naming_a_missing_id_fails(feat: Repo) -> None:
    feat.edit(
        f"{CHANGE}/validation.md",
        "- negative bill -> cli.negative-amount",
        "- negative bill -> cli.negative-bill",
    )
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "I13: review focus 'negative bill' names unknown id cli.negative-bill" in result.stdout


def test_g_121_line_requirements_only_warns(feat: Repo) -> None:
    rel = f"{CHANGE}/requirements.md"
    missing = 121 - len(feat.read(rel).splitlines())
    notes = "".join(f"- context note {n}\n" for n in range(missing))
    feat.edit(rel, "## Rollback\n", notes + "## Rollback\n")  # under Context: Rollback is one line
    assert len(feat.read(rel).splitlines()) == 121
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert f"warn  {rel}: 121 lines (cap 120)" in result.stdout


def test_h_open_question_in_an_approved_change_fails(feat: Repo) -> None:
    approve(feat)
    feat.append(f"{CHANGE}/requirements.md", "- [NEEDS CLARIFICATION: exit 1 or 2?]\n")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  {CHANGE}/requirements.md:" in result.stdout
    assert "must be answered" in result.stdout


def test_h_open_question_in_a_draft_change_only_warns(feat: Repo) -> None:
    question = "- [NEEDS CLARIFICATION: exit 1 or 2?]\n"
    feat.edit(f"{CHANGE}/requirements.md", "## Rollback\n", question + "## Rollback\n")
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert f"warn  {CHANGE}/requirements.md:" in result.stdout


def test_h_open_question_in_mission_fails_even_on_a_plan_branch(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "plan/2026-09-24-replan")
    repo.append("specs/mission.md", "\n[NEEDS CLARIFICATION: is a GUI in scope?]\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  specs/mission.md:" in result.stdout
    assert "I1" not in result.stdout


def before_g1(repo: Repo) -> None:
    """Put the repo before its first merge (G1): main at a commit that holds no .project.toml,
    and plan/project-init one commit past it with the adopted tree, checked out."""
    adopted = repo.git("rev-parse", "HEAD^{tree}").strip()
    repo.git("rm", "-q", "--cached", ".project.toml")
    tree = repo.git("write-tree").strip()
    repo.git("reset", "-q")
    base = repo.git("commit-tree", tree, "-m", "chore: before project-init").strip()
    top = repo.git("commit-tree", adopted, "-p", base, "-m", "chore(init): project-init v3").strip()
    repo.git("switch", "-q", "-c", "plan/project-init")
    repo.git("reset", "-q", top)
    repo.git("update-ref", "refs/heads/main", base)


def test_h_open_questions_before_g1_are_listed_and_block_only_g1(repo: Repo) -> None:
    """orca re-check defect 3, design 6.P2: the talk leaves open questions as markers, in
    mission.md too. Before G1 (main holds no .project.toml) spec-check lists each one as a
    warning, so verify stays green on plan/project-init; G1's merge (check --strict) refuses
    while any remain. Once main holds .project.toml, a marker in mission.md fails again."""
    before_g1(repo)
    repo.append("specs/mission.md", "\n[NEEDS CLARIFICATION: is a GUI in scope?]\n")
    repo.append("specs/roadmap.md", "\n<!-- [needs clarification: web page or not?] -->\n")
    mission = len(repo.read("specs/mission.md").splitlines())
    roadmap = len(repo.read("specs/roadmap.md").splitlines())
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert (
        f"warn  specs/mission.md:{mission}: open question [NEEDS CLARIFICATION: is a GUI in "
        "scope?]; G1's merge refuses it"
    ) in result.stdout, output(result)
    assert (
        f"warn  specs/roadmap.md:{roadmap}: open question [needs clarification: web page or "
        "not?]; G1's merge refuses it"
    ) in result.stdout, output(result)
    assert "must be answered" not in result.stdout
    strict = repo.check("--strict")
    assert strict.returncode == 1, output(strict)
    assert f"FAIL  specs/mission.md:{mission}: open question [NEEDS CLARIFICATION" in strict.stdout
    assert f"FAIL  specs/roadmap.md:{roadmap}: open question [NEEDS CLARIFICATION" in strict.stdout
    # G1 landed: main holds .project.toml, and the same branch fails on mission.md
    repo.git("update-ref", "refs/heads/main", "HEAD")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  specs/mission.md:{mission}: open question" in result.stdout


def test_i_agents_md_naming_a_missing_task_fails(repo: Repo) -> None:
    repo.append("AGENTS.md", "Deploy with `mise run nope`.\n")
    repo.pytest()  # AGENTS.md is outside specs/: the old results are stale
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  I15: AGENTS.md:" in result.stdout
    assert "`mise run nope`, which is not a mise task" in result.stdout


def test_j_mission_changed_on_a_feature_branch_fails(feat: Repo) -> None:
    feat.edit("specs/mission.md", "receipts, a GUI.", "receipts, a GUI, a web page.")
    feat.commit("docs: widen the scope")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  I1: specs/mission.md changed on {FEAT}" in result.stdout


def test_j_mission_changed_on_a_plan_branch_passes(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "plan/2026-09-24-pivot")
    repo.edit("specs/mission.md", "receipts, a GUI.", "receipts, a GUI, a web page.")
    repo.commit("spec: widen the scope")
    result = repo.check()
    assert result.returncode == 0, output(result)


# ---------------------------------------------------------------- more check rules


def test_strict_mode_refuses_pending_scenarios(feat: Repo) -> None:
    result = feat.check("--strict")
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.negative-amount: no linked test" in result.stdout
    assert "pend " not in result.stdout


def test_partial_results_are_refused(repo: Repo) -> None:
    assert repo.pytest("--spec", "cli.tip-default").returncode == 0
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "test results are partial (--spec, 5 deselected)" in result.stdout


def test_missing_results_are_refused(repo: Repo) -> None:
    (repo.path / ".cache" / "spec-results.json").unlink()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "no test results (.cache/spec-results.json): run `mise run test`" in result.stdout


def test_collection_error_fails(repo: Repo) -> None:
    repo.write(
        "tests/test_parse.py",
        "import pytest\n\nfrom tipcalc import parse_amount\n\n\n"
        '@pytest.mark.spec("cli.bad-amount")\ndef test_parse() -> None:\n'
        '    assert parse_amount("abc") is None\n',
    )
    assert repo.pytest().returncode == 2  # interrupted: nothing ran
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  collection error in tests/test_parse.py: ModuleNotFoundError" in result.stdout
    assert "test results are partial (interrupted)" in result.stdout
    repo.pytest("--continue-on-collection-errors")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  collection error in tests/test_parse.py: ModuleNotFoundError" in result.stdout
    assert "partial" not in result.stdout


def test_scenario_grammar_problems_fail(repo: Repo) -> None:
    repo.edit(
        "specs/capabilities/cli.md",
        "The CLI SHALL never end with a Python traceback.",
        "The CLI SHALL never crash. It SHALL exit 2.",
    )
    repo.edit(
        "specs/capabilities/cli.md",
        "- THEN stdout is `tip: 15.0`",
        "- AND stdout is `tip: 15.0`",
    )
    repo.append("specs/capabilities/cli.md", "\n### Scenario: cli.Bad_ID\n- WHEN x\n- THEN y\n")
    repo.append("specs/capabilities/config.md", "\nSome design prose.\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    out = result.stdout
    assert "needs exactly one SHALL sentence (found 2)" in out
    assert "scenario cli.tip-default needs WHEN and THEN bullets" in out
    assert "scenario id 'cli.Bad_ID' must match <cap>.<slug> in lowercase" in out
    assert "config.md:" in out
    assert "lines are '- GIVEN/WHEN/THEN/AND ...' bullets" in out


def test_gap_whose_roadmap_item_is_ticked_only_warns(repo: Repo) -> None:
    repo.edit("specs/roadmap.md", "- [ ] entrypoint-hardening:", "- [x] entrypoint-hardening:")
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "warn  cli.no-args: gap slug 'entrypoint-hardening' is ticked done" in result.stdout


def test_duplicate_scenario_id_fails(repo: Repo) -> None:
    repo.append(
        "specs/capabilities/cli.md",
        "\n### Scenario: cli.tip-default\n- WHEN the user runs `tipcalc 1`\n- THEN it prints\n",
    )
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "cli.tip-default: duplicate id (specs/capabilities/cli.md:" in result.stdout


def test_plan_group_naming_an_unknown_id_fails(feat: Repo) -> None:
    feat.edit(f"{CHANGE}/plan.md", "cli.negative-amount |", "cli.negative-amount cli.nope |")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  {CHANGE}/plan.md: G1 names unknown id cli.nope" in result.stdout


def test_check_change_lints_one_change_as_approve_would(feat: Repo) -> None:
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)
    assert "change 2026-09-24-entrypoint-hardening: ok" in result.stdout
    feat.edit(f"{CHANGE}/plan.md", "Files: src/tipcalc/config.py (NEW)", "Files: {FILES}")
    feat.append(f"{CHANGE}/validation.md", "- [NEEDS CLARIFICATION: who reviews?]\n")
    result = feat.check("--change", "2026-09-24-entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert "unfilled placeholder {FILES}" in result.stdout
    assert "must be answered" in result.stdout


def test_done_change_folder_is_frozen(feat: Repo) -> None:
    feat.edit(f"{CHANGE}/requirements.md", "status: draft ", "status: done ")
    feat.commit("chore(entrypoint-hardening): close")
    feat.git("switch", "-q", "main")
    feat.git("merge", "-q", "--ff-only", FEAT)
    feat.git("switch", "-q", "-c", "fix/typo")
    feat.edit(f"{CHANGE}/requirements.md", "all end in a traceback", "all end in tracebacks")
    feat.commit("docs: typo")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  I5: {CHANGE} is done and frozen" in result.stdout


TICK = ("- [ ] entrypoint-hardening:", "- [x] entrypoint-hardening:")
CLOSE_MESSAGE = f"chore(entrypoint-hardening): close\n\n{TOOL_TRAILER}"


# What `git cliff --with-commit "<title>" -o CHANGELOG.md` adds to the fixture's CHANGELOG.md for
# the change title "fix(cli): clear errors instead of tracebacks" (git-cliff 2.14.1 and the
# [tool.git-cliff] config in fixtures/tipcalc/pyproject.toml, run by hand).
CLOSE_ENTRY = "\n## [Unreleased]\n\n### Fixed\n\n- clear errors instead of tracebacks (cli)\n"


def close(feat: Repo, changelog: str = CLOSE_ENTRY) -> None:
    """What merge's close commit holds (design 5.7 step 7), committed with its trailer."""
    feat.edit(f"{CHANGE}/requirements.md", "status: approved ", "status: done ")
    feat.edit("specs/roadmap.md", *TICK)
    feat.append("CHANGELOG.md", changelog)
    feat.commit(CLOSE_MESSAGE)


def test_roadmap_on_a_feature_branch_is_written_only_by_the_tool(feat: Repo) -> None:
    feat.edit("specs/roadmap.md", *TICK)
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  I1: specs/roadmap.md is edited on {FEAT}" in result.stdout
    feat.commit("chore: tick the roadmap")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"changes specs/roadmap.md on {FEAT}; only merge writes it" in result.stdout


def test_a_hand_written_merge_trailer_excuses_nothing(feat: Repo) -> None:
    feat.edit("specs/roadmap.md", *TICK)
    feat.commit(f"chore: tick\n\n{TOOL_TRAILER}")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert (
        "carries 'Merged-By: mise run merge', but it is not merge's close commit: it does not "
        f"move {CHANGE} from approved to done" in result.stdout
    )


def test_merge_close_commit_passes(feat: Repo) -> None:
    approve(feat)
    feat.commit("spec(entrypoint-hardening): approve")
    close(feat)
    feat.pytest()
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert "I1" not in result.stdout
    assert "I2" not in result.stdout


@pytest.mark.parametrize(
    ("extra", "problem"),
    [
        (
            "after",
            "commits follow it, and merge's close commit is the last one on the branch",
        ),
        ("src", "it also changes src/tipcalc/__init__.py"),
        (
            "other-item",
            "it changes specs/roadmap.md beyond the item 'entrypoint-hardening'",
        ),
    ],
)
def test_a_close_commit_does_only_what_merge_does(feat: Repo, extra: str, problem: str) -> None:
    approve(feat)
    feat.commit("spec(entrypoint-hardening): approve")
    if extra == "src":
        feat.append("src/tipcalc/__init__.py", "# closing note\n")
    if extra == "other-item":
        feat.edit("specs/roadmap.md", "- [ ] percent-flag:", "- [x] percent-flag:")
    close(feat)
    if extra == "after":
        feat.append("README.md", "\nA note.\n")
        feat.commit("docs: note")
    feat.pytest()
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"but it is not merge's close commit: {problem}" in result.stdout


def test_changelog_on_a_feature_branch_fails(feat: Repo) -> None:
    feat.write("CHANGELOG.md", "# Changelog\n")
    feat.commit("docs: changelog by hand")
    feat.pytest()
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  I2: commit" in result.stdout
    assert f"changes CHANGELOG.md on {FEAT}; only merge writes it" in result.stdout


def test_feat_branch_without_a_change_folder_fails(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "feat/split-bill")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  feat/split-bill: the feat lane needs specs/changes/<date>-split-bill/" in (
        result.stdout
    )


def test_fast_lane_branch_may_pend_without_a_folder(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "chg/negative-amount")
    repo.append("specs/capabilities/cli.md", NEW_SCENARIO)
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "pend  cli.negative-amount: no linked test (added on chg/negative-amount)" in (
        result.stdout
    )


def test_check_is_deterministic(feat: Repo) -> None:
    first, second = feat.check(), feat.check()
    assert first.stdout == second.stdout
    assert first.returncode == second.returncode == 0


def test_scenario_changes_on_chore_and_refactor_branches_fail(repo: Repo) -> None:
    repo.git("switch", "-q", "-c", "chore/tidy")
    repo.edit("specs/capabilities/cli.md", "and the exit code is 0\n", "and the exit is 0\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.tip-default: scenario modified on chore/tidy; chore/ never changes" in (
        result.stdout
    )
    repo.git("switch", "-q", "-c", "refactor/split")
    repo.append("specs/capabilities/cli.md", NEW_SCENARIO)
    result = repo.check()
    assert "FAIL  cli.negative-amount: scenario added on refactor/split" in result.stdout
    assert "FAIL  cli.negative-amount: no linked test" in result.stdout  # never pending here
    assert "pend " not in result.stdout
    assert "specs/capabilities/cli.md: changed" not in result.stdout  # the ids say it already


REWORD = ("SHALL never end with a Python traceback", "SHALL end with a Python traceback")


@pytest.mark.parametrize("lane", ["chore", "refactor"])
def test_any_capability_edit_on_chore_and_refactor_branches_fails(repo: Repo, lane: str) -> None:
    """Table 0.3: capabilities are never touched on these lanes. Turning a requirement's SHALL
    sentence around changes no scenario block, and still fails, uncommitted or committed."""
    branch = f"{lane}/copy"
    repo.git("switch", "-q", "-c", branch)
    repo.edit("specs/capabilities/cli.md", *REWORD)
    uncommitted = repo.check()
    repo.commit(f"{lane}: reword")
    committed = repo.check()
    line = f"FAIL  specs/capabilities/cli.md: changed on {branch}; {lane}/ never changes"
    for result in (uncommitted, committed):
        assert result.returncode == 1, output(result)
        assert line in result.stdout
        assert "scenario modified" not in result.stdout


def test_a_capability_edit_on_a_spec_lane_is_not_a_lane_problem(repo: Repo) -> None:
    """fix/ may correct a spec that was wrong (table 0.3), so the same edit passes there."""
    repo.git("switch", "-q", "-c", "fix/copy")
    repo.edit("specs/capabilities/cli.md", *REWORD)
    repo.commit("fix: reword")
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "never changes capabilities" not in result.stdout


def test_github_variables_count_only_in_ci(repo: Repo) -> None:
    """GITHUB_BASE_REF set by hand, outside CI, cannot move the base under the branch and empty
    its diff; in CI a branch is never its own base either."""
    repo.git("switch", "-q", "-c", "chore/x")
    repo.append("specs/mission.md", "More.\n")
    repo.commit("chore: widen the mission")
    for env in (
        {},
        {"GITHUB_BASE_REF": "chore/x"},
        {"GITHUB_ACTIONS": "true", "GITHUB_BASE_REF": "chore/x"},
        {"GITHUB_ACTIONS": "true", "GITHUB_BASE_REF": "main"},
    ):
        result = repo.check(env=env)
        assert result.returncode == 1, (env, output(result))
        assert "FAIL  I1: specs/mission.md changed on chore/x" in result.stdout, env


# ---------------------------------------------------------------- M2 round 1: fail-open holes

SHALL_LINE = "The CLI SHALL print the tip for the bill given as the first argument.\n"
TIP_THEN = "- THEN stdout is `tip: 15.0` and the exit code is 0\n"
HIDDEN = "- WHEN the user runs `tipcalc 100 extra`\n- THEN the exit code is 2\n"


@pytest.mark.parametrize(
    ("anchor", "heading"),
    [
        (SHALL_LINE, "\n ### Scenario: cli.hidden\n"),  # right under a SHALL line
        (SHALL_LINE, "\n   ### Scenario: cli.hidden\n"),
        (SHALL_LINE, "\t### Scenario: cli.hidden\n"),
        (TIP_THEN, "  ### Scenario: cli.hidden\n"),  # nested under a THEN bullet
    ],
    ids=["1-space", "3-spaces", "tab", "in-a-bullet"],
)
def test_an_indented_scenario_heading_is_still_read_and_fails(
    repo: Repo, anchor: str, heading: str
) -> None:
    repo.edit("specs/capabilities/cli.md", anchor, anchor + heading + HIDDEN)
    repo.commit("spec: hidden")
    result = repo.check("--strict")
    assert result.returncode == 1, output(result)
    assert "heading '### Scenario: cli.hidden' is indented; headings start at column 1" in (
        result.stdout
    )
    assert "FAIL  cli.hidden: no linked test" in result.stdout


@pytest.mark.parametrize(
    "rel", ["specs/capabilities/billing/split.md", "specs/capabilities/split.markdown"]
)
def test_a_capability_file_out_of_place_fails(repo: Repo, rel: str) -> None:
    repo.write(
        rel,
        "# Capability: split\n\n## Requirement: Split\nThe CLI SHALL split the bill.\n\n"
        "### Scenario: split.two-people\n- WHEN the user runs `tipcalc 100 --split 2`\n"
        "- THEN stdout is `each: 57.5`\n",
    )
    repo.commit("spec: split")
    result = repo.check("--strict")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {rel}: capabilities are specs/capabilities/<cap>.md; this file is never read"
        in result.stdout
    )


def test_doc_commands_leave_sentence_punctuation_out(repo: Repo) -> None:
    repo.append(
        "README.md",
        "\nBefore pushing, mise run verify. Then mise run status, and mise run spec-check: done.\n",
    )
    repo.pytest()
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "I15" not in result.stdout
    repo.append("README.md", "Or mise run nope.\n")
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "names `mise run nope`, which is not a mise task" in result.stdout


FAILING_EXTRA = (
    "import pytest\nfrom helpers import tipcalc\n\n\n"
    '@pytest.mark.spec("cli.tip-default")\ndef test_again() -> None:\n'
    '    assert tipcalc("100").stdout == "tip: 99\\n"\n'
)


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (("--ignore=tests/test_extra.py",), "--ignore"),
        (("--ignore-glob=*extra*",), "--ignore-glob"),
        (
            ("tests/test_cli.py", "tests/test_config.py"),
            "selected tests/test_cli.py tests/test_config.py",
        ),
        (
            ("tests/test_cli.py::test_tip_default",),
            "selected tests/test_cli.py::test_tip_default",
        ),
        (
            ("tests",),
            "selected tests",
        ),  # no testpaths configured: the suite is the rootdir
    ],
    ids=["ignore", "ignore-glob", "files", "node", "folder"],
)
def test_a_run_that_leaves_tests_out_is_partial(
    repo: Repo, args: tuple[str, ...], reason: str
) -> None:
    repo.write("tests/test_extra.py", FAILING_EXTRA)
    assert repo.pytest().returncode == 1
    assert repo.check().returncode == 1  # the full run sees the failing linked test
    repo.pytest(*args)
    data = repo.results()
    assert data["complete"] is False
    partial = data["partial"]
    assert isinstance(partial, list)
    assert reason in partial
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  test results are partial ({reason}" in result.stdout


def test_a_run_from_a_subfolder_is_partial(repo: Repo) -> None:
    Repo(repo.path / "tests").pytest()
    assert repo.results()["partial"] == ["selected tests"]


def test_runs_that_cover_the_suite_are_complete(repo: Repo) -> None:
    for args in ((), (".",), ("tests", ".")):
        repo.pytest(*args)
        assert repo.results()["complete"] is True, args
    repo.edit(
        "pyproject.toml",
        'markers = ["spec',
        'testpaths = ["tests"]\nmarkers = ["spec',
    )
    for args in ((), ("tests",)):
        repo.pytest(*args)
        assert repo.results()["complete"] is True, args
    Repo(repo.path / "tests").pytest()
    assert repo.results()["complete"] is True  # from inside the only testpath


def test_a_gap_reason_must_name_the_exact_id(repo: Repo) -> None:
    repo.edit(
        "tests/test_cli.py",
        'reason="cli.help: traceback',
        'reason="cli.help-page: traceback',
    )
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert (
        "FAIL  cli.help: tests/test_cli.py::test_help: a gap test needs "
        '@pytest.mark.xfail(strict=True, reason="cli.help: ...")' in result.stdout
    )


def test_open_question_in_a_capability_after_approval_fails(feat: Repo) -> None:
    # Lower case and two spaces still count as the marker.
    feat.edit(
        "specs/capabilities/cli.md",
        SHALL_LINE,
        SHALL_LINE + "[needs  clarification: x]\n",
    )
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert "warn  specs/capabilities/cli.md:" in result.stdout
    approve(feat)
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  specs/capabilities/cli.md:" in result.stdout
    assert "must be answered" in result.stdout


# ---------------------------------------------------------------- M2 round 2: fail-open holes

USAGE_FIX = (
    "    bill = float(sys.argv[1])\n",
    (
        "    if len(sys.argv) < 2:\n"
        '        print("usage: tipcalc BILL", file=sys.stderr)\n'
        "        raise SystemExit(2)\n"
        "    bill = float(sys.argv[1])\n"
    ),
)
NO_ARGS_XFAIL = '@pytest.mark.xfail(strict=True, reason="cli.no-args'
BROKEN_FIXTURE = (
    "from helpers import tipcalc\n",
    (
        "from helpers import tipcalc\n\n\n"
        "@pytest.fixture\ndef broken() -> None:\n    raise RuntimeError('setup')\n"
    ),
)


@pytest.mark.parametrize(
    ("edits", "problem"),
    [
        (
            [
                (
                    NO_ARGS_XFAIL,
                    '@pytest.mark.xfail(strict=True, run=False, reason="cli.no-args',
                )
            ],
            "xfail(run=False) never runs the test, so fixing the gap never turns it red",
        ),
        (
            [
                BROKEN_FIXTURE,
                (
                    "def test_no_args() -> None:",
                    "def test_no_args(broken: None) -> None:",
                ),
            ],
            "xfailed before its body ran (a fixture or setup failed)",
        ),
        (
            [
                (
                    "    r = tipcalc()\n",
                    '    pytest.xfail("cli.no-args: crashes")\n    r = tipcalc()\n',
                )
            ],
            "xfails by calling pytest.xfail()",
        ),
        (
            [
                (
                    "    r = tipcalc()\n",
                    '    pytest.fail("cli.no-args: crashes")\n    r = tipcalc()\n',
                )
            ],
            "xfails by calling pytest.fail()",
        ),
        (
            [
                (
                    '    assert "Traceback" not in r.stderr\n',
                    '    assert "Traceback" not in r.stdrr\n',
                )
            ],
            "its body raised AttributeError, not an AssertionError",
        ),
        (
            [
                (
                    "    r = tipcalc()\n",
                    '    r = tipcalc()\n    raise RuntimeError("boom")\n',
                )
            ],
            "its body raised RuntimeError, not an AssertionError",
        ),
        (
            [
                (
                    "    r = tipcalc()\n",
                    '    r = tipcalc()\n    raise RuntimeError("boom")\n',
                ),
                (
                    'strict=True, reason="cli.no-args',
                    'strict=True, raises=Exception, reason="cli.no-args',
                ),
            ],
            "its body raised RuntimeError, not an AssertionError",
        ),
    ],
    ids=[
        "run-false",
        "failing-fixture",
        "imperative-xfail",
        "imperative-fail",
        "typo",
        "unrelated-error",
        "broad-raises",
    ],
)
def test_a_gap_test_that_never_fails_on_the_gap_fails(
    repo: Repo, edits: list[tuple[str, str]], problem: str
) -> None:
    for old, new in edits:
        repo.edit("tests/test_cli.py", old, new)
    assert repo.pytest().returncode == 0  # pytest reports xfailed
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  cli.no-args: tests/test_cli.py::test_no_args: {problem}" in result.stdout
    repo.edit("src/tipcalc/__init__.py", *USAGE_FIX)  # the gap is fixed: still red
    assert repo.pytest().returncode == 0  # and pytest still reports xfailed
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  cli.no-args: tests/test_cli.py::test_no_args: {problem}" in result.stdout


IN_PROCESS_NO_ARGS = """

@pytest.mark.spec("cli.no-args")
@pytest.mark.xfail(strict=True, raises=IndexError, reason="cli.no-args: IndexError today")
def test_no_args_in_process(monkeypatch: pytest.MonkeyPatch) -> None:
    import tipcalc

    monkeypatch.setattr("sys.argv", ["tipcalc"])
    with pytest.raises(SystemExit):
        tipcalc.main()
"""


def test_a_gap_test_may_xfail_on_the_crash_its_raises_names(repo: Repo) -> None:
    repo.append("tests/test_cli.py", IN_PROCESS_NO_ARGS)
    repo.edit(
        "pyproject.toml",
        'addopts = "-q --strict-markers -p no:cacheprovider"',
        'addopts = "-q --strict-markers -p no:cacheprovider"\npythonpath = ["src"]',
    )
    assert repo.pytest().returncode == 0
    nodes = repo.results()["nodes"]
    assert isinstance(nodes, dict)
    node = nodes["tests/test_cli.py::test_no_args_in_process"]
    assert node["body"] == "IndexError"
    assert node["xfail"]["raises"] == ["IndexError"]
    result = repo.check()
    assert result.returncode == 0, output(result)
    repo.edit("src/tipcalc/__init__.py", *USAGE_FIX)  # the gap is fixed: strict XPASS, red
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.no-args: tests/test_cli.py::test_no_args_in_process passes now" in (
        result.stdout
    )


@pytest.mark.parametrize(
    ("body", "raises", "hits"),
    [
        ("AssertionError", [], True),
        ("DID NOT RAISE", [], True),
        ("IndexError", ["IndexError"], True),
        ("KeyError", ["IndexError", "KeyError"], True),
        ("AttributeError", [], False),
        ("NotImplementedError", [], False),
        ("RuntimeError", ["Exception"], False),
        ("RuntimeError", ["RuntimeError", "BaseException"], False),
    ],
)
def test_which_gap_bodies_hit_the_gap(body: str, raises: list[str], hits: bool) -> None:
    project = load_project_module()
    node = project.Node(
        node="t",
        ids=["cli.a"],
        outcome="xfailed",
        xfail_strict=True,
        xfail_reason="cli.a: gap",
        xfail_run=True,
        xfail_raises=raises,
        skip=False,
        crash="",
        body=body,
    )
    assert project.gap_body_hits_gap(node) is hits


def test_a_file_that_is_not_utf8_fails_and_is_still_checked(repo: Repo) -> None:
    # (h) on main: an open question in mission.md, next to a Latin-1 byte.
    path = repo.path / "specs" / "mission.md"
    path.write_bytes(path.read_bytes() + b"\n[NEEDS CLARIFICATION: caf\xe9?]\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  specs/mission.md: not UTF-8 (byte 0xe9 on line" in result.stdout
    assert "must be answered" in result.stdout
    # (i): AGENTS.md naming a task that does not exist, next to a Latin-1 byte.
    path = repo.path / "AGENTS.md"
    path.write_bytes(path.read_bytes() + b"\nRun `mise run nope` (caf\xe9).\n")
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  AGENTS.md: not UTF-8 (byte 0xe9 on line" in result.stdout
    assert "names `mise run nope`, which is not a mise task" in result.stdout


def test_a_change_file_that_is_not_utf8_fails_and_is_still_checked(feat: Repo) -> None:
    # (f) and (h) in an approved change, then a requirements.md of random bytes.
    approve(feat)
    folder = feat.path / CHANGE
    path = folder / "validation.md"
    path.write_bytes(path.read_bytes().replace(b"-> cli.no-args", b"-> cli.nope \xff"))
    path = folder / "requirements.md"
    path.write_bytes(path.read_bytes() + b"\n[NEEDS CLARIFICATION: caf\xe9?]\n")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  {CHANGE}/validation.md: not UTF-8 (byte 0xff on line" in result.stdout
    assert "names unknown id cli.nope" in result.stdout
    assert f"FAIL  {CHANGE}/requirements.md: not UTF-8 (byte 0xe9 on line" in result.stdout
    assert f"FAIL  {CHANGE}/requirements.md:" in result.stdout
    assert "must be answered" in result.stdout
    path.write_bytes(bytes(range(128, 256)) * 2)
    for args in ((), ("--change", "entrypoint-hardening")):
        result = feat.check(*args)
        assert result.returncode == 1, output(result)
        assert f"FAIL  {CHANGE}/requirements.md: not UTF-8 (byte 0x80 on line 1)" in result.stdout


def test_a_mise_config_that_is_not_utf8_fails_without_a_traceback(repo: Repo) -> None:
    path = repo.path / "mise.toml"
    path.write_bytes(path.read_bytes() + b"\n# caf\xe9\n")
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  I15: cannot read the mise tasks: mise.toml:" in result.stdout
    assert "Traceback" not in output(result)


ITEM = "- [ ] entrypoint-hardening: clear errors instead of tracebacks"


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        (f"<!--\n{ITEM}\n-->", False),
        (f"  <!-- parked\n{ITEM}\n  -->", False),
        (f"<!-- {ITEM} -->", False),
        (f"{ITEM} <!-- note -->", True),
        # A `<!--` that does not close on its own line mid-paragraph hides no list item:
        # markdown shows the item, so it counts.
        (f"Parked: <!-- moved\n{ITEM} -->", True),
    ],
    ids=["block", "indented-block", "one-line", "trailing-note", "opened-mid-line"],
)
def test_a_gap_slug_hidden_in_a_comment_is_not_on_the_roadmap(
    repo: Repo, text: str, shown: bool
) -> None:
    repo.edit("specs/roadmap.md", ITEM, text)
    result = repo.check()
    missing = "gap slug 'entrypoint-hardening' is not in specs/roadmap.md"
    assert result.returncode == (0 if shown else 1), output(result)
    assert (missing in result.stdout) is not shown


def test_review_focus_rows_in_a_comment_do_not_count(feat: Repo) -> None:
    rows = "- no args -> cli.no-args\n"
    feat.edit(f"{CHANGE}/validation.md", rows, f"<!--\n{rows}- typo -> cli.nope\n-->\n")
    result = feat.check()
    assert result.returncode == 0, output(result)  # the hidden row with a bad id is not read
    assert "cli.nope" not in result.stdout
    feat.git("checkout", "--", f"{CHANGE}/validation.md")
    text = feat.read(f"{CHANGE}/validation.md")
    start = text.index("## Review focus")
    end = text.index("## Run it")
    heading, _, focus = text[start:end].partition("\n")
    feat.write(
        f"{CHANGE}/validation.md",
        text[:start] + f"{heading}\n<!--\n{focus}-->\n" + text[end:],
    )
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "I13: Review focus is empty" in result.stdout


def test_an_open_question_parked_in_a_comment_still_counts(feat: Repo) -> None:
    approve(feat)
    feat.append(f"{CHANGE}/requirements.md", "<!-- [NEEDS CLARIFICATION: later?] -->\n")
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "must be answered" in result.stdout


def test_prose_lines_cut_html_comments_as_markdown_does() -> None:
    prose_lines = load_project_module().prose_lines
    text = (
        "a <!-- x --> b\n"  # 1
        "<!--\n"  # 2
        "hidden\n"  # 3
        "--> c\n"  # 4
        "d <!--> e\n"  # 5: <!--> is a whole (empty) comment
        "`<!--` f\n"  # 6: a code span, not a comment
        "```\n"  # 7
        "<!-- code, not a comment\n"  # 8
        "```\n"  # 9
        "g\n"  # 10
        "<!-- ```\n"  # 11: a fence inside a comment is hidden
        "h -->\n"  # 12
        "i\n"  # 13
        "j <!-- stays literal\n"  # 14: opened mid-line and not closed on it
        "k\n"  # 15
    )
    assert prose_lines(text) == [
        (1, "a  b"),
        (2, ""),
        (4, " c"),
        (5, "d  e"),
        (6, "`` f"),
        (10, "g"),
        (11, ""),
        (12, ""),
        (13, "i"),
        (14, "j <!-- stays literal"),
        (15, "k"),
    ]
    kept = dict(prose_lines(text, hide_comments=False))
    assert kept[3] == "hidden"


@pytest.mark.parametrize(
    ("setup", "changelog", "problem"),
    [
        (
            "chg/tweak",
            "# Changelog\n\n- totally real entry\n",
            "it removes or rewrites lines of CHANGELOG.md; merge only adds its entry",
        ),
        (
            "chg/tweak",
            "+\n## [Unreleased]\n\n### Added\n\n- tweak\n",
            "its entry '- tweak' is not under '### Changed' or '### Removed'",
        ),
        (
            "chg/tweak",
            "+\n## [Unreleased]\n\n### Changed\n\n- tweak\n- and more\n",
            "it adds 2 entries to CHANGELOG.md; merge adds exactly one",
        ),
        (
            "chg/tweak",
            "+\n## [0.2.0] - 2026-09-24\n\n### Changed\n\n- tweak\n",
            "its entry '- tweak' is not under '## [Unreleased]'",
        ),
        (
            "chg/tweak",
            "+\n## [Unreleased]\n\n### Changed\n\nSee the docs.\n- tweak\n",
            "it adds 'See the docs.' to CHANGELOG.md",
        ),
        (
            "chore/copy",
            "+\n## [Unreleased]\n\n### Changed\n\n- copy\n",
            "merge writes no CHANGELOG.md line for the chore/ lane",
        ),
        (
            "plan/2026-09-24-replan",
            "+\n## [Unreleased]\n\n### Changed\n\n- replan\n",
            "merge writes no CHANGELOG.md line for the plan/ lane",
        ),
        (
            "refactor/speed",
            "+\n## [Unreleased]\n\n### Fixed\n\n- speed\n",
            "its entry '- speed' is not under '### Performance'",
        ),
        ("chg/tweak", "+\n## [Unreleased]\n\n### Changed\n\n- tweak\n", None),
        ("fix/typo", "+\n## [Unreleased]\n\n### Fixed\n\n- typo (cli)\n", None),
        ("refactor/speed", "+\n## [Unreleased]\n\n### Performance\n\n- speed\n", None),
    ],
    ids=[
        "chg-rewrite",
        "chg-wrong-group",
        "chg-two-entries",
        "chg-released-section",
        "chg-extra-text",
        "chore-no-line",
        "plan-no-line",
        "refactor-not-perf",
        "chg-ok",
        "fix-ok",
        "refactor-perf-ok",
    ],
)
def test_a_close_commit_on_a_fast_lane_adds_only_merges_changelog_line(
    repo: Repo, setup: str, changelog: str, problem: str | None
) -> None:
    repo.git("switch", "-q", "-c", setup)
    if changelog.startswith("+"):
        repo.append("CHANGELOG.md", changelog[1:])
    else:
        repo.write("CHANGELOG.md", changelog)
    repo.commit(f"docs: changelog\n\n{TOOL_TRAILER}")
    repo.pytest()
    result = repo.check()
    if problem is None:
        assert result.returncode == 0, output(result)
        return
    assert result.returncode == 1, output(result)
    assert f"but it is not merge's close commit: {problem}" in result.stdout


def test_a_feat_close_commit_ticks_the_roadmap(feat: Repo) -> None:
    approve(feat)
    feat.commit("spec(entrypoint-hardening): approve")
    feat.edit(f"{CHANGE}/requirements.md", "status: approved ", "status: done ")
    feat.append("CHANGELOG.md", CLOSE_ENTRY)
    feat.commit(CLOSE_MESSAGE)
    feat.pytest()
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert (
        "but it is not merge's close commit: it leaves specs/roadmap.md alone; merge ticks "
        "'entrypoint-hardening' (or adds it, unplanned)" in result.stdout
    )


def test_a_close_commit_may_create_the_changelog_from_the_configured_header(
    repo: Repo,
) -> None:
    header = repo.read("CHANGELOG.md")
    repo.git("rm", "-q", "CHANGELOG.md")
    repo.commit("chore: drop the changelog")
    repo.git("switch", "-q", "-c", "fix/typo")
    repo.write("CHANGELOG.md", header + "\n## [Unreleased]\n\n### Fixed\n\n- typo\n")
    repo.commit(f"docs: changelog\n\n{TOOL_TRAILER}")
    repo.pytest()
    result = repo.check()
    assert result.returncode == 0, output(result)
    repo.git("reset", "-q", "--soft", "HEAD~1")
    repo.write("CHANGELOG.md", "# Changes\n\n## [Unreleased]\n\n### Fixed\n\n- typo\n")
    repo.commit(f"docs: changelog\n\n{TOOL_TRAILER}")
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "it removes or rewrites lines of CHANGELOG.md" in result.stdout


@pytest.mark.parametrize(
    ("edit", "changelog", "problem"),
    [
        (
            None,
            "\n## [Unreleased]\n\n### Fixed\n\n- clear errors (cli)\n",
            (
                "its entry is '- clear errors (cli)', and merge writes "
                "'- clear errors instead of tracebacks (cli)' for the change title"
            ),
        ),
        (
            None,
            "\n## [Unreleased]\n\n### Added\n\n- clear errors instead of tracebacks (cli)\n",
            "its entry '- clear errors instead of tracebacks (cli)' is not under '### Fixed'",
        ),
        (
            None,
            "",
            (
                "it adds no CHANGELOG.md line; merge adds "
                "'- clear errors instead of tracebacks (cli)' under '### Fixed'"
            ),
        ),
        (
            ("All notable changes", "Every change"),
            CLOSE_ENTRY,
            "it removes or rewrites lines of CHANGELOG.md",
        ),
        (
            ('title: "fix(cli):', 'title: "docs(cli):'),
            CLOSE_ENTRY,
            "merge writes no CHANGELOG.md line for the title 'docs(cli): clear errors",
        ),
    ],
    ids=["other-text", "other-group", "no-line", "rewrite", "title-without-a-line"],
)
def test_a_feat_close_commit_adds_the_line_for_its_title(
    feat: Repo, edit: tuple[str, str] | None, changelog: str, problem: str
) -> None:
    if edit is not None and edit[0].startswith("title"):
        feat.edit(f"{CHANGE}/requirements.md", *edit)
    approve(feat)
    feat.commit("spec(entrypoint-hardening): approve")
    if edit is not None and not edit[0].startswith("title"):
        feat.edit("CHANGELOG.md", *edit)
    close(feat, changelog)
    feat.pytest()
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert f"but it is not merge's close commit: {problem}" in result.stdout


def test_stale_results_are_refused(repo: Repo) -> None:
    text = repo.read("tests/test_cli.py")
    start = text.index('@pytest.mark.spec("cli.tip-default")')
    end = text.index('@pytest.mark.spec("cli.no-args")')
    repo.write("tests/test_cli.py", text[:start] + text[end:])
    repo.append("src/tipcalc/__init__.py", 'raise SystemExit("broken")\n')
    repo.commit("refactor: break it")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert (
        "FAIL  test results are stale (src/tipcalc/__init__.py, tests/test_cli.py changed since "
        "the run): run `mise run test`" in result.stdout
    )
    assert "proven" not in result.stdout  # nothing is judged on stale results
    assert "(results " in repo.project("status").stdout
    assert ", stale)" in repo.project("status").stdout
    repo.pytest()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "stale" not in result.stdout
    assert "FAIL  cli.tip-default: no linked test" in result.stdout


def test_a_new_untracked_file_makes_results_stale(repo: Repo) -> None:
    repo.write("tests/test_more.py", "def test_more() -> None:\n    assert False\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "test results are stale (tests/test_more.py changed since the run)" in result.stdout


def test_edits_under_specs_leave_results_current(repo: Repo) -> None:
    repo.append("specs/mission.md", "\nOne more line.\n")
    repo.write("specs/backlog/2026-09-25-rounding.md", "---\nstatus: open\n---\nRounding.\n")
    result = repo.check()
    assert result.returncode == 0, output(result)


STALE_SRC = "test results are stale (src/tipcalc/__init__.py changed since the run)"


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_an_index_flag_cannot_hide_an_edit_after_the_run(repo: Repo, flag: str) -> None:
    """git never compares a file marked assume-unchanged or skip-worktree with the disk, so
    `git ls-files -m` hides its edits; the stale guard hashes such a file itself."""
    repo.git("update-index", flag, "src/tipcalc/__init__.py")
    result = repo.check()
    assert result.returncode == 0, output(result)  # the flag alone changes no file
    repo.append("src/tipcalc/__init__.py", "raise SystemExit(3)\n")
    assert repo.git("ls-files", "-m") == ""  # git itself looks away
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  {STALE_SRC}" in result.stdout
    repo.pytest()  # a run on the edited file stands for it: the map hashes the disk copy
    assert STALE_SRC not in repo.check().stdout


def test_a_loose_stat_setting_cannot_hide_an_edit_after_the_run(repo: Repo) -> None:
    """core.checkStat=minimal and core.trustctime=false leave git only size and whole-second
    mtime: an edit of the same size, with the mtime put back, looks unchanged to it. The stale
    guard runs git with the full stat check (and without fsmonitor or the untracked cache)."""
    path = repo.path / "src/tipcalc/__init__.py"
    old = path.stat().st_mtime_ns - 10**11  # 100 s back: never racy against the index
    os.utime(path, ns=(old, old))
    repo.git("config", "core.checkStat", "minimal")
    repo.git("config", "core.trustctime", "false")
    repo.git("update-index", "-q", "--refresh")
    time.sleep(1.1)  # git compares ctime in whole seconds
    repo.edit("src/tipcalc/__init__.py", '"15"', '"25"')
    os.utime(path, ns=(old, old))
    assert repo.git("ls-files", "-m") == ""  # git itself looks away
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"FAIL  {STALE_SRC}" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("--strict-markers",),
        ("--strict-config",),
        ("-o", "strict_markers=true"),
        ("-o", "xfail_strict=yes"),
    ],
    ids=["strict-markers", "strict-config", "o-strict-markers", "o-xfail-strict"],
)
def test_a_strictness_switch_keeps_the_run_complete(repo: Repo, args: tuple[str, ...]) -> None:
    repo.pytest(*args)
    data = repo.results()
    assert data["complete"] is True, data["partial"]
    result = repo.check()
    assert result.returncode == 0, output(result)


@pytest.mark.parametrize(
    ("args", "reason"),
    [
        (("-o", "python_files=test_cli.py"), "-o python_files"),
        (("-o", "xfail_strict=false"), "-o xfail_strict"),
        (("-o", "strict_markers=true", "-o", "testpaths=tests/none"), "-o testpaths"),
    ],
    ids=["python-files", "loosened-xfail", "mixed"],
)
def test_other_ini_overrides_make_the_run_partial(
    repo: Repo, args: tuple[str, ...], reason: str
) -> None:
    repo.pytest(*args)
    assert repo.results()["partial"] == [reason]
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert f"test results are partial ({reason})" in result.stdout


def test_the_adoption_branch_passes_strict(tmp_path: Path) -> None:
    """G1: main holds only the old code; plan/project-init adds the specs, tests and gates."""
    repo = build(tmp_path / "tipcalc")
    repo.git("checkout", "-q", "--orphan", "old")  # keeps the work tree
    repo.git("rm", "-q", "-r", "--cached", "--", ".")
    repo.git("add", "--", "src", "pyproject.toml", ".gitignore")
    repo.git("commit", "-q", "-m", "tipcalc as it was")
    repo.git("branch", "-q", "-M", "main")
    repo.git("switch", "-q", "-c", "plan/project-init")
    repo.commit("chore(init): project-init v3")
    assert repo.git("ls-tree", "-r", "--name-only", "main").split() == [
        ".gitignore",
        "pyproject.toml",
        "src/tipcalc/__init__.py",
    ]
    repo.pytest()
    result = repo.check("--strict")
    assert result.returncode == 0, output(result)
    assert "6 scenarios; 1 proven, 5 gaps, 0 pending; 6 added, 0 modified, 0 removed" in (
        result.stdout
    )


@pytest.mark.parametrize(
    ("before", "after", "problem"),
    [
        ("- [ ] a: A\n- [ ] b: B\n", "- [x] a: A\n- [ ] b: B\n", None),
        ("- [ ] b: B\n", "- [x] a: A (unplanned)\n- [ ] b: B\n", None),
        ("- [ ] b: B\n", "- [ ] b: B\n- [x] a: A (unplanned)\n", None),
        ("- [ ] b: B\n", "- [x] a: A\n- [ ] b: B\n", "a new roadmap item is one line"),
        ("- [ ] a: A\n- [ ] b: B\n", "- [x] a: A\n- [x] b: B\n", "beyond the item 'a'"),
        ("- [ ] a: A\n- [ ] b: B\n", "- [ ] b: B\n- [x] a: A\n", "where it stands"),
        ("- [ ] a: A\n", "- [x] a: A, renamed\n", "may only tick the item 'a'"),
        ("- [x] a: A\n", "- [x] a: A\n", "may only tick the item 'a'"),
    ],
    ids=[
        "tick",
        "unplanned",
        "unplanned-last",
        "unmarked",
        "two",
        "moved",
        "renamed",
        "no-op",
    ],
)
def test_roadmap_close_edits(before: str, after: str, problem: str | None) -> None:
    found = load_project_module().roadmap_close_problem(before, after, "a")
    assert (found is None) if problem is None else (problem in (found or "")), found


@pytest.mark.parametrize(
    ("before", "after", "problem"),
    [
        ("- [x] a: A\n- [ ] b: B\n", "- [x] a: A (launched 2026-09-26)\n- [ ] b: B\n", None),
        ("- [x] a: A\n", "- [x] a: A\n", "merge marks the item 'a' launched"),
        (
            "- [x] a: A\n- [ ] b: B\n",
            "- [x] a: A (launched 2026-09-26)\n- [x] b: B\n",
            "beyond the item 'a'",
        ),
        ("- [x] a: A\n", "- [x] a: A, renamed (launched 2026-09-26)\n", "may only append"),
        ("- [x] a: A\n", "- [x] a: A (launched soon)\n", "may only append"),
        ("- [ ] a: A\n", "- [x] a: A (launched 2026-09-26)\n", "'a' is not ticked yet"),
        ("- [ ] b: B\n", "- [ ] b: B\n- [x] a: A (launched 2026-09-26)\n", "has no item 'a'"),
        (
            "- [x] a: A (launched 2026-09-01)\n",
            "- [x] a: A (launched 2026-09-01) (launched 2026-09-26)\n",
            "'a' is launched already",
        ),
    ],
    ids=["mark", "no-op", "two", "renamed", "no-date", "unticked", "missing", "again"],
)
def test_roadmap_launch_edits(before: str, after: str, problem: str | None) -> None:
    found = load_project_module().roadmap_launch_problem(before, after, "a")
    assert (found is None) if problem is None else (problem in (found or "")), found


LAUNCH_ITEM = "- [x] split-bill: split the bill and the tip between people"


@pytest.mark.parametrize(
    ("branch", "also", "problem"),
    [
        ("chore/launch-split-bill", None, None),
        ("chore/split-bill-notes", None, "it also changes specs/roadmap.md"),
        (
            "chore/launch-split-bill",
            ("- [ ] percent-flag:", "- [x] percent-flag:"),
            "it changes specs/roadmap.md beyond the item 'split-bill'",
        ),
    ],
    ids=["launch", "no-launch", "beyond"],
)
def test_a_launch_close_commit_marks_its_roadmap_item(
    repo: Repo, branch: str, also: tuple[str, str] | None, problem: str | None
) -> None:
    """Design D.2: on any lane, the close commit of a launch-<slug> branch appends the launched
    mark to the item <slug>, and changes nothing else in the roadmap. Outside feat/, no other
    branch's close commit touches the roadmap."""
    repo.edit("specs/roadmap.md", "- [ ] split-bill:", "- [x] split-bill:")
    repo.commit(f"feat(cli): split the bill between people\n\n{TOOL_TRAILER}")
    repo.git("switch", "-q", "-c", branch)
    repo.git("commit", "-q", "--allow-empty", "-m", "chore(launch): split-bill")
    repo.edit("specs/roadmap.md", LAUNCH_ITEM, f"{LAUNCH_ITEM} (launched 2026-09-26)")
    if also:
        repo.edit("specs/roadmap.md", *also)
    repo.commit(f"chore({branch.split('/')[1]}): close for merge\n\n{TOOL_TRAILER}")
    repo.pytest()
    result = repo.check()
    if problem is None:
        assert result.returncode == 0, output(result)
        assert "I1" not in result.stdout
    else:
        assert result.returncode == 1, output(result)
        assert f"but it is not merge's close commit: {problem}" in result.stdout


@pytest.fixture(scope="session")
def pytest_majors(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """A python with pytest 8 and one with pytest 9, in venvs uv builds from its cache."""
    uv = shutil.which("uv")
    assert uv is not None  # test_pytest_majors is skipped without uv
    home = tmp_path_factory.mktemp("majors")  # outside any mise.toml: uv may be a mise shim
    pythons: dict[str, str] = {}
    for major, requirement in (("8", "pytest>=8.4,<9"), ("9", "pytest>=9,<10")):
        venv = home / f"pytest{major}"
        for argv in (
            [uv, "venv", "--quiet", "--python", sys.executable, str(venv)],
            [
                uv,
                "pip",
                "install",
                "--quiet",
                "--python",
                str(venv / "bin" / "python"),
                requirement,
            ],
        ):
            done = subprocess.run(argv, cwd=home, capture_output=True, text=True, check=False)
            assert done.returncode == 0, done.stderr
        pythons[major] = str(venv / "bin" / "python")
    return pythons


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
@pytest.mark.parametrize("major", ["8", "9"])
def test_pytest_majors(pytest_majors: dict[str, str], tmp_path: Path, major: str) -> None:
    """The core cases on each pytest major: (d), (d'), (a) and a partial run."""
    python = pytest_majors[major]
    repo = build(tmp_path / "tipcalc")

    def run_tests(*args: str) -> subprocess.CompletedProcess[str]:
        return repo.run(python, "-m", "pytest", *args)

    version = repo.run(python, "-m", "pytest", "--version")
    assert f"pytest {major}." in output(version)
    assert run_tests().returncode == 0
    result = repo.check()
    assert result.returncode == 0, output(result)
    assert "6 scenarios; 1 proven, 5 gaps, 0 pending" in result.stdout
    run_tests("--spec", "cli.no-args")
    assert "test results are partial (--spec, 5 deselected)" in repo.check().stdout
    repo.edit("src/tipcalc/__init__.py", *USAGE_FIX)
    assert run_tests().returncode == 1
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "cli.no-args: tests/test_cli.py::test_no_args passes now (strict XPASS)" in result.stdout
    text = repo.read("tests/test_cli.py")
    start = text.index('@pytest.mark.spec("cli.tip-default")')
    end = text.index('@pytest.mark.spec("cli.no-args")')
    repo.write("tests/test_cli.py", text[:start] + text[end:])
    run_tests()
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "FAIL  cli.tip-default: no linked test" in result.stdout


# ---------------------------------------------------------------- status


def test_status_on_main_names_the_next_roadmap_item(repo: Repo) -> None:
    result = repo.project("status")
    assert result.returncode == 0, output(result)
    assert "[tipcalc] main | no open change" in result.stdout
    assert "proven 1, gaps 5, pending 0, failing 0" in result.stdout
    assert "next roadmap item: entrypoint-hardening" in result.stdout


def test_status_of_a_clean_draft_is_ready_for_approve(feat: Repo) -> None:
    result = feat.project("status")
    assert result.returncode == 0, output(result)
    assert f"[tipcalc] {FEAT} | lane feat | change 2026-09-24-entrypoint-hardening (draft)" in (
        result.stdout
    )
    assert "ready for approve: a human runs `! mise run approve`" in result.stdout


def test_status_of_a_broken_draft_is_not_ready(feat: Repo) -> None:
    feat.edit(f"{CHANGE}/validation.md", "-> cli.no-args", "-> cli.no-arg")
    result = feat.project("status")
    assert "not ready for approve: 1 problem" in result.stdout, output(result)
    assert "unknown id cli.no-arg" in result.stdout


def test_status_of_an_approved_change_names_the_next_group(feat: Repo) -> None:
    approve(feat)
    result = feat.project("status")
    assert result.returncode == 0, output(result)
    assert (
        "next: G1 usage errors: cli.no-args cli.help cli.bad-amount cli.negative-amount"
        in result.stdout
    )


def test_status_change_prints_the_change_and_its_capability_diff(feat: Repo) -> None:
    result = feat.project("status", "--change")
    assert result.returncode == 0, output(result)
    assert f"== {CHANGE}/requirements.md" in result.stdout
    assert f"== {CHANGE}/validation.md" in result.stdout
    assert "+### Scenario: cli.negative-amount" in result.stdout
    assert "-### Scenario: cli.no-args [gap: entrypoint-hardening]" in result.stdout


def test_status_says_when_main_moved(feat: Repo) -> None:
    feat.git("switch", "-q", "main")
    feat.append("README.md", "\nA note.\n")
    feat.commit(f"docs: note\n\n{TOOL_TRAILER}")
    feat.git("switch", "-q", FEAT)
    result = feat.project("status")
    assert "main moved: run git merge main" in result.stdout, output(result)


def test_status_merge_on_main_says_merge_lands_a_lane_branch(repo: Repo) -> None:
    """status --merge and --audit are M5 (tests/test_lifecycle.py); on main the preview stops
    at step 1, and the audit only reports."""
    result = repo.project("status", "--merge")
    assert result.returncode == 1
    assert "on main: merge lands a lane branch" in result.stdout, output(result)
    result = repo.project("status", "--audit")
    assert result.returncode == 0, output(result)
    assert result.stdout.startswith("audit main: ")


# ---------------------------------------------------------------- the conftest plugin


def test_results_hold_nodes_and_outcomes_per_id(repo: Repo) -> None:
    data = repo.results()
    assert data["format"] == 3
    assert data["complete"] is True
    ids = data["ids"]
    assert isinstance(ids, dict)
    assert ids["cli.tip-default"] == [
        {"node": "tests/test_cli.py::test_tip_default", "outcome": "passed"}
    ]
    assert ids["cli.no-args"] == [{"node": "tests/test_cli.py::test_no_args", "outcome": "xfailed"}]
    nodes = data["nodes"]
    assert isinstance(nodes, dict)
    assert nodes["tests/test_cli.py::test_no_args"]["xfail"] == {
        "strict": True,
        "run": True,
        "reason": "cli.no-args: traceback today (gap entrypoint-hardening)",
        "conditional": False,
        "raises": [],
    }
    assert nodes["tests/test_cli.py::test_no_args"]["body"] == "AssertionError"
    assert nodes["tests/test_cli.py::test_tip_default"]["body"] == ""
    files = data["files"]
    assert isinstance(files, dict)
    assert "src/tipcalc/__init__.py" in files
    assert "tests/test_cli.py" in files
    assert not [path for path in files if path.startswith(("specs/", ".cache/"))]


def test_spec_option_selects_linked_tests_and_marks_the_run_partial(repo: Repo) -> None:
    result = repo.pytest("--spec", "cli.tip-default,cli.no-args")
    assert "1 passed, 4 deselected, 1 xfailed" in result.stdout, output(result)
    data = repo.results()
    assert data["complete"] is False
    assert data["partial"] == ["--spec", "4 deselected"]
    ids = data["ids"]
    assert isinstance(ids, dict)
    assert sorted(ids) == ["cli.no-args", "cli.tip-default"]
    repeated = repo.pytest("--spec", "cli.help", "--spec", "cli.bad-amount")
    assert "4 deselected, 2 xfailed" in repeated.stdout, output(repeated)


def test_results_record_every_outcome_kind_and_collection_errors(repo: Repo) -> None:
    repo.write(
        "tests/test_kinds.py",
        "import pytest\n\n\n"
        "@pytest.fixture\ndef broken() -> None:\n    raise RuntimeError('setup')\n\n\n"
        '@pytest.mark.spec("k.failed")\ndef test_failed() -> None:\n    assert 1 == 2\n\n\n'
        '@pytest.mark.spec("k.stub")\ndef test_stub() -> None:\n    raise NotImplementedError\n\n\n'
        '@pytest.mark.spec("k.error")\ndef test_error(broken: None) -> None:\n    pass\n\n\n'
        '@pytest.mark.spec("k.xpassed")\n@pytest.mark.xfail(strict=True, reason="k.xpassed")\n'
        "def test_xpassed() -> None:\n    pass\n\n\n"
        '@pytest.mark.spec("k.skipped")\n@pytest.mark.skip(reason="k.skipped")\n'
        "def test_skipped() -> None:\n    pass\n\n\n"
        "@pytest.mark.spec()\ndef test_empty_tag() -> None:\n    pass\n",
    )
    repo.write("tests/test_broken.py", "import nowhere  # noqa: F401\n")
    repo.pytest("--continue-on-collection-errors")
    data = repo.results()
    ids = data["ids"]
    nodes = data["nodes"]
    assert isinstance(ids, dict)
    assert isinstance(nodes, dict)
    outcomes = {k: v[0]["outcome"] for k, v in ids.items() if k.startswith("k.")}
    assert outcomes == {
        "k.failed": "failed",
        "k.stub": "failed",
        "k.error": "error",
        "k.xpassed": "xpassed",
        "k.skipped": "skipped",
    }
    assert nodes["tests/test_kinds.py::test_failed"]["exc"] == "AssertionError"
    assert nodes["tests/test_kinds.py::test_stub"]["exc"] == "NotImplementedError"
    assert nodes["tests/test_kinds.py::test_error"]["exc"] == "RuntimeError"
    assert nodes["tests/test_kinds.py::test_skipped"]["skip"] is True
    assert data["collect_errors"] == [
        {
            "node": "tests/test_broken.py",
            "error": "ModuleNotFoundError: No module named 'nowhere'",
            "exc": "ModuleNotFoundError",
        }
    ]
    assert data["bad_tags"] == [
        {
            "node": "tests/test_kinds.py::test_empty_tag",
            "problem": 'use @pytest.mark.spec("<cap>.<slug>", ...) with ids only',
        }
    ]


def test_collect_only_writes_no_results(repo: Repo) -> None:
    (repo.path / ".cache" / "spec-results.json").unlink()
    assert repo.pytest("--collect-only").returncode == 0
    assert not (repo.path / ".cache" / "spec-results.json").exists()


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv is not on PATH")
def test_project_py_runs_as_a_pep723_script(repo: Repo) -> None:
    # From outside the repo: uv is often a mise shim, and a shim refuses to run inside a repo
    # whose mise.toml is not trusted yet (init runs `mise trust`; this copy never did).
    script = str(repo.path / "scripts" / "project.py")
    result = subprocess.run(
        ["uv", "run", "--quiet", "--script", script, "--version"],
        cwd=repo.path.parent,
        capture_output=True,
        text=True,
        check=False,
        env=clean_env(),
    )
    assert result.returncode == 0, output(result)
    assert result.stdout.strip() == "project.py 3.1.0"


# ---------------------------------------------------------------- parsing units


def load_project_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("project_under_test", PROJECT_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve their module through sys.modules
    keep, sys.dont_write_bytecode = (
        sys.dont_write_bytecode,
        True,
    )  # no __pycache__ in templates/
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = keep
    return module


def test_frontmatter_scalars() -> None:
    project = load_project_module()
    text = (
        "---\n"
        'change: "2026-09-24-x"\n'
        "status: draft                  # draft | approved | done\n"
        "roadmap:                       # the roadmap slug, once scheduled\n"
        'title: "fix(cli): say \\"no\\" # politely"   # comment\n'
        "note: 'it''s'\n"
        "---\n"
    )
    fields, problem = project.frontmatter(text)
    assert problem is None
    assert fields == {
        "change": "2026-09-24-x",
        "status": "draft",
        "roadmap": "",
        "title": 'fix(cli): say "no" # politely',
        "note": "it's",
    }
    assert project.frontmatter("no block\n")[1] == "no frontmatter (a leading --- block)"
    assert project.frontmatter("---\na: b\n")[1] == "frontmatter has no closing ---"


def test_scenario_blocks_ignore_whitespace_but_see_the_gap_tag() -> None:
    project = load_project_module()
    base = (
        "# Capability: cli\n\n## Requirement: R\nThe CLI SHALL work.\n\n"
        "### Scenario: cli.a [gap: fix-it]\n- WHEN x\n- THEN y\n"
    )
    spaced = base.replace("- THEN y", "- THEN   y   ").replace("\n\n###", "\n\n\n###")
    untagged = base.replace(" [gap: fix-it]", "")
    reworded = base.replace("- THEN y", "- THEN z")
    report = project.Report()
    blocks = {}
    for name, text in (
        ("base", base),
        ("spaced", spaced),
        ("untagged", untagged),
        ("reworded", reworded),
    ):
        (scenario,) = project.parse_capability("specs/capabilities/cli.md", text, report)
        blocks[name] = scenario
    assert report.lines == []
    assert blocks["base"].gap == "fix-it"
    assert blocks["untagged"].gap is None
    assert blocks["base"].block == blocks["spaced"].block  # not MODIFIED
    assert blocks["base"].block != blocks["untagged"].block  # MODIFIED: the tag went
    assert blocks["base"].block != blocks["reworded"].block  # MODIFIED: the THEN changed


UNIT_BASE = (
    "# Capability: cli\n\n## Requirement: R\nThe CLI SHALL work.\n\n"
    "### Scenario: cli.a\n- WHEN x\n- THEN y\n"
)
UNIT_B = "### Scenario: cli.b\n- WHEN x\n- THEN y\n"


def parse(text: str) -> tuple[list[str], list[str]]:
    """(scenario ids, report lines) for one capability file."""
    project = load_project_module()
    report = project.Report()
    scenarios = project.parse_capability("specs/capabilities/cli.md", text, report)
    return [s.id for s in scenarios], [line for _, line in report.lines]


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        (UNIT_BASE + "  ```\n  output\n", "code fence is never closed"),
        (UNIT_BASE + "  <!-- note\n", "comment is never closed"),
        (
            UNIT_BASE + "  ```\n" + UNIT_B,
            "line sits left of the fence opened on line 9",
        ),
        (
            UNIT_BASE + "  <!-- note\n" + UNIT_B + "  -->\n",
            "left of the comment opened on",
        ),
        (UNIT_BASE + "<!-- note --> <h3>Scenario: cli.b</h3>\n", "text after '-->'"),
        (
            UNIT_BASE.replace("work.\n", "work.\n**Scenario: cli.b**\n"),
            "'Scenario:' outside",
        ),
        (
            UNIT_BASE.replace("work.\n", "work.\n\nScenario cli.b\n---\n"),
            "only '-' or '='",
        ),
        (UNIT_BASE.replace("work.\n", "work.\n- WHEN z\n"), "bullets belong under"),
        (UNIT_BASE.replace("work.\n", "work.\n* THEN z\n"), "bullets belong under"),
    ],
    ids=[
        "fence-at-eof",
        "comment-at-eof",
        "fence-outdented",
        "comment-outdented",
        "after-comment",
        "scenario-in-prose",
        "setext",
        "bullets-in-requirement",
        "star-bullets-in-requirement",
    ],
)
def test_markdown_that_could_hide_a_scenario_fails(text: str, problem: str) -> None:
    _, lines = parse(text)
    assert any(problem in line for line in lines), lines


def test_fences_close_only_on_their_own_marker() -> None:
    ids, lines = parse(UNIT_BASE + "  ```\n  ~~~\n  ```\n" + UNIT_B)
    assert ids == ["cli.a", "cli.b"]
    assert lines == []
    ids, lines = parse(UNIT_BASE + "  ````\n  ```\n  ````\n" + UNIT_B)
    assert ids == ["cli.a", "cli.b"]
    assert lines == []


def test_literal_output_in_a_fence_or_code_span_is_fine() -> None:
    text = UNIT_BASE.replace("- THEN y\n", "- THEN stdout is `Scenario: z`:\n") + (
        "  ```\n  # Report\n  Scenario: text\n  ---\n  ```\n"
    )
    ids, lines = parse(text)
    assert ids == ["cli.a"]
    assert lines == []


def test_names_id_matches_whole_ids_only() -> None:
    names_id = load_project_module().names_id
    assert names_id("cli.help: traceback today", "cli.help")
    assert names_id("fixed later, see cli.help.", "cli.help")
    assert names_id("(cli.help)", "cli.help")
    assert not names_id("cli.help-page: traceback", "cli.help")
    assert not names_id("cli.helper", "cli.help")
    assert not names_id("cli.help.x", "cli.help")
    assert not names_id("xcli.help", "cli.help")


# ---------------------------------------------------------------- acceptance runs A and E


def test_roadmap_titles_and_human_checks_are_shown_as_written() -> None:
    """Runs A and E: prose_lines blanks inline code to ``; what merge shows (the next item,
    the checks to attest) and records on main comes from the line as written."""
    project = load_project_module()
    roadmap = (
        "# Roadmap\n\n## Phase 1\n"
        "- [ ] greet-name: `hello <name>` prints `Hello, <name>` <!-- a note -->\n"
    )
    ((_, slug, ticked, title, section),) = project.roadmap_entries(roadmap)
    assert (slug, ticked, section) == ("greet-name", False, "Phase 1")
    assert title == "`hello <name>` prints `Hello, <name>`"

    validation = (
        "## Review focus\n"
        "- `tipcalc 1e999 -> inf` -> cli.nope\n"
        "## Human checks\n"
        "- The `error:` lines read clearly to someone who has never seen the code.\n"
    )
    change = project.Change("2026-09-24-x", "specs/changes/2026-09-24-x", {})
    report = project.Report()
    project.lint_validation(change, validation, {}, report)
    assert change.human_checks == [
        "The `error:` lines read clearly to someone who has never seen the code."
    ]
    message = (
        "specs/changes/2026-09-24-x/validation.md:2: I13: review focus '`tipcalc 1e999 -> inf`' "
        "names "
        "unknown id cli.nope"
    )
    assert ("FAIL", message) in report.lines


def test_the_results_say_whose_code_raised(repo: Repo) -> None:
    """Run E: a test body that crashes in its own code (an IndexError on empty output) is
    recorded as raised_in "test"; a crash inside the code under test as "code"."""
    repo.append(
        "tests/test_cli.py",
        '\n\n@pytest.mark.spec("cli.tip-default")\ndef test_first_line() -> None:\n'
        '    assert tipcalc("--nope").stdout.splitlines()[0] == "usage"\n',
    )
    repo.append("tests/test_cli.py", IN_PROCESS_NO_ARGS)
    repo.edit(
        "pyproject.toml",
        'addopts = "-q --strict-markers -p no:cacheprovider"',
        'addopts = "-q --strict-markers -p no:cacheprovider"\npythonpath = ["src"]',
    )
    repo.pytest()
    nodes = repo.results()["nodes"]
    assert isinstance(nodes, dict)
    own = nodes["tests/test_cli.py::test_first_line"]
    assert (own["body"], own["raised_in"]) == ("IndexError", "test")
    code = nodes["tests/test_cli.py::test_no_args_in_process"]
    assert (code["body"], code["raised_in"]) == ("IndexError", "code")
    passing = nodes["tests/test_cli.py::test_tip_default"]
    assert passing["raised_in"] == ""


@pytest.mark.parametrize(
    ("body", "raised_in", "kind"),
    [
        ("AssertionError", "test", "right"),
        ("IndexError", "test", "test"),
        ("IndexError", "code", "raised"),
        ("IndexError", "", "raised"),  # results from a conftest that predates raised_in
        ("NameError", "test", "wrong"),
    ],
)
def test_a_test_side_exception_is_its_own_kind_of_red(body: str, raised_in: str, kind: str) -> None:
    project = load_project_module()
    node = project.Node(
        node="t",
        ids=["cli.a"],
        outcome="failed",
        xfail_strict=None,
        xfail_reason="",
        xfail_run=True,
        xfail_raises=[],
        skip=False,
        crash=f"{body}: x",
        body=body,
        raised_in=raised_in,
    )
    assert project.red_kind(node) == kind


# ---------------------------------------------------------------- v3.1 M12: the trunk map

TRUNK = "\n## Trunk\n- src/tipcalc/__init__.py: the entrypoint every command runs through\n"


def test_trunk_globs_are_gitignore_style_and_anchored_at_the_root() -> None:
    """Design A.1: `**` crosses folders, `*` and `?` stay inside one, and every pattern is
    anchored at the repo root: `config.py` is the root's own file, never src/config.py."""
    project = load_project_module()
    cases = [
        ("src/tipcalc/__init__.py", "src/tipcalc/__init__.py", True),
        ("src/tipcalc/__init__.py", "x/src/tipcalc/__init__.py", False),
        ("config.py", "config.py", True),
        ("config.py", "src/config.py", False),
        ("/config.py", "config.py", True),
        ("migrations/**", "migrations/0001_init.sql", True),
        ("migrations/**", "migrations/old/0001.sql", True),
        ("migrations/**", "app/migrations/0001.sql", False),
        ("migrations/", "migrations/old/0001.sql", True),
        ("src/*.py", "src/app.py", True),
        ("src/*.py", "src/app/cli.py", False),
        ("**/settings.py", "settings.py", True),
        ("**/settings.py", "src/app/settings.py", True),
        ("src/**/config.py", "src/config.py", True),
        ("src/**/config.py", "src/a/b/config.py", True),
        ("src/**/config.py", "src/a/b/config.pyc", False),
        ("src/?.py", "src/a.py", True),
        ("src/?.py", "src/ab.py", False),
        ("src/[ab].py", "src/b.py", True),
        ("src/[!ab].py", "src/b.py", False),
        ("src/[!ab].py", "src/c.py", True),
        ("src/a+b.py", "src/a+b.py", True),
        ("src/a.py", "src/aXpy", False),
    ]
    wrong = [
        (glob, path, hit)
        for glob, path, hit in cases
        if (project.glob_regex(glob).fullmatch(path) is not None) != hit
    ]
    assert wrong == []


def test_the_trunk_section_parses_and_names_its_bad_lines() -> None:
    project = load_project_module()
    text = (
        "# Tech stack: x\n\n## Distribution\nnone\n\n## Trunk\n"
        "<!-- - ignored.py: a comment is not an entry -->\n"
        "- src/app/__init__.py: the entrypoint\n"
        "- `migrations/**`: schema changes reach every row\n"
        "\n"
        "- src/app/config.py\n"
        "- tests/**:\n"
        "- ../outside.py: out of the repo\n"
        "## Never use\n- x: y\n"
    )
    trunk = project.trunk_map(text)
    assert trunk.found
    assert [(e.glob, e.why, e.line) for e in trunk.entries] == [
        ("src/app/__init__.py", "the entrypoint", 8),
        ("migrations/**", "schema changes reach every row", 9),
    ]
    assert trunk.problems == [
        "specs/tech-stack.md:11: a Trunk line is '- <glob>: <why>', not '- src/app/config.py'",
        "specs/tech-stack.md:12: trunk entry 'tests/**' needs its why: what makes it trunk",
        "specs/tech-stack.md:13: trunk entry '../outside.py' must name paths inside the repo",
    ]
    entry = trunk.entry_for("migrations/0001_init.sql")
    assert entry is not None and entry.why == "schema changes reach every row"
    assert trunk.entry_for("src/app/cli.py") is None
    assert trunk.entry_for("x.py") is None
    missing = project.trunk_map("# Tech stack: x\n\n## Never use\n- x: y\n")
    assert not missing.found and missing.entries == [] and missing.problems == []
    empty = project.trunk_map("## Trunk\n\n## Never use\n")
    assert empty.found and empty.entries == [] and empty.problems == []
    assert not project.trunk_map(None).found


def test_plan_groups_read_their_files() -> None:
    project = load_project_module()
    text = (
        "## G1 a | x.y | risk: low | parallel: no\n"
        "Files: src/a.py, `src/b.py` (NEW), tests/test_a.py (NEW, split out)\n"
        "## G2 b | x.z | risk: high | parallel: no\n"
        "Files: src/c/\n"
    )
    groups = project.parse_groups(text, None, "")
    assert [group.files for group in groups] == [
        ["src/a.py", "src/b.py", "tests/test_a.py"],
        ["src/c/"],
    ]


def test_a_malformed_trunk_line_fails(repo: Repo) -> None:
    repo.append("specs/tech-stack.md", TRUNK + "- tests/**:\n- src/tipcalc\n")
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert "trunk entry 'tests/**' needs its why: what makes it trunk" in result.stdout
    assert "a Trunk line is '- <glob>: <why>', not '- src/tipcalc'" in result.stdout
    repo.write("specs/tech-stack.md", repo.read("specs/tech-stack.md").split("- tests/**")[0])
    result = repo.check()
    assert result.returncode == 0, output(result)


def test_the_template_trunk_line_fails_until_p2_fills_it(repo: Repo) -> None:
    """The product template's Trunk section ends in a placeholder line. P2's placeholder grep
    catches it, and spec-check refuses it too, so an unfilled section never passes verify."""
    template = SKILL.parents[2] / "12-system" / "templates" / "sdd" / "tech-stack.md"
    section = "## Trunk" + template.read_text(encoding="utf-8").split("\n## Trunk", 1)[1]
    repo.append("specs/tech-stack.md", "\n" + section)
    result = repo.check()
    assert result.returncode == 1, output(result)
    assert (
        "a Trunk line holds the placeholder {GLOB}: write the entries talk settled, "
        "'- <glob>: <why>', or leave the section empty"
    ) in result.stdout
    repo.write("specs/tech-stack.md", repo.read("specs/tech-stack.md").split("- {GLOB}")[0])
    result = repo.check()
    assert result.returncode == 0, output(result)


def test_i17_a_low_risk_group_that_touches_trunk_fails(feat: Repo) -> None:
    """Design A.3: spec-check (and approve) refuse a group whose Files: match a trunk entry
    unless it says risk: high, naming the file and why it is trunk."""
    feat.append("specs/tech-stack.md", TRUNK)
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {CHANGE}/plan.md: I17: G1 lists src/tipcalc/__init__.py, which is trunk (the "
        "entrypoint every command runs through); mark it risk: high"
    ) in result.stdout
    assert "G2 lists" not in result.stdout  # config.py (NEW) and its tests are leaf
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert "I17: G1 lists src/tipcalc/__init__.py" in result.stdout
    feat.edit(
        f"{CHANGE}/plan.md",
        "cli.negative-amount | risk: low",
        "cli.negative-amount | risk: high",
    )
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)


def test_status_names_the_trunk_files_of_a_risk_high_group(feat: Repo) -> None:
    feat.append("specs/tech-stack.md", TRUNK)
    feat.edit(
        f"{CHANGE}/plan.md",
        "cli.negative-amount | risk: low",
        "cli.negative-amount | risk: high",
    )
    approve(feat)
    result = feat.project("status")
    assert result.returncode == 0, output(result)
    assert (
        "next: G1 usage errors: cli.no-args cli.help cli.bad-amount cli.negative-amount (no "
        "passing tests yet, risk: high (compile pauses after it); trunk: src/tipcalc/__init__.py)"
    ) in result.stdout


# ---------------------------------------------------------------- v3.1 M14: rollback and flags

REQ = f"{CHANGE}/requirements.md"
REVERT = (
    "revert: the change stays inside the CLI; a revert of the squash brings the tracebacks back"
)
FLAG = "TIPCALC_FLAG_STRICT"
FLAG_ROW = (
    f"# {FLAG} | flag | bool | no | 0 | strict input (change 2026-09-24-entrypoint-hardening)\n"
)
FLAG_OFF = f"""
### Scenario: cli.lenient-when-off [flag-off: {FLAG}]
- GIVEN {FLAG} is unset
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0
"""


def test_the_rollback_line_is_one_of_three() -> None:
    project = load_project_module()

    def parse(body: str) -> tuple[object, list[str], bool]:
        text = f"---\nstatus: draft\n---\n## Why\nx\n## Rollback\n{body}## Context\n- y\n"
        rollback, problems, found = project.rollback_section(text)
        return rollback, [message for _, message in problems], found

    for body, want in (
        ("revert: nothing outside the repo changes\n", "revert: nothing outside the repo changes"),
        ("- flag: APP_FLAG_SPLIT\n", "flag: APP_FLAG_SPLIT"),
        (
            "<!-- one line -->\none-way: the CSV column is published\n",
            "one-way: the CSV column is published",
        ),
    ):
        rollback, problems, found = parse(body)
        assert (str(rollback), problems, found) == (want, [], True), body
    one_line = (
        "## Rollback holds exactly one line: revert: <why> | flag: <ENV_NAME> | one-way: <what>"
    )
    for body, problem in (
        ("", f"{one_line} (found none)"),
        ("revert: a\nflag: B\n", f"{one_line} (found 2)"),
        ("revert:\n", "revert: needs its why: why a revert of the squash is enough"),
        ("one-way:  \n", "one-way: needs what cannot be undone"),
        ("flag: app flag\n", "flag: names an environment variable in capitals, not 'app flag'"),
        (
            "undo: git revert\n",
            (
                "a Rollback line is 'revert: <why>', 'flag: <ENV_NAME>' or 'one-way: <what>', "
                "not 'undo: git revert'"
            ),
        ),
    ):
        rollback, problems, found = parse(body)
        assert (rollback, problems, found) == (None, [problem], True), body
    assert parse("{ROLLBACK_KIND}: {ROLLBACK_DETAIL}\n")[:2] == (None, [])  # the placeholder check
    assert project.rollback_section("---\nstatus: draft\n---\n## Why\nx\n") == (None, [], False)


def test_scenario_tags_hold_a_gap_or_a_flag_off_guard() -> None:
    project = load_project_module()

    def parse(tags: str) -> tuple[list[object], list[str]]:
        text = (
            "# Capability: cli\n\n## Requirement: R\nThe CLI SHALL work.\n\n"
            f"### Scenario: cli.a {tags}\n- WHEN x\n- THEN y\n"
        )
        report = project.Report()
        found = project.parse_capability("specs/capabilities/cli.md", text, report)
        return found, [line for _, line in report.lines]

    [scenario], problems = parse("[flag-off: APP_FLAG_X]")
    assert problems == []
    assert (scenario.flag_off, scenario.gap) == ("APP_FLAG_X", None)
    assert scenario.block.startswith("### Scenario: cli.a [flag-off: APP_FLAG_X]\n")
    [plain], _ = parse("")
    assert plain.flag_off is None and plain.block != scenario.block
    only = "(only [gap: <slug>] and [flag-off: <ENV_NAME>])"
    assert parse("[flag-off: app_flag]")[1] == [
        f"specs/capabilities/cli.md:6: unknown tag after cli.a: '[flag-off: app_flag]' {only}"
    ]
    both = (
        "specs/capabilities/cli.md:6: scenario cli.a has a [gap] and a [flag-off] tag; it is "
        "one or the other"
    )
    assert parse("[gap: fix-it] [flag-off: APP_FLAG_X]")[1] == [both]


def test_i21_a_draft_needs_exactly_one_rollback_line(feat: Repo) -> None:
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)
    feat.edit(REQ, f"## Rollback\n{REVERT}\n", "")
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {REQ}: I21: missing section '## Rollback' (one line: revert: <why> | flag: "
        "<ENV_NAME> | one-way: <what>)"
    ) in result.stdout
    feat.append(REQ, "## Rollback\nrevert: a\nundo: b\n")
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert f"FAIL  {REQ}:18: I21: ## Rollback holds exactly one line" in result.stdout
    assert "(found 2)" in result.stdout


def test_i21_a_change_approved_before_v3_1_may_lack_rollback(feat: Repo) -> None:
    feat.edit(REQ, f"## Rollback\n{REVERT}\n", "")
    approve(feat)
    result = feat.check()
    assert result.returncode == 0, output(result)
    assert f"warn  {REQ}: I21: missing section '## Rollback'" in result.stdout


def test_i21_revert_cannot_undo_a_service_change_that_touches_trunk(feat: Repo) -> None:
    feat.append("specs/tech-stack.md", TRUNK)
    feat.edit(
        f"{CHANGE}/plan.md",
        "cli.negative-amount | risk: low",
        "cli.negative-amount | risk: high",
    )
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)  # Distribution none: a revert is enough
    feat.edit("specs/tech-stack.md", "## Distribution\nnone\n", "## Distribution\nservice\n")
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {REQ}: I21: revert: cannot undo a service change that touches trunk "
        "(src/tipcalc/__init__.py: the entrypoint every command runs through); say flag: "
        "<ENV_NAME> or one-way: <what>"
    ) in result.stdout


def test_a_one_way_change_needs_a_risk_high_group(feat: Repo) -> None:
    feat.edit(REQ, REVERT, "one-way: the exit codes become a published interface")
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {REQ}: I21: one-way: needs a risk: high group in plan.md; put the one-way work "
        "there"
    ) in result.stdout
    feat.edit(
        f"{CHANGE}/plan.md",
        "config.percent-invalid | risk: low",
        "config.percent-invalid | risk: high",
    )
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)


def test_i22_a_flag_needs_its_env_row_and_a_flag_off_guard(feat: Repo) -> None:
    feat.edit(REQ, REVERT, f"flag: {FLAG}")
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 1, output(result)
    assert (
        f"FAIL  {REQ}: I22: flag: {FLAG} needs a row of kind flag in .env.example: "
        f"# {FLAG} | flag | bool | no | 0 | <what it turns on>"
    ) in result.stdout
    assert (
        f"FAIL  {REQ}: I22: flag: {FLAG} needs a [flag-off: {FLAG}] scenario that pins the old "
        "behaviour with the flag off"
    ) in result.stdout
    feat.write(".env.example", FLAG_ROW)
    feat.append("specs/capabilities/cli.md", FLAG_OFF)
    feat.edit(
        f"{CHANGE}/plan.md", "cli.negative-amount |", "cli.negative-amount cli.lenient-when-off |"
    )
    result = feat.check("--change", "entrypoint-hardening")
    assert result.returncode == 0, output(result)

    # a [flag-off] tag must name a flag row, wherever it stands
    feat.write(".env.example", FLAG_ROW.replace("| flag |", "| knob |"))
    feat.pytest()
    result = feat.check()
    assert result.returncode == 1, output(result)
    assert (
        f"I22: [flag-off: {FLAG}] names no flag row in .env.example; add '# {FLAG} | flag | bool "
        "| no | 0 | <what it turns on>'"
    ) in result.stdout


@pytest.mark.parametrize(
    ("rollback", "backlog", "problem"),
    [
        (f"flag: {FLAG}", "2026-09-25-launch-entrypoint-hardening.md", None),
        (
            REVERT,
            "2026-09-25-launch-entrypoint-hardening.md",
            "it also changes specs/backlog/2026-09-25-launch-entrypoint-hardening.md",
        ),
        (
            f"flag: {FLAG}",
            "2026-09-25-other.md",
            "it also changes specs/backlog/2026-09-25-other.md",
        ),
    ],
)
def test_a_flag_close_commit_may_add_its_launch_item(
    feat: Repo, rollback: str, backlog: str, problem: str | None
) -> None:
    """Design B.2: merge's close commit of a flag: change adds the launch backlog item, and a
    close commit adds no other new file."""
    feat.edit(REQ, REVERT, rollback)
    approve(feat)
    feat.commit("spec(entrypoint-hardening): approve")
    feat.write(f"specs/backlog/{backlog}", "---\nstatus: open\n---\n# Launch\n")
    close(feat)
    feat.pytest()
    result = feat.check()
    if problem is None:
        assert result.returncode == 0, output(result)
        assert "I1" not in result.stdout and "I2" not in result.stdout
    else:
        assert result.returncode == 1, output(result)
        assert f"but it is not merge's close commit: {problem}" in result.stdout


def test_doctor_checks_flag_rows_and_their_age(repo: Repo) -> None:
    """Design B.2: a flag row is a bool, off by default; one that has sat on the default branch
    for more than 30 days is flag debt."""
    old = datetime.now().astimezone() - timedelta(days=40)
    repo.write(
        ".env.example",
        "# NAME | kind | type | required | default | notes\n"
        "# APP_FLAG_OLD | flag | bool | no | 0 | save cards\n",
    )
    repo.git("add", ".env.example")
    stamp = {"GIT_AUTHOR_DATE": old.isoformat(), "GIT_COMMITTER_DATE": old.isoformat()}
    committed = repo.run("git", "commit", "-q", "-m", "feat: save cards behind a flag", env=stamp)
    assert committed.returncode == 0, output(committed)
    repo.append(
        ".env.example",
        "# APP_FLAG_NEW | flag | bool | no | off | new\n# APP_FLAG_BAD | flag | str | no | 1 | x\n",
    )
    repo.commit("feat: two more flags")
    result = repo.project("doctor")
    assert (
        f"warn  env APP_FLAG_OLD: flag debt: on main since {old.date().isoformat()} (40 days); "
        "launch it: flip it on, then remove the flag, its off path and its [flag-off] scenarios"
    ) in result.stdout, output(result)
    assert "APP_FLAG_NEW: flag debt" not in result.stdout
    assert "FAIL  env APP_FLAG_BAD: a flag's type is bool, not 'str'" in result.stdout
    assert (
        "FAIL  env APP_FLAG_BAD: a flag's default is off (0, false, no or off), not '1'"
        in result.stdout
    )
    assert "env APP_FLAG_NEW: a flag's" not in result.stdout
