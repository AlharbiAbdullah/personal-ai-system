"""project-init v3, milestone M7: scripts/init.py, the deterministic half of the skill.

Every test works in its own temp folder. The tipcalc tests clone ~/projects/tipcalc (or
$TIPCALC_SOURCE) with `git clone --no-local` and never write to it; they skip when it is absent.
init.py runs as a subprocess under this interpreter (stdlib only), except for the unit tests of
its text mergers, which import it.
"""

from __future__ import annotations

import base64
import fcntl
import gzip
import hashlib
import importlib.util
import json
import os
import re
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import time
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parent
SKILL = TESTS.parent
INIT = SKILL / "scripts" / "init.py"
FIXTURES = TESTS / "fixtures"
PRODUCT_TEMPLATES = SKILL.parents[2] / "12-system" / "templates" / "sdd"
REPORT_INDENT = " " * 14  # the column init.py's P0 and P1 reports continue a row in
TIPCALC_SOURCE = Path(os.environ.get("TIPCALC_SOURCE", Path.home() / "projects" / "tipcalc"))
FAKE_AWS_ID = "AKIA" + "QYLPMN5HHHFPZAM2"  # split, so this file never matches the rule itself
PLACEHOLDER = re.compile(r"\{[A-Z][A-Z0-9_]*\}")
DECISIONS_KEEP = "project_memory/decisions/.gitkeep"
TEXT_RENDERS = (
    "mise.toml",
    ".env.example",
    "specs/README.md",
    "project_memory/README.md",
    ".githooks/reference-transaction",
)
VALUES = {"DESCRIPTION": "Tiny CLI that prints the tip for a bill."}
PY = {"pyproject.toml": '[project]\nname = "app"\n'}  # P0 stops a repo with no stack pack


def clean_env(**extra: str) -> dict[str, str]:
    """No user or system git config, a fixed identity, no active virtualenv."""
    env = {k: v for k, v in os.environ.items() if k not in ("VIRTUAL_ENV", "GIT_DIR")}
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "author@example.invalid",
            "GIT_COMMITTER_NAME": "Test Author",
            "GIT_COMMITTER_EMAIL": "author@example.invalid",
        }
    )
    env.update(extra)
    return env


def init(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INIT), *args],
        capture_output=True,
        text=True,
        env=env or clean_env(),
        timeout=900,
        check=False,
    )


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env or clean_env(),
        check=False,
    )
    assert result.returncode == 0, f"git {' '.join(args)}: {result.stderr}"
    return result.stdout


def write(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def make_repo(root: Path, files: dict[str, str], branch: str = "main") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    write(root, files)
    git(root, "init", "-q", "-b", branch)
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "feat: initial")
    return root


def preflight_json(repo: Path, *extra: str) -> tuple[int, dict[str, object]]:
    result = init(
        "preflight",
        str(repo),
        "--json",
        "--offline",
        "--vault",
        str(repo.parent / "no-vault"),
        "--search-root",
        str(repo.parent / "no-search"),
        *extra,
    )
    assert result.returncode in (0, 1), result.stderr
    return result.returncode, json.loads(result.stdout)


def listed(facts: dict[str, object], key: str) -> list[dict[str, object]]:
    value = facts[key]
    assert isinstance(value, list)
    return value


def stop_ids(facts: dict[str, object]) -> list[str]:
    stops = facts["stops"]
    assert isinstance(stops, list)
    return [str(s["id"]) for s in stops]


def tree_hash(root: Path) -> str:
    """Every file under root, .git included: path, mode and content (links by target)."""
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in sorted(filenames):
            path = Path(dirpath) / name
            info = path.lstat()
            digest.update(str(path.relative_to(root)).encode())
            digest.update(str(stat.S_IMODE(info.st_mode)).encode())
            data = os.readlink(path).encode() if path.is_symlink() else path.read_bytes()
            digest.update(hashlib.sha256(data).digest())
    return digest.hexdigest()


def load_init() -> ModuleType:
    spec = importlib.util.spec_from_file_location("project_init_script", INIT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TIPCALC_PYPROJECT = """[project]
name = "tipcalc"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
authors = [
    { name = "Some Author", email = "author@example.invalid" }
]
requires-python = ">=3.14"
dependencies = []

[project.scripts]
tipcalc = "tipcalc:main"

[build-system]
requires = ["uv_build>=0.12.10,<0.13.0"]
build-backend = "uv_build"
"""
TIPCALC_SRC = """import os
import sys


def tip(bill: float, percent: float) -> float:
    return round(bill * percent / 100, 2)


def main() -> None:
    percent = float(os.environ.get("TIPCALC_DEFAULT_PERCENT", "15"))
    bill = float(sys.argv[1])
    print(f"tip: {tip(bill, percent)}")
"""
UV_GITIGNORE = (
    "# Python-generated files\n__pycache__/\n*.py[oc]\nbuild/\ndist/\nwheels/\n*.egg-info\n\n"
    "# Virtual environments\n.venv\n"
)
TECH_STACK = """# Tech stack: tipcalc

## Runtime
- Language: Python >=3.14.

## Distribution
none

## Standing rules
- S-1: secrets are `op://` pointers only.

## Trunk
- src/tipcalc/__init__.py: the entrypoint of the tipcalc command (tipcalc:main)
"""
TIPCALC_TRUNK = "- src/tipcalc/__init__.py: the entrypoint of the tipcalc command (tipcalc:main)"
CLI_CAPABILITY = """# Capability: cli

## Requirement: Tip output
The CLI SHALL print the tip for a bill.

### Scenario: cli.tip-default
- GIVEN no percent
- WHEN `tipcalc 100` runs
- THEN it prints `tip: 15.0`
"""


def tipcalc_like(root: Path, extra: dict[str, str] | None = None) -> Path:
    """A tipcalc-shaped repo on plan/project-init with the P2 product text, no network needed.
    extra: more files for its first commit."""
    make_repo(
        root,
        {
            "pyproject.toml": TIPCALC_PYPROJECT,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            ".gitignore": UV_GITIGNORE,
            ".python-version": "3.14\n",
            "README.md": "# tipcalc\n\nTiny CLI that computes a tip.\n",
            **(extra or {}),
        },
    )
    git(root, "switch", "-q", "-c", "plan/project-init")
    write(root, {"specs/tech-stack.md": TECH_STACK, "specs/capabilities/cli.md": CLI_CAPABILITY})
    return root


def render(
    repo: Path, *extra: str, values: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    args = ["render", str(repo), *extra]
    if values is not None:
        args += ["--values", json.dumps(values)]
    return init(*args)


def generated(repo: Path) -> dict[str, str]:
    data = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    table = data.get("generated", {})
    assert isinstance(table, dict)
    return {str(k): str(v) for k, v in table.items()}


@pytest.fixture(scope="module")
def tipcalc(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Run B's starting point: tipcalc master, origin removed, uv.lock created but untracked."""
    if not (TIPCALC_SOURCE / ".git").exists():
        pytest.skip(f"no tipcalc repo at {TIPCALC_SOURCE}")
    dest = tmp_path_factory.mktemp("adopt") / "tipcalc"
    subprocess.run(
        ["git", "clone", "-q", "--no-local", "--branch", "master", str(TIPCALC_SOURCE), str(dest)],
        check=True,
        env=clean_env(),
    )
    git(dest, "remote", "remove", "origin")
    subprocess.run(["uv", "lock", "-q"], cwd=dest, check=True, env=clean_env(), timeout=600)
    return dest


def userns() -> bool:
    return (
        subprocess.run(["unshare", "-rn", "true"], capture_output=True, check=False).returncode == 0
    )


def gitleaks_cmd() -> list[str] | None:
    """The argv that runs gitleaks here (run it from a folder without an untrusted mise.toml)."""
    for argv in (["gitleaks"], ["mise", "x", "gitleaks@8.30.1", "--", "gitleaks"]):
        try:
            done = subprocess.run(
                [*argv, "version"], capture_output=True, cwd=Path.home(), check=False, timeout=300
            )
        except FileNotFoundError:
            continue
        if done.returncode == 0:
            return argv
    return None


def need[T](value: T | None, why: str) -> T:
    """value, or the test skipped with why. The skip is raised here, so a type checker narrows
    value at every call even where it cannot resolve pytest's own types (NoReturn on skip)."""
    if value is None:
        raise pytest.skip.Exception(why)
    return value


def gitleaks_available() -> bool:
    return gitleaks_cmd() is not None


def real_ruff(cwd: Path) -> str | None:
    """A real ruff binary from uv's cache (the one a project's `uv add --dev ruff` installs)."""
    done = subprocess.run(
        ["uv", "run", "--no-project", "--with", "ruff", "python", "-c"]
        + ["import ruff; print(ruff.find_ruff_bin())"],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=clean_env(),
        check=False,
        timeout=600,
    )
    path = done.stdout.strip()
    return path if done.returncode == 0 and path and Path(path).is_file() else None


def real_ty(cwd: Path) -> str | None:
    """A real ty binary from uv's cache (the one a project's `uv add --dev ty` installs)."""
    done = subprocess.run(
        ["uv", "run", "--no-project", "--with", "ty", "python", "-c"]
        + ["import ty; print(ty.find_ty_bin())"],
        capture_output=True,
        text=True,
        cwd=cwd,
        env=clean_env(),
        check=False,
        timeout=600,
    )
    path = done.stdout.strip()
    return path if done.returncode == 0 and path and Path(path).is_file() else None


STUB_PROJECT = (  # scripts/project.py for P5 tests: the matrix exits MATRIX_EXIT (default 0)
    '# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n# ///\n'
    "import os\nimport sys\n\n"
    "sys.exit(int(os.environ.get('MATRIX_EXIT', '0')) if sys.argv[1:] == ['selftest'] else 0)\n"
)


# ---------------------------------------------------------------------------------------------
# P0: modes


def test_scaffold_for_an_empty_folder_a_lone_claude_folder_and_an_empty_repo(
    tmp_path: Path,
) -> None:
    folder = tmp_path / "hello"
    folder.mkdir()
    code, facts = preflight_json(folder)
    assert (code, facts["mode"]) == (0, "SCAFFOLD")
    write(folder, {".claude/settings.json": "{}\n", "README.md": "# hello\n"})
    code, facts = preflight_json(folder)
    assert (code, facts["mode"]) == (0, "SCAFFOLD")  # N24: a lone .claude/ never counts
    git(folder, "init", "-q", "-b", "main")
    code, facts = preflight_json(folder)
    assert (code, facts["mode"]) == (0, "SCAFFOLD")


def test_adopt_for_a_repo_with_code_even_with_a_claude_folder(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "app", {**PY, "app.py": "print(1)\n", ".claude/settings.json": "{}\n"}
    )
    code, facts = preflight_json(repo)
    assert (code, facts["mode"]) == (0, "ADOPT")


def test_extend_when_the_manifest_exists_and_it_wins_over_legacy_folders(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "app",
        {
            **PY,
            "app.py": "x = 1\n",
            ".project.toml": 'standard = "project-init v3"\n',
            ".gitignore": "sessions/\n",
        },
    )
    (repo / "sessions").mkdir()
    code, facts = preflight_json(repo)
    assert (code, facts["mode"], facts["mode_evidence"]) == (0, "EXTEND", [".project.toml"])


def test_extend_plus_v2_migrate_from_the_v2_stamp(tmp_path: Path) -> None:
    readme = "# project_memory\n\nsome text\n\nStandard: project-init v2\n"
    repo = make_repo(
        tmp_path / "app", {**PY, "app.py": "x = 1\n", "project_memory/README.md": readme}
    )
    code, facts = preflight_json(repo)
    assert (code, facts["mode"]) == (0, "EXTEND+v2-migrate")


@pytest.mark.parametrize(
    "legacy",
    [
        "project_memory/sessions/s.jsonl",
        "project_memory/pending/p.json",
        "project_memory/summaries/x.md",
        "project_memory/chromadb/db.sqlite3",
        "project_memory/accumulated_knowledge.json",
        ".claude/hooks/project-session-start.py",
    ],
)
def test_migrate_for_every_legacy_marker(tmp_path: Path, legacy: str) -> None:
    stores = tuple(f"project_memory/{d}/" for d in ("sessions", "pending", "summaries", "chromadb"))
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n", ".gitignore": "\n".join(stores)})
    write(repo, {legacy: "{}\n"})
    if not legacy.startswith(stores):  # v1 gitignored its stores and committed the rest
        git(repo, "add", legacy)
        git(repo, "commit", "-q", "-m", "chore: legacy")
    code, facts = preflight_json(repo)
    assert (code, facts["mode"]) == (0, "MIGRATE")
    evidence = facts["mode_evidence"]
    assert isinstance(evidence, list)
    assert any(legacy.startswith(e) for e in evidence)
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    lines = text.splitlines()
    assert lines[0].startswith("mode ........ MIGRATE")
    assert lines[1] == "evidence .... " + ", ".join(str(e) for e in evidence)


# ---------------------------------------------------------------------------------------------
# P0: stops


def test_a_dirty_tree_stops_but_an_untracked_lockfile_does_not(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n"})
    write(repo, {"uv.lock": "version = 1\n"})
    code, facts = preflight_json(repo)
    assert (code, stop_ids(facts), facts["untracked_lockfiles"]) == (0, [], ["uv.lock"])
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "untracked: uv.lock (lockfile: will commit)" in text

    write(repo, {"app.py": "x = 2\n"})
    code, facts = preflight_json(repo)
    assert (code, stop_ids(facts)) == (1, ["dirty"])
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "STOP ........ dirty tree: app.py" in text
    assert "1. Stop so you can commit or stash (Recommended:" in text
    assert "2. Run --plan only." in text


def test_an_upstream_both_ahead_and_behind_stops(tmp_path: Path) -> None:
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(origin))
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n"})
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "push", "-q", "-u", "origin", "main")
    other = tmp_path / "other"
    git(tmp_path, "clone", "-q", str(origin), str(other))
    write(other, {"b.py": "y = 1\n"})
    git(other, "add", "b.py")
    git(other, "commit", "-q", "-m", "feat: b")
    git(other, "push", "-q", "origin", "main")

    write(repo, {"c.py": "z = 1\n"})
    git(repo, "add", "c.py")
    git(repo, "commit", "-q", "-m", "feat: c")
    code, facts = preflight_json(repo)
    assert (code, stop_ids(facts), facts["ahead"]) == (0, [], 1)  # ahead only: fine

    git(repo, "fetch", "-q", "origin")
    code, facts = preflight_json(repo)
    assert (code, stop_ids(facts), facts["ahead"], facts["behind"]) == (1, ["diverged"], 1, 1)


def test_an_origin_with_another_root_commit_stops(tmp_path: Path) -> None:
    stranger = make_repo(tmp_path / "stranger", {"s.py": "s = 1\n"})
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n"})
    git(repo, "remote", "add", "origin", str(stranger))
    git(repo, "fetch", "-q", "origin")
    code, facts = preflight_json(repo)
    assert (code, stop_ids(facts)) == (1, ["shared-origin"])
    stops = facts["stops"]
    assert isinstance(stops, list)
    assert "root commit differs" in str(stops[0]["what"])


def test_an_origin_another_local_repo_uses_stops_like_helios_demo(tmp_path: Path) -> None:
    work = tmp_path / "work"
    helios = make_repo(work / "helios", {"app.py": "x = 1\n"})
    git(helios, "remote", "add", "origin", "git@github.com:someone/helios.git")
    demo = make_repo(work / "helios-demo", {"demo.py": "y = 1\n"})
    git(demo, "remote", "add", "origin", "https://github.com/someone/helios")
    result = init(
        "preflight",
        str(demo),
        "--offline",
        "--vault",
        str(tmp_path / "v"),
        "--search-root",
        str(work),
    )
    assert result.returncode == 1, result.stdout
    assert f"another local repo uses the same origin: {helios}" in result.stdout
    assert "1. Treat this as its own repo and re-point origin yourself." in result.stdout
    assert "2. Stop (Recommended: its origin belongs to helios)." in result.stdout


def test_root_level_sessions_and_pending_packages_are_code_not_legacy(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "webapp",
        {
            **PY,
            "app.py": "x = 1\n",
            "sessions/__init__.py": "SESSIONS = 1\n",
            "pending/__init__.py": "PENDING = 1\n",
            "summaries/__init__.py": "",
        },
    )
    code, facts = preflight_json(repo)
    assert (code, facts["mode"]) == (0, "ADOPT")
    result = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / "archive"),
        "--quarantine-root",
        str(tmp_path / "q"),
    )
    assert result.returncode == 0, result.stderr
    assert "nothing moved" in result.stdout
    assert git(repo, "status", "--porcelain") == ""
    assert not (tmp_path / "q").exists() and not (tmp_path / "archive").exists()


def test_the_origin_owner_is_named_by_the_origin_s_repo_name(tmp_path: Path) -> None:
    work = tmp_path / "work"
    both = {"pyproject.toml": '[project]\nname = "helios"\n'}  # a fork keeps the project name
    helios = make_repo(work / "helios", {**both, "app.py": "x = 1\n"})
    git(helios, "remote", "add", "origin", "git@github.com:someone/helios.git")
    demo = make_repo(work / "helios-demo", {**both, "demo.py": "y = 1\n"})
    git(demo, "remote", "add", "origin", "https://github.com/someone/helios")
    args = ("--offline", "--vault", str(tmp_path / "v"), "--search-root", str(work))
    result = init("preflight", str(demo), *args)
    assert result.returncode == 1, result.stdout
    assert "2. Stop (Recommended: its origin belongs to helios)." in result.stdout
    result = init("preflight", str(helios), *args)
    assert result.returncode == 0, result.stdout  # helios owns its origin: a note, no stop
    assert "stops ....... none" in result.stdout
    assert f"another local repo also uses this origin: {demo}" in result.stdout
    assert "belongs to helios-demo" not in result.stdout

    other = make_repo(work / "tool", {"t.py": "t = 1\n"})
    git(other, "remote", "add", "origin", "https://github.com/someone/unrelated.git")
    again = make_repo(work / "tool-copy", {"t.py": "t = 2\n"})
    git(again, "remote", "add", "origin", "https://github.com/someone/unrelated.git")
    result = init("preflight", str(again), *args)
    assert result.returncode == 1
    assert "origin's name, unrelated, matches no single checkout" in result.stdout


def test_code_without_a_commit_stops(tmp_path: Path) -> None:
    folder = tmp_path / "loose"
    write(folder, {**PY, "main.py": "print(1)\n"})
    code, facts = preflight_json(folder)
    assert (code, facts["mode"], stop_ids(facts)) == (1, "ADOPT", ["no-commit"])


def test_a_folder_inside_another_repo_stops(tmp_path: Path) -> None:
    outer = make_repo(tmp_path / "outer", {"a.py": "a = 1\n"})
    inner = outer / "inner"
    inner.mkdir()
    code, facts = preflight_json(inner)
    assert (code, facts["mode"], stop_ids(facts)) == (1, "SCAFFOLD", ["nested"])


def test_only_origin_counts_and_dead_remotes_are_flagged(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n"})
    git(repo, "remote", "add", "upstream", str(tmp_path / "gone.git"))
    code, facts = preflight_json(repo)
    assert (code, facts["origin"], facts["dead_remotes"]) == (0, None, ["upstream"])
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert f"upstream {tmp_path / 'gone.git'} (dead)  (only origin counts)" in text


# ---------------------------------------------------------------------------------------------
# P0: facts and signals


def test_lane_named_branches_from_before_adoption_are_a_note(tmp_path: Path) -> None:
    """Run B: an unmerged v2 chore/project-init, or an old feat/ branch, in a repo not adopted
    yet is a note, never a stop: after G1, project.py's I8 skips a branch that forks before the
    adoption. The adoption's own plan/project-init is not listed; an EXTEND repo gets no note."""
    repo = make_repo(tmp_path / "repo", {**PY, "app.py": "print(1)\n"})
    git(repo, "branch", "fix/merged-long-ago")  # merged: it never blocked anything
    write(repo, {"later.py": "print(2)\n"})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feat: later")
    for branch in ("chore/project-init", "feat/old", "plan/project-init", "wip/other"):
        git(repo, "switch", "-q", "-c", branch, "main~1")
        write(repo, {f"{branch.replace('/', '-')}.txt": "work\n"})
        git(repo, "add", "-A")
        git(repo, "commit", "-q", "-m", f"wip: {branch}")
    git(repo, "switch", "-q", "main")
    code, facts = preflight_json(repo)
    notes = facts["notes"]
    assert isinstance(notes, list)
    found = [str(n) for n in notes if "from before adoption" in str(n)]
    assert found == [
        (
            "lane-named branches from before adoption: chore/project-init, feat/old. They are "
            "not changes: I8 skips a branch that forks before the adoption, and `mise run "
            "status` lists them"
        )
    ], notes
    assert code == 0 and stop_ids(facts) == []
    write(repo, {".project.toml": 'standard = "project-init v3"\n'})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(init): project-init v3")
    _, facts = preflight_json(repo)
    assert facts["mode"] == "EXTEND"
    assert not any("from before adoption" in str(n) for n in listed(facts, "notes"))


def test_signals_come_from_parsed_manifests_only(tmp_path: Path) -> None:
    pyproject = TIPCALC_PYPROJECT.replace(
        'description = "Add your description here"',
        'description = "fastapi-style auth for django and flask users"\n'
        'keywords = ["auth", "fastapi", "sqlalchemy", "docker"]',
    )
    repo = make_repo(
        tmp_path / "tipcalc",
        {
            "pyproject.toml": pyproject,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            "README.md": "uses redis and react\n",
        },
    )
    code, facts = preflight_json(repo)
    assert code == 0
    assert facts["signals"] == {"cli": ["pyproject.toml [project.scripts]"]}
    assert "auth" not in json.dumps(facts["signals"])
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "signals .. cli; no db/api/ui/deploy/pipeline" in text


def test_signals_from_dependencies_and_marker_files(tmp_path: Path) -> None:
    pyproject = TIPCALC_PYPROJECT.replace(
        "dependencies = []", 'dependencies = ["FastAPI>=0.110", "psycopg[binary]>=3", "dbt-core"]'
    )
    repo = make_repo(
        tmp_path / "svc",
        {
            "pyproject.toml": pyproject,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            "Dockerfile": "FROM scratch\n",
            "k8s/app.yaml": "kind: Deployment\n",
            "web/package.json": json.dumps({"dependencies": {"react": "19"}}),
        },
    )
    _, facts = preflight_json(repo)
    signals = facts["signals"]
    assert isinstance(signals, dict)
    assert list(signals) == ["cli", "api", "db", "ui", "deploy", "pipeline"]
    assert signals["api"] == ["pyproject.toml: fastapi"]
    assert signals["db"] == ["pyproject.toml: psycopg"]
    assert signals["ui"] == ["web/package.json: react"]
    assert signals["deploy"] == ["Dockerfile", "k8s/"]
    assert signals["pipeline"] == ["pyproject.toml: dbt-core"]


def test_env_reads_by_ast_scan(tmp_path: Path) -> None:
    src = (
        '"""Mentions os.environ.get("NOT_A_READ") in prose only."""\n'
        "import os\n"
        "from os import getenv\n\n"
        'PERCENT = float(os.environ.get("APP_PERCENT", "15"))\n'
        'LEVEL = getenv("APP_LEVEL")\n'
        'TOKEN = os.environ["APP_TOKEN"]\n'
        'STREAM = float(os.environ.get("LLM_STREAM_TOKEN_TIMEOUT_S", "30"))\n'
        'KEY_FILE = os.getenv("API_KEY_FILE", "/run/key")\n'
        'HOME = os.environ["HOME"]\n'
        'WHERE = os.getenv("PATH")\n'
        'PASSWORD = os.getenv("DB_PASSWORD", "password123")\n'
        'EMPTY = os.getenv("APP_EMPTY", "")\n'
    )
    repo = make_repo(
        tmp_path / "app",
        {"src/app/__init__.py": src, "tests/test_app.py": 'import os\nos.getenv("TEST_ONLY")\n'},
    )
    _, facts = preflight_json(repo)
    reads = {str(r["name"]): r for r in listed(facts, "env_reads")}
    assert sorted(reads) == [
        "API_KEY_FILE",
        "APP_EMPTY",
        "APP_LEVEL",
        "APP_PERCENT",
        "APP_TOKEN",
        "DB_PASSWORD",
        "LLM_STREAM_TOKEN_TIMEOUT_S",
    ]  # HOME and PATH are the OS's, not the app's contract
    assert (reads["APP_PERCENT"]["type"], reads["APP_PERCENT"]["default"]) == ("float", "15")
    assert reads["APP_PERCENT"]["kind"] == "knob"
    assert (reads["APP_TOKEN"]["kind"], reads["APP_TOKEN"]["required"]) == ("secret", True)
    assert reads["APP_PERCENT"]["where"] == ["src/app/__init__.py:5"]
    assert reads["LLM_STREAM_TOKEN_TIMEOUT_S"]["kind"] == "knob"  # read through float()
    assert reads["API_KEY_FILE"]["kind"] == "knob"  # a path to a secret, not the secret
    assert (reads["DB_PASSWORD"]["kind"], reads["DB_PASSWORD"]["default"]) == (
        "secret",
        "(masked)",
    )
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "password123" not in text
    assert "DB_PASSWORD (secret, str, default (masked);" in text
    assert 'APP_EMPTY (knob, str, default "";' in text
    assert "OS variables read, not part of the env contract: HOME, PATH" in text


def test_human_authors_set_the_tier_and_bots_do_not_count(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "app", {"a.py": "a = 1\n"})
    bot = clean_env(
        GIT_AUTHOR_NAME="dependabot[bot]", GIT_AUTHOR_EMAIL="bot@users.noreply.github.com"
    )
    write(repo, {"b.py": "b = 1\n"})
    git(repo, "add", "b.py", env=bot)
    git(repo, "commit", "-q", "-m", "chore: bump", env=bot)
    _, facts = preflight_json(repo)
    assert (facts["tier"], len(listed(facts, "authors"))) == ("solo", 1)

    human = clean_env(GIT_AUTHOR_NAME="Second Human", GIT_AUTHOR_EMAIL="second@example.invalid")
    write(repo, {"c.py": "c = 1\n"})
    git(repo, "add", "c.py", env=human)
    git(repo, "commit", "-q", "-m", "feat: c", env=human)
    _, facts = preflight_json(repo)
    assert (facts["tier"], len(listed(facts, "authors"))) == ("team", 2)


def test_one_person_under_several_emails_counts_once(tmp_path: Path) -> None:
    repo = make_repo(tmp_path / "app", {"a.py": "a = 1\n"})
    web = clean_env(
        GIT_AUTHOR_NAME="Tester Web", GIT_AUTHOR_EMAIL="1234+TestAuthor@users.noreply.github.com"
    )
    write(repo, {"w.py": "w = 1\n"})
    git(repo, "add", "w.py", env=web)
    git(repo, "commit", "-q", "-m", "docs: edit on github", env=web)
    _, facts = preflight_json(repo)
    assert (facts["tier"], len(listed(facts, "authors"))) == ("solo", 1)  # D9: one GitHub web edit

    identities = [
        ("John Doe", "DoeJohn@users.noreply.github.com"),
        ("john doe", "j.doe@example.invalid"),
        ("John Doe", "j.doe@example.invalid"),
        ("John Q", "10000001+DoeJohn@users.noreply.github.com"),
        ("zeta240", "9zqxmt@privaterelay.example.invalid"),
        ("Claude", "noreply@anthropic.com"),
    ]
    other = make_repo(tmp_path / "helios", {"m.py": "m = 0\n"})
    for i, (name, email) in enumerate(identities):
        who = clean_env(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email)
        write(other, {f"m{i}.py": f"m = {i}\n"})
        git(other, "add", f"m{i}.py", env=who)
        git(other, "commit", "-q", "-m", f"feat: m{i}", env=who)
    _, facts = preflight_json(other)
    # Test Author, the John identities as one person, zeta240; Claude is a bot
    assert (facts["tier"], len(listed(facts, "authors"))) == ("team", 3)


def test_gh_failures_are_tolerated(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gh"
    fake.write_text(
        '#!/bin/sh\n[ "$1" = --version ] && { echo "gh version 9.9.9"; exit 0; }\n'
        'echo "gh: boom" >&2\nexit 1\n',
        encoding="utf-8",
    )
    fake.chmod(0o755)
    repo = make_repo(tmp_path / "app", {**PY, "app.py": "x = 1\n"})
    env = clean_env(PATH=f"{bin_dir}:{os.environ['PATH']}")
    result = init("preflight", str(repo), "--json", "--vault", str(tmp_path / "v"), env=env)
    assert result.returncode == 0, result.stderr
    facts = json.loads(result.stdout)
    assert facts["tools"]["gh"] == "9.9.9"
    assert facts["gh"] == {"status": "not logged in"}


def test_preflight_prints_the_design_block_for_tipcalc(tipcalc: Path, tmp_path: Path) -> None:
    before = tree_hash(tipcalc)
    result = init(
        "preflight",
        str(tipcalc),
        "--offline",
        "--vault",
        str(tmp_path / "vault"),
        "--search-root",
        str(tmp_path / "none"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert lines[0] == (
        "mode ........ ADOPT            git ..... master, 1 commit, no origin, "
        "untracked: uv.lock (lockfile: will commit)"
    )
    assert lines[1] == (
        "stack ....... python/uv, cli (tipcalc = tipcalc:main)       "
        "signals .. cli; no db/api/ui/deploy/pipeline"
    )
    assert lines[2].startswith("tools ....... mise ")
    assert lines[3] == "vault ....... no kitchen/active/idea named tipcalc"
    assert (
        "TIPCALC_DEFAULT_PERCENT (knob, float, default 15; src/tipcalc/__init__.py:"
        in result.stdout
    )
    assert "stops ....... none" in result.stdout
    assert tree_hash(tipcalc) == before  # P0 is read-only, the index included


def test_vault_matches_are_reported(tmp_path: Path) -> None:
    vault = tmp_path / "vault"
    write(
        vault,
        {"05-projects/kitchen/app/PRD.md": "x\n", "09-ideas/seed.md": "---\nspawned: app\n---\n"},
    )
    repo = make_repo(tmp_path / "app", {"app.py": "x = 1\n"})
    _, facts = preflight_json(repo, "--vault", str(vault))
    assert facts["vault"] == ["05-projects/kitchen/app/", "09-ideas/seed.md"]


# ---------------------------------------------------------------------------------------------
# P1: probe


def test_probe_tipcalc_finds_five_crashes_and_one_pass_and_never_writes_the_repo(
    tipcalc: Path,
) -> None:
    trunk_block = (
        "trunk ....... 1 candidate for ## Trunk in specs/tech-stack.md (a static scan: no code "
        f"ran)\n{REPORT_INDENT}{TIPCALC_TRUNK}\n"
    )
    if not userns():
        result = init("probe", str(tipcalc))
        assert "probe ....... skipped: no user namespaces" in result.stdout
        assert trunk_block in result.stdout  # static: it needs no sandbox
        return
    before = tree_hash(tipcalc)
    result = init("probe", str(tipcalc), "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert (report["status"], report["untouched"]) == ("ran", True)
    assert report["trunk"] == [
        {"glob": "src/tipcalc/__init__.py", "why": TIPCALC_TRUNK.split(": ", 1)[1]}
    ]
    rows = report["rows"]
    passes = [r for r in rows if r["outcome"] == "pass"]
    crashes = [r for r in rows if r["outcome"] == "crash"]
    assert [(r["args"], r["stdout"]) for r in passes] == [(["100"], "tip: 15.0")]
    assert sorted(r["reason"] for r in crashes) == ["IndexError"] + ["ValueError"] * 4
    by_call = {(json.dumps(r["env"]), tuple(r["args"])): r["reason"] for r in crashes}
    assert by_call[("{}", ())] == "IndexError"
    assert by_call[("{}", ("--help",))] == "ValueError"
    assert by_call[("{}", ("abc",))] == "ValueError"
    assert by_call[('{"TIPCALC_DEFAULT_PERCENT": ""}', ("100",))] == "ValueError"
    assert by_call[('{"TIPCALC_DEFAULT_PERCENT": "abc"}', ("100",))] == "ValueError"

    text = init("probe", str(tipcalc)).stdout
    assert "probe ....... (scratch clone, network off)" in text
    # tipcalc's README has no fence: the pass row says its args were a guess
    assert '              tipcalc 100 -> "tip: 15.0" exit 0 (guessed args: no README fence)' in text
    assert (
        "              tipcalc -> IndexError traceback | tipcalc --help -> ValueError | "
        "tipcalc abc -> ValueError"
    ) in text
    assert (
        '              TIPCALC_DEFAULT_PERCENT="" -> ValueError | '
        "TIPCALC_DEFAULT_PERCENT=abc -> ValueError"
    ) in text
    assert text.endswith(trunk_block)
    assert tree_hash(tipcalc) == before


def test_probe_takes_the_happy_path_from_a_readme_fence(tmp_path: Path) -> None:
    if not userns():
        pytest.skip("no user namespaces")
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"README.md": "# tipcalc\n\n```sh\nuv run tipcalc 42.50   # tip: 6.38\n```\n"})
    git(repo, "commit", "-q", "-am", "docs: quickstart")
    result = init("probe", str(repo), "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert (report["happy"], report["happy_source"]) == (["42.50"], "readme")
    passes = [r for r in report["rows"] if r["outcome"] == "pass"]
    assert [(r["args"], r["stdout"]) for r in passes] == [(["42.50"], "tip: 6.38")]
    env_rows = [r for r in report["rows"] if r["source"] == "env"]
    assert {r["args"][0] for r in env_rows} == {"42.50"}


def test_probe_runs_only_help_for_service_shaped_repos(tmp_path: Path) -> None:
    if not userns():
        pytest.skip("no user namespaces")
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"Dockerfile": "FROM scratch\n"})
    git(repo, "add", "Dockerfile")
    git(repo, "commit", "-q", "-m", "build: container")
    result = init("probe", str(repo), "--json")
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["restricted"] is True
    assert [r["args"] for r in report["rows"]] == [["--help"]]


STUBBORN_CHILD = (
    "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(90)"
)
STUBBORN_SRC = f"""import signal
import subprocess
import sys
import time


def main() -> None:
    if sys.argv[1:]:
        print("ok")
        return
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    subprocess.Popen([sys.executable, "-c", {STUBBORN_CHILD!r}])
    time.sleep(90)
"""


def probe_scratch(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    """A TMPDIR of this test's own for init.py, so the probe's scratch folder (its clone, its
    venv, its cases' HOME) sits under it: another test run on the same machine probes under
    another folder, and probe_leftovers() never counts that run's live cases."""
    scratch = tmp_path / "probe-tmp"
    scratch.mkdir()
    return scratch, clean_env(TMPDIR=str(scratch))


def probe_leftovers(scratch: Path) -> list[tuple[int, str]]:
    """Live processes a probe under scratch started: an argv element names scratch (a program
    of the clone's venv), or the environment does (HOME, which every case child inherits).
    Read from /proc, never pgrep -f: a shell whose command text quotes the path never runs
    from it, and argv elements are compared one by one."""
    mark = str(scratch).encode()
    found: list[tuple[int, str]] = []
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or proc.name == str(os.getpid()):
            continue
        try:
            argv = (proc / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        try:
            environ = (proc / "environ").read_bytes().split(b"\0")
        except OSError:
            environ = []
        if any(mark in arg for arg in argv) or any(mark in var for var in environ):
            found.append((int(proc.name), b" ".join(argv).decode(errors="replace")))
    return found


def test_probe_kills_a_script_that_ignores_sigterm_and_its_children(tmp_path: Path) -> None:
    if not userns():
        pytest.skip("no user namespaces")
    pyproject = TIPCALC_PYPROJECT.replace('name = "tipcalc"', 'name = "stubborn"').replace(
        'tipcalc = "tipcalc:main"', 'stubborn = "stubborn:main"'
    )
    repo = make_repo(
        tmp_path / "stubborn",
        {
            "pyproject.toml": pyproject,
            "src/stubborn/__init__.py": STUBBORN_SRC,
            "README.md": "# stubborn\n",
            ".python-version": "3.14\n",  # the probe's python note stays out
        },
    )
    scratch, env = probe_scratch(tmp_path)
    result = init("probe", str(repo), "--json", env=env)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ran", report["reason"]
    rows = report["rows"]
    hung = [r for r in rows if r["args"] == []]
    assert [(r["outcome"], r["reason"]) for r in hung] == [("timeout", "timeout")]
    assert hung[0]["exit"] in (137, -9)  # SIGTERM was ignored: `timeout -k` had to SIGKILL
    assert report["timeouts"] == 1
    assert probe_leftovers(scratch) == []
    assert not list(scratch.glob("project-init-probe-*"))  # the probe removed its folder
    text = init("probe", str(repo), env=env).stdout
    assert "stubborn -> timeout (killed after 10 s)" in text
    assert "timeout traceback" not in text
    tail = text[: text.index("\nsurface ..... ")]  # the static lines come last: surface, trunk
    assert "3 pass, 0 crashes, 1 timeout;" in tail and tail.endswith("repo untouched")


LEAKY_SRC = """import subprocess
import sys


def main() -> None:
    quiet = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}
    subprocess.Popen(["sleep", "317.25"], **quiet)  # a background child, then a normal exit
    subprocess.Popen(["sleep", "318.25"], start_new_session=True, **quiet)  # its own session
    print("ok")
"""


def test_probe_leaves_no_process_behind_after_a_normal_exit(tmp_path: Path) -> None:
    if not userns():
        pytest.skip("no user namespaces")
    pyproject = TIPCALC_PYPROJECT.replace('name = "tipcalc"', 'name = "leaky"').replace(
        'tipcalc = "tipcalc:main"', 'leaky = "leaky:main"'
    )
    repo = make_repo(
        tmp_path / "leaky",
        {"pyproject.toml": pyproject, "src/leaky/__init__.py": LEAKY_SRC, "README.md": "# l\n"},
    )
    scratch, env = probe_scratch(tmp_path)
    try:
        result = init("probe", str(repo), "--json", env=env)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report["status"] == "ran", report["reason"]
        assert {r["outcome"] for r in report["rows"]} == {"pass"}
        assert probe_leftovers(scratch) == []  # both sleeps inherited the cases' HOME
    finally:
        for pid, _ in probe_leftovers(scratch):
            os.kill(pid, signal.SIGKILL)


def test_readme_fences_give_the_happy_paths() -> None:
    module = load_init()
    readme = (
        "# tipcalc\n\n```bash\nmake setup && make doctor\n"
        "uv run tipcalc 42.50          # tip: 6.38\n"
        "TIPCALC_DEFAULT_PERCENT=20 uv run --locked tipcalc 42.50   # tip: 8.5\n"
        "mise run start -- 100\n```\n\ntipcalc 7 outside a fence\n"
    )
    found = module.readme_invocations(readme, "tipcalc", "tipcalc")
    assert found == [
        ({}, ["42.50"]),
        ({"TIPCALC_DEFAULT_PERCENT": "20"}, ["42.50"]),
        ({}, ["100"]),
    ]


# ---------------------------------------------------------------------------------------------
# P1: trunk candidates (v3.1, design A.2): a static scan, no code runs

TRUNK_LINE = re.compile(r"^- (\S+): (\S.*)$")  # design A.1: `- <glob>: <why>`, the why required
SHOP_FILES = {  # a package with fan-in: 8 modules, so a trunk module has 3 importers or more
    "pyproject.toml": '[project]\nname = "shop"\nversion = "0.1.0"\n\n'
    '[project.scripts]\nshop = "shop.cli:main"\n',
    "src/shop/__init__.py": "",
    "src/shop/cli.py": "from shop import config, orders\n\n\ndef main() -> None:\n"
    "    orders.run(config.load())\n",
    "src/shop/config.py": 'import os\n\n\ndef load() -> str:\n    return os.environ.get("SHOP_DB_URL", "")\n',
    "src/shop/db.py": "from .config import load\n",
    "src/shop/orders.py": "from . import db\nfrom .config import load\n",
    "src/shop/cart.py": "from shop import config\nfrom shop.db import load\n",
    "src/shop/money.py": "CENT = 1\n",
    "src/shop/report.py": "import shop.db\nfrom .money import CENT\n",
    "src/shop/schema/orders.sql": "create table orders (id int);\n",
    "tests/test_orders.py": "from shop import db, money\n",  # a test is no importer
    "migrations/env.py": "from shop import db\n",  # outside the package: no importer either
    "migrations/001_init.sql": "create table t (id int);\n",
    "queries/top.sql": "select 1;\n",
    "specs/tech-stack.md": "# Tech stack: shop\n\n## Standing rules\n"
    "- S-1: money is integer cents, in `src/shop/money.py`; secrets are `op://` pointers.\n",
}
SHOP_TRUNK = [
    ("src/shop/cli.py", "the entrypoint of the shop command (shop.cli:main)"),
    ("src/shop/config.py", "imported by 4 of 7 other modules in shop; settings, by its file name"),
    ("src/shop/db.py", "imported by 3 of 7 other modules in shop"),
    ("migrations/**", "migrations: schema changes reach every row"),
    ("queries/**", "SQL files: schema changes reach every row"),
    ("src/shop/schema/**", "the schema: every row follows it"),
    ("src/shop/money.py", "named by standing rule S-1"),
]


def trunk_rows(root: Path) -> list[tuple[str, str]]:
    return [(row.glob, row.why) for row in load_init().trunk_candidates(root)]


def test_trunk_candidates_for_the_tipcalc_fixture() -> None:
    """The one console script's module, and nothing else: tipcalc is one module, it has no
    settings module or schema, and its standing rules name no path."""
    assert trunk_rows(FIXTURES / "tipcalc") == [
        ("src/tipcalc/__init__.py", "the entrypoint of the tipcalc command (tipcalc:main)")
    ]


def test_trunk_candidates_find_entrypoints_fan_in_settings_schema_and_rule_paths(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "shop", SHOP_FILES)
    rows = trunk_rows(repo)
    assert rows == SHOP_TRUNK  # by kind, then by path; a path found twice is one row
    assert trunk_rows(repo) == rows  # stable
    for glob, why in rows:
        assert TRUNK_LINE.match(f"- {glob}: {why}"), glob

    # with an env contract, its `read in` column names the settings modules: a file named like
    # one, or one that holds a pydantic-settings class. A reader that is neither never counts
    contract = (
        "# NAME | kind | type | required | default | notes\n"
        "# SHOP_DB_URL | secret | str | yes | - | op:// pointer; read in src/shop/config.py\n"
        "#SHOP_DB_URL=op://<vault>/<item>/<field>\n"
        "# SHOP_DEBUG | knob | bool | no | false | read in src/shop/knobs.py, src/shop/cli.py\n"
        "#SHOP_DEBUG=false\n"
        "# SHOP_TOKEN | secret | str | no | - | op:// pointer; read in src/shop/knobs.py\n"
    )
    knobs = (
        "from pydantic_settings import BaseSettings\n\n\n"
        "class Knobs(BaseSettings):\n    debug: bool = False\n"
    )
    write(repo, {".env.example": contract, "src/shop/knobs.py": knobs})
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "feat: knobs")
    why = dict(trunk_rows(repo))
    assert why["src/shop/config.py"] == (
        "imported by 4 of 8 other modules in shop; settings read from the env: SHOP_DB_URL"
    )
    assert why["src/shop/knobs.py"] == "settings read from the env: SHOP_DEBUG, SHOP_TOKEN"
    assert why["src/shop/cli.py"] == "the entrypoint of the shop command (shop.cli:main)"


RULE_FILES = {  # standing rules that name code, schema, docs, specs and the env contract
    "pyproject.toml": '[project]\nname = "app"\nversion = "0.1.0"\n',
    "src/app/__init__.py": "",
    "src/app/money.py": "CENT = 1\n",
    "src/app/pay/__init__.py": "",
    "src/app/pay/card.py": "CARD = 1\n",
    "api/schema.graphql": "type Query { a: Int }\n",
    "sql/top.sql": "select 1;\n",
    "templates/page.html": "<p>hi</p>\n",
    ".env.example": "# APP_X | knob | str | no |  | the x\n",
    "README.md": "# app\n",
    "docs/env.md": "# env\n",
    "docs/api.py": "EXAMPLE = 1\n",
    "specs/README.md": "# how\n",
    "specs/capabilities/cli.md": "# Capability: cli\n",
    "project_memory/lessons.md": "# lessons\n",
    "proof/2026-01-02-x/README.md": "# Proof\n",
    "proof/2026-01-02-x/G1-run-x.txt": "x\n",
    "specs/tech-stack.md": "# Tech stack: app\n\n## Standing rules\n"
    "- S-1: every env read has its row in `.env.example`, as `docs/env.md` and `README.md` say.\n"
    "- S-2: specs live in `specs/` and `specs/README.md`, lessons in "
    "`project_memory/lessons.md`, proof in `proof/`, examples in `docs/`.\n"
    "- S-3: money is cents, in `src/app/money.py` and `src/app/pay/`; queries in `sql/`; the "
    "API in `api/schema.graphql`; pages in `templates/`.\n",
}


def test_standing_rules_propose_code_and_schema_paths_only(tmp_path: Path) -> None:
    """A standing rule names the env contract, the docs and the specs as often as code. Only
    code and schema paths become candidates (the M18 review): the env contract, markdown and
    text docs, docs/, specs/, project_memory/ and proof/ never do. In run F, `.env.example`
    became trunk that way, and every flag change then touched trunk."""
    repo = make_repo(tmp_path / "app", RULE_FILES)
    files = set(git(repo, "ls-files").split())
    assert load_init().rule_candidates(repo, files) == [
        ("api/schema.graphql", "named by standing rule S-3"),
        ("sql/**", "named by standing rule S-3"),
        ("src/app/money.py", "named by standing rule S-3"),
        ("src/app/pay/**", "named by standing rule S-3"),
    ]
    globs = [glob for glob, _ in trunk_rows(repo)]
    assert globs == ["sql/**", "api/schema.graphql", "src/app/money.py", "src/app/pay/**"]


def test_fan_in_needs_a_quarter_of_the_package_and_at_least_three(tmp_path: Path) -> None:
    """16 modules: a trunk module has max(3, 25% of 16) = 4 importers. Imports resolve in
    every form: absolute, `from . import x`, `from .x import y`, `import pkg.x as y`."""
    files = {"src/big/__init__.py": "", "src/big/hub.py": "", "src/big/near.py": ""}
    files |= {f"src/big/m{i}.py": "" for i in range(13)}
    files["src/big/m0.py"] = "from big import hub\n"
    files["src/big/m1.py"] = "from . import hub\n"
    files["src/big/m2.py"] = "import big.hub as h\n"
    files["src/big/m3.py"] = "from .hub import x\nfrom big.hub import y\n"  # one importer
    files["src/big/m4.py"] = "from .near import x\n"
    files["src/big/m5.py"] = "from big.near import x\n"
    files["src/big/m6.py"] = "import big.near\nfrom ... import far\n"  # past the top: ignored
    assert trunk_rows(make_repo(tmp_path / "big", files)) == [
        ("src/big/hub.py", "imported by 4 of 15 other modules in big")
    ]


def test_fan_in_needs_at_most_ten_importers_in_a_big_package(tmp_path: Path) -> None:
    """48 modules: 25% would be 12, but 10 importers are enough (orca's core/config.py has 38
    importers in a package where 25% is more than that). 9 are not. As in orca, a stray
    src/__init__.py leaves src/ the import root, and an import through `src.` counts too."""
    files = {"src/__init__.py": "", "src/wide/__init__.py": "", "src/wide/hub.py": ""}
    files["src/wide/near.py"] = ""
    files |= {f"src/wide/m{i:02}.py": "" for i in range(45)}
    for i in range(10):
        files[f"src/wide/m{i:02}.py"] = "from wide import hub\n"
    files["src/wide/m09.py"] = "from src.wide.hub import x\n"
    for i in range(10, 19):
        files[f"src/wide/m{i:02}.py"] = "from . import near\n"
    assert trunk_rows(make_repo(tmp_path / "wide", files)) == [
        ("src/wide/hub.py", "imported by 10 of 47 other modules in wide")
    ]


def test_a_settings_module_by_name_is_trunk_at_the_package_root_or_shared(
    tmp_path: Path,
) -> None:
    """With no env contract, a config.py or settings.py counts at the package root, or when 2
    modules outside its own folder import it. A per-source config that only its own folder
    imports (orca's sources/*/config.py) is leaf. sources/ has no __init__.py: a namespace
    folder inside feeds, so feeds.sources.<name> is still the feeds package."""
    files = {
        "src/feeds/__init__.py": "",
        "src/feeds/settings.py": "TIMEOUT = 5\n",  # the package root: trunk, importers or not
        "src/feeds/api.py": "from feeds.core import config\n",
        "src/feeds/core/__init__.py": "",
        "src/feeds/core/config.py": "URL = 'x'\n",
        "src/feeds/core/client.py": "from .config import URL\n",  # inside core/: no count
    }
    for name in ("boe", "cma", "gaca"):
        files[f"src/feeds/sources/{name}/__init__.py"] = ""
        files[f"src/feeds/sources/{name}/config.py"] = "PAGE = 1\n"
        files[f"src/feeds/sources/{name}/fetch.py"] = "from .config import PAGE\n"
        files[f"src/feeds/sources/{name}/parse.py"] = f"from feeds.sources.{name} import config\n"
    files["src/feeds/sources/boe/fetch.py"] += "from feeds.core.config import URL\n"
    files["src/feeds/sources/gaca/parse.py"] += "from ..cma import config\n"  # one outside: leaf
    rows = trunk_rows(make_repo(tmp_path / "feeds", files))
    assert rows == [
        ("src/feeds/core/config.py", "settings, by its file name"),
        ("src/feeds/settings.py", "settings, by its file name"),
    ]


def test_no_trunk_candidates_says_so() -> None:
    lines = load_init().trunk_lines([])
    assert lines == [
        (
            "trunk ....... no candidates (a static scan found no console script, fan-in module, "
            "settings module or schema folder): P2 writes the ## Trunk section empty"
        )
    ]


def test_the_probe_report_lists_the_trunk_candidates(tmp_path: Path) -> None:
    """--plan prints P0 and P1: the candidates show there, in the section's own line format,
    whether or not the sandbox could run anything."""
    repo = make_repo(tmp_path / "shop", SHOP_FILES)
    before = tree_hash(repo)
    result = init("probe", str(repo))
    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.splitlines()
    head = lines.index(
        "trunk ....... 7 candidates for ## Trunk in specs/tech-stack.md (a static scan: no code "
        "ran)"
    )
    assert lines[head + 1 :] == [f"{REPORT_INDENT}- {g}: {w}" for g, w in SHOP_TRUNK]
    report = json.loads(init("probe", str(repo), "--json").stdout)
    assert report["trunk"] == [{"glob": g, "why": w} for g, w in SHOP_TRUNK]
    assert tree_hash(repo) == before


def surface_repo(root: Path, dependencies: list[str], scripts: bool) -> Path:
    """A repo whose pyproject.toml declares these runtime dependencies, with or without a
    console script."""
    deps = ", ".join(f'"{d}"' for d in dependencies)
    text = f'[project]\nname = "app"\nversion = "0.1.0"\ndependencies = [{deps}]\n'
    if scripts:
        text += '\n[project.scripts]\napp = "app:main"\n'
    return make_repo(
        root, {"pyproject.toml": text, "src/app/__init__.py": "def main() -> None: ...\n"}
    )


def test_the_probe_names_the_ui_surface_and_its_proof_setup(tmp_path: Path) -> None:
    """Design C.2: P1 names the repo's surface from its declared runtime dependencies, with the
    list project.py's UI warning reads (never a copy of it): a web UI framework, a TUI
    framework, or console scripts only. P7's punch list names the matching proof setup."""
    module = load_init()
    spec = importlib.util.spec_from_file_location(
        "project_py_ui", SKILL / "templates/scripts/project.py"
    )
    assert spec is not None and spec.loader is not None
    project = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = project
    spec.loader.exec_module(project)
    kinds = module.ui_frameworks()
    assert set(kinds) == set(project.UI_FRAMEWORKS)
    assert kinds["streamlit"] == "web" and kinds["textual"] == "terminal"
    cases = [
        ("web", ["Streamlit>=1.40"], True, "web", "mise run proof -- setup web"),
        ("tui", ["textual"], False, "terminal", "mise run proof -- setup terminal"),
        ("cli", ["httpx"], True, "cli", ""),
        ("api", ["fastapi"], False, "none", ""),
    ]
    for name, deps, scripts, kind, setup in cases:
        repo = surface_repo(tmp_path / name, deps, scripts)
        surface = module.ui_surface(repo)
        assert (surface.kind, surface.setup) == (kind, setup), name
        items = module.publish_punch_list(repo, {}, False)
        assert [i for i in items if "proof -- setup" in i] == (
            [f"{setup} ({surface.evidence}): the capture tools for its proof"] if setup else []
        ), items
    web = module.ui_surface(tmp_path / "web")
    assert web.evidence == "a web UI: streamlit in pyproject.toml"
    result = init("probe", str(tmp_path / "web"))
    assert (
        "surface ..... a web UI: streamlit in pyproject.toml; proof by screenshot and video "
        "(P7: mise run proof -- setup web)"
    ) in result.stdout, result.stdout
    report = json.loads(init("probe", str(tmp_path / "cli"), "--json").stdout)
    assert report["surface"] == {
        "kind": "cli",
        "evidence": "console scripts only: app",
        "setup": "",
    }
    text = init("probe", str(tmp_path / "cli")).stdout
    assert "surface ..... console scripts only: app; proof by run, which needs no setup" in text


def test_the_tech_stack_template_has_a_trunk_section_p2_fills() -> None:
    """The product template: a `## Trunk` section with a one-line comment on its format and a
    placeholder line, so P2's placeholder grep fails until the talk answer replaces it. A
    tech-stack.md made from it needs no v3.1 upgrade item."""
    text = (PRODUCT_TEMPLATES / "tech-stack.md").read_text(encoding="utf-8")
    body = text.split("\n## Trunk\n", 1)[1].split("\n## ", 1)[0].strip().splitlines()
    comment, *entries = body
    assert comment.startswith("<!-- ") and comment.endswith(" -->")
    assert "- <glob>: <why>" in comment and "--gate-change" in comment
    assert entries == ["- {GLOB}: {WHY_IT_IS_TRUNK}"]
    assert PLACEHOLDER.search(entries[0])
    filled = text.replace(entries[0], TIPCALC_TRUNK)
    assert TRUNK_LINE.match(TIPCALC_TRUNK)
    module = load_init()
    assert module.has_trunk_section(filled)
    assert not module.has_trunk_section(TECH_STACK.split("\n## Trunk\n", 1)[0])


def test_a_launch_lane_stays_chg_whatever_its_size() -> None:
    """A launch-<slug> lane removes a flag's scaffolding and turns on behaviour already specified
    and proven, so Q7's scenario count does not apply to it and it never ratchets to feat (the
    M18 review: run E's launch touched 8 scenarios). The launch text, the lanes section of the
    process doc and the sdd skill's ratchet rule all say so."""
    sdd = SKILL / "templates" / "skills" / "sdd"
    lane = (sdd / "launch.md").read_text(encoding="utf-8").split("## 5. The launch lane", 1)[1]
    assert "ratchet" not in lane.lower() and "Q7 does not apply" in lane, lane
    readme = (SKILL / "templates" / "specs-README.md").read_text(encoding="utf-8")
    lanes = readme.split("\n## Lanes\n", 1)[1].split("\n## ", 1)[0]
    exempt = [line for line in lanes.splitlines() if "launch-<slug>" in line and "Q7" in line]
    assert len(exempt) == 1 and exempt[0].startswith("- "), lanes
    skill = (sdd / "SKILL.md").read_text(encoding="utf-8")
    ratchet = skill.split("**Ratchet.**", 1)[1].split("\n\n", 1)[0]
    assert "launch-<slug>" in ratchet and "never ratchets" in ratchet, ratchet


def test_a_scaffold_asks_the_trunk_question_after_p3_makes_the_entrypoint(tmp_path: Path) -> None:
    """SCAFFOLD talks before any code exists, so P2 has no candidates. But P3's `uv init
    --package` makes one console script, and an entrypoint is trunk (design A.2). The M18
    acceptance run found a scaffold's section left empty that way. So P3 runs the probe's
    static scan once the scaffold is committed, and the Trunk question takes its candidate."""
    root = tmp_path / "hello"
    root.mkdir()
    made = subprocess.run(
        ["uv", "init", "--package", "--name", "hello", "--vcs", "none", "--no-workspace", "."],
        cwd=root,
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )
    assert made.returncode == 0, made.stdout + made.stderr
    assert trunk_rows(root) == [
        ("src/hello/__init__.py", "the entrypoint of the hello command (hello:main)")
    ]
    scaffold = (SKILL / "phases" / "3-scaffold.md").read_text(encoding="utf-8")
    block = scaffold.split("## SCAFFOLD: an empty folder\n", 1)[1].split("\n## ", 1)[0]
    assert "init.py probe" in block and "## Trunk" in block, block
    talk = (SKILL / "phases" / "2-talk.md").read_text(encoding="utf-8")
    trunk = talk.split("- **The Trunk section**", 1)[1].split("\n- **", 1)[0]
    assert "3-scaffold.md" in trunk and "(SCAFFOLD has no code yet), skip" not in trunk, trunk


# ---------------------------------------------------------------------------------------------
# P4: render


def test_render_then_check_reports_zero_drift(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    hashes = generated(repo)
    for rel, recorded in hashes.items():
        data = (repo / rel).read_bytes()
        assert recorded == "sha256:" + hashlib.sha256(data).hexdigest(), rel
    for rel in TEXT_RENDERS:
        text = (repo / rel).read_text(encoding="utf-8")
        assert not PLACEHOLDER.search(text), rel
    assert set(hashes) >= {
        "mise.toml",
        ".claude/settings.json",
        ".env.example",
        ".gitignore",
        ".gitattributes",
        ".gitleaks.toml",
        ".githooks/pre-commit",
        ".githooks/commit-msg",
        ".githooks/pre-push",
        ".githooks/reference-transaction",
        "scripts/project.py",
        "tests/conftest.py",
        "project_memory/README.md",
        ".claude/skills/sdd/SKILL.md",
        "pyproject.toml",
        "specs/README.md",
    }
    assert not (repo / ".github").exists()  # no origin: no CI
    assert "AGENTS.md" not in hashes and not (repo / "AGENTS.md").exists()  # P6 writes it
    for hook in ("pre-commit", "commit-msg", "pre-push", "reference-transaction"):
        assert os.access(repo / ".githooks" / hook, os.X_OK)
    assert "D=main;" in (repo / ".githooks/reference-transaction").read_text(encoding="utf-8")
    mise = (repo / "mise.toml").read_text(encoding="utf-8")
    assert 'run = "uv run --locked tipcalc"' in mise
    assert "[tasks.release]" not in mise  # distribution none
    assert "who may merge" not in (repo / "project_memory/README.md").read_text(encoding="utf-8")
    env_example = (repo / ".env.example").read_text(encoding="utf-8")
    # the file that reads it, with no line number: that goes stale at the first edit above it
    row = "# TIPCALC_DEFAULT_PERCENT | knob | float | no | 15 | read in src/tipcalc/__init__.py\n"
    assert row in env_example
    assert "\n#TIPCALC_DEFAULT_PERCENT=15\n" in env_example

    pyproject = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["description"] == VALUES["DESCRIPTION"]
    tool = pyproject["tool"]
    assert tool["ruff"]["lint"]["extend-select"] == ["S", "ANN"]
    assert tool["ruff"]["extend-exclude"] == ["scripts/project.py", "tests/conftest.py"]
    assert tool["pytest"]["ini_options"]["markers"] == ["spec(*ids): scenario ids this test proves"]
    assert tool["git-cliff"]["bump"]["features_always_bump_minor"] is True
    ignore = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ignore.index("!.env.example") == ignore.index(".env.*") + 1
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert (manifest["standard"], manifest["default_branch"], manifest["origin_url"]) == (
        "project-init v3",
        "main",
        "",
    )
    assert manifest["paths"] == {"src": ["src"], "tests": ["tests"]}
    assert manifest["signals"] == {"cli": "pyproject.toml [project.scripts]"}
    assert manifest["server_protection"] == "none: no GitHub remote"
    # retried later; the note names the P4 step that makes the venv in every mode (Run C: a v2
    # repo has ruff and ty in its dev group but no .venv, so no `uv add` makes one)
    assert manifest["ruff_baseline"] == (
        "skipped: no .venv/bin/ruff yet (P4 runs `uv sync` before render)"
    )
    assert manifest["ty_baseline"] == (
        "skipped: no .venv/bin/ty yet (P4 runs `uv sync` before render)"
    )
    history = manifest["gitleaks_baseline"]
    assert history == "none: history is clean" or history.startswith("skipped: gitleaks")
    assert set(manifest["seeded"]) == {"project_memory/lessons.md", DECISIONS_KEEP}
    assert (
        (repo / "project_memory/lessons.md")
        .read_text(encoding="utf-8")
        .startswith("<!-- lessons.md: what surprised us")
    )
    assert (repo / DECISIONS_KEEP).is_file()
    assert not (repo / "project_memory/team.md").exists()  # solo: no team files (D9)

    check = render(repo, "--check")
    assert check.returncode == 0, check.stdout
    assert "render --check: 0 drift" in check.stdout
    # Run D: every file matches, yet no `mise install` ran here, so no git gate is on
    assert "gates ....... core.hooksPath is unset, not .githooks: the git gates are off" in (
        check.stdout
    )
    assert check.stdout.rstrip().endswith("; the git gates are off here")
    git(repo, "config", "core.hooksPath", ".githooks")
    assert "the git gates are off" not in render(repo, "--check").stdout

    stamps = {rel: (repo / rel).stat().st_mtime_ns for rel in [*hashes, ".project.toml"]}
    again = render(repo)
    assert again.returncode == 0, again.stdout
    assert again.stdout.strip().endswith("render: 0 changes")
    assert {rel: (repo / rel).stat().st_mtime_ns for rel in stamps} == stamps


def test_an_unchanged_render_is_upgraded_silently(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    result = render(repo, values={"ENTRY": "tipcalc --verbose"})
    assert result.returncode == 0, result.stdout
    assert re.search(r"^  upgrade +mise\.toml$", result.stdout, re.MULTILINE)
    assert "(yours)" not in result.stdout
    mise = (repo / "mise.toml").read_text(encoding="utf-8")
    assert 'run = "uv run --locked tipcalc --verbose"' in mise
    assert render(repo, "--check").returncode == 0  # the new value persists in [values]


def test_an_unfilled_placeholder_refuses_and_writes_nothing(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    no_scripts = TIPCALC_PYPROJECT.replace('[project.scripts]\ntipcalc = "tipcalc:main"\n', "")
    (repo / "pyproject.toml").write_text(no_scripts, encoding="utf-8")
    before = tree_hash(repo)
    result = render(repo)
    assert result.returncode == 1, result.stdout
    assert "render: refused, placeholders left unfilled (nothing written):" in result.stdout
    entry = r"^  ENTRY +in mise\.toml +\(no \[project\.scripts\]"
    assert re.search(entry, result.stdout, re.MULTILINE)
    description = r"^  DESCRIPTION +in pyproject\.toml  \(specs/mission\.md has no one-liner"
    assert re.search(description, result.stdout, re.MULTILINE)
    assert "START_EXAMPLE" not in result.stdout  # the front door is P6's, not P4's
    assert tree_hash(repo) == before

    (repo / "specs/tech-stack.md").write_text("# Tech stack\n", encoding="utf-8")
    before = tree_hash(repo)
    result = render(repo, values={**VALUES, "ENTRY": "uvicorn app.main:app"})
    assert result.returncode == 1
    assert "IF_RELEASE" in result.stdout and "set DISTRIBUTION" in result.stdout
    assert tree_hash(repo) == before


def test_ci_is_rendered_only_with_a_github_origin(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    other = "https://gitlab.example.invalid/someone/tipcalc.git"
    git(repo, "remote", "add", "origin", other)
    assert render(repo, "--offline", values=VALUES).returncode == 0
    assert not (repo / ".github").exists()  # another host: GitHub Actions never runs
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["origin_url"] == other  # a local folder is refused instead (Run D)

    repo = tipcalc_like(tmp_path / "gh" / "tipcalc")
    origin = "https://github.com/someone/tipcalc.git"
    git(repo, "remote", "add", "origin", origin)
    refused = render(repo, "--offline", values=VALUES)
    assert refused.returncode == 1
    assert "CHECKOUT_REF" in refused.stdout and "MISE_ACTION_REF" in refused.stdout

    refs = {**VALUES, "CHECKOUT_REF": "v4", "MISE_ACTION_REF": "v4"}
    assert render(repo, "--offline", values=refs).returncode == 0
    ci = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'branches: ["main"]' in ci
    assert '  "verify":' in ci
    assert "actions/checkout@v4" in ci and "jdx/mise-action@v4" in ci
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["origin_url"] == origin
    assert manifest["server_protection"].startswith("pending: EXTEND applies server rules")


def test_a_repo_with_its_own_ci_gets_sdd_yml(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {".github/workflows/backend.yml": "name: backend\n"})
    refs = {**VALUES, "CHECKOUT_REF": "v4", "MISE_ACTION_REF": "v4"}
    assert render(repo, "--offline", "--remote", "github", values=refs).returncode == 0
    sdd = (repo / ".github/workflows/sdd.yml").read_text(encoding="utf-8")
    assert '  "sdd":' in sdd
    assert "\nname: sdd\n" in sdd  # never `ci` beside the repo's own workflow (helios's `CI`)
    assert not (repo / ".github/workflows/ci.yml").exists()
    assert (repo / ".github/workflows/backend.yml").read_text(encoding="utf-8") == "name: backend\n"


def test_a_line_removed_from_a_merged_file_is_a_customization(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    ignore = repo / ".gitignore"
    ignore.write_text(ignore.read_text(encoding="utf-8") + "local-notes/\n", encoding="utf-8")
    added = render(repo)  # a line the project added: the merge has nothing to do
    assert added.returncode == 0, added.stdout
    assert added.stdout.strip().endswith("render: 0 changes")
    assert render(repo, "--check").returncode == 0

    removed = "\n".join(
        ln for ln in ignore.read_text(encoding="utf-8").splitlines() if ln != ".agent/"
    )
    ignore.write_text(removed + "\n", encoding="utf-8")
    result = render(repo)
    assert result.returncode == 3, result.stdout
    assert re.search(r"^  customized +\.gitignore: not overwritten", result.stdout, re.MULTILINE)
    assert "-.agent/" in result.stdout  # the question's diff runs from the render to yours
    assert "re-run render with the same --values: take the render with --force-file .gitignore" in (
        result.stdout
    )
    assert ".agent/" not in ignore.read_text(encoding="utf-8").splitlines()
    assert render(repo, "--keep-file", ".gitignore").returncode == 0
    assert render(repo, "--check").returncode == 0

    pyproject = repo / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    pyproject.write_text(text.replace('extend-select = ["S", "ANN"]', ""), encoding="utf-8")
    result = render(repo)
    assert result.returncode == 3
    assert re.search(r"^  customized +pyproject\.toml", result.stdout, re.MULTILINE)
    assert "extend-select" not in pyproject.read_text(encoding="utf-8")


def test_a_refused_render_writes_nothing_and_saves_no_values(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    pyproject = repo / "pyproject.toml"
    edited = pyproject.read_text(encoding="utf-8").replace('extend-select = ["S", "ANN"]', "")
    pyproject.write_text(edited, encoding="utf-8")
    before = tree_hash(repo)
    result = render(repo, values={"DESCRIPTION": "Another one-liner.", "ENTRY": "tipcalc -v"})
    assert result.returncode == 3, result.stdout
    customized = r"^  customized +pyproject\.toml: not overwritten \(changed since"
    assert re.search(customized, result.stdout, re.MULTILINE)
    assert re.search(r"^  waiting +mise\.toml$", result.stdout, re.MULTILINE)
    assert "nothing written" in result.stdout
    assert tree_hash(repo) == before  # mise.toml not upgraded, .project.toml [values] unsaved
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["values"] == VALUES


def test_merges_keep_line_endings_indents_and_comments() -> None:
    module = load_init()
    template = (SKILL / "templates" / "gitignore-extra").read_text(encoding="utf-8")
    crlf = module.merge_lines("*.log\r\n.venv\r\n", template, gitignore=True)
    assert "\r\n" in crlf and "\n" not in crlf.replace("\r\n", "")
    additions = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    current = (
        '[project]\nname = "x"\n\n[tool.pytest.ini_options]\nmarkers = [\n'
        '    "slow: long tests",   # CI only\n'
        "    'db: needs postgres'\n"
        "]\n"
    )
    merged = module.merge_pyproject(current, additions, None)
    assert (
        '    "slow: long tests",   # CI only\n'
        "    'db: needs postgres',\n"
        '    "spec(*ids): scenario ids this test proves",\n'
        "]\n"
    ) in merged
    assert module.merge_pyproject(merged, additions, None) == merged
    windows = module.merge_pyproject(current.replace("\n", "\r\n"), additions, None)
    assert windows == merged.replace("\n", "\r\n")


def test_render_never_writes_through_a_symlink(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    shared = tmp_path / "shared-gitignore"
    shared.write_text(UV_GITIGNORE, encoding="utf-8")
    (repo / ".gitignore").unlink()
    (repo / ".gitignore").symlink_to(shared)
    result = render(repo, values=VALUES)
    assert result.returncode == 3, result.stdout + result.stderr
    assert f".gitignore: a symlink to {shared}: never written through" in result.stdout
    assert "nothing written" in result.stdout
    assert not (repo / "mise.toml").exists() and not (repo / ".project.toml").exists()
    assert (repo / ".gitignore").is_symlink()
    assert shared.read_text(encoding="utf-8") == UV_GITIGNORE
    check = render(repo, "--check", values=VALUES)
    assert check.returncode == 3 and "  symlink     .gitignore" in check.stdout

    forced = render(repo, "--force-file", ".gitignore", values=VALUES)
    assert forced.returncode == 0, forced.stdout
    assert not (repo / ".gitignore").is_symlink()
    lines = (repo / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert {".venv", "__pycache__/", "*.py[oc]", ".env.*", "!.env.example"} <= set(lines)
    assert shared.read_text(encoding="utf-8") == UV_GITIGNORE

    other = tipcalc_like(tmp_path / "linked" / "tipcalc")
    real = tmp_path / "shared-pyproject.toml"
    real.write_text(TIPCALC_PYPROJECT, encoding="utf-8")
    (other / "pyproject.toml").unlink()
    (other / "pyproject.toml").symlink_to(real)
    result = render(other, values=VALUES)
    assert result.returncode == 3, result.stdout + result.stderr
    assert "Traceback" not in result.stderr
    assert (other / "pyproject.toml").is_symlink()
    assert real.read_text(encoding="utf-8") == TIPCALC_PYPROJECT


def test_an_unparsable_pyproject_is_refused_not_a_traceback(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    (repo / "pyproject.toml").write_text('[project\nname = "tipcalc"\n', encoding="utf-8")
    before = tree_hash(repo)
    result = render(repo, values=VALUES)
    assert result.returncode == 1
    assert "pyproject.toml does not parse" in result.stderr
    assert "Traceback" not in result.stderr
    assert tree_hash(repo) == before
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "note ........ pyproject.toml does not parse (" in text


def test_a_branch_name_that_is_shell_is_refused(tmp_path: Path) -> None:
    branch = "x;touch${IFS}pwned"
    repo = make_repo(
        tmp_path / "tc-inj",
        {
            "pyproject.toml": TIPCALC_PYPROJECT,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            "specs/tech-stack.md": TECH_STACK,
        },
        branch=branch,
    )
    before = tree_hash(repo)
    result = render(repo, values=VALUES)
    assert result.returncode == 1
    assert "DEFAULT_BRANCH" in result.stderr and "nothing written" in result.stderr
    assert tree_hash(repo) == before
    assert not (repo / ".githooks").exists() and not (repo / "pwned").exists()

    ok = make_repo(
        tmp_path / "ok", {"pyproject.toml": TIPCALC_PYPROJECT, "specs/tech-stack.md": TECH_STACK}
    )
    bad = render(ok, values={"DESCRIPTION": "one\n[tasks.x]", "ENTRY": "app"})
    assert bad.returncode == 1 and "DESCRIPTION: one line" in bad.stderr
    quoted = render(ok, values={**VALUES, "ENTRY": 'app"\n[tasks.x]\nrun = "sh'})
    assert quoted.returncode == 1 and "inside a TOML string in mise.toml" in quoted.stderr
    assert not (ok / "mise.toml").exists()

    # no console script: ENTRY is the start command, any command line a TOML string can hold
    service = make_repo(
        tmp_path / "svc",
        {
            "pyproject.toml": TIPCALC_PYPROJECT.replace(
                '[project.scripts]\ntipcalc = "tipcalc:main"\n', ""
            ),
            "specs/tech-stack.md": TECH_STACK,
        },
    )
    entry = "uvicorn backend.main:app --host 0.0.0.0 --port 8000"
    done = render(service, values={**VALUES, "ENTRY": entry})
    assert done.returncode == 0, done.stdout + done.stderr
    mise = tomllib.loads((service / "mise.toml").read_text(encoding="utf-8"))
    assert mise["tasks"]["start"]["run"] == f"uv run --locked {entry}"
    assert init("render", str(service), "--values", '{"DESCRIPTION": 5}').returncode == 2
    via_values = init("render", str(service), "--values", '{"START_EXAMPLE": "mise run start"}')
    assert via_values.returncode == 2 and "verify.json" in via_values.stderr


def test_merge_pyproject_keeps_project_values_and_is_idempotent() -> None:
    module = load_init()
    additions = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    current = (
        '[project]\nname = "x"\ndescription = "Add your description here"\n\n'
        "[tool.ruff]\nline-length = 88\n"
        'extend-exclude = [".claude"]   # vendored scripts\n\n'
        "[tool.ruff.lint.per-file-ignores]\n"
        '"tests/**" = ["S101"]          # pytest asserts\n\n'
        '[tool.pytest.ini_options]\naddopts = "-q"\ntestpaths = ["tests"]\n'
    )
    merged = module.merge_pyproject(current, additions, "A real one-liner.")
    data = tomllib.loads(merged)
    assert data["project"]["description"] == "A real one-liner."
    assert data["tool"]["ruff"]["line-length"] == 88
    assert data["tool"]["ruff"]["extend-exclude"] == [
        ".claude",
        "scripts/project.py",
        "tests/conftest.py",
    ]
    assert "# vendored scripts" in merged  # the list keeps an item of its own: its comment stays
    assert data["tool"]["ruff"]["lint"]["per-file-ignores"]["tests/**"] == ["S101", "S603", "S607"]
    # now just the template's list: the template's comment, not one that explains S101 alone
    assert (
        '"tests/**" = ["S101", "S603", "S607"]          # assert, and subprocess tests of the '
        "real entrypoint\n" in merged
    )
    assert (
        data["tool"]["pytest"]["ini_options"]["addopts"]
        == "-q --strict-markers -p no:cacheprovider"
    )
    assert data["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert data["tool"]["git-cliff"] == tomllib.loads(additions)["tool"]["git-cliff"]
    assert module.merge_pyproject(merged, additions, "A real one-liner.") == merged


def test_gitignore_merge_keeps_the_env_contract_tracked() -> None:
    module = load_init()
    template = (SKILL / "templates" / "gitignore-extra").read_text(encoding="utf-8")
    current = "!.env.example\n.venv/\n__pycache__\n"
    merged = module.merge_lines(current, template, gitignore=True)
    lines = merged.splitlines()
    assert lines.index("!.env.example", 1) == lines.index(".env.*") + 1
    assert lines.count(".venv/") + lines.count(".venv") == 1
    assert module.merge_lines(merged, template, gitignore=True) == merged


def test_the_punch_list_counts_the_contract_secret_rows_only() -> None:
    module = load_init()
    template = (SKILL / "templates" / "env.example").read_text(encoding="utf-8")
    knob = module.EnvRead("APP_PERCENT", "knob", "float", False, "15", ["src/app.py:3"])
    token = module.EnvRead("APP_TOKEN", "secret", "str", True, None, ["src/app.py:4"])
    knobs_only = template.replace("{ENV_ROWS}", module.env_rows([knob]))
    assert "op://" in knobs_only  # the kind legend names it
    assert "STRIPE_KEY" not in knobs_only  # no example row: the contract lists real reads only
    assert module.contract_secrets(knobs_only) == []
    both = template.replace("{ENV_ROWS}", module.env_rows([knob, token]))
    added = both + "# DB_PASSWORD | secret | str | yes | - | added by hand\n"
    assert module.contract_secrets(added) == ["APP_TOKEN", "DB_PASSWORD"]


NATIVE_PYTEST = (
    '[project]\nname = "native"\nversion = "0.1.0"\n\n'
    '[tool.pytest]\naddopts = ["-x"]   # stop at the first failure\n'
)


def test_a_native_pytest_table_gets_native_lists_and_pytest_9_starts(tmp_path: Path) -> None:
    module = load_init()
    additions = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    merged = module.merge_pyproject(NATIVE_PYTEST, additions, None)
    pytest_table = tomllib.loads(merged)["tool"]["pytest"]
    assert "ini_options" not in pytest_table  # never both tables: pytest 9 would not start
    assert pytest_table["addopts"] == ["-x", "-q", "--strict-markers", "-p", "no:cacheprovider"]
    assert pytest_table["markers"] == ["spec(*ids): scenario ids this test proves"]
    assert "# stop at the first failure" in merged
    assert module.merge_pyproject(merged, additions, None) == merged
    both = NATIVE_PYTEST + '\n[tool.pytest.ini_options]\nmarkers = ["slow"]\n'
    with pytest.raises(module.Refusal, match="pytest 9 refuses to start with both"):
        module.merge_pyproject(both, additions, None)
    dotted = '[project]\nname = "x"\n\n[tool]\npytest.addopts = ["-x"]\n'
    with pytest.raises(module.Refusal, match="written as dotted keys"):
        module.merge_pyproject(dotted, additions, None)

    # pytest 9 itself: it starts on the merge (the spec marker registered, --strict-markers on),
    # and refuses the two-table file the old merge produced
    project = tmp_path / "native"
    test_file = 'import pytest\n\n\n@pytest.mark.spec("cli.x")\ndef test_x() -> None:\n    pass\n'
    write(project, {"pyproject.toml": merged, "tests/test_spec.py": test_file})
    argv = ["uv", "run", "--no-project", "--with", "pytest>=9", "pytest"]

    def pytest9(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [*argv, *args],
            cwd=project,
            capture_output=True,
            text=True,
            env=clean_env(),
            check=False,
            timeout=600,
        )

    version = pytest9("--version")
    if version.returncode != 0:
        pytest.skip(f"pytest 9 is not installable here: {version.stderr[-200:]}")
    assert re.search(r"pytest 9\.", version.stdout + version.stderr)
    done = pytest9()
    assert done.returncode == 0, done.stdout + done.stderr
    assert "1 passed" in done.stdout
    old = NATIVE_PYTEST + '\n[tool.pytest.ini_options]\nmarkers = ["spec(*ids): x"]\n'
    (project / "pyproject.toml").write_text(old, encoding="utf-8")
    refused = pytest9()
    assert refused.returncode != 0 and "Cannot use both" in refused.stdout + refused.stderr

    repo = tipcalc_like(tmp_path / "tipcalc")
    pyproject = repo / "pyproject.toml"
    pyproject.write_text(
        pyproject.read_text(encoding="utf-8") + '\n[tool.pytest]\naddopts = ["-x"]\n',
        encoding="utf-8",
    )
    assert render(repo, values=VALUES).returncode == 0
    rendered = tomllib.loads(pyproject.read_text(encoding="utf-8"))["tool"]["pytest"]
    assert "ini_options" not in rendered and "--strict-markers" in rendered["addopts"]


def test_a_native_string_addopts_becomes_the_list_pytest_9_needs(tmp_path: Path) -> None:
    """A native [tool.pytest] whose addopts (or markers) is one string makes pytest 9 refuse to
    start ("expects a list for type 'args'"). The merge writes those lines as native lists, the
    template's flags and the spec marker added, and a second merge changes nothing."""
    module = load_init()
    additions = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    stringy = (
        '[project]\nname = "native"\nversion = "0.1.0"\n\n'
        '[tool.pytest]\naddopts = "-x --tb=short"   # fail fast\n'
        'markers = """\n    slow: slow tests\n"""\n'
    )
    merged = module.merge_pyproject(stringy, additions, None)
    table = tomllib.loads(merged)["tool"]["pytest"]
    assert "ini_options" not in table
    assert table["addopts"] == [
        "-x",
        "--tb=short",
        "-q",
        "--strict-markers",
        "-p",
        "no:cacheprovider",
    ]
    assert table["markers"] == ["slow: slow tests", "spec(*ids): scenario ids this test proves"]
    assert "# fail fast" in merged
    assert module.merge_pyproject(merged, additions, None) == merged
    unsplittable = stringy.replace('"-x --tb=short"', '"-k \'unclosed"')
    with pytest.raises(module.Refusal, match="does not split"):
        module.merge_pyproject(unsplittable, additions, None)

    project = tmp_path / "native"
    test_file = 'import pytest\n\n\n@pytest.mark.spec("cli.x")\ndef test_x() -> None:\n    pass\n'
    write(project, {"pyproject.toml": stringy, "tests/test_spec.py": test_file})
    argv = ["uv", "run", "--no-project", "--with", "pytest>=9", "pytest"]

    def pytest9() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            argv,
            cwd=project,
            capture_output=True,
            text=True,
            env=clean_env(),
            check=False,
            timeout=600,
        )

    refused = pytest9()
    if "No solution found" in refused.stderr or "Failed to" in refused.stderr:
        pytest.skip(f"pytest 9 is not installable here: {refused.stderr[-200:]}")
    assert refused.returncode != 0  # the control: pytest 9 will not start on the string
    assert "expects a list" in refused.stdout + refused.stderr
    (project / "pyproject.toml").write_text(merged, encoding="utf-8")
    done = pytest9()
    assert done.returncode == 0, done.stdout + done.stderr
    assert "1 passed" in done.stdout


def test_render_seeds_the_memory_files_once_and_never_overwrites_them(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    lessons = repo / "project_memory" / "lessons.md"
    template = (SKILL / "templates" / "project_memory" / "lessons.md").read_text(encoding="utf-8")
    assert lessons.read_text(encoding="utf-8") == template
    assert "project_memory/lessons.md merge=union" in (repo / ".gitattributes").read_text(
        encoding="utf-8"
    )
    hashes = generated(repo)
    assert "project_memory/lessons.md" not in hashes and DECISIONS_KEEP not in hashes

    # the project's own from now on: an appended lesson and a first ADR are no drift
    lessons.write_text(template + "\n## 2026-09-24 | x\nTrigger: a\nRule: b\n", encoding="utf-8")
    (repo / DECISIONS_KEEP).unlink()
    write(repo, {"project_memory/decisions/2026-09-24-exit-codes.md": "---\nstatus: active\n---\n"})
    check = render(repo, "--check")
    assert check.returncode == 0, check.stdout
    again = render(repo)
    assert again.returncode == 0 and again.stdout.strip().endswith("render: 0 changes")
    assert not (repo / DECISIONS_KEEP).exists()  # the ADR stands in for the placeholder
    assert "## 2026-09-24 | x" in lessons.read_text(encoding="utf-8")

    # deleted: the next render seeds it again, and --check calls it missing until then
    lessons.unlink()
    missing = render(repo, "--check")
    assert missing.returncode == 3 and "  missing     project_memory/lessons.md" in missing.stdout
    assert render(repo).returncode == 0 and lessons.read_text(encoding="utf-8") == template

    # v2 lessons are carried over as they are, and never listed as seeded
    carried = tipcalc_like(tmp_path / "v2" / "tipcalc")
    write(carried, {"project_memory/lessons.md": "# Lessons\n\n## 2026-01-01 | old\n"})
    assert render(carried, values=VALUES).returncode == 0
    old = (carried / "project_memory/lessons.md").read_text(encoding="utf-8")
    assert old == "# Lessons\n\n## 2026-01-01 | old\n"
    manifest = tomllib.loads((carried / ".project.toml").read_text(encoding="utf-8"))
    assert list(manifest["seeded"]) == [DECISIONS_KEEP]


SARA = ("Sara Q", "12345+saraq@users.noreply.github.com")
OMAR = ("Omar Z", "omar@example.invalid")


def team_repo(root: Path) -> Path:
    """tipcalc with three human authors in six months: the team tier (D9). The one running
    project-init (git user.email) is Sara, whose noreply address names her login; Omar
    committed after her, so she is not the newest author."""
    repo = tipcalc_like(root)
    for i, (name, email) in enumerate((SARA, OMAR)):
        source = repo / "src" / "tipcalc" / "__init__.py"
        source.write_text(source.read_text(encoding="utf-8") + f"# {i}\n", encoding="utf-8")
        env = clean_env(GIT_AUTHOR_NAME=name, GIT_AUTHOR_EMAIL=email)
        git(repo, "commit", "-q", "-am", f"fix: change {i}", env=env)
    git(repo, "config", "user.email", SARA[1])
    return repo


def test_the_team_tier_renders_team_md_codeowners_and_the_pr_template(tmp_path: Path) -> None:
    repo = team_repo(tmp_path / "tipcalc")
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "team tier" in result.stdout
    team = (repo / "project_memory" / "team.md").read_text(encoding="utf-8")
    assert not PLACEHOLDER.search(team)
    roster = [ln for ln in team.splitlines() if re.match(r"^\| .+ \| (Lead|Contributor) \|", ln)]
    assert roster == [  # the Lead first, then the Contributors, newest first
        "| Sara Q | Lead | @saraq |",
        "| Omar Z | Contributor | (unknown) |",
        "| Test Author | Contributor | (unknown) |",
    ]
    assert "| `*` | @saraq |" in team
    owners = (repo / ".github" / "CODEOWNERS").read_text(encoding="utf-8")
    assert owners.splitlines()[-1] == "* @saraq"
    assert owners.startswith("# Generated by project-init from the Ownership table")
    pr = (repo / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert pr == (SKILL / "templates" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "| who may merge | `team.md` |" in (repo / "project_memory/README.md").read_text(
        encoding="utf-8"
    )
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["tier"] == "team"
    assert "project_memory/team.md" in manifest["seeded"]
    assert {".github/CODEOWNERS", ".github/pull_request_template.md"} <= set(manifest["generated"])

    # CODEOWNERS follows team.md: a new Ownership row is an upgrade, not a question
    team_md = repo / "project_memory" / "team.md"
    team_md.write_text(team + "| `src/tipcalc/` | @omarz, omar@example.invalid |\n", "utf-8")
    again = render(repo)
    assert again.returncode == 0, again.stdout
    assert re.search(r"^  upgrade +\.github/CODEOWNERS$", again.stdout, re.MULTILINE)
    owners = (repo / ".github" / "CODEOWNERS").read_text(encoding="utf-8").splitlines()
    assert owners[-2:] == ["* @saraq", "src/tipcalc/ @omarz omar@example.invalid"]
    assert render(repo, "--check").returncode == 0

    # no owner a CODEOWNERS line can name: a comment, and a punch-list note
    team_md.write_text(team.replace("| `*` | @saraq |", "| `*` | (the lead's @login) |"), "utf-8")
    none = render(repo)
    assert none.returncode == 0
    assert "CODEOWNERS names no owner yet" in none.stdout
    assert (
        (repo / ".github/CODEOWNERS")
        .read_text(encoding="utf-8")
        .splitlines()[-1]
        .startswith("# No owner yet")
    )


def test_brownfield_lint_debt_becomes_a_shrink_only_baseline_once(tmp_path: Path) -> None:
    ruff = need(real_ruff(tmp_path), "no ruff binary in uv's cache")
    repo = tipcalc_like(tmp_path / "tipcalc")
    legacy = "import subprocess\n\n\ndef run(cmd):\n    return subprocess.call(cmd, shell=True)\n"
    write(repo, {"src/tipcalc/legacy.py": legacy, "tool.py": legacy})
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "ruff").symlink_to(ruff)  # P4's `uv add --dev ruff` put it here
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert "# project-init baseline: shrink only" in text
    ignores = tomllib.loads(text)["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert {"ANN001", "ANN201", "S602"} <= set(ignores["src/tipcalc/legacy.py"])
    # a root file's row is anchored: a bare `tool.py` would match every tool.py in the repo
    assert {"ANN001", "ANN201", "S602"} <= set(ignores["./tool.py"])
    assert "tool.py" not in ignores
    assert ignores["tests/**"] == ["S101", "S603", "S607"]
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert re.fullmatch(r"\d+ findings in 2 files", manifest["ruff_baseline"])
    assert "ruff baseline: " in result.stdout and "plus one backlog item (N3)" in result.stdout
    backlog = list((repo / "specs" / "backlog").glob("*-ruff-baseline.md"))
    assert len(backlog) == 1 and str(backlog[0].relative_to(repo)) in manifest["seeded"]
    assert "# Shrink the ruff baseline" in backlog[0].read_text(encoding="utf-8")

    def lint() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [ruff, "check", "--no-cache", "."],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    first = lint()
    assert first.returncode == 0, first.stdout  # the baseline absorbs the adoption-time debt
    write(repo, {"src/tipcalc/tool.py": "def f(x):\n    return x\n"})
    assert "src/tipcalc/tool.py" in lint().stdout  # the root's row does not cover it
    (repo / "src/tipcalc/tool.py").unlink()
    # taken once: debt added after adoption is never absorbed, so lint (and doctor) catch it
    write(repo, {"src/tipcalc/newer.py": "def f(x):\n    return x\n"})
    again = render(repo)
    assert again.returncode == 0, again.stdout
    assert "newer.py" not in (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert lint().returncode == 1
    assert len(list((repo / "specs" / "backlog").glob("*.md"))) == 1


TY_DEBT = """import os


def run(cmd: str) -> int:
    return os.system(cmd)


COUNT: int = "none"
"""


def test_brownfield_type_debt_becomes_a_shrink_only_ty_exclude_once(tmp_path: Path) -> None:
    """ty has no per-file ignore (design Risk 8): each file ty flags at adoption is left out of
    `ty check` by [tool.ty.src] exclude under its own mark, with one backlog item. Taken once,
    so type debt added later still fails ty."""
    ty = need(real_ty(tmp_path), "no ty binary in uv's cache")
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"src/tipcalc/legacy.py": TY_DEBT})
    for argv in (  # the venv P4's `uv add --dev ruff ty pytest` leaves (tests import pytest)
        ["uv", "venv", "-q", ".venv"],
        ["uv", "pip", "install", "-q", "--python", ".venv/bin/python", "pytest"],
    ):
        made = subprocess.run(
            argv,
            cwd=repo,
            env=clean_env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=600,
        )
        if made.returncode != 0:
            pytest.skip(f"{' '.join(argv[:2])} failed: {made.stderr.strip()[-200:]}")
    (repo / ".venv" / "bin" / "ty").symlink_to(ty)

    def types() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [ty, "check", "--output-format", "concise"],
            cwd=repo,
            env=clean_env(),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    before = types()
    assert before.returncode == 1 and "src/tipcalc/legacy.py" in before.stdout, before.stdout
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ty baseline: 2 diagnostics in 1 file, left out of `ty check`" in result.stdout
    assert "plus one backlog item (Risk 8)" in result.stdout
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert "# project-init ty baseline: shrink only" in text
    assert "# project-init baseline: shrink only" not in text  # doctor's ruff mark stays off
    parsed = tomllib.loads(text)
    assert parsed["tool"]["ty"]["src"]["exclude"] == ["src/tipcalc/legacy.py"]
    assert parsed["tool"]["pytest"]["ini_options"]["markers"]  # the table after it is intact
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["ty_baseline"] == "2 diagnostics in 1 file"
    backlog = list((repo / "specs" / "backlog").glob("*-ty-baseline.md"))
    assert len(backlog) == 1 and str(backlog[0].relative_to(repo)) in manifest["seeded"]
    item = backlog[0].read_text(encoding="utf-8")
    assert "# Shrink the ty baseline" in item and "`src/tipcalc/legacy.py`" in item

    after = types()
    assert after.returncode == 0, after.stdout  # the baseline absorbs the adoption-time debt
    assert render(repo, "--check").returncode == 0
    # taken once: type debt added after adoption is never absorbed, so `mise run types` fails
    write(repo, {"src/tipcalc/newer.py": 'LATER: int = "later"\n'})
    again = render(repo)
    assert again.returncode == 0, again.stdout
    assert "ty baseline" not in again.stdout
    assert "newer.py" not in (repo / "pyproject.toml").read_text(encoding="utf-8")
    later = types()
    assert later.returncode == 1 and "src/tipcalc/newer.py" in later.stdout, later.stdout
    assert len(list((repo / "specs" / "backlog").glob("*.md"))) == 1


def test_history_leaks_are_fingerprinted_once_in_gitleaksignore(tmp_path: Path) -> None:
    gitleaks = need(gitleaks_cmd(), "gitleaks is not runnable here")
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"notes.txt": f"key {FAKE_AWS_ID}\n"})
    git(repo, "add", "notes.txt")
    git(repo, "commit", "-q", "-m", "chore: notes")
    git(repo, "rm", "-q", "notes.txt")
    git(repo, "commit", "-q", "-m", "chore: drop the notes")
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "history already holds 1 finding of the leak rules" in result.stdout
    assert "rotate the secrets among them (punch list: the aws-access-token findings)" in (
        result.stdout
    )
    ignore = (repo / ".gitleaksignore").read_text(encoding="utf-8")
    assert re.search(r"(?m)^[0-9a-f]{40}:notes\.txt:aws-access-token:1$", ignore)
    assert FAKE_AWS_ID not in ignore
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["gitleaks_baseline"] == "1 finding in history (.gitleaksignore)"
    assert ".gitleaksignore" in manifest["seeded"]

    def secrets_task() -> int:  # `mise run secrets`, from outside the repo's untrusted mise.toml
        scan = [*gitleaks, "git", str(repo), "--redact", "--no-banner", "--log-level", "error"]
        scan += ["--gitleaks-ignore-path", str(repo)]
        return subprocess.run(scan, cwd=tmp_path, capture_output=True, check=False).returncode

    assert secrets_task() == 0  # verify's history scan passes the adopted history
    # taken once: a leak committed after adoption is never absorbed into the ignore file
    write(repo, {"later.txt": "token ghp_" + "Xk3vB9qLm2Np7Rt4Ws8Yz1Ac5De6Fg0Hj2Kp\n"})
    git(repo, "add", "later.txt")
    git(repo, "commit", "-q", "--no-verify", "-m", "chore: later")
    assert render(repo).returncode == 0
    assert (repo / ".gitleaksignore").read_text(encoding="utf-8") == ignore
    assert secrets_task() != 0


def test_per_signal_skills_come_only_with_file_evidence_and_a_dry_run(tmp_path: Path) -> None:
    service = TIPCALC_PYPROJECT.replace(
        "dependencies = []", 'dependencies = ["fastapi", "sqlalchemy"]'
    )
    repo = make_repo(
        tmp_path / "svc",
        {
            "pyproject.toml": service,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            "specs/tech-stack.md": TECH_STACK,
            "backend/alembic.ini": "[alembic]\nscript_location = migrations\n",
            "backend/pyproject.toml": '[project]\nname = "backend"\nversion = "0"\n',
            "wrangler.toml": 'name = "svc"\n',
            "Dockerfile": "FROM python:3.14\n",
        },
    )
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    skills = repo / ".claude" / "skills"
    assert sorted(p.name for p in skills.iterdir()) == ["db", "deploy", "run-tipcalc", "sdd"]
    run_skill = (skills / "run-tipcalc" / "SKILL.md").read_text(encoding="utf-8")
    assert run_skill.startswith("---\nname: run-tipcalc\n")
    db = (skills / "db" / "SKILL.md").read_text(encoding="utf-8")
    assert "`backend/alembic.ini`" in db and "`backend/`" in db
    assert "uv run --locked alembic heads" in db
    deploy = (skills / "deploy" / "SKILL.md").read_text(encoding="utf-8")
    assert "`wrangler.toml`" in deploy and "wrangler deploy --dry-run" in deploy
    for text in (run_skill, db, deploy):
        assert not PLACEHOLDER.search(text)
    assert {".claude/skills/db/SKILL.md", ".claude/skills/deploy/SKILL.md"} <= set(generated(repo))
    assert render(repo, "--check").returncode == 0

    # P5 runs each skill's dry-run where it lives; run-<name> makes start --help required
    write(repo, {"scripts/project.py": STUB_PROJECT})
    env = fake_tools(tmp_path)
    npx = tmp_path / "fakebin" / "npx"
    npx.write_text(
        '#!/bin/sh\necho "npx $* (in $(basename "$PWD"))" >> "$FAKE_LOG"\n', encoding="utf-8"
    )
    npx.chmod(0o755)
    done = init("selftest", str(repo), "--start-args", "100", env=env)
    assert done.returncode == 1, done.stdout + done.stderr  # the fake start --help crashes
    assert "  FAIL  mise run start -- --help (exit 1" in done.stdout
    log = (tmp_path / "fake.log").read_text(encoding="utf-8")
    assert "mise x -- uv run --locked alembic heads\n" in log
    assert re.search(
        r"(?m)^npx --no-install wrangler deploy --dry-run --outdir \S+/deploy \(in svc\)$", log
    )
    checks = {c["key"]: c for c in verify_checks(repo)}
    assert checks["skill db"]["cwd"] == "backend" and checks["skill db"]["green"] is True
    assert str(checks["skill deploy"]["name"]).startswith("npx --no-install wrangler deploy")

    # the same signals without a dry-run-able file: no skill, and a note says why
    bare = make_repo(
        tmp_path / "bare",
        {
            "pyproject.toml": TIPCALC_PYPROJECT.replace(
                "dependencies = []", 'dependencies = ["sqlalchemy"]'
            ),
            "specs/tech-stack.md": TECH_STACK,
            "Dockerfile": "FROM python:3.14\n",
        },
    )
    plain = render(bare, values=VALUES)
    assert plain.returncode == 0, plain.stdout
    assert sorted(p.name for p in (bare / ".claude" / "skills").iterdir()) == ["sdd"]
    assert "no db skill: no alembic.ini" in plain.stdout
    assert "no deploy skill: only wrangler has a dry-run" in plain.stdout


def test_the_agents_symlink_comes_only_with_its_flag(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    assert not (repo / ".agents").exists()
    linked = render(repo, "--agents-symlink")
    assert linked.returncode == 0, linked.stdout + linked.stderr
    assert re.search(r"^  missing +\.agents/skills/sdd$", linked.stdout, re.MULTILINE)
    link = repo / ".agents" / "skills" / "sdd"
    assert link.is_symlink() and os.readlink(link) == "../../.claude/skills/sdd"
    assert (link / "SKILL.md").is_file()
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["agents_symlink"] is True and ".agents/skills/sdd" in manifest["generated"]
    assert render(repo, "--check").returncode == 0  # kept on later renders, flag or not
    again = render(repo)
    assert again.returncode == 0 and again.stdout.strip().endswith("render: 0 changes")

    link.unlink()
    link.symlink_to("../../elsewhere")
    moved = render(repo)
    assert moved.returncode == 3 and "customized" in moved.stdout
    assert os.readlink(link) == "../../elsewhere"
    assert render(repo, "--force-file", ".agents/skills/sdd").returncode == 0
    assert os.readlink(link) == "../../.claude/skills/sdd"


def test_forcing_a_restored_line_keeps_one_standard_block(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    ignore = repo / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines()
    ignore.write_text("\n".join(ln for ln in lines if ln != ".agent/") + "\n", encoding="utf-8")
    assert render(repo).returncode == 3
    forced = render(repo, "--force-file", ".gitignore")
    assert forced.returncode == 0, forced.stdout
    text = ignore.read_text(encoding="utf-8")
    assert text.count("# project-init standard") == 1
    assert ".agent/" in text.splitlines()
    assert render(repo, "--check").returncode == 0


def test_settings_json_names_the_project_py_hooks(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    settings = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    (start,) = [h["command"] for e in settings["hooks"]["SessionStart"] for h in e["hooks"]]
    (bash,) = settings["hooks"]["PreToolUse"]
    assert bash["matcher"] == "Bash"
    assert re.search(r'scripts/project\.py" hook session-start \|\| echo ', start)
    assert bash["hooks"][0]["command"].endswith('scripts/project.py" hook pre-bash')


def test_the_rendered_project_py_serves_both_claude_hooks(tmp_path: Path) -> None:
    """The commands the rendered .claude/settings.json runs: `hook session-start` and `hook
    pre-bash` exit 0 on a plain call, and pre-bash blocks a gate bypass with exit 2, the code
    Claude Code reads as a block. An unknown hook name would also exit 2 (argparse), which
    is why a project.py without them would block every Bash call from P4 on."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0

    def hook(name: str, payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(repo / "scripts" / "project.py"), "hook", name],
            input=json.dumps(payload),
            cwd=repo,
            capture_output=True,
            text=True,
            env=clean_env(),
            check=False,
            timeout=120,
        )

    def bash(command: str) -> dict[str, object]:
        return {
            "session_id": "t",
            "cwd": str(repo),
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }

    start: dict[str, object] = {
        "session_id": "t",
        "cwd": str(repo),
        "hook_event_name": "SessionStart",
    }
    for name, payload in (("pre-bash", bash("ls")), ("session-start", start)):
        done = hook(name, payload)
        assert done.returncode == 0, f"hook {name}: exit {done.returncode}: {done.stderr[-300:]}"
    blocked = hook("pre-bash", bash("git commit --no-verify -m wip"))
    assert blocked.returncode == 2, blocked.stdout + blocked.stderr
    assert "pre-bash: blocked" in blocked.stderr


# ---------------------------------------------------------------------------------------------
# P7: publish


FAKE_GH = """#!/usr/bin/env python3
import json
import os
import subprocess
import sys

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write("gh " + " ".join(args) + "\\n")
if args[:2] == ["auth", "status"]:
    sys.exit(0)
if args[:2] == ["api", "user"]:
    print("")  # gh's default login lacks the user scope: no plan to read
    sys.exit(0)
if args[:1] == ["api"] and args[1].endswith("/protection"):
    if os.environ.get("FAKE_PLAN", "free") == "free":
        why = "Upgrade to GitHub Pro or make this repository public to enable this feature."
        print(json.dumps({"message": why, "status": "403"}))
        print("gh: " + why + " (HTTP 403)", file=sys.stderr)
    else:
        print(json.dumps({"message": "Branch not protected", "status": "404"}))
        print("gh: Branch not protected (HTTP 404)", file=sys.stderr)
    sys.exit(1)
if args[:2] == ["repo", "create"]:
    bare = os.path.join(os.environ["FAKE_REMOTES"], args[2] + ".git")
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", bare], check=True)
    url = "https://github.com/test-owner/" + args[2] + ".git"
    subprocess.run(["git", "remote", "add", "origin", url], check=True)
    sys.exit(0)
if args[:2] == ["repo", "edit"]:
    if os.path.exists(os.environ["FAKE_EDIT_FAIL"]):
        print("HTTP 502: Bad Gateway", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
sys.exit(2)
"""


def shipped_repo(
    tmp_path: Path, extra: dict[str, str] | None = None
) -> tuple[Path, dict[str, str]]:
    """tipcalc after P4, a green P5 and P6: what P7 starts from."""
    repo, env = front_door_repo(tmp_path, extra)
    done = render(repo, "--front-door")
    assert done.returncode == 0, done.stdout + done.stderr
    return repo, env


def ship_log(repo: Path) -> list[str]:
    return git(repo, "log", "--format=%s", "main..HEAD").splitlines()


def test_publish_dry_run_prints_the_p7_order_and_runs_nothing(tmp_path: Path) -> None:
    repo, env = shipped_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD")
    result = init("publish", str(repo), "--remote", "github", "--dry-run", env=env)
    assert result.returncode == 0, result.stderr
    assert "commit ...... chore(init): project-init v3 (on plan/project-init)" in result.stdout
    assert "P5 selftest (" in result.stdout and "Happy path: mise run start -- 100" in result.stdout
    assert "add '.project.toml'" in result.stdout and "add 'AGENTS.md'" in result.stdout
    steps = [ln for ln in result.stdout.splitlines() if re.match(r"^  \d\. ", ln)]
    assert len(steps) == 5
    assert steps[0] == (
        "  1. gh repo create tipcalc --private --source . --remote origin -d "
        "'Tiny CLI that prints the tip for a bill.'"
    )
    assert "--push" not in steps[0]
    assert steps[1] == "  2. git push -u origin main"  # before record: its probe needs main
    assert "origin_url" in steps[2] and "git commit --amend --no-edit" in steps[2]
    assert "gh api repos/<owner>/tipcalc/branches/main/protection" in steps[2]
    assert "README quickstart rendered again with its clone line" in steps[2]
    assert steps[3] == "  4. git push -u origin plan/project-init"
    assert steps[4] == (
        "  5. gh repo edit --default-branch main --delete-branch-on-merge --enable-squash-merge"
    )
    assert "no --push on create: main goes first" in result.stdout
    assert "while origin lacks main (N10)" in result.stdout
    assert git(repo, "remote").strip() == ""
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "diff", "--cached", "--name-only") == ""
    local = init("publish", str(repo), "--dry-run", env=env)
    assert "remote ...... none (local only); --remote github adds one" in local.stdout

    # a default branch that stayed master (no P3 rename): every step and note names master
    git(repo, "branch", "-m", "main", "master")
    manifest = repo / ".project.toml"
    text = manifest.read_text(encoding="utf-8")
    assert 'default_branch = "main"' in text
    master_text = text.replace('default_branch = "main"', 'default_branch = "master"')
    manifest.write_text(master_text, encoding="utf-8")
    master = init("publish", str(repo), "--remote", "github", "--dry-run", env=env)
    assert master.returncode == 0, master.stdout + master.stderr
    assert "  2. git push -u origin master" in master.stdout
    assert "--default-branch master " in master.stdout
    assert "no --push on create: master goes first" in master.stdout
    assert "while origin lacks master (N10)" in master.stdout
    assert "main" not in master.stdout.split("remote ......", 1)[1]


def test_publish_with_an_origin_it_did_not_make_creates_nothing(tmp_path: Path) -> None:
    repo, env = shipped_repo(tmp_path)
    git(repo, "remote", "add", "origin", "https://github.com/someone/tipcalc.git")
    result = init("publish", str(repo), "--remote", "github", "--dry-run", env=env)
    assert result.returncode == 0, result.stderr
    assert "origin already set (https://github.com/someone/tipcalc.git)" in result.stdout
    assert "gh repo create" not in result.stdout


def test_publish_makes_one_pathspec_commit_with_the_p5_results(tmp_path: Path) -> None:
    repo, env = shipped_repo(tmp_path)
    main_before = git(repo, "rev-parse", "main")
    write(repo, {"notes.txt": "a scratch file nobody staged\n"})
    result = init("publish", str(repo), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert ship_log(repo) == ["chore(init): project-init v3"]
    assert git(repo, "rev-parse", "main") == main_before
    assert git(repo, "status", "--porcelain") == "?? notes.txt\n"  # named paths only (N14)
    assert "not staged .. not project-init's" in result.stdout
    committed = git(repo, "show", "--name-only", "--format=", "HEAD").splitlines()
    for rel in (
        ".project.toml",
        "AGENTS.md",
        "README.md",
        "mise.toml",
        "pyproject.toml",
        "scripts/project.py",
        ".githooks/pre-commit",
        "specs/tech-stack.md",
        "specs/capabilities/cli.md",
        DECISIONS_KEEP,
    ):
        assert rel in committed, rel
    assert "notes.txt" not in committed
    body = git(repo, "log", "-1", "--format=%b")
    assert re.search(
        r"^P5 selftest \(.+\): verify\.json green, \d+ of \d+ checks", body, re.MULTILINE
    )
    assert "- mise run verify: green" in body
    assert 'Happy path: mise run start -- 100 -> "tip: 15.0".' in body
    assert "Probe gaps: none." in body
    assert "committed ... plan/project-init: chore(init): project-init v3" in result.stdout
    assert "remote ...... none (local only)" in result.stdout
    assert "next ........ review, then `! mise run merge`" in result.stdout
    assert "punch list .. git config --global init.defaultBranch main" in result.stdout
    assert "1Password" not in result.stdout  # a knob only; the template's op:// comments no secret

    head = git(repo, "rev-parse", "--short", "HEAD").strip()
    look = init("publish", str(repo), "--dry-run", env=env)  # says what the re-run will do
    assert look.returncode == 0, look.stdout + look.stderr
    assert (
        f"commit ...... chore(init): project-init v3 (already: {head}; nothing new, no amend)"
    ) in look.stdout
    assert "amend ......" not in look.stdout and "P5 selftest (" not in look.stdout
    again = init("publish", str(repo), env=env)  # nothing new: the one commit stands
    assert again.returncode == 0, again.stdout + again.stderr
    assert "(already: " in again.stdout and ship_log(repo) == ["chore(init): project-init v3"]
    assert git(repo, "rev-parse", "--short", "HEAD").strip() == head
    write(repo, {"specs/backlog/later.md": "# later\n"})
    look = init("publish", str(repo), "--dry-run", env=env)
    assert "add 'specs/backlog/later.md'" in look.stdout
    assert "amend ....... chore(init): project-init v3 (on plan/project-init)" in look.stdout
    amended = init("publish", str(repo), env=env)  # a late change joins the ship commit
    assert amended.returncode == 0, amended.stdout + amended.stderr
    assert "(amended)" in amended.stdout and ship_log(repo) == ["chore(init): project-init v3"]
    assert "specs/backlog/later.md" in git(repo, "show", "--name-only", "--format=", "HEAD")


def test_publish_refuses_before_p6_on_a_stale_p5_and_on_the_default_branch(
    tmp_path: Path,
) -> None:
    early = tipcalc_like(tmp_path / "early")
    assert render(early, values=VALUES).returncode == 0
    refused = init("publish", str(early))
    assert refused.returncode == 1 and "P6 has not run" in refused.stderr

    repo, env = shipped_repo(tmp_path)
    ignore = repo / ".gitignore"
    kept = ignore.read_text(encoding="utf-8")
    ignore.write_text(kept + ".claude/settings.json\n", encoding="utf-8")
    shown = init("publish", str(repo), "--dry-run", env=env)
    assert "IGNORED ..... publish refuses until .gitignore stops ignoring:" in shown.stdout
    ignored = init("publish", str(repo), env=env)
    assert ignored.returncode == 1
    assert ".gitignore ignores paths the ship commit needs (.claude/settings.json)" in (
        ignored.stderr
    )
    assert git(repo, "diff", "--cached", "--name-only") == ""  # nothing staged
    ignore.write_text(kept, encoding="utf-8")
    source = repo / "src" / "tipcalc" / "__init__.py"
    source.write_text(source.read_text(encoding="utf-8") + "# changed\n", encoding="utf-8")
    stale = init("publish", str(repo), env=env)
    assert stale.returncode == 1
    assert "publish refused: .agent/project-init/verify.json is stale" in stale.stderr
    git(repo, "checkout", "--", "src")
    git(repo, "stash", "-u", "-q")
    git(repo, "switch", "-q", "main")
    on_main = init("publish", str(repo), env=env)
    assert on_main.returncode == 1 and "HEAD is on main" in on_main.stderr
    assert ship_log(repo) == []


def test_publish_remote_github_creates_pushes_and_resumes_at_the_failed_step(
    tmp_path: Path,
) -> None:
    """The five remote steps against a fake gh, with github.com/test-owner/ rewritten to local
    bare repos. A failed step stops publish and names it; the re-run starts at that step and
    never runs gh repo create again."""
    repo, env = shipped_repo(tmp_path)
    fake = tmp_path / "fakebin" / "gh"
    fake.write_text(FAKE_GH, encoding="utf-8")
    fake.chmod(0o755)
    remotes = tmp_path / "remotes"
    remotes.mkdir()
    fail = tmp_path / "edit-fails"
    fail.touch()
    env = {**env, "FAKE_REMOTES": str(remotes), "FAKE_EDIT_FAIL": str(fail)}
    git(repo, "config", f"url.{remotes}/.insteadOf", "https://github.com/test-owner/")

    first = init("publish", str(repo), "--remote", "github", env=env)
    assert first.returncode == 1, first.stdout + first.stderr
    assert "remote step 5 (settings) failed (exit 1: HTTP 502: Bad Gateway)" in first.stderr
    assert "re-run publish --remote github to continue from step 5" in first.stderr
    bare = remotes / "tipcalc.git"
    assert git(bare, "rev-parse", "main") == git(repo, "rev-parse", "main")
    assert git(bare, "rev-parse", "plan/project-init") == git(repo, "rev-parse", "HEAD")
    assert ship_log(repo) == ["chore(init): project-init v3"]  # the record step amended it
    manifest = tomllib.loads(git(repo, "show", "HEAD:.project.toml"))
    assert manifest["origin_url"] == "https://github.com/test-owner/tipcalc.git"
    # `gh api user` gives no plan with gh's default scopes; the protection API's 403 decides
    assert manifest["server_protection"] == "unavailable: Free private"
    # H31: once the remote exists, the quickstart region opens with its clone line
    readme = git(repo, "show", "HEAD:README.md")
    clone = "git clone https://github.com/test-owner/tipcalc.git && cd tipcalc\n"
    assert "```sh\n" + clone + "curl https://mise.run | sh" in readme
    region = readme[readme.index("<!-- project-init:quickstart:begin") :]
    digest = "sha256:" + hashlib.sha256(region.encode()).hexdigest()
    assert manifest["generated"]["README.md"] == digest
    assert "README.md ... quickstart region rendered again" in first.stdout

    fail.unlink()
    second = init("publish", str(repo), "--remote", "github", env=env)
    assert second.returncode == 0, second.stdout + second.stderr
    assert "settings .... ok" in second.stdout
    assert "(private; unavailable: Free private)" in second.stdout
    assert "server rules: unavailable: Free private" in second.stdout
    calls = (tmp_path / "fake.log").read_text(encoding="utf-8").splitlines()
    assert sum(1 for c in calls if c.startswith("gh repo create tipcalc --private")) == 1
    # recorded once, never retried: the re-run starts at settings
    assert calls.count("gh api repos/test-owner/tipcalc/branches/main/protection") == 1
    assert (
        calls.count(
            "gh repo edit --default-branch main --delete-branch-on-merge --enable-squash-merge"
        )
        == 2
    )
    state = json.loads((repo / ".agent/project-init/publish.json").read_text(encoding="utf-8"))
    assert state["done"] == ["create", "push-default", "record", "push-branch", "settings"]
    assert git(repo, "status", "--porcelain") == ""


# ---------------------------------------------------------------------------------------------
# MIGRATE: transcripts


def v1_layout(root: Path) -> Path:
    ignore = (
        "# Project Memory (personal, not shared)\nproject_memory/sessions/\n"
        "project_memory/pending/\nproject_memory/summaries/\nproject_memory/chromadb/\n"
    )
    repo = make_repo(
        root,
        {
            "app.py": "x = 1\n",
            ".gitignore": ignore,
            "project_memory/accumulated_knowledge.json": "{}\n",
        },
    )
    write(
        repo,
        {
            "project_memory/sessions/2026-01-02.jsonl": (
                '{"role":"user","content":"hello"}\n'
                f'{{"role":"user","content":"my key is {FAKE_AWS_ID} ok"}}\n'
            ),
            "project_memory/pending/session_1.json": '{"summary": "nothing secret"}\n',
            "project_memory/summaries/week.md": "# week\n",
            "project_memory/chromadb/chroma.sqlite3": "binary-ish\n",
        },
    )
    return repo


def test_migrate_transcripts_quarantines_redacts_rescans_and_archives(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "helios")
    status_before = git(repo, "status", "--porcelain")
    qroot = tmp_path / "state" / "quarantine"
    archive = tmp_path / "archive"
    result = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(archive),
        "--quarantine-root",
        str(qroot),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert FAKE_AWS_ID not in result.stdout + result.stderr

    boxes = list(qroot.iterdir())
    assert len(boxes) == 1 and boxes[0].name.startswith("helios-")
    assert stat.S_IMODE(qroot.stat().st_mode) == 0o700
    assert stat.S_IMODE(boxes[0].stat().st_mode) == 0o700
    for name in ("sessions", "pending", "summaries", "chromadb"):
        assert not (repo / "project_memory" / name).exists()
        assert (boxes[0] / "project_memory" / name).is_dir()

    for base in (qroot, archive):
        for path in base.rglob("*"):
            if path.is_file():
                assert FAKE_AWS_ID.encode() not in path.read_bytes(), path
    session = archive / "helios" / "project_memory" / "sessions" / "2026-01-02.jsonl"
    assert "my key is REDACTED:aws-access-token ok" in session.read_text(encoding="utf-8")
    assert (archive / "helios" / "project_memory" / "pending" / "session_1.json").is_file()
    assert (archive / "helios" / "project_memory" / "summaries" / "week.md").is_file()
    assert not (archive / "helios" / "project_memory" / "chromadb").exists()
    assert "aws-access-token  project_memory/sessions/2026-01-02.jsonl" in result.stdout

    assert git(repo, "status", "--porcelain") == status_before == ""
    assert git(repo, "diff", "--cached", "--name-only") == ""
    assert (repo / "project_memory" / "accumulated_knowledge.json").is_file()

    # a re-run finds no store, and says where they went instead of "nothing moved"
    again = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(archive),
        "--quarantine-root",
        str(qroot),
    )
    assert again.returncode == 0, again.stdout + again.stderr
    assert f"done ........ {boxes[0]}: archived to {archive / 'helios'}" in again.stdout
    assert "nothing moved" not in again.stdout


def test_migrate_transcripts_refuses_before_moving_anything(tmp_path: Path) -> None:
    repo = v1_layout(tmp_path / "helios")
    inside = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / "a"),
        "--quarantine-root",
        str(repo / "quarantine"),
    )
    assert inside.returncode == 1
    assert "is a git repo" in inside.stderr
    write(tmp_path, {"a/helios/old.jsonl": "{}\n"})
    taken = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / "a"),
        "--quarantine-root",
        str(tmp_path / "q"),
    )
    assert taken.returncode == 1
    assert "already holds files" in taken.stderr
    assert (repo / "project_memory" / "sessions" / "2026-01-02.jsonl").is_file()
    assert not (tmp_path / "q").exists()


def migrate(repo: Path, tmp_path: Path, tag: str) -> subprocess.CompletedProcess[str]:
    return init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / f"archive-{tag}"),
        "--quarantine-root",
        str(tmp_path / f"state-{tag}" / "quarantine"),
    )


def archive_bytes(folder: Path) -> list[tuple[str, bytes]]:
    return [
        (str(p.relative_to(folder)), p.read_bytes())
        for p in sorted(folder.rglob("*"))
        if p.is_file() and not p.is_symlink()
    ]


GENERIC_KEY = "q7VdN2xLp9Rt4" + "Wz8Ks6Hm3Bc5Fy1Gj0Q"  # split, like FAKE_AWS_ID


def test_migrate_redacts_a_secret_everywhere_it_is_written(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    escaped = json.dumps({"content": f'config: api_key = "{GENERIC_KEY}"'})
    allowed = json.dumps({"content": f"key {FAKE_AWS_ID}, see the gitleaks:allow docs"})
    only_json = json.dumps({"content": f'api_key = "{GENERIC_KEY[::-1]}"'})
    write(
        repo,
        {
            "project_memory/summaries/t.md": f'api_key = "{GENERIC_KEY}"\n',  # gitleaks sees it
            "project_memory/sessions/t.json": escaped + "\n",  # JSON-escaped: gitleaks does not
            "project_memory/sessions/allow.jsonl": allowed + "\n",  # the line allows itself
            "project_memory/pending/only.json": only_json + "\n",  # escaped, and nowhere else
        },
    )
    result = migrate(repo, tmp_path, "t")
    assert result.returncode == 0, result.stdout + result.stderr
    secrets = (GENERIC_KEY, GENERIC_KEY[::-1], FAKE_AWS_ID)
    assert not any(k in result.stdout + result.stderr for k in secrets)
    archived = archive_bytes(tmp_path / "archive-t")
    assert {rel for rel, _ in archived} >= {
        "mg/project_memory/sessions/t.json",
        "mg/project_memory/sessions/allow.jsonl",
        "mg/project_memory/pending/only.json",
        "mg/project_memory/summaries/t.md",
    }
    for rel, data in archived:
        for key in secrets:
            assert key.encode() not in data, rel
    session = tmp_path / "archive-t/mg/project_memory/sessions/t.json"
    assert json.loads(session.read_text(encoding="utf-8")) == {
        "content": 'config: api_key = "REDACTED:generic-api-key"'
    }
    assert "generic-api-key  project_memory/sessions/t.json" in result.stdout
    # three distinct values (the AWS id sits in two files), counted as values, not file pairs
    assert "redacted .... 3 distinct secret value(s) replaced" in result.stdout
    assert "every archived file read" in result.stdout


def test_migrate_never_archives_what_gitleaks_cannot_read(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    token = "ghp_" + "Xk3vB9qLm2Np7Rt4Ws8Yz1Ac5De6Fg0Hj2Kp"
    outside = tmp_path / "outside" / "secret.jsonl"
    write(tmp_path, {"outside/secret.jsonl": json.dumps({"content": f"token {token}"}) + "\n"})
    repo = v1_layout(tmp_path / "mg")
    sessions = repo / "project_memory" / "sessions"
    (sessions / "linked.jsonl").symlink_to(outside)
    (sessions / "linked-folder").symlink_to(outside.parent, target_is_directory=True)
    with gzip.open(sessions / "old.jsonl.gz", "wb") as handle:
        handle.write((json.dumps({"content": f"old token {token}"}) + "\n").encode())
    (sessions / "blob.bin").write_bytes(b"\0\1binary " + token.encode())

    result = migrate(repo, tmp_path, "l")
    # held files are never archived: the run says which and why, archives the rest, exits 1
    assert result.returncode == 1, result.stdout + result.stderr
    assert "project_memory/sessions/linked.jsonl" in result.stdout  # copied in place of the link
    assert "unpacked .... project_memory/sessions/old.jsonl" in result.stdout
    held = result.stdout.split("held back", 1)[1]
    assert "project_memory/sessions/linked-folder: a link to a folder" in held
    assert "project_memory/sessions/blob.bin: binary" in held
    assert "old.jsonl.gz" not in held  # its content is archived; the packed original is kept
    assert (
        "originals ... packed originals kept in .held/: project_memory/sessions/old.jsonl.gz"
        in (result.stdout)
    )
    root = tmp_path / "archive-l" / "mg" / "project_memory" / "sessions"
    names = sorted(p.name for p in root.iterdir())
    assert names == ["2026-01-02.jsonl", "linked.jsonl", "old.jsonl"]
    assert not any(p.is_symlink() for p in root.rglob("*"))
    for rel, data in archive_bytes(tmp_path / "archive-l"):
        assert token.encode() not in data and FAKE_AWS_ID.encode() not in data, rel
    assert "REDACTED:github-pat" in (root / "old.jsonl").read_text(encoding="utf-8")
    assert token in outside.read_text(encoding="utf-8")  # the link's target is never written


def test_migrate_reads_files_that_start_like_a_binary_format(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    token = "ghp_" + "Xk3vB9qLm2Np7Rt4Ws8Yz1Ac5De6Fg0Hj2Kp"
    repo = v1_layout(tmp_path / "mg")
    signed = {
        "project_memory/summaries/pdf.md": f"%PDF-1.4\nkey {FAKE_AWS_ID}\n",
        "project_memory/summaries/rtf.txt": "{\\rtf1 " + f"token {token}\n",
        "project_memory/summaries/exe.md": f"MZ header\ntoken {token}\n",
        "project_memory/sessions/tar.jsonl": "x" * 257 + "ustar" + f" key {FAKE_AWS_ID}\n",
        "project_memory/sessions/iso.md": "y" * 32769 + "CD001" + f" token {token}\n",
    }
    write(repo, signed)
    result = migrate(repo, tmp_path, "sig")
    assert result.returncode == 0, result.stdout + result.stderr
    archived = dict(archive_bytes(tmp_path / "archive-sig"))
    for rel in signed:
        data = archived[f"mg/{rel}"]  # archived, not held back
        assert token.encode() not in data and FAKE_AWS_ID.encode() not in data, rel
        assert b"REDACTED:" in data, rel


def test_migrate_holds_back_a_file_gitleaks_would_not_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """The canary proof: without the head, gitleaks skips a %PDF view, and the padded retry
    reads it; without the pad as well, the run notices it never read that file, holds it back,
    and archives the rest."""
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    module = load_init()

    def run(base: Path) -> tuple[int, str]:
        repo = v1_layout(base / "mg")
        write(repo, {"project_memory/summaries/pdf.md": f"%PDF-1.4\nkey {FAKE_AWS_ID}\n"})
        code = module.main(
            [
                "migrate-transcripts",
                str(repo),
                "--archive-root",
                str(base / "archive"),
                "--quarantine-root",
                str(base / "state" / "quarantine"),
            ]
        )
        return code, capsys.readouterr().out

    monkeypatch.setattr(module, "VIEW_HEAD", "")
    code, out = run(tmp_path / "retry")
    assert code == 0, out  # the first view was skipped; the padded one was read
    pdf = tmp_path / "retry" / "archive" / "mg" / "project_memory" / "summaries" / "pdf.md"
    assert "REDACTED:aws-access-token" in pdf.read_text(encoding="utf-8")

    monkeypatch.setattr(module, "VIEW_PAD", "")
    held = tmp_path / "held"
    code, out = run(held)
    assert code == 1, out  # held back: never archived, so not a success
    assert "project_memory/summaries/pdf.md: gitleaks did not read it" in out
    root = held / "archive" / "mg" / "project_memory"
    assert not (root / "summaries" / "pdf.md").exists()
    assert (root / "summaries" / "week.md").is_file()
    for rel, data in archive_bytes(held / "archive"):
        assert FAKE_AWS_ID.encode() not in data, rel


def test_the_quarantine_root_is_never_rechmoded_or_left_half_made(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    shared = tmp_path / "shared"
    shared.mkdir(mode=0o755)
    shared.chmod(0o755)
    result = init(
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / "archive"),
        "--quarantine-root",
        str(shared),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert stat.S_IMODE(shared.stat().st_mode) == 0o755  # the user's folder keeps its mode
    boxes = list(shared.iterdir())
    assert len(boxes) == 1 and stat.S_IMODE(boxes[0].stat().st_mode) == 0o700

    other = v1_layout(tmp_path / "other")
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o555)
    try:
        refused = init(
            "migrate-transcripts",
            str(other),
            "--archive-root",
            str(tmp_path / "archive-2"),
            "--quarantine-root",
            str(locked),
        )
    finally:
        locked.chmod(0o755)
    assert refused.returncode == 1, refused.stdout + refused.stderr
    assert "quarantine refused" in refused.stderr and "Traceback" not in refused.stderr
    assert list(locked.iterdir()) == []
    assert (other / "project_memory" / "sessions" / "2026-01-02.jsonl").is_file()


def test_migrate_refuses_tracked_or_linked_stores_and_moves_nothing(tmp_path: Path) -> None:
    repo = make_repo(
        tmp_path / "tracked",
        {"app.py": "x = 1\n", "project_memory/sessions/s.jsonl": "{}\n"},
    )
    result = migrate(repo, tmp_path, "tr")
    assert result.returncode == 1
    assert "git tracks files in the legacy stores (project_memory/sessions/s.jsonl)" in (
        result.stderr
    )
    assert git(repo, "status", "--porcelain") == ""
    assert not (tmp_path / "state-tr").exists()

    linked = v1_layout(tmp_path / "linked")
    store = tmp_path / "elsewhere"
    store.mkdir()
    shutil.move(str(linked / "project_memory" / "pending"), str(store / "pending"))
    (linked / "project_memory" / "pending").symlink_to(store / "pending")
    result = migrate(linked, tmp_path, "ln")
    assert result.returncode == 1
    assert "a linked store; nothing moved" in result.stderr
    assert (linked / "project_memory" / "sessions" / "2026-01-02.jsonl").is_file()


def test_an_empty_store_migrates_and_a_rerun_is_not_blocked(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = make_repo(tmp_path / "mg", {"app.py": "x = 1\n", ".gitignore": "project_memory/\n"})
    for _ in range(2):
        (repo / "project_memory" / "sessions").mkdir(parents=True)
        result = migrate(repo, tmp_path, "e")
        assert result.returncode == 0, result.stdout + result.stderr
        assert (tmp_path / "archive-e" / "mg" / "project_memory" / "sessions").is_dir()
        assert not (repo / "project_memory" / "sessions").exists()


def test_an_empty_archive_folder_does_not_block_a_rerun(tmp_path: Path) -> None:
    module = load_init()
    empty = tmp_path / "archive" / "mg" / "project_memory" / "sessions"
    empty.mkdir(parents=True)
    assert module.holds_files(tmp_path / "archive" / "mg") is False
    (empty / "x.jsonl").write_text("{}\n", encoding="utf-8")
    assert module.holds_files(tmp_path / "archive" / "mg") is True


def chunk_cut_transcripts(repo: Path, module: ModuleType) -> tuple[str, list[str]]:
    """Two transcripts built on gitleaks 8.30's chunk cuts (100,000 bytes plus a 25,000-byte
    peek, then about every 28.7 KB, when no blank line is in reach). big.jsonl puts a fake key at
    byte 124,990 of both the raw file and its view: line 1 decodes to no string, and it is as
    long as the view's head, which takes its place. dense.md packs distinct keys, so one
    straddles every later cut. Returns (that first key, the dense keys)."""
    first = module.canary()
    zeros = (len(module.VIEW_HEAD) - 4) // 2
    line1 = "[" + "0," * zeros + "0]"
    assert len(line1) + 1 == len(module.VIEW_HEAD)
    line2 = "x" * (124_989 - len(module.VIEW_HEAD)) + " " + first + " " + "y" * 60000
    raw = f"{line1}\n{line2}\n"
    assert raw.index(first) == 124_990
    assert (module.VIEW_HEAD + line2).index(first) == 124_990
    dense = [module.canary() for _ in range(12_000)]  # about 250 KB: cuts at 125 K, 153.7 K, ...
    write(
        repo,
        {
            "project_memory/sessions/big.jsonl": raw,
            "project_memory/summaries/dense.md": " ".join(dense) + "\n",
        },
    )
    return first, dense


def test_migrate_finds_keys_that_straddle_gitleaks_chunk_cuts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    gitleaks = need(gitleaks_cmd(), "gitleaks is not runnable here")
    module = load_init()
    repo = v1_layout(tmp_path / "mg")
    first, dense = chunk_cut_transcripts(repo, module)

    # the cases are real: gitleaks on the files as they are misses keys at the cuts
    report = tmp_path / "raw.json"
    subprocess.run(
        [*gitleaks, "dir", str(repo / "project_memory"), "-f", "json", "-r", str(report)]
        + ["--no-banner", "--exit-code", "0", "--log-level", "error"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    seen = {f["Secret"] for f in json.loads(report.read_text(encoding="utf-8"))}
    assert first not in seen
    assert any(key not in seen for key in dense)

    result = migrate(repo, tmp_path, "cut")
    assert result.returncode == 0, result.stdout + result.stderr
    archived = archive_bytes(tmp_path / "archive-cut")
    assert {rel for rel, _ in archived} >= {
        "mg/project_memory/sessions/big.jsonl",
        "mg/project_memory/summaries/dense.md",
    }
    blob = b"".join(data for _, data in archived)
    assert first.encode() not in blob
    missed = [key for key in dense if key.encode() in blob]
    assert missed == []
    assert b"REDACTED:aws-access-token" in blob

    # the control: one whole view per file (no pieces) archives the first key and says clean
    monkeypatch.setattr(module, "PIECE_BYTES", 1 << 40)
    control = v1_layout(tmp_path / "control" / "mg")
    first, _ = chunk_cut_transcripts(control, module)
    code = module.main(
        [
            "migrate-transcripts",
            str(control),
            "--archive-root",
            str(tmp_path / "archive-control"),
            "--quarantine-root",
            str(tmp_path / "state-control" / "quarantine"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0 and "rescan clean" in out
    leaked = dict(archive_bytes(tmp_path / "archive-control"))[
        "mg/project_memory/sessions/big.jsonl"
    ]
    assert first.encode() in leaked


def test_a_rerun_reports_an_unfinished_quarantine_and_otherwise_moves_nothing(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "mg", {"app.py": "x = 1\n"})
    fresh = migrate(repo, tmp_path, "u")
    assert fresh.returncode == 0 and "nothing moved" in fresh.stdout
    (tmp_path / "state-u" / "quarantine" / "mg-2026-01-01").mkdir(parents=True)  # no record
    result = migrate(repo, tmp_path, "u")
    assert result.returncode == 1, result.stdout
    assert "UNKNOWN ..... " in result.stdout and "no finished run recorded" in result.stdout
    assert "nothing moved" not in result.stdout


HIDDEN_AWS_ID = "AKIA" + "ZT4RWB6YNQ3KMVXC"  # a second key, only ever written base64-encoded
HIDDEN_BLOB = base64.b64encode(
    f"config: aws_access_key_id = {HIDDEN_AWS_ID} more text here".encode()
).decode()  # gitleaks decodes it; redaction cannot


def with_encoded_transcript(repo: Path) -> None:
    """A transcript whose only secret is written base64-encoded: migrate must hold it back."""
    encoded = json.dumps({"content": f"blob {HIDDEN_BLOB} end"}) + "\n"
    write(repo, {"project_memory/sessions/encoded.jsonl": encoded})


def test_migrate_holds_a_secret_it_cannot_replace_and_a_rerun_says_so(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    hidden, blob = HIDDEN_AWS_ID, HIDDEN_BLOB
    with_encoded_transcript(repo)
    result = migrate(repo, tmp_path, "d")
    assert result.returncode == 1, result.stdout + result.stderr
    held = result.stdout.split("held back", 1)[1]
    assert (
        "project_memory/sessions/encoded.jsonl: aws-access-token: found only in a decoded form"
    ) in held
    assert "aws-access-token  project_memory/sessions/encoded.jsonl  (held back)" in result.stdout
    assert "FAIL" not in result.stdout  # the rest is archived, redacted
    # one value was replaced (FAKE_AWS_ID, in 2026-01-02.jsonl); the hidden one sits in the held
    # file only, and is counted as such, never as replaced
    assert "redacted .... 1 distinct secret value(s) replaced" in result.stdout
    assert "in 1 file(s)" in result.stdout
    assert "; 1 more found only in held-back file(s)" in result.stdout
    (quarantine,) = list((tmp_path / "state-d" / "quarantine").iterdir())
    assert (quarantine / ".held" / "project_memory" / "sessions" / "encoded.jsonl").is_file()
    archive = tmp_path / "archive-d" / "mg" / "project_memory"
    assert not (archive / "sessions" / "encoded.jsonl").exists()
    session = (archive / "sessions" / "2026-01-02.jsonl").read_text(encoding="utf-8")
    assert "REDACTED:aws-access-token" in session
    for rel, data in archive_bytes(tmp_path / "archive-d"):
        assert FAKE_AWS_ID.encode() not in data and blob.encode() not in data, rel
        assert hidden.encode() not in data, rel

    again = migrate(repo, tmp_path, "d")  # no store left in the repo
    assert again.returncode == 1, again.stdout
    assert "nothing moved" not in again.stdout
    assert f"HELD ........ {quarantine}: archived to" in again.stdout
    assert "project_memory/sessions/encoded.jsonl: aws-access-token" in again.stdout


def test_resume_needs_an_unfinished_unlocked_quarantine_and_an_empty_archive(
    tmp_path: Path,
) -> None:
    """--resume refuses with nothing to resume, while another run holds the quarantine's lock
    (a re-run reports that one RUNNING), and while the archive already holds files."""
    repo = make_repo(tmp_path / "mg", {"app.py": "x = 1\n"})
    nothing = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"), capture_output=True, text=True, check=False
    )
    assert nothing.returncode == 1 and "no unfinished migrate of this repo" in nothing.stderr

    quarantine = tmp_path / "state" / "quarantine" / "mg-2026-01-01"
    (quarantine / "project_memory" / "sessions").mkdir(parents=True)
    (quarantine / "project_memory" / "sessions" / "s.jsonl").write_text("{}\n", encoding="utf-8")
    record = {"repo": str(repo), "archive": str(tmp_path / "archive" / "mg"), "state": "moving"}
    (quarantine / "project-init-migrate.json").write_text(json.dumps(record), encoding="utf-8")
    (quarantine / ".work" / "views").mkdir(parents=True)
    with (quarantine / "project-init-migrate.lock").open("w") as held:
        fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)  # a run working in it right now
        report = subprocess.run(
            migrate_argv(repo, tmp_path), capture_output=True, text=True, check=False
        )
        busy = subprocess.run(
            migrate_argv(repo, tmp_path, "--resume"), capture_output=True, text=True, check=False
        )
    assert report.returncode == 1
    assert f"RUNNING ..... {quarantine}: a migrate run is working in it" in report.stdout
    assert (quarantine / ".work").is_dir()  # a live run's views are never touched
    assert busy.returncode == 1 and "another migrate run is working in it" in busy.stderr

    write(tmp_path, {"archive/mg/old.jsonl": "{}\n"})
    taken = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"), capture_output=True, text=True, check=False
    )
    assert taken.returncode == 1
    assert "already holds files (an earlier archive copy)" in taken.stderr
    assert (quarantine / "project_memory" / "sessions" / "s.jsonl").is_file()


def test_a_view_costs_its_bytes_not_a_pad_per_file(tmp_path: Path) -> None:
    """3,000 small transcripts: each view is the file's decoded text, the head and a canary, so
    the work folder stays near the store's size. The 40 KB pad goes only into the retry views of
    a file whose first view gitleaks skipped, and it is spaces: gitleaks indexes newlines."""
    module = load_init()
    quarantine = tmp_path / "q"
    store = quarantine / "project_memory" / "sessions"
    store.mkdir(parents=True)
    body = json.dumps({"role": "user", "content": "hello"}) + "\n"
    files = []
    for i in range(3000):
        path = store / f"s{i:04d}.json"
        path.write_text(body, encoding="utf-8")
        files.append(path)
    views = module.build_views(quarantine, files, tmp_path / "views", module.VIEW_HEAD)
    assert len(views) == 3000
    total = sum(p.stat().st_size for p in (tmp_path / "views").iterdir())
    assert total <= 3000 * (len(body) + len(module.VIEW_HEAD) + 32)
    module.build_views(quarantine, files[:1], tmp_path / "padded", module.VIEW_PAD)
    (padded,) = (tmp_path / "padded").iterdir()
    data = padded.read_bytes()
    assert data.startswith(b" " * 32774) and b"\n" not in data[: len(module.VIEW_PAD) - 1]


def test_many_small_transcripts_migrate_in_seconds(tmp_path: Path) -> None:
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    module = load_init()
    repo = v1_layout(tmp_path / "mg")
    keys = []
    files = {}
    for i in range(2000):
        content = f"message {i}"
        if i % 400 == 0:
            keys.append(module.canary())
            content += f" key {keys[-1]}"
        files[f"project_memory/sessions/s{i:04d}.json"] = json.dumps({"content": content}) + "\n"
    write(repo, files)
    started = time.monotonic()
    result = migrate(repo, tmp_path, "many")
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stdout + result.stderr
    assert elapsed < 45, f"{elapsed:.1f} s"  # a 40 KB newline pad per view took about 60 s
    blob = b"".join(data for _, data in archive_bytes(tmp_path / "archive-many"))
    assert not [key for key in keys if key.encode() in blob]
    assert blob.count(b"REDACTED:aws-access-token") >= len(keys)


SLOW_GITLEAKS = """#!/usr/bin/env python3
import json
import os
import sys
import time

real = json.loads(os.environ["REAL_GITLEAKS"])
views = sys.argv[1:2] == ["dir"] and sys.argv[2].endswith("/views")
if views and os.path.exists(os.environ["SLOW_FLAG"]):
    count = os.environ["SLOW_MARK"] + ".views"
    seen = 1 + (int(open(count).read()) if os.path.exists(count) else 0)
    with open(count, "w") as handle:
        handle.write(str(seen))
    if seen >= int(os.environ.get("SLOW_FROM", "1")):
        with open(os.environ["SLOW_MARK"], "w") as handle:
            handle.write(str(os.getpid()))
        time.sleep(600)
os.execvp(real[0], [*real, *sys.argv[1:]])
"""


def slow_gitleaks(tmp_path: Path) -> tuple[dict[str, str], Path, Path]:
    """A gitleaks on PATH that hangs on the view scan while SLOW_FLAG exists, else the real
    one. Returns (the env for init.py, the flag, the mark it writes its pid to)."""
    real = gitleaks_cmd()
    assert real is not None
    if real == ["gitleaks"]:
        found = shutil.which("gitleaks")
        assert found is not None
        real = [found]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "gitleaks"
    fake.write_text(SLOW_GITLEAKS, encoding="utf-8")
    fake.chmod(0o755)
    flag, mark = tmp_path / "slow", tmp_path / "scanning.pid"
    flag.touch()
    temp = tmp_path / "tmp"
    temp.mkdir()
    env = clean_env(
        PATH=f"{bin_dir}{os.pathsep}{os.environ['PATH']}",
        REAL_GITLEAKS=json.dumps(real),
        SLOW_FLAG=str(flag),
        SLOW_MARK=str(mark),
        TMPDIR=str(temp),
    )
    return env, flag, mark


def migrate_argv(repo: Path, tmp_path: Path, *extra: str) -> list[str]:
    return [
        sys.executable,
        str(INIT),
        "migrate-transcripts",
        str(repo),
        "--archive-root",
        str(tmp_path / "archive"),
        "--quarantine-root",
        str(tmp_path / "state" / "quarantine"),
        *extra,
    ]


def stop_mid_scan(
    repo: Path, tmp_path: Path, env: dict[str, str], mark: Path, how: signal.Signals
) -> tuple[subprocess.CompletedProcess[str], int]:
    """Start a migrate, wait until gitleaks is on the views, send it `how`. Returns (the run,
    the pid of the gitleaks that was scanning)."""
    proc = subprocess.Popen(
        migrate_argv(repo, tmp_path),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    deadline = time.monotonic() + 300
    while not (mark.is_file() and mark.read_text(encoding="utf-8").strip()):
        assert proc.poll() is None, proc.communicate()
        assert time.monotonic() < deadline, "the view scan never started"
        time.sleep(0.1)
    proc.send_signal(how)
    out, err = proc.communicate(timeout=120)
    return subprocess.CompletedProcess(proc.args, proc.returncode, out, err), int(
        mark.read_text(encoding="utf-8")
    )


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return Path(f"/proc/{pid}").exists() and "zombie" not in (
        Path(f"/proc/{pid}/status").read_text(encoding="utf-8").lower()
        if Path(f"/proc/{pid}/status").exists()
        else ""
    )


def test_sigterm_mid_scan_removes_the_views_and_resume_finishes(tmp_path: Path) -> None:
    """A Bash-tool timeout sends SIGTERM. The decoded views live in the quarantine's .work/,
    never in $TMPDIR, and the signal runs the cleanup: gitleaks killed, .work/ removed, the
    state `failed` with the reason. A re-run says so; --resume finishes the archive."""
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    env, flag, mark = slow_gitleaks(tmp_path)
    stopped, scanner = stop_mid_scan(repo, tmp_path, env, mark, signal.SIGTERM)
    assert stopped.returncode == 128 + signal.SIGTERM, stopped.stdout + stopped.stderr
    assert "stopped by SIGTERM" in stopped.stderr and "--resume" in stopped.stderr
    (quarantine,) = list((tmp_path / "state" / "quarantine").iterdir())
    assert not (quarantine / ".work").exists()
    assert not alive(scanner)
    assert [p.name for p in (tmp_path / "tmp").iterdir() if p.name.startswith("project-init")] == []
    state = json.loads((quarantine / "project-init-migrate.json").read_text(encoding="utf-8"))
    assert state["state"] == "failed" and state["why"] == "stopped by SIGTERM"
    assert not (tmp_path / "archive").exists()

    again = subprocess.run(
        migrate_argv(repo, tmp_path), capture_output=True, text=True, env=env, check=False
    )
    assert again.returncode == 1, again.stdout + again.stderr
    assert f"FAILED ...... {quarantine}: stopped by SIGTERM; nothing was archived" in again.stdout
    assert "--resume" in again.stdout

    flag.unlink()
    done = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert f"resume ...... {quarantine}: project_memory/sessions" in done.stdout
    session = tmp_path / "archive" / "mg" / "project_memory" / "sessions" / "2026-01-02.jsonl"
    assert "REDACTED:aws-access-token" in session.read_text(encoding="utf-8")
    for rel, data in archive_bytes(tmp_path / "archive"):
        assert FAKE_AWS_ID.encode() not in data, rel
    assert not (quarantine / ".work").exists()
    state = json.loads((quarantine / "project-init-migrate.json").read_text(encoding="utf-8"))
    assert state["state"] == "archived"


def test_a_stop_after_the_redaction_keeps_the_rotation_list_for_resume(tmp_path: Path) -> None:
    """The first round has already replaced the key in place when the rescan is stopped, so
    no later scan can find it again. The (rule, file) pair was journaled in the state before
    that write, and --resume still lists it under rotate."""
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    env, flag, mark = slow_gitleaks(tmp_path)
    env["SLOW_FROM"] = "2"  # the first view scan runs; the rescan after the redaction hangs
    stopped, _ = stop_mid_scan(repo, tmp_path, env, mark, signal.SIGTERM)
    assert stopped.returncode == 128 + signal.SIGTERM, stopped.stdout + stopped.stderr
    (quarantine,) = list((tmp_path / "state" / "quarantine").iterdir())
    rel = "project_memory/sessions/2026-01-02.jsonl"
    text = (quarantine / rel).read_text(encoding="utf-8")
    assert "REDACTED:aws-access-token" in text and FAKE_AWS_ID not in text  # redacted, then cut
    state = json.loads((quarantine / "project-init-migrate.json").read_text(encoding="utf-8"))
    assert state["state"] == "failed" and ["aws-access-token", rel] in state["rotate"]

    flag.unlink()
    done = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "0 distinct secret value(s) replaced" in done.stdout
    assert "1 more file(s) redacted by the run that stopped" in done.stdout
    assert f"\n{' ' * 14}aws-access-token  {rel}" in done.stdout.split("rotate ......", 1)[1]


def test_a_stop_right_after_a_hold_keeps_the_held_file_on_the_rotation_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A held file is never scanned again, so its (rule, file) pair must be in the state before
    the file moves into .held/. The run here stops as the redaction starts: the file is held,
    nothing is redacted or journaled by redact() yet. --resume still lists the held pair under
    rotate, next to the pair it redacts itself."""
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    with_encoded_transcript(repo)
    module = load_init()

    def stop_as_redaction_starts(*_args: object) -> None:
        raise module.Stopped(signal.SIGTERM)  # what the SIGTERM handler raises, right here

    monkeypatch.setattr(module, "redact", stop_as_redaction_starts)
    assert module.main(migrate_argv(repo, tmp_path)[2:]) == 128 + signal.SIGTERM
    (quarantine,) = list((tmp_path / "state" / "quarantine").iterdir())
    held = "project_memory/sessions/encoded.jsonl"
    assert (quarantine / ".held" / held).is_file()
    state = json.loads((quarantine / "project-init-migrate.json").read_text(encoding="utf-8"))
    assert state["state"] == "failed" and state["why"] == "stopped by SIGTERM"
    assert held in state["held"]
    assert state["rotate"] == [["aws-access-token", held]]

    done = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"),
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
    )
    assert done.returncode == 1, done.stdout + done.stderr  # still held: exit 1
    rotate = done.stdout.split("rotate ......", 1)[1]
    assert f"aws-access-token  {held}  (held back)" in rotate
    assert "aws-access-token  project_memory/sessions/2026-01-02.jsonl" in rotate
    for rel, data in archive_bytes(tmp_path / "archive"):
        assert FAKE_AWS_ID.encode() not in data and HIDDEN_BLOB.encode() not in data, rel
    state = json.loads((quarantine / "project-init-migrate.json").read_text(encoding="utf-8"))
    assert state["state"] == "held" and ["aws-access-token", held] in state["rotate"]


def test_sigkill_mid_scan_leaves_views_only_in_the_quarantine_until_the_rerun(
    tmp_path: Path,
) -> None:
    """SIGKILL runs no cleanup: the views stay, but in the mode-700 quarantine next to the
    stores they were decoded from, never in $TMPDIR. The next run removes them and says so; a
    fresh run refuses while the quarantine is unfinished; --resume moves the store that
    appeared since and finishes."""
    if not gitleaks_available():
        pytest.skip("gitleaks is not runnable here")
    repo = v1_layout(tmp_path / "mg")
    shutil.rmtree(repo / "project_memory" / "summaries")
    env, flag, mark = slow_gitleaks(tmp_path)
    killed, scanner = stop_mid_scan(repo, tmp_path, env, mark, signal.SIGKILL)
    try:
        assert killed.returncode == -signal.SIGKILL
    finally:
        if alive(scanner):  # its own process group: the kill never reached it
            os.kill(scanner, signal.SIGKILL)
    (quarantine,) = list((tmp_path / "state" / "quarantine").iterdir())
    views = quarantine / ".work" / "views"
    assert any(FAKE_AWS_ID.encode() in p.read_bytes() for p in views.iterdir())
    assert stat.S_IMODE(quarantine.stat().st_mode) == 0o700
    assert [p.name for p in (tmp_path / "tmp").iterdir() if p.name.startswith("project-init")] == []

    again = subprocess.run(
        migrate_argv(repo, tmp_path), capture_output=True, text=True, env=env, check=False
    )
    assert again.returncode == 1, again.stdout + again.stderr
    assert f"UNFINISHED .. {quarantine}: the run never recorded an end" in again.stdout
    assert "removed its leftover .work/ (decoded views of the transcripts)" in again.stdout
    assert not (quarantine / ".work").exists()

    write(repo, {"project_memory/summaries/new.md": f"key {FAKE_AWS_ID}\n"})
    refused = subprocess.run(
        migrate_argv(repo, tmp_path), capture_output=True, text=True, env=env, check=False
    )
    assert refused.returncode == 1
    assert "holds an unfinished migrate of this repo (state moving)" in refused.stderr
    assert "--resume" in refused.stderr
    assert (repo / "project_memory" / "summaries" / "new.md").is_file()
    assert len(list((tmp_path / "state" / "quarantine").iterdir())) == 1

    flag.unlink()
    done = subprocess.run(
        migrate_argv(repo, tmp_path, "--resume"),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert "(project_memory/summaries moved in now)" in done.stdout
    assert not (repo / "project_memory" / "summaries").exists()
    archived = dict(archive_bytes(tmp_path / "archive"))
    assert "mg/project_memory/summaries/new.md" in archived
    for rel, data in archived.items():
        assert FAKE_AWS_ID.encode() not in data, rel
    assert not (quarantine / ".work").exists()


# ---------------------------------------------------------------------------------------------
# P5: selftest and verify.json; P6: the front door

FAKE_MISE = """#!/usr/bin/env python3
import os
import sys
import time

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write("mise " + " ".join(args) + "\\n")
if args[:2] == ["run", "verify"] and os.environ.get("FAKE_VERIFY_SLEEP"):
    time.sleep(float(os.environ["FAKE_VERIFY_SLEEP"]))
if args[:2] == ["run", "start"]:
    rest = args[3:] if args[2:3] == ["--"] else args[2:]
    if rest == ["--help"]:
        print("Traceback (most recent call last):\\nValueError", file=sys.stderr)
        sys.exit(1)
    print(os.environ.get("FAKE_START_OUT", "tip: 15.0"))
    sys.exit(0)
if args[:1] == ["run"] and args[1] in os.environ.get("FAKE_FAIL", "").split(","):
    print(args[1] + ": failed", file=sys.stderr)
    sys.exit(1)
sys.exit(0)
"""
FAKE_UV = """#!/usr/bin/env python3
import os
import sys

args = sys.argv[1:]
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write("uv " + " ".join(args) + "\\n")
if args == ["--version"]:
    print("uv 0.12.10")
    sys.exit(0)
if args[:4] == ["run", "--script", "scripts/project.py", "selftest"]:
    print("selftest: ok (fake matrix)")
    sys.exit(int(os.environ.get("FAKE_MATRIX_EXIT", "0")))
sys.exit(2)
"""


def fake_tools(tmp_path: Path, *, uv: bool = True, **extra: str) -> dict[str, str]:
    """An env whose `mise` (and `uv`) are fakes that log their argv: P5 without a network."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    for name, text in (("mise", FAKE_MISE), *((("uv", FAKE_UV),) if uv else ())):
        (bin_dir / name).write_text(text, encoding="utf-8")
        (bin_dir / name).chmod(0o755)
    log = tmp_path / "fake.log"
    return clean_env(PATH=f"{bin_dir}:{os.environ['PATH']}", FAKE_LOG=str(log), **extra)


def verify_record(repo: Path) -> dict[str, object]:
    data = json.loads((repo / ".agent/project-init/verify.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def verify_checks(repo: Path) -> list[dict[str, object]]:
    checks = verify_record(repo)["checks"]
    assert isinstance(checks, list)
    return checks


def test_selftest_runs_the_positive_checks_then_relays_the_matrix(tmp_path: Path) -> None:
    repo = tmp_path / "rendered"
    write(
        repo,
        {
            "scripts/project.py": (
                '# /// script\n# requires-python = ">=3.12"\n# dependencies = []\n# ///\n'
                "import sys\n\nsys.exit(7 if sys.argv[1:] == ['selftest'] else 0)\n"
            ),
            "specs/mission.md": "# m\n",
        },
    )
    env = fake_tools(tmp_path, uv=False)  # the real uv runs the stub project.py
    result = init("selftest", str(repo), "--start-args", "100", env=env)
    assert result.returncode == 7, result.stdout + result.stderr
    log = (tmp_path / "fake.log").read_text(encoding="utf-8").splitlines()
    assert log == [
        "mise install",
        "mise run doctor",
        "mise run verify",
        "mise tasks ls",
        "mise run status",
        "mise run change -- --help",
        "mise run backlog -- --help",
        "mise run tdd -- --help",
        "mise run proof -- --help",
        "mise run start -- --help",
        "mise x -- gitleaks dir --no-banner --redact -c .gitleaks.toml specs",
        "mise run start -- 100",
    ]
    assert "  gap   mise run start -- --help (exit 1" in result.stdout
    assert 'happy path .. mise run start -- 100 -> "tip: 15.0"' in result.stdout
    record = verify_record(repo)
    assert record["green"] is False
    assert record["matrix"] == {
        "argv": ["uv", "run", "--script", "scripts/project.py", "selftest"],
        "exit": 7,
        "green": False,
    }
    assert record["start"] == {
        "args": ["100"],
        "command": "mise run start -- 100",
        "output": "tip: 15.0",
        "green": True,
    }

    failing = fake_tools(tmp_path, FAKE_FAIL="verify")
    result = init("selftest", str(repo), "--start-args", "100", env=failing)
    assert result.returncode == 1, result.stdout
    assert "  FAIL  mise run verify (exit 1" in result.stdout
    assert verify_record(repo)["green"] is False

    shutil.rmtree(repo / "scripts")
    missing = init("selftest", str(repo), env=env)
    assert missing.returncode == 1
    assert "scripts/project.py is missing" in missing.stderr


def test_selftest_names_an_untrusted_mise_config(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "uv"
    shim.write_text(
        "#!/bin/sh\necho 'mise ERROR Config files in /x/mise.toml are not trusted.' >&2\nexit 1\n",
        encoding="utf-8",
    )
    shim.chmod(0o755)
    repo = tmp_path / "rendered"
    write(repo, {"scripts/project.py": "print(1)\n"})
    result = init("selftest", str(repo), env=clean_env(PATH=f"{bin_dir}:/usr/bin:/bin"))
    assert result.returncode == 1
    assert "Run `mise trust` in" in result.stderr
    assert not (repo / ".agent").exists()


def test_selftest_dry_runs_the_release_of_a_distributable_project(tmp_path: Path) -> None:
    repo = tmp_path / "rendered"
    stack = TECH_STACK.replace("## Distribution\nnone", "## Distribution\npypi")
    write(repo, {"scripts/project.py": STUB_PROJECT, "specs/tech-stack.md": stack})
    env = fake_tools(tmp_path, uv=False)  # the real uv runs the stub project.py
    result = init("selftest", str(repo), "--start-args", "100", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    log = (tmp_path / "fake.log").read_text(encoding="utf-8").splitlines()
    assert "mise x -- uv version --bump patch --dry-run" in log
    assert "mise x -- git-cliff --bumped-version" in log
    (build,) = [ln for ln in log if ln.startswith("mise x -- uv build -o ")]
    out_dir = Path(build.removeprefix("mise x -- uv build -o "))
    assert not out_dir.is_relative_to(repo) and not out_dir.parent.exists()  # $TMPDIR, removed
    assert log[-1] == "mise run start -- 100"  # the happy path stays last
    names = [c["name"] for c in verify_checks(repo)]
    assert "uv build -o $TMPDIR" in names and "git cliff --bumped-version" in names


def test_selftest_takes_the_probe_pass_row_when_no_readme_fence_names_one(tmp_path: Path) -> None:
    if not userns():
        pytest.skip("no user namespaces: the probe cannot run")
    repo = tipcalc_like(tmp_path / "tipcalc")  # its README has no fence
    write(repo, {"scripts/project.py": STUB_PROJECT})
    env = fake_tools(tmp_path, uv=False)
    result = init("selftest", str(repo), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "happy args .. 100, from the probe's pass row (guessed args: no README fence)" in (
        result.stdout
    )
    log = (tmp_path / "fake.log").read_text(encoding="utf-8").splitlines()
    assert log[-1] == "mise run start -- 100"
    start = verify_record(repo)["start"]
    assert isinstance(start, dict) and start["args"] == ["100"]


FLOOD = """import sys
print("FIRST")
block = "x" * 1023 + "\\n"
for _ in range(300 * 1024):  # 300 MB
    sys.stdout.write(block)
print("LAST")
print("err-first", file=sys.stderr)
"""
MEASURE = """import importlib.util, resource, sys
spec = importlib.util.spec_from_file_location("init_script", sys.argv[1])
module = importlib.util.module_from_spec(spec)
sys.modules["init_script"] = module
spec.loader.exec_module(module)
result = module.run([sys.executable, sys.argv[2]], timeout=300, own_group=True)
print(result.code, len(result.out), result.out.startswith("FIRST"),
      result.out.rstrip().endswith("LAST"), "bytes not kept" in result.out,
      result.err.strip(), resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
"""


def test_child_output_is_bounded_to_a_head_and_a_tail(tmp_path: Path) -> None:
    """A child that floods stdout (300 MB here) costs the probe and selftest a bounded buffer:
    communicate() held it all (931 MB peak for this flood)."""
    write(tmp_path, {"flood.py": FLOOD, "measure.py": MEASURE})
    done = subprocess.run(
        [sys.executable, str(tmp_path / "measure.py"), str(INIT), str(tmp_path / "flood.py")],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert done.returncode == 0, done.stderr
    code, size, first, last, marked, err, peak_kb = done.stdout.split()
    assert (code, first, last, marked, err) == ("0", "True", "True", "True", "err-first")
    assert int(size) < 200_000
    assert int(peak_kb) < 150_000


def front_door_repo(
    tmp_path: Path, extra: dict[str, str] | None = None
) -> tuple[Path, dict[str, str]]:
    """tipcalc on plan/project-init after P4 (render) and a green P5 (fake tools)."""
    repo = tipcalc_like(tmp_path / "tipcalc", extra)
    assert render(repo, values=VALUES).returncode == 0
    env = fake_tools(tmp_path)
    done = init("selftest", str(repo), "--start-args", "100", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    return repo, env


QUICKSTART = """<!-- project-init:quickstart:begin (tool-owned: the next project-init run replaces this region and shows the diff) -->
## Quickstart

```sh
curl https://mise.run | sh      # once per machine
mise install                    # tools, dependencies, git hooks
mise run verify                 # green = ready
mise run start -- 100           # tip: 15.0
```

How changes are made: `specs/README.md`. Agents start at `AGENTS.md`.
At merge a human reads the trunk diff and skims the rest against the change's `proof/` folder.
<!-- project-init:quickstart:end -->
"""  # the region exactly as design 6.P6 prints it


def test_the_front_door_is_built_from_green_p5_commands(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "early")
    assert render(repo, values=VALUES).returncode == 0
    before = tree_hash(repo)
    early = render(repo, "--front-door")
    assert early.returncode == 1 and "no .agent/project-init/verify.json" in early.stderr
    assert tree_hash(repo) == before

    repo, _ = front_door_repo(tmp_path)
    result = render(repo, "--front-door")
    assert result.returncode == 0, result.stdout + result.stderr
    agents = (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert len(agents.splitlines()) <= 40
    assert not PLACEHOLDER.search(agents)
    assert "Run the app: `mise run start -- 100`." in agents
    assert '(`@pytest.mark.spec("cli.tip-default")`)' in agents
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert readme == "# tipcalc\n\nTiny CLI that computes a tip.\n\n" + QUICKSTART
    assert "+mise run start -- 100           # tip: 15.0" in result.stdout  # the diff is shown
    hashes = generated(repo)
    region = hashlib.sha256(QUICKSTART.encode()).hexdigest()
    assert hashes["README.md"] == f"sha256:{region}"  # the region, not the whole README
    assert hashes["AGENTS.md"] == "sha256:" + hashlib.sha256(agents.encode()).hexdigest()

    assert "render --check: 0 drift (2 of 2 files" in render(repo, "--front-door", "--check").stdout
    check = render(repo, "--check")
    assert check.returncode == 0 and "0 drift (24 of 24 files match)" in check.stdout
    again = render(repo)  # the machinery render keeps P6's files and hashes
    assert again.returncode == 0 and again.stdout.strip().endswith("render: 0 changes")
    assert generated(repo) == hashes

    # a new happy path: the region is replaced where it is, the rest of the README stays
    (repo / "README.md").write_text(readme + "\n## Usage\n\nRun it.\n", encoding="utf-8")
    changed = fake_tools(tmp_path, FAKE_START_OUT="tip: 6.38")
    assert init("selftest", str(repo), "--start-args", "42.50", env=changed).returncode == 0
    upgrade = render(repo, "--front-door")
    assert upgrade.returncode == 0, upgrade.stdout
    assert re.search(r"^  upgrade +README\.md$", upgrade.stdout, re.MULTILINE)
    text = (repo / "README.md").read_text(encoding="utf-8")
    assert "mise run start -- 42.50         # tip: 6.38\n" in text
    assert text.count("project-init:quickstart:begin") == 1
    assert text.endswith("<!-- project-init:quickstart:end -->\n\n## Usage\n\nRun it.\n")
    assert "Run the app: `mise run start -- 42.50`." in (repo / "AGENTS.md").read_text()


def test_the_front_door_refuses_a_red_or_stale_p5(tmp_path: Path) -> None:
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    red = fake_tools(tmp_path, FAKE_FAIL="backlog")
    assert init("selftest", str(repo), "--start-args", "100", env=red).returncode == 1
    before = tree_hash(repo)
    refused = render(repo, "--front-door")
    assert refused.returncode == 1
    assert "P5 is not green (mise run backlog -- --help)" in refused.stderr
    assert tree_hash(repo) == before

    green = fake_tools(tmp_path)
    assert init("selftest", str(repo), "--start-args", "100", env=green).returncode == 0
    mise = repo / "mise.toml"
    mise.write_text(mise.read_text(encoding="utf-8") + "# a later edit\n", encoding="utf-8")
    stale = render(repo, "--front-door")
    assert stale.returncode == 1 and "is stale" in stale.stderr
    assert not (repo / "AGENTS.md").exists()
    # the code and the local .env the happy path ran with count too
    source = repo / "src" / "tipcalc" / "__init__.py"
    for edit in (
        lambda: source.write_text(source.read_text(encoding="utf-8") + "# later\n", "utf-8"),
        lambda: (repo / ".env").write_text("TIPCALC_DEFAULT_PERCENT=20\n", encoding="utf-8"),
    ):
        assert init("selftest", str(repo), "--start-args", "100", env=green).returncode == 0
        edit()
        later = render(repo, "--front-door")
        assert later.returncode == 1 and "is stale" in later.stderr

    # a record that lacks a command the front door names is refused by name (R2)
    assert init("selftest", str(repo), "--start-args", "100", env=green).returncode == 0
    record = verify_record(repo)
    checks = record["checks"]
    assert isinstance(checks, list)
    record["checks"] = [c for c in checks if c["key"] != "mise run backlog"]
    (repo / ".agent/project-init/verify.json").write_text(json.dumps(record), encoding="utf-8")
    unproven = render(repo, "--front-door")
    assert unproven.returncode == 1
    assert "no green record in verify.json for `mise run backlog`" in unproven.stderr


def test_a_hand_edited_agents_md_gets_a_diff_and_is_never_overwritten(tmp_path: Path) -> None:
    repo, _ = front_door_repo(tmp_path)
    assert render(repo, "--front-door").returncode == 0
    agents = repo / "AGENTS.md"
    edited = agents.read_text(encoding="utf-8") + "- Local rule: ask before touching src/.\n"
    agents.write_text(edited, encoding="utf-8")
    readme = (repo / "README.md").read_text(encoding="utf-8")
    changed = fake_tools(tmp_path, FAKE_START_OUT="tip: 6.0")
    assert init("selftest", str(repo), "--start-args", "40", env=changed).returncode == 0

    result = render(repo, "--front-door")
    assert result.returncode == 3, result.stdout
    assert "--- a/AGENTS.md (render)" in result.stdout
    assert "+++ b/AGENTS.md (yours)" in result.stdout
    assert "+- Local rule: ask before touching src/." in result.stdout  # the same sign as --check
    assert "--force-file AGENTS.md" in result.stdout
    assert "re-run render --front-door: take the render with --force-file AGENTS.md" in (
        result.stdout
    )
    assert "--values" not in result.stdout  # the front door's call takes none
    assert agents.read_text(encoding="utf-8") == edited
    assert (repo / "README.md").read_text(encoding="utf-8") == readme  # nothing written

    check = render(repo, "--check")  # the machinery --check sees it by its recorded hash
    assert check.returncode == 3
    assert "  customized  AGENTS.md  (front door" in check.stdout
    assert render(repo).returncode == 0  # the machinery render never touches it

    kept = render(repo, "--front-door", "--keep-file", "AGENTS.md")
    assert kept.returncode == 0, kept.stdout
    assert agents.read_text(encoding="utf-8") == edited
    # the README region moved too (tip: 6.0), so this render changed a file besides the manifest
    assert re.search(r"^render: [1-9]\d* change", kept.stdout, re.MULTILINE), kept.stdout
    assert "tip: 6.0" in (repo / "README.md").read_text(encoding="utf-8")
    assert render(repo, "--front-door", "--check").returncode == 0
    assert render(repo, "--check").returncode == 0

    plain = render(repo, "--force-file", "AGENTS.md")
    assert plain.returncode == 2 and "add --front-door" in plain.stderr
    forced = render(repo, "--front-door", "--force-file", "AGENTS.md")
    assert forced.returncode == 0, forced.stdout
    assert "Local rule" not in agents.read_text(encoding="utf-8")
    assert "kept" not in tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert render(repo, "--check").returncode == 0


def test_the_readme_region_is_asked_about_when_edited_and_made_when_missing(
    tmp_path: Path,
) -> None:
    repo, _ = front_door_repo(tmp_path)
    (repo / "README.md").unlink()
    write(repo, {"Makefile": "test:\n\tpytest\n"})
    assert render(repo, "--front-door").returncode == 0
    made = (repo / "README.md").read_text(encoding="utf-8")
    assert made == f"# tipcalc\n\n{VALUES['DESCRIPTION']}\n\n" + QUICKSTART

    fenced = made.replace("# once per machine", "# once per machine (or brew install mise)")
    fenced += "\n```sh\nmake setup\nmake test\nmise run deploy\n"
    fenced += "make test && make doctor | tee log.txt\n"
    fenced += "uv run --locked tipcalc-old --percent 20 --verbose > out.txt\n```\n"
    (repo / "README.md").write_text(fenced, encoding="utf-8")
    result = render(repo, "--front-door")
    assert result.returncode == 3, result.stdout
    assert re.search(r"^  customized +README\.md: not overwritten", result.stdout, re.MULTILINE)
    assert "readme ...... stale command, fix it by hand: `make setup` (no make target setup)" in (
        result.stdout
    )
    assert "`mise run deploy` (no mise task deploy)" in result.stdout
    # each command of an `a && b | c` line is checked on its own, and shown whole
    assert "`make doctor` (no make target doctor)" in result.stdout
    assert "`tee log.txt`" not in result.stdout
    assert (
        "`uv run --locked tipcalc-old --percent 20 --verbose` (no console script or file "
        "tipcalc-old)" in result.stdout
    )
    assert "make test" not in result.stdout
    assert (repo / "README.md").read_text(encoding="utf-8") == fenced


def test_init_py_runs_as_a_pep_723_script(tmp_path: Path) -> None:
    folder = tmp_path / "empty"
    folder.mkdir()
    result = subprocess.run(
        [
            "uv",
            "run",
            "--script",
            str(INIT),
            "preflight",
            str(folder),
            "--offline",
            "--vault",
            str(tmp_path / "v"),
            "--search-root",
            str(tmp_path / "s"),
        ],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=clean_env(),
        check=False,
        timeout=300,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("mode ........ SCAFFOLD")


# ---------------------------------------------------------------------------------------------
# Acceptance runs A to E, round 1: each test pins one defect the runs found


HELLO_PYPROJECT = TIPCALC_PYPROJECT.replace('name = "tipcalc"', 'name = "hello"').replace(
    'tipcalc = "tipcalc:main"', 'hello = "hello:main"'
)
HELLO_SRC = 'def main() -> None:\n    print("Hello from hello!")\n'


def hello_like(root: Path) -> Path:
    """Run A after P3: what `uv init --package` leaves, its README.md empty."""
    make_repo(
        root,
        {
            "pyproject.toml": HELLO_PYPROJECT,
            "src/hello/__init__.py": HELLO_SRC,
            ".gitignore": UV_GITIGNORE,
            ".python-version": "3.14\n",
            "README.md": "",
        },
    )
    git(root, "switch", "-q", "-c", "plan/project-init")
    return root


def test_selftest_prefers_a_bare_run_to_the_guessed_100(tmp_path: Path) -> None:
    """Run A: a CLI with no README fence that runs bare gets no made-up `100` as its happy
    path; tipcalc, whose bare run crashes, still gets it (the no-fence test above)."""
    if not userns():
        pytest.skip("no user namespaces: the probe cannot run")
    repo = hello_like(tmp_path / "hello")
    write(repo, {"scripts/project.py": STUB_PROJECT})
    env = fake_tools(tmp_path, uv=False)
    result = init("selftest", str(repo), env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "happy args .. (none), from the probe's pass row (a bare run)" in result.stdout
    log = (tmp_path / "fake.log").read_text(encoding="utf-8").splitlines()
    assert log[-1] == "mise run start"
    start = verify_record(repo)["start"]
    assert isinstance(start, dict) and start["args"] == [] and start["command"] == "mise run start"


def test_an_empty_readme_gets_the_name_and_the_pitch() -> None:
    """Run A: `uv init --package` writes an empty README.md; P6 treats it as no README."""
    module = load_init()
    block = "<!-- project-init:quickstart:begin -->\n## Quickstart\n<!-- project-init:quickstart:end -->\n"
    for current in ("", "\n", None):
        text, now = module.readme_with_region(current, block, "hello", "A CLI that greets a name.")
        assert now is None
        assert text == "# hello\n\nA CLI that greets a name.\n\n" + block


MISSION = """<!-- mission.md: why the product exists. -->
# tipcalc

## One-liner
Tiny CLI that prints the tip for a bill.

## Who it is for
Me.
"""


def test_render_takes_the_description_from_the_mission_one_liner(tmp_path: Path) -> None:
    """Runs B and C: the one-liner P2 wrote becomes the pyproject description (H6) with no
    --values; a placeholder one-liner still refuses, and names where the value comes from. A
    DESCRIPTION value stands in only while the mission has no one-liner."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"specs/mission.md": MISSION.replace("Tiny CLI", "{ONE_LINER}")})
    refused = render(repo)
    assert refused.returncode == 1, refused.stdout
    assert "DESCRIPTION        in pyproject.toml" in refused.stdout
    assert "no one-liner under `## One-liner`" in refused.stdout

    write(repo, {"specs/mission.md": MISSION})
    done = render(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert 'description = "Tiny CLI that prints the tip for a bill."' in pyproject
    assert "only when the project sets none" not in pyproject  # the template's own note, Run A
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert "DESCRIPTION" not in manifest.get("values", {})  # the mission is the one source

    other = render(repo, values={"DESCRIPTION": "Another pitch."})  # the mission is the source
    assert other.returncode == 0, other.stdout
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert 'description = "Tiny CLI that prints the tip for a bill."' in pyproject


def test_a_local_folder_origin_is_never_recorded(tmp_path: Path) -> None:
    """Run D: a clone of a folder has that folder as origin; .project.toml is tracked, so
    render refuses to write the path, and drops one an older render wrote."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    local = tmp_path / "origin.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(local))
    git(repo, "remote", "add", "origin", str(local))
    text = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert f"origin {local} (a local folder: render refuses to record it)" in text
    before = tree_hash(repo)
    refused = render(repo, "--offline", values=VALUES)
    assert refused.returncode == 1
    assert "origin is a local folder" in refused.stderr and "git remote remove origin" in (
        refused.stderr
    )
    assert tree_hash(repo) == before

    git(repo, "remote", "remove", "origin")
    assert render(repo, "--offline", values=VALUES).returncode == 0
    manifest = repo / ".project.toml"
    assert tomllib.loads(manifest.read_text(encoding="utf-8"))["origin_url"] == ""
    older = manifest.read_text(encoding="utf-8").replace(
        'origin_url = ""', f'origin_url = "{local}"'
    )
    manifest.write_text(older, encoding="utf-8")  # what an older render wrote
    assert render(repo, "--offline", values=VALUES).returncode == 0
    assert str(local) not in manifest.read_text(encoding="utf-8")

    # EXTEND's audit on a `git clone --no-local` copy: --check writes nothing, so it names the
    # folder origin as a finding and still lists the drift
    git(repo, "remote", "add", "origin", str(local))
    before = tree_hash(repo)
    check = render(repo, "--check", "--offline")
    assert check.returncode == 0, check.stdout + check.stderr
    assert f"origin ...... origin is a local folder ({local}): audited as if there" in (
        check.stdout
    )
    assert "render --check: 0 drift" in check.stdout
    assert tree_hash(repo) == before


def test_preflight_names_the_tools_the_repo_pins_in_mise_toml(tmp_path: Path) -> None:
    """Run D: EXTEND preflight runs tools from the home folder, where the repo's pins do not
    apply; it says they are pinned in mise.toml, not that P4 will pin them."""
    module = load_init()
    repo = make_repo(
        tmp_path / "app",
        {
            "app.py": "x = 1\n",
            "mise.toml": '[tools]\nuv = "0.12.10"\ngitleaks = "8.30.1"\n'
            '"aqua:orhun/git-cliff" = "2.14.1"\n',
        },
    )
    facts = module.preflight(repo, True, tmp_path / "no-vault", [tmp_path / "no-search"])
    assert facts.tool_pins == ["uv", "gitleaks", "git-cliff"]
    facts.tools.update({"gitleaks": None, "git-cliff": None})
    text = module.format_preflight(facts)
    assert "gitleaks, git-cliff pinned in mise.toml (run through `mise x --`" in text
    assert "pinned in P4" not in text
    facts.tool_pins = []
    assert "gitleaks, git-cliff not runnable (pinned in P4)" in module.format_preflight(facts)


def test_the_ship_commit_carries_the_adrs_and_the_dry_run_names_what_it_leaves(
    tmp_path: Path,
) -> None:
    """Run C: an ADR P2 or P9 wrote replaces the decisions/.gitkeep seed, so [seeded] lists
    no path under decisions/; the pathspec names the folder itself. The dry run shows the
    untracked files it leaves out before anything is staged."""
    repo, env = shipped_repo(tmp_path)
    adr = f"{DECISIONS_KEEP.rsplit('/', 1)[0]}/2026-09-23-quality-gate.md"
    write(repo, {adr: "---\naliases: [D-001]\n---\n# ruff, ty and pytest\n", "notes.txt": "x\n"})
    look = init("publish", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert f"add '{adr}'" in look.stdout
    assert "not staged .. not project-init's; stage them by hand if they belong:" in look.stdout
    assert "\n              notes.txt\n" in look.stdout
    done = init("publish", str(repo), env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert adr in git(repo, "show", "--name-only", "--format=", "HEAD").splitlines()
    assert git(repo, "status", "--porcelain") == "?? notes.txt\n"


def test_keeping_a_front_door_file_is_a_change_with_one_diff_direction(tmp_path: Path) -> None:
    """Run D: keeping a hand-edited AGENTS.md writes only the [kept] row of the tracked
    manifest, and render says that is a change. The P6 question shows the edit with the same
    sign as render --check: from the render (or the version P6 wrote) to yours."""
    repo, _ = front_door_repo(tmp_path)
    assert render(repo, "--front-door").returncode == 0
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(init): project-init v3")
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "- Local rule.\n", encoding="utf-8")
    check = render(repo, "--check")
    asked = render(repo, "--front-door")
    assert (check.returncode, asked.returncode) == (3, 3), check.stdout + asked.stdout
    for result in (check, asked):
        assert "+- Local rule." in result.stdout and "-- Local rule." not in result.stdout
    kept = render(repo, "--front-door", "--keep-file", "AGENTS.md")
    assert kept.returncode == 0, kept.stdout
    assert kept.stdout.strip().endswith(
        "render: 1 change (.project.toml only: it is tracked, so it ships like any change)"
    )
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert "AGENTS.md" in manifest["kept"]
    assert render(repo, "--front-door").stdout.strip().endswith("render: 0 changes")


def test_an_extend_ship_commit_says_upgrade(tmp_path: Path) -> None:
    """Run D: the EXTEND ship commit is `chore(init): project-init v3 upgrade` (8-extend.md);
    the first one, with no manifest on the default branch, keeps the plain subject."""
    repo, env = shipped_repo(tmp_path)
    assert init("publish", str(repo), env=env).returncode == 0
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "plan/project-init")  # G1, as far as git sees it
    git(repo, "switch", "-q", "-c", "plan/2026-09-25-project-init")
    write(repo, {"specs/backlog/later.md": "# later\n"})
    look = init("publish", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert (
        "commit ...... chore(init): project-init v3 upgrade (on plan/2026-09-25-project-init)"
    ) in look.stdout
    assert "Kept as the project wrote it" not in look.stdout and "Upgraded" not in look.stdout


def test_an_extend_ship_body_says_which_file_was_kept(tmp_path: Path) -> None:
    """Run D: an EXTEND upgrade that only keeps a hand-edited AGENTS.md is a 3-line manifest
    diff. The ship body (and, through merge, main's squash body) says why: the file was kept
    as the project wrote it, and the next run asks again when its template changes."""
    repo, env = shipped_repo(tmp_path)
    assert init("publish", str(repo), env=env).returncode == 0
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "plan/project-init")
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "- Money is rounded.\n", "utf-8")
    git(repo, "commit", "-q", "-am", "chore: note where money is rounded in AGENTS.md")
    git(repo, "switch", "-q", "-c", "plan/2026-09-25-project-init")
    assert init("selftest", str(repo), "--start-args", "100", env=env).returncode == 0
    kept = render(repo, "--front-door", "--keep-file", "AGENTS.md")
    assert kept.returncode == 0, kept.stdout + kept.stderr
    look = init("publish", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert (
        "Kept as the project wrote it: AGENTS.md. The new render was declined; the [kept] row "
        "in .project.toml asks again when its template changes."
    ) in look.stdout
    assert "Upgraded" not in look.stdout


def skill_copy(tmp_path: Path) -> Path:
    """This skill's SKILL.md, scripts and templates in a scratch folder, where a template can
    move as a new skill version moves it. Returns the copy's init.py."""
    dest = tmp_path / "skill"
    dest.mkdir()
    shutil.copy2(SKILL / "SKILL.md", dest / "SKILL.md")
    for part in ("scripts", "templates"):
        shutil.copytree(SKILL / part, dest / part, ignore=shutil.ignore_patterns("__pycache__"))
    return dest / "scripts" / "init.py"


def init_at(script: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """init.py from another skill folder: stdout and stderr, with the exit code first."""
    done = subprocess.run(
        [sys.executable, str(script), *args],
        capture_output=True,
        text=True,
        env=env or clean_env(),
        timeout=900,
        check=False,
    )
    return f"exit {done.returncode}\n{done.stdout}{done.stderr}"


def test_a_front_door_template_that_moved_is_seen_by_the_audit(tmp_path: Path) -> None:
    """Run D: render --check cannot render the front door without P5's record, so P6 records
    the hash of each front-door template. A template that moved since is an upgrade for an
    untouched file, and asks again about a kept one; P6 then renders it, and the EXTEND ship
    body says what it upgraded. A manifest with no template hash on record counts as moved."""
    repo, env = shipped_repo(tmp_path)
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    templates = SKILL / "templates"
    assert manifest["front_door_templates"] == {
        "AGENTS.md": "sha256:" + hashlib.sha256((templates / "AGENTS.md").read_bytes()).hexdigest(),
        "README.md": "sha256:"
        + hashlib.sha256((templates / "README-quickstart.md").read_bytes()).hexdigest(),
    }
    assert init("publish", str(repo), env=env).returncode == 0
    git(repo, "switch", "-q", "main")
    git(repo, "merge", "-q", "--ff-only", "plan/project-init")  # G1, as far as git sees it
    git(repo, "branch", "-q", "-D", "plan/project-init")
    git(repo, "switch", "-q", "-c", "plan/2026-09-25-project-init")
    assert "0 drift (24 of 24 files match)" in render(repo, "--check").stdout

    moved = skill_copy(tmp_path)
    template = moved.parents[1] / "templates" / "AGENTS.md"
    template.write_text(template.read_text(encoding="utf-8") + "- A new standard line.\n", "utf-8")
    check = init_at(moved, "render", str(repo), "--check")
    assert check.startswith("exit 3\n"), check
    assert (
        "  upgrade     AGENTS.md  (front door: its template changed since P6 rendered it: P6 "
        "renders it again)"
    ) in check
    assert "README.md  (front door" not in check  # its template did not move
    p6 = init_at(moved, "render", str(repo), "--front-door", env=env)
    assert p6.startswith("exit 0\n") and re.search(r"(?m)^  upgrade +AGENTS\.md$", p6), p6
    assert "- A new standard line." in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert init_at(moved, "render", str(repo), "--check").startswith("exit 0\n")
    look = init_at(moved, "publish", str(repo), "--dry-run", env=env)
    assert "Upgraded to the current render: AGENTS.md." in look, look

    # kept, then the template moves again: asked about once more, not reported as kept
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "- Local rule.\n", encoding="utf-8")
    kept = init_at(moved, "render", str(repo), "--front-door", "--keep-file", "AGENTS.md", env=env)
    assert kept.startswith("exit 0\n"), kept
    audit = init_at(moved, "render", str(repo), "--check")
    assert audit.startswith("exit 0\n") and "  kept        AGENTS.md  (front door" in audit, audit
    template.write_text(template.read_text(encoding="utf-8") + "- Moved again.\n", "utf-8")
    again = init_at(moved, "render", str(repo), "--check")
    assert again.startswith("exit 3\n"), again
    assert (
        "  customized  AGENTS.md  (front door: kept, and its template changed since: P6 asks "
        "again, keep yours or take the render)"
    ) in again

    # a manifest from before the template hashes: nothing says the front door is current
    text = (repo / ".project.toml").read_text(encoding="utf-8")
    (repo / ".project.toml").write_text(
        text[: text.index("\n[front_door_templates]")] + "\n", encoding="utf-8"
    )
    old = render(repo, "--check").stdout
    assert (
        "  upgrade     README.md  (front door: no template hash on record, so it may be behind "
        "its template: P6 renders it again)"
    ) in old, old
    assert "  customized  AGENTS.md  (front door: kept, with no template hash on record" in old


def test_extend_check_shows_a_customized_front_door_edit_from_history(tmp_path: Path) -> None:
    """Run D: the audit asks about a customized AGENTS.md with a diff, before any branch or
    P5: the diff runs from the version P6 wrote (found by its recorded hash) to the file now."""
    repo, _ = shipped_repo(tmp_path)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "chore(init): project-init v3")
    agents = repo / "AGENTS.md"
    agents.write_text(agents.read_text(encoding="utf-8") + "- Local rule: ask first.\n", "utf-8")
    git(repo, "commit", "-q", "-am", "chore: a local rule")
    check = render(repo, "--check")
    assert check.returncode == 3, check.stdout
    assert "  customized  AGENTS.md  (front door, by its recorded hash)" in check.stdout
    shipped = git(repo, "rev-parse", "HEAD~1").strip()[:10]
    assert f"--- a/AGENTS.md (as P6 wrote it, {shipped})" in check.stdout
    assert "+++ b/AGENTS.md (yours)" in check.stdout
    assert "+- Local rule: ask first." in check.stdout


def test_extend_check_flags_a_ci_push_branch_that_is_gone(tmp_path: Path) -> None:
    """Run C: a workflow render does not own that still pushes on `master` after the rename,
    or never on the default branch, is audit drift (H15). Render's own CI is hash-checked."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    git(repo, "branch", "develop", "main")
    write(
        repo,
        {
            ".github/workflows/old.yml": "name: old\non:\n  pull_request:\n  push:\n"
            "    branches: [main, master]\njobs:\n  checks:\n    runs-on: ubuntu-latest\n",
            ".github/workflows/dev.yml": "on:\n  push:\n    branches:\n      - develop\n",
            ".github/workflows/any.yml": "on: [push, pull_request]\n",
        },
    )
    check = render(repo, "--check")
    assert check.returncode == 3, check.stdout
    assert (
        "  ci          .github/workflows/old.yml: push branches [main, master], default branch "
        "main: master is no branch here (H15)"
    ) in check.stdout
    assert (
        ".github/workflows/dev.yml: push branches [develop], default branch main: it never "
        "runs on main (H15)"
    ) in check.stdout
    assert "any.yml" not in check.stdout


def as_v30(repo: Path) -> None:
    """The repo as a v3.0 render left it: tech-stack.md with no Trunk section, and a
    scripts/project.py of VERSION 3.0.0 whose hash .project.toml records (so render --check
    calls it upgrade once the template moves on)."""
    stack = repo / "specs/tech-stack.md"
    stack.write_text(TECH_STACK.split("\n## Trunk\n", 1)[0], encoding="utf-8")
    project = repo / "scripts/project.py"
    old = generated(repo)["scripts/project.py"]
    text = re.sub(r'(?m)^VERSION = ".*"$', 'VERSION = "3.0.0"', project.read_text("utf-8"))
    project.write_text(text + "# as v3.0 shipped it\n", encoding="utf-8")
    new = "sha256:" + hashlib.sha256(project.read_bytes()).hexdigest()
    manifest = repo / ".project.toml"
    manifest.write_text(manifest.read_text("utf-8").replace(old, new), encoding="utf-8")


def test_extend_check_proposes_the_trunk_section_on_a_v3_0_repo(tmp_path: Path) -> None:
    """v3.1 (design A.2): the audit of a v3.0 repo lists the machinery upgrade and a trunk item
    with the probe's candidates. The section is product text: render never writes it, and the
    item stays until the talk answer is in specs/tech-stack.md on the plan/ branch."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    as_v30(repo)
    check = render(repo, "--check")
    assert check.returncode == 3, check.stdout
    assert re.search(r"^  upgrade +scripts/project\.py$", check.stdout, re.MULTILINE)
    item = (
        "trunk ....... v3.1 upgrade: specs/tech-stack.md has no ## Trunk section, and "
        "scripts/project.py is 3.0.0. Until it has one, every path counts as leaf. P2 proposes "
        "it on the plan/ branch from 1 candidate:\n"
        f"{REPORT_INDENT}{TIPCALC_TRUNK}\n"
    )
    assert item in check.stdout
    assert re.search(r"^render --check: [2-9]\d* drift", check.stdout, re.MULTILINE)

    stack = (repo / "specs/tech-stack.md").read_bytes()
    upgraded = render(repo)
    assert upgraded.returncode == 0, upgraded.stdout
    assert re.search(r"^  upgrade +scripts/project\.py$", upgraded.stdout, re.MULTILINE)
    assert item in upgraded.stdout  # a reminder: the writing render leaves specs/ alone
    assert (repo / "specs/tech-stack.md").read_bytes() == stack

    write(repo, {"specs/tech-stack.md": TECH_STACK})  # P2's answer: keep all
    after = render(repo, "--check")
    assert after.returncode == 0, after.stdout
    assert "trunk ......." not in after.stdout
    assert "render --check: 0 drift" in after.stdout


def test_the_trunk_item_outside_a_v3_0_repo(tmp_path: Path) -> None:
    """A newer repo whose tech-stack.md lost the section gets the item without the v3.1 lead;
    a repo with no tech-stack.md yet gets none (P2 writes it from the template)."""
    module = load_init()
    write(tmp_path, {"specs/tech-stack.md": "# Tech stack: x\n\n## Distribution\nnone\n"})
    write(tmp_path, {"scripts/project.py": 'VERSION = "3.1.0"\n'})
    assert module.trunk_upgrade(tmp_path) == [
        (
            "specs/tech-stack.md has no ## Trunk section. Until it has one, every path counts as "
            "leaf. P2 writes it empty on the plan/ branch: the static scan found no candidate"
        )
    ]
    (tmp_path / "specs/tech-stack.md").unlink()
    assert module.trunk_upgrade(tmp_path) == []


def test_workflow_push_branches_reads_the_list_forms() -> None:
    read = load_init().workflow_push_branches
    assert read('on:\n  push:\n    branches: ["main"]\n') == ["main"]
    assert read("'on':\n  push:\n    branches:\n      - main   # the default\n      - 'x'\n") == [
        "main",
        "x",
    ]
    assert read("on:\n  pull_request:\n    branches: [main]\n") is None
    assert read("on: push\n") is None
    assert read("on:\n  push:\n    tags: [v*]\n") is None


SETTINGS_SRC = """from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TIPCALC_", env_ignore_empty=True)

    default_percent: float | None = 15.0
    verbose: bool = False
    api_token: str = Field(..., alias="TIPCALC_TOKEN")
"""


def test_env_reads_see_pydantic_settings_fields(tmp_path: Path) -> None:
    """Run E: S-1 moves env reads into pydantic-settings; the scan sees them."""
    write(tmp_path, {"src/app/settings.py": SETTINGS_SRC})
    reads = {r.name: r for r in load_init().env_reads(tmp_path)}
    assert sorted(reads) == ["TIPCALC_DEFAULT_PERCENT", "TIPCALC_TOKEN", "TIPCALC_VERBOSE"]
    percent = reads["TIPCALC_DEFAULT_PERCENT"]
    assert (percent.kind, percent.type, percent.default, percent.required) == (
        "knob",
        "float",
        "15.0",
        False,
    )
    assert reads["TIPCALC_VERBOSE"].default == "false"
    token = reads["TIPCALC_TOKEN"]
    assert (token.kind, token.required) == ("secret", True)


def test_the_env_contract_keeps_the_project_rows(tmp_path: Path) -> None:
    """Run E: a feature types its knob by hand and moves the read to pydantic-settings; render
    keeps the row as written and never proposes deleting it. A new read still gets a row."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    assert render(repo, values=VALUES).returncode == 0
    env_file = repo / ".env.example"
    text = env_file.read_text(encoding="utf-8")
    row = next(ln for ln in text.splitlines() if ln.startswith("# TIPCALC_DEFAULT_PERCENT |"))
    typed = "# TIPCALC_DEFAULT_PERCENT | knob | float 0..100 | no | 15 | the default tip, percent"
    env_file.write_text(text.replace(row, typed), encoding="utf-8")
    write(repo, {"src/tipcalc/__init__.py": "def main() -> None:\n    print('tip')\n"})
    check = render(repo, "--check")
    assert check.returncode == 0, check.stdout  # nothing to delete, nothing customized
    assert typed in env_file.read_text(encoding="utf-8")

    write(repo, {"src/tipcalc/extra.py": 'import os\n\nLEVEL = os.environ.get("TIPCALC_LEVEL")\n'})
    check = render(repo, "--check")
    assert "customized  .env.example" in check.stdout  # an addition on top of a hand edit asks
    assert "-# TIPCALC_LEVEL | knob | str | no | - |" in check.stdout  # render -> yours
    assert "+" + typed not in check.stdout


V2_README = """# tipcalc

Tiny CLI that computes a tip.

## Quickstart

```bash
make setup && make doctor     # once per machine
uv run tipcalc 42.50          # tip: 6.38 (15% default)
make verify                   # format, lint, types, tests
```

Contributing: see `ONBOARDING.md` and `AGENTS.md`.
"""
V2_SETTINGS = """{
  "hooks": {
    "SessionStart": [
      {"hooks": [{"type": "command", "command": "python3 .claude/hooks/project-memory-inject.py"}]}
    ],
    "PreToolUse": [
      {"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 .claude/hooks/project-branch-guard.py"}]}
    ]
  },
  "permissions": {"allow": ["Bash(make verify)"]}
}
"""
V2_LESSONS = """# Lessons

## 2026-09-23 | Set-but-empty TIPCALC_DEFAULT_PERCENT crashes tipcalc
Trigger: a blank value raised ValueError.
Rule: unset the var to test the default.

## 2026-09-23 | The /project-init hook scripts fail this repo's own ruff gate
Trigger: ruff reported 25 errors in the hooks.
Rule: keep `.claude` in `[tool.ruff] extend-exclude`.
"""
V2_RUFF_LINT = """
[tool.ruff.lint]
extend-select = ["S", "ANN"]   # S = security (bandit), ANN = annotations

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101"]          # pytest is built on bare `assert`; S101 would fail every test file
"""
V2_RETIRING = """
## 2026-09-25 | Retired: The /project-init hook scripts fail this repo's own ruff gate
Trigger: the v3 migration removed .claude/hooks and the `.claude` entry in extend-exclude.
Rule: ruff checks the whole repo; only the two tool-owned files stay excluded.
"""
V2_CI_YML = """name: ci
on:
  pull_request:
  push:
    branches: [main, master]
jobs:
  checks:
    runs-on: ubuntu-latest
    steps:
      - run: uv run pytest -q
"""


def v2_repo(root: Path) -> Path:
    """tipcalc with the v2 project-init merged (Run C's fixture, cut down), on main."""
    return make_repo(
        root,
        {
            "pyproject.toml": TIPCALC_PYPROJECT
            + '\n[tool.ruff]\nline-length = 100\nextend-exclude = [".claude"]   # vendored hooks\n'
            + V2_RUFF_LINT,
            "src/tipcalc/__init__.py": TIPCALC_SRC,
            ".gitignore": UV_GITIGNORE,
            ".python-version": "3.14\n",
            "README.md": V2_README,
            "AGENTS.md": "# tipcalc\n\nRun `make verify`.\n",
            ".mise.toml": '[tools]\nuv = "0.12.10"\npython = "3.14.7"\n',
            ".env.example": "# TIPCALC_DEFAULT_PERCENT=15\n",
            ".editorconfig": "root = true\n",
            ".claude/settings.json": V2_SETTINGS,
            ".claude/hooks/project-branch-guard.py": "print('guard')\n",
            ".claude/hooks/project-memory-inject.py": "print('inject')\n",
            ".claude/skills/run/SKILL.md": "# run\n",
            ".github/workflows/ci.yml": V2_CI_YML,
            ".github/CODEOWNERS": "* @someone\n",
            "project_memory/README.md": "# Project Memory\n\n---\nStandard: project-init v2\n",
            "project_memory/facts.md": "# Facts\n",
            "project_memory/decisions.md": "# Decisions\n\n## D-001 | 2026-09-23 | quality gate | "
            "active\nWhat: ruff, ty and pytest.\n",
            "project_memory/lessons.md": V2_LESSONS,
            "project_memory/log.md": "# Log\n",
            "project_memory/.gitattributes": "log.md merge=union\n",
            "docs/spec.md": "# Spec\n",
            "Makefile": "verify:\n\tuv run pytest\n",
            "scripts/doctor.sh": "#!/bin/sh\n",
            "scripts/git-hooks/pre-commit": "#!/bin/sh\n",
            "ONBOARDING.md": "# Onboarding\n",
            "CHANGELOG.md": "# Changelog\n",
            "tests/test_smoke.py": "def test_smoke() -> None:\n    assert True\n",
        },
    )


def test_a_retired_v2_lesson_is_not_named_again(tmp_path: Path) -> None:
    """migrate-v2 names a lesson the migration contradicts until P2 retires it, and never
    names the retiring entry itself, with or without the old date in its title."""
    module = load_init()
    root = tmp_path / "repo"
    write(root, {"project_memory/lessons.md": V2_LESSONS})
    assert [title for title, _ in module.stale_v2_lessons(root)] == [
        "2026-09-23 | The /project-init hook scripts fail this repo's own ruff gate"
    ]
    for retiring in (
        V2_RETIRING,
        V2_RETIRING.replace("Retired: The", "retired: 2026-09-23 | The").replace(" own ", "  own "),
    ):
        write(root, {"project_memory/lessons.md": V2_LESSONS + retiring})
        assert module.stale_v2_lessons(root) == []


def test_a_v2_lesson_on_the_v2_doctor_is_named(tmp_path: Path) -> None:
    """Run C: the tipcalc v2 lesson says "doctor fails on set-but-empty". v3's doctor reads an
    empty value as unset (H17), so the lesson is stale although it names no v2 path. A bare
    `doctor` counts; a lesson naming `make doctor` lists that term once, not `doctor` too."""
    module = load_init()
    root = tmp_path / "repo"
    doctor = (
        "## 2026-09-23 | Set-but-empty TIPCALC_DEFAULT_PERCENT crashes tipcalc\n"
        "Trigger: a blank value raised ValueError.\n"
        "Rule: unset the var, never blank it. doctor fails on set-but-empty.\n"
    )
    make = "## 2026-09-24 | Run the checks first\nTrigger: x.\nRule: run `make doctor` first.\n"
    other = "## 2026-09-24 | Doctors hours\nTrigger: the doctors' office.\nRule: none.\n"
    write(root, {"project_memory/lessons.md": f"# Lessons\n\n{doctor}\n{make}\n{other}"})
    assert module.stale_v2_lessons(root) == [
        ("2026-09-23 | Set-but-empty TIPCALC_DEFAULT_PERCENT crashes tipcalc", ["doctor"]),
        ("2026-09-24 | Run the checks first", ["make doctor"]),
    ]


def test_a_v2_repo_migrates_through_one_prompt(tmp_path: Path) -> None:
    """Run C: the one migration prompt comes from init.py with each fate; --apply makes the
    moves; render and P6 then take the v2 files the prompt covered without asking again; the
    v2 ci.yml is replaced with no remote; the v2 Quickstart gives way to the region; the ship
    pathspec carries the ADR."""
    repo = v2_repo(tmp_path / "tipcalc")
    pre = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert "mode ........ EXTEND+v2-migrate" in pre
    assert "migrate ..... after P1: init.py migrate-v2 prints the one prompt" in pre

    before = tree_hash(repo)
    prompt = init("migrate-v2", str(repo))
    assert prompt.returncode == 0, prompt.stdout + prompt.stderr
    out = prompt.stdout
    assert tree_hash(repo) == before
    for line in (
        ".mise.toml ",
        "Makefile ",
        ".claude/hooks ",
        "project_memory/decisions.md ",
        ".github/CODEOWNERS ",
        "README.md ## Quickstart ",
        "pyproject.toml extend-exclude .claude ",
    ):
        assert f"\n  {line}" in out, line
    assert re.search(r"\n  tests/test_smoke\.py +kept: product code, not v2 machinery\n", out)
    assert "git mv to mise.toml" in out and "deleted in the solo tier (D9)" in out
    assert "lesson ...... \"2026-09-23 | The /project-init hook scripts fail this repo's own " in (
        out
    )
    assert "Set-but-empty" not in out
    assert "1. Apply all (Recommended:" in out and "2. Stop" in out

    on_main = init("migrate-v2", str(repo), "--apply")
    assert on_main.returncode == 1 and "git switch -c plan/project-init" in on_main.stderr
    git(repo, "switch", "-q", "-c", "plan/project-init")
    write(
        repo,
        {
            "specs/mission.md": MISSION,
            "specs/tech-stack.md": TECH_STACK,
            "specs/capabilities/cli.md": CLI_CAPABILITY,
        },
    )
    no_adr = init("migrate-v2", str(repo), "--apply")
    assert no_adr.returncode == 1 and "aliases: [D-001]" in no_adr.stderr
    assert (repo / "Makefile").exists()
    adr = "project_memory/decisions/2026-09-23-quality-gate.md"
    write(repo, {adr: "---\naliases: [D-001]\nstatus: active\n---\n# Quality gate\n"})
    # P2 appends the retiring lesson: neither it nor the lesson it retires is listed again
    lessons = V2_LESSONS + V2_RETIRING
    write(repo, {"project_memory/lessons.md": lessons})
    assert "lesson ......" not in init("migrate-v2", str(repo)).stdout
    applied = init("migrate-v2", str(repo), "--apply")
    assert applied.returncode == 0, applied.stdout + applied.stderr
    assert "lesson ......" not in applied.stdout
    staged = git(repo, "diff", "--cached", "--name-status").splitlines()
    assert any(ln.startswith("R") and ln.endswith("mise.toml") for ln in staged), staged
    for gone in ("Makefile", ".claude/hooks", "project_memory/decisions.md", "ONBOARDING.md"):
        assert not (repo / gone).exists(), gone
    assert (repo / "project_memory/lessons.md").read_text(encoding="utf-8") == lessons
    assert ".claude/hooks/" not in (repo / ".claude/settings.json").read_text(encoding="utf-8")
    assert '".claude"' not in (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert init("migrate-v2", str(repo), "--apply").stdout.strip() == (
        "migrate-v2: nothing left to apply"
    )

    refs = {"CHECKOUT_REF": "v4", "MISE_ACTION_REF": "v4"}
    done = render(repo, "--offline", values=refs)
    assert done.returncode == 0, done.stdout + done.stderr  # no customized question again
    ci = (repo / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert 'branches: ["main"]' in ci and '  "verify":' in ci  # replaced with no remote
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["migrated_from"] == "project-init v2"
    pyproject = (repo / "pyproject.toml").read_text(encoding="utf-8")
    # the v2 row now holds the template's list, so it carries the template's comment (Run B's)
    assert '"tests/**" = ["S101", "S603", "S607"]          # assert, and subprocess tests' in (
        pyproject
    )
    assert "S101 would fail every test file" not in pyproject
    assert ".github/workflows/ci.yml" in manifest["generated"]
    assert 'python = "3.14.7"' not in (repo / "mise.toml").read_text(encoding="utf-8")
    assert render(repo, "--check", "--offline").returncode == 0

    env = fake_tools(tmp_path)
    assert init("selftest", str(repo), "--start-args", "100", env=env).returncode == 0
    front = render(repo, "--front-door")
    assert front.returncode == 0, front.stdout + front.stderr  # AGENTS.md: the prompt's too
    # the v2 Quickstart this render replaces is not audited as prose left for the human
    assert "readme ......" not in front.stdout and "fix it by hand" not in front.stdout
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert readme.count("## Quickstart") == 1
    assert "make setup" not in readme and "ONBOARDING" not in readme
    assert readme.startswith("# tipcalc\n\nTiny CLI that computes a tip.\n\n<!-- project-init")
    assert "make verify" not in (repo / "AGENTS.md").read_text(encoding="utf-8")

    look = init("publish", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert f"add '{adr}'" in look.stdout
    assert "D  Makefile" in look.stdout
    assert "commit ...... chore(init): project-init v3 (on plan/project-init)" in look.stdout


# ---------------------------------------------------------------------------------------------
# M11 rollout fixes (orca, open-kit, helios, the remote trial)


def commit_as(repo: Path, rel: str, subject: str, **who: str) -> None:
    """One commit of rel with the given GIT_AUTHOR_*/GIT_COMMITTER_* overrides."""
    write(repo, {rel: f"{rel}\n"})
    git(repo, "add", rel, env=clean_env(**who))
    git(repo, "commit", "-q", "-m", subject, env=clean_env(**who))


WEB_FLOW = {"GIT_COMMITTER_NAME": "GitHub", "GIT_COMMITTER_EMAIL": "noreply@github.com"}
ZETA240 = {"GIT_AUTHOR_NAME": "zeta240", "GIT_AUTHOR_EMAIL": "9zqxmt@privaterelay.example.invalid"}


def test_web_ui_uploads_and_bots_never_make_a_second_human(tmp_path: Path) -> None:
    """D9 on helios: 3 'Add files via upload' commits GitHub's web UI made for a second account
    set the team tier, and merge then waited for a review nobody could give."""
    repo = make_repo(tmp_path / "helios", {"pyproject.toml": '[project]\nname = "helios"\n'})
    for i in range(3):
        commit_as(repo, f"names{i}.py", "Add files via upload", **ZETA240, **WEB_FLOW)
    commit_as(repo, "bump.txt", "chore: bump", GIT_AUTHOR_NAME="dependabot[bot]")
    code, facts = preflight_json(repo)
    assert code == 0, facts["stops"]
    assert (facts["tier"], listed(facts, "authors")) == (
        "solo",
        ["Test Author <author@example.invalid>"],
    )
    assert facts["author_commits"] == {"Test Author <author@example.invalid>": 1}
    assert facts["authors_not_counted"] == [
        "zeta240 <9zqxmt@privaterelay.example.invalid>: 3 GitHub web uploads, no git commit"
    ]
    assert facts["bot_commits"] == 1
    text = init(
        "preflight", str(repo), "--offline", "--vault", str(tmp_path / "v"), "--search-root", "x"
    ).stdout
    assert "authors ..... 1 human in 6 months: solo tier\n" in text
    assert "              counted: Test Author (1 commit)\n" in text
    assert (
        "              not counted (web-UI commits only and bots, D9): zeta240 (3 GitHub web "
        "uploads, no git commit); 1 bot commit\n"
    ) in text
    # render's tier follows the same count: no team.md, CODEOWNERS or PR template
    assert load_init().human_authors(repo) == ["Test Author <author@example.invalid>"]

    # a pull request GitHub merged is real work: its author counts
    commit_as(repo, "pr.py", "feat: a teammate's change (#4)", **ZETA240, **WEB_FLOW)
    _, facts = preflight_json(repo)
    assert facts["tier"] == "team" and facts["authors_not_counted"] == []
    # and so does a commit made with git by an account that also uploaded
    other = make_repo(tmp_path / "other", {"pyproject.toml": '[project]\nname = "other"\n'})
    commit_as(other, "u.py", "Add files via upload", **ZETA240, **WEB_FLOW)
    commit_as(other, "g.py", "feat: from a clone", **ZETA240)
    _, facts = preflight_json(other)
    assert facts["tier"] == "team"
    counted = facts["author_commits"]
    assert isinstance(counted, dict)
    assert counted["zeta240 <9zqxmt@privaterelay.example.invalid>"] == 1
    # a pull request GitHub rebased: committer GitHub, no (#N), but the author date is the one
    # the teammate committed with git, a day before GitHub wrote it
    based = make_repo(tmp_path / "based", {"pyproject.toml": '[project]\nname = "based"\n'})
    now = int(time.time())
    day = {
        "GIT_AUTHOR_DATE": f"@{now - 2 * 86400} +0000",
        "GIT_COMMITTER_DATE": f"@{now - 86400} +0000",
    }
    commit_as(based, "r.py", "feat: rebased onto main", **ZETA240, **WEB_FLOW, **day)
    _, facts = preflight_json(based)
    assert facts["tier"] == "team" and facts["authors_not_counted"] == []
    # a web edit (authored and committed at once, no upload) is not
    edit = make_repo(tmp_path / "edit", {"pyproject.toml": '[project]\nname = "edit"\n'})
    same = {
        "GIT_AUTHOR_DATE": f"@{now - 86400} +0000",
        "GIT_COMMITTER_DATE": f"@{now - 86400} +0000",
    }
    commit_as(edit, "README.md", "Update README.md", **ZETA240, **WEB_FLOW, **same)
    _, facts = preflight_json(edit)
    assert facts["tier"] == "solo"
    assert facts["authors_not_counted"] == [
        "zeta240 <9zqxmt@privaterelay.example.invalid>: 1 GitHub web edit, no git commit"
    ]


def test_a_repo_with_no_stack_pack_stops_before_the_talk(tmp_path: Path) -> None:
    """open-kit (node): P0 passed, the talk ran, and render refused only in P4. P0 stops now,
    and the probe says why it probed nothing."""
    repo = make_repo(
        tmp_path / "open-kit",
        {"package.json": '{"name": "openkit", "bin": {"openkit": "cli.js"}}\n', "cli.js": "1\n"},
    )
    code, facts = preflight_json(repo)
    assert code == 1 and stop_ids(facts) == ["no-stack-pack"]
    stop = listed(facts, "stops")[0]
    assert str(stop["what"]).startswith("no stack pack for node: project-init v3 ships the Python")
    assert stop["options"] == [
        "Stop here (Recommended: v3 ships the Python pack only).",
        (
            "Adopt specs/ and memory only, no gates: `git switch -c plan/project-init`, then P2 "
            "writes the constitution and the ADRs there, and nothing is rendered "
            "(0-preflight.md)."
        ),
    ]
    assert facts["python"] == {}
    # open-kit's real state: a dirty tree too. The stack stop decides the run, so it comes
    # first, in the list and in the printed prompt
    write(repo, {"cli.js": "2\n"})
    code, facts = preflight_json(repo)
    assert code == 1 and stop_ids(facts) == ["no-stack-pack", "dirty"]
    printed = init("preflight", str(repo), "--offline", "--vault", str(tmp_path / "v")).stdout
    assert printed.index("no stack pack for node") < printed.index("dirty tree")
    git(repo, "checkout", "--", "cli.js")
    # a Python repo whose pyproject.toml sits in a subfolder: render needs it at the root
    sub = make_repo(tmp_path / "mono", {"backend/pyproject.toml": '[project]\nname = "b"\n'})
    _, facts = preflight_json(sub)
    assert stop_ids(facts) == ["no-stack-pack"]
    assert str(listed(facts, "stops")[0]["what"]).startswith("no stack pack for python (backend/)")
    # code with no stack marker at all: the stop names none rather than "unknown"
    shell = make_repo(tmp_path / "shell", {"deploy.sh": "echo hi\n"})
    _, facts = preflight_json(shell)
    assert str(listed(facts, "stops")[0]["what"]).startswith(
        "no stack pack (no pyproject.toml, package.json, Cargo.toml or go.mod): project-init v3"
    )
    refused = render(shell)
    assert refused.returncode == 1
    assert "(P0 stops such a repo before the talk)" in refused.stderr
    # an empty folder is SCAFFOLD: uv init makes the pyproject, so no stop
    empty = tmp_path / "empty"
    empty.mkdir()
    assert stop_ids(preflight_json(empty)[1]) == []
    prepare = init("prepare", str(repo))
    assert prepare.returncode == 1 and "no stack pack for node" in prepare.stderr
    if userns():
        probe = init("probe", str(repo))
        assert probe.returncode == 0, probe.stderr
        assert probe.stdout.startswith(
            "probe ....... unprobed: no stack pack for node: the probe runs Python console "
            "scripts ([project.scripts]) only"
        )


def test_preflight_reports_a_tracked_agent_folder_and_publish_ships_it_untracked(
    tmp_path: Path,
) -> None:
    """D7 in ADOPT (orca: 90 tracked .agent/ files, no ADOPT step untracked them)."""
    plan = {".agent/execplan-done.md": "# a finished plan\n", ".agent/decisions.md": "# d\n"}
    base = make_repo(tmp_path / "base", {"pyproject.toml": '[project]\nname = "b"\n', **plan})
    _, facts = preflight_json(base)
    assert facts["agent_tracked"] == 2
    text = init(
        "preflight", str(base), "--offline", "--vault", str(tmp_path / "v"), "--search-root", "x"
    ).stdout
    assert (
        ".agent/ ..... tracked (2 files): P2 reads it as intake, then P4 runs "
        "`git rm -r -q --cached .agent` (D7)"
    ) in text

    repo, env = shipped_repo(tmp_path, plan)
    look = init("publish", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert "D7 .......... publish refuses: .agent/ is still tracked (2 files)" in look.stdout
    refused = init("publish", str(repo), env=env)
    assert refused.returncode == 1
    assert "run `git rm -r -q --cached .agent` (P4), then re-run publish" in refused.stderr
    assert git(repo, "diff", "--cached", "--name-only") == ""  # nothing staged
    git(repo, "rm", "-r", "-q", "--cached", ".agent")
    done = init("publish", str(repo), env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    shipped = git(repo, "show", "--name-status", "--format=", "HEAD")
    assert "D\t.agent/decisions.md" in shipped and "D\t.agent/execplan-done.md" in shipped
    assert (repo / ".agent" / "decisions.md").is_file()  # the local scratch stays on disk
    assert git(repo, "check-ignore", ".agent/decisions.md").strip() == ".agent/decisions.md"


def test_python_candidates_come_from_the_repo_and_meet_requires_python(tmp_path: Path) -> None:
    mod = load_init()
    allows = mod.spec_allows
    assert allows(">=3.12", "3.14") and not allows(">=3.12", "3.11")
    assert allows(">=3.12,<3.13", "3.12") and not allows(">=3.12,<3.13", "3.13")
    assert allows("~=3.11", "3.13") and not allows("~=3.11", "3.10")
    assert allows("~=3.11.2", "3.11") and not allows("~=3.11.2", "3.12")
    assert allows("==3.12.*", "3.12") and not allows("==3.12.*", "3.13")
    assert allows(">3.11", "3.11")  # 3.11.1 is above 3.11
    assert allows(None, "3.9") and allows("weird", "3.9")  # unreadable: uv judges it

    orca = tmp_path / "orca"
    write(
        orca,
        {
            "pyproject.toml": '[project]\nname = "orca"\nrequires-python = ">=3.12"\n',
            "Dockerfile": "FROM --platform=linux/amd64 python:3.12-slim AS builder\n",
            "worker/Dockerfile": "FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim\n",
            ".github/workflows/ci.yml": (
                "jobs:\n  t:\n    strategy:\n      matrix:\n"
                '        python-version: ["3.11", "3.12"]  # 3.11 for the old box\n'
                "    steps:\n      - uses: actions/setup-python@v5\n        with:\n"
                "          python-version: ${{ matrix.python-version }}\n"
                "          python-version-file: .python-version\n"
            ),
        },
    )
    got = [(c.version, c.sources) for c in mod.python_candidates(orca)]
    assert got == [
        ("3.12", ["Dockerfile", ".github/workflows/ci.yml", "requires-python floor"]),
        ("3.13", ["worker/Dockerfile"]),
        (None, ["uv's default"]),
    ]  # 3.11 (CI) is below requires-python, so it is never tried
    write(orca, {".python-version": "3.14\n"})
    assert [(c.version, c.sources) for c in mod.python_candidates(orca)] == [
        (None, [".python-version"])
    ]
    bare = tmp_path / "bare"
    write(bare, {"pyproject.toml": '[project]\nname = "bare"\n'})
    assert [c.version for c in mod.python_candidates(bare)] == [None]

    _, facts = preflight_json(make_repo(tmp_path / "p0", {"pyproject.toml": TIPCALC_PYPROJECT}))
    assert facts["python"] == {
        "pin": None,
        "requires": ">=3.14",
        "candidates": [
            {"version": "3.14", "sources": ["requires-python floor"]},
            {"version": None, "sources": ["uv's default"]},
        ],
    }
    text = init(
        "preflight", str(tmp_path / "p0"), "--offline", "--vault", "v", "--search-root", "x"
    ).stdout
    assert (
        "python ...... no .python-version (requires-python >=3.14): P1 and P4 try 3.14 "
        "(requires-python floor), uv's default; P4 pins the first that builds (init.py prepare)"
    ) in text


FAKE_BUILD_UV = """#!/usr/bin/env python3
# uv for the pin tests: any sync on Python 3.14 (asked for, or uv's own default) fails the
# way orca's lxml 5.4.0 does; 3.12 builds. Each call is logged with whether the target
# folder had a .python-version at that moment.
import os
import sys

args = sys.argv[1:]
folder = args[1] if args[:1] == ["--directory"] else os.getcwd()
rest = args[2:] if args[:1] == ["--directory"] else args
pinned = os.path.exists(os.path.join(folder, ".python-version"))
with open(os.environ["FAKE_LOG"], "a", encoding="utf-8") as log:
    log.write(("pinned " if pinned else "unpinned ") + " ".join(rest) + "\\n")
if rest[:2] == ["cache", "dir"]:
    print(os.environ.get("FAKE_UV_CACHE", "/nonexistent"))
    sys.exit(0)
if rest[:1] == ["sync"]:
    if "--python" in rest:
        version = rest[rest.index("--python") + 1]
    elif pinned:
        version = open(os.path.join(folder, ".python-version")).read().split()[0]
    else:
        version = "3.14"
    bin_dir = os.path.join(folder, ".venv", "bin")
    os.makedirs(bin_dir, exist_ok=True)
    with open(os.path.join(folder, ".venv", "pyvenv.cfg"), "w") as cfg:
        cfg.write("home = /x\\nversion_info = " + version + ".7\\n")
    if version == "3.14":
        print("Resolved 235 packages", file=sys.stderr)
        print("\\u00d7 Failed to build `lxml==5.4.0`", file=sys.stderr)
        why = "hint: `lxml` (v5.4.0) was included because `app` depends on `crawl4ai`"
        print(why, file=sys.stderr)
        print("hint: Build failures usually indicate a problem with the package", file=sys.stderr)
        sys.exit(1)
    script = os.path.join(bin_dir, "app")
    with open(script, "w") as handle:
        handle.write("#!/bin/sh\\necho app ok\\n")
    os.chmod(script, 0o755)
    sys.exit(0)
if rest[:2] == ["lock", "--check"]:
    sys.exit(1)
sys.exit(0)
"""
APP_PYPROJECT = """[project]
name = "app"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["crawl4ai"]

[project.optional-dependencies]
dev = ["pytest>=7.4.0", "pytest-asyncio>=0.21.0", "app[cov]"]
cov = ["pytest-cov>=4.1.0"]
gpu = ["torch"]

[project.scripts]
app = "app:main"
"""


def build_env(tmp_path: Path) -> dict[str, str]:
    bin_dir = tmp_path / "buildbin"
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "uv").write_text(FAKE_BUILD_UV, encoding="utf-8")
    (bin_dir / "uv").chmod(0o755)
    return clean_env(
        PATH=f"{bin_dir}:{os.environ['PATH']}",
        FAKE_LOG=str(tmp_path / "uv.log"),
        TMPDIR=str(tmp_path),
    )


def test_prepare_pins_the_python_that_builds_before_any_uv_add_or_sync(tmp_path: Path) -> None:
    """orca: no .python-version, uv picked 3.14, lxml 5.4.0 failed to build, and P4's first
    `uv add` would have stopped the run. prepare pins what builds first (item 1), then adds
    the project's own test extras to the dev group (helios: pytest-asyncio, item 4)."""
    repo = make_repo(
        tmp_path / "app",
        {
            "pyproject.toml": APP_PYPROJECT,
            "src/app/__init__.py": "def main() -> None:\n    print('app ok')\n",
            ".github/workflows/ci.yml": (
                'jobs:\n  t:\n    steps:\n      - with:\n          python-version: "3.14"\n'
            ),
        },
    )
    env = build_env(tmp_path)
    on_main = init("prepare", str(repo), env=env)
    assert on_main.returncode == 1 and "HEAD is on main" in on_main.stderr
    git(repo, "switch", "-q", "-c", "plan/project-init")

    look = init("prepare", str(repo), "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert (
        "python ...... try 3.14 (.github/workflows/ci.yml), 3.12 (requires-python floor), uv's "
        "default in a scratch clone; write the first that builds to .python-version"
    ) in look.stdout
    assert (
        "dev deps .... uv add --dev 'pytest>=7.4.0' 'pytest-asyncio>=0.21.0' 'pytest-cov>=4.1.0' "
        "ruff ty ([project.optional-dependencies] dev, [project.optional-dependencies] cov, "
        "the standard)"
    ) in look.stdout
    assert not (tmp_path / "uv.log").exists()  # the dry run ran nothing
    assert not (repo / ".python-version").exists()

    done = init("prepare", str(repo), env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert (repo / ".python-version").read_text(encoding="utf-8") == "3.12\n"
    assert (
        "python ...... .python-version 3.12 written (it builds; from requires-python floor; "
        "failed first: 3.14: \u00d7 Failed to build `lxml==5.4.0`; hint: `lxml` (v5.4.0) was "
        "included because `app` depends on `crawl4ai`)"
    ) in done.stdout
    calls = (tmp_path / "uv.log").read_text(encoding="utf-8").splitlines()
    scratch = [c for c in calls if c.startswith("unpinned sync")]
    assert scratch == ["unpinned sync -q --python 3.14", "unpinned sync -q --python 3.12"]
    repo_calls = calls[len(scratch) :]
    assert repo_calls == [
        "pinned add --dev -q pytest>=7.4.0 pytest-asyncio>=0.21.0 pytest-cov>=4.1.0 ruff ty",
        "pinned lock --check -q",
        "pinned lock -q",
        "pinned sync --locked -q",
    ]  # every uv call on the repo came after the pin
    assert "sync ........ uv sync --locked: .venv on Python 3.12" in done.stdout
    assert git(repo, "status", "--porcelain", "--", "src") == ""  # the scratch clone, not this

    # the pin ships: publish names it with the lockfiles
    assert ".python-version" in load_init().ship_paths(repo, {})
    again = init("prepare", str(repo), "--python", "3.13", env=env)
    assert again.returncode == 2 and "pins 3.12 in .python-version already" in again.stderr


def test_prepare_takes_the_version_p1_reported_and_refuses_one_outside_the_spec(
    tmp_path: Path,
) -> None:
    repo = make_repo(tmp_path / "app", {"pyproject.toml": APP_PYPROJECT})
    git(repo, "switch", "-q", "-c", "plan/project-init")
    env = build_env(tmp_path)
    low = init("prepare", str(repo), "--python", "3.11", env=env)
    assert low.returncode == 2 and "requires-python >=3.12 does not allow it" in low.stderr
    done = init("prepare", str(repo), "--python", "3.12", env=env)
    assert done.returncode == 0, done.stdout + done.stderr
    assert ".python-version 3.12 written (--python)" in done.stdout
    calls = (tmp_path / "uv.log").read_text(encoding="utf-8").splitlines()
    assert calls[0].startswith("pinned add --dev") and not any("unpinned" in c for c in calls)

    stuck = make_repo(
        tmp_path / "stuck", {"pyproject.toml": APP_PYPROJECT.replace(">=3.12", ">=3.14")}
    )
    git(stuck, "switch", "-q", "-c", "plan/project-init")
    refused = init("prepare", str(stuck), env=env)
    assert refused.returncode == 1
    assert "no Python version builds the committed state (3.14: \u00d7 Failed" in refused.stderr
    assert not (stuck / ".python-version").exists()


def test_dev_additions_carry_the_project_s_own_test_dependencies(tmp_path: Path) -> None:
    mod = load_init()
    write(
        tmp_path / "a",
        {
            "pyproject.toml": (
                '[project]\nname = "My_App"\n\n[dependency-groups]\n'
                'dev = ["ruff>=0.6", {include-group = "test"}]\n'
                'test = ["pytest>=8", "hypothesis"]\nlint = ["mypy"]\n\n'
                "[project.optional-dependencies]\n"
                'testing = ["my-app[extra]", "respx"]\nextra = ["freezegun"]\n'
            )
        },
    )
    assert mod.dev_additions(tmp_path / "a") == [
        ("freezegun", "[project.optional-dependencies] extra"),
        ("respx", "[project.optional-dependencies] testing"),
        ("ty", "the standard"),
    ]  # ruff and the test group (pytest too) are in the dev group already, the test group
    # through its include-group; mypy's lint group is not a test group
    write(tmp_path / "b", {"pyproject.toml": '[project]\nname = "b"\n'})
    assert [r for r, _ in mod.dev_additions(tmp_path / "b")] == ["ruff", "ty", "pytest"]
    # a test group the dev group does not include is added, its own includes followed
    groups = (
        '[project]\nname = "c"\n\n[dependency-groups]\ndev = ["ruff"]\n'
        'Tests = ["pytest-asyncio", {include-group = "cov"}]\ncov = ["pytest-cov"]\n'
    )
    write(tmp_path / "c", {"pyproject.toml": groups})
    assert mod.dev_additions(tmp_path / "c") == [
        ("pytest-asyncio", "[dependency-groups] tests"),
        ("pytest-cov", "[dependency-groups] tests"),
        ("ty", "the standard"),
        ("pytest", "the standard"),
    ]
    # uv's default-groups syncs more than dev: what it installs is never added again
    synced = groups + '\n[tool.uv]\ndefault-groups = ["dev", "tests"]\n'
    write(tmp_path / "d", {"pyproject.toml": synced})
    assert [r for r, _ in mod.dev_additions(tmp_path / "d")] == ["ty", "pytest"]
    write(tmp_path / "e", {"pyproject.toml": synced.replace('["dev", "tests"]', '"all"')})
    assert [r for r, _ in mod.dev_additions(tmp_path / "e")] == ["ty", "pytest"]


def test_probe_builds_with_the_first_python_that_works_when_the_repo_pins_none(
    tmp_path: Path,
) -> None:
    if not userns():
        pytest.skip("no user namespaces")
    repo = make_repo(
        tmp_path / "app",
        {
            "pyproject.toml": APP_PYPROJECT,
            "Dockerfile": "FROM python:3.14-slim\n",
            "src/app/__init__.py": "def main() -> None:\n    print('app ok')\n",
        },
    )
    env = build_env(tmp_path)
    result = init("probe", str(repo), "--json", env=env)
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "ran" and report["python"] == "3.12"
    assert report["python_failures"] == [
        (
            "3.14: \u00d7 Failed to build `lxml==5.4.0`; hint: `lxml` (v5.4.0) was included "
            "because `app` depends on `crawl4ai`"
        )
    ]  # the cause, not uv's last line ("hint: Build failures usually ...")
    text = init("probe", str(repo), env=env).stdout
    assert (
        "python ...... no .python-version: 3.12 built the clone; P4 pins it (init.py prepare "
        "--python 3.12); tried first: 3.14: \u00d7 Failed to build"
    ) in text
    assert not (repo / ".python-version").exists()  # P1 writes nothing


def test_the_probe_says_how_little_it_learns_about_a_service(tmp_path: Path) -> None:
    """orca: a stub console script and service signals gave --help only, and the report did
    not say that told nothing about the service. helios: no console script at all."""
    if not userns():
        pytest.skip("no user namespaces")
    repo = tipcalc_like(tmp_path / "tipcalc")
    write(repo, {"Dockerfile": "FROM scratch\n"})
    git(repo, "add", "Dockerfile")
    git(repo, "commit", "-q", "-m", "build: container")
    text = init("probe", str(repo)).stdout
    assert (
        "service ..... little signal for a service: the deploy signals limit it to --help, "
        "which never reaches the running service"
    ) in text
    assert (
        "P2: suggest the service's health check as the Run-it row of the first feat change "
        "(validation.md `## Run it`), e.g. `| curl -fsS http://localhost:<port>/health | 0 | | |`"
    ) in text
    report = json.loads(init("probe", str(repo), "--json").stdout)
    assert report["service"] == ["deploy: Dockerfile"]

    service = make_repo(
        tmp_path / "svc",
        {"pyproject.toml": '[project]\nname = "svc"\ndependencies = ["fastapi"]\n'},
    )
    skipped = init("probe", str(service)).stdout
    assert skipped.startswith("probe ....... skipped: no console scripts ([project.scripts])\n")
    assert (
        "service ..... little signal for a service: the api signals mark a service, and with no "
        "console script nothing ran\n"
    ) in skipped
    plain = init("probe", str(tipcalc_like(tmp_path / "plain" / "tipcalc"))).stdout
    assert "service ....." not in plain
    # a service whose build failed: nothing ran either, and the note does not blame scripts
    mod = load_init()
    failed = mod.ProbeReport(
        "unprobed", "uv sync failed in the clean clone: x", [], "", True, [], True
    )
    failed.service = ["api: pyproject.toml: fastapi"]
    assert mod.probe_notes(failed)[0] == (
        "service ..... little signal for a service: the api signals mark a service, and nothing "
        "ran (above)"
    )


def test_publish_names_the_github_repo_after_the_folder_or_repo(tmp_path: Path) -> None:
    """The remote trial: publish named the repo after the distribution (`tipcalc`), so the trial
    repo `project-init-v3-trial` could not be made without renaming the package."""
    repo, env = shipped_repo(tmp_path)
    trial = repo.rename(tmp_path / "project-init-v3-trial")
    look = init("publish", str(trial), "--remote", "github", "--dry-run", env=env)
    assert look.returncode == 0, look.stdout + look.stderr
    assert "  1. gh repo create project-init-v3-trial --private --source ." in look.stdout
    named = init(
        "publish",
        str(trial),
        "--remote",
        "github",
        "--repo",
        "tipcalc-v3-trial",
        "--dry-run",
        env=env,
    )
    assert "  1. gh repo create tipcalc-v3-trial --private" in named.stdout
    assert "repos/<owner>/tipcalc-v3-trial/branches/main/protection" in named.stdout
    bad = init("publish", str(trial), "--remote", "github", "--repo", "a b", "--dry-run", env=env)
    assert bad.returncode == 2 and "'a b' is not a GitHub repo name" in bad.stderr
    # a name that reads as a flag: gh would take `--push` (push on create, N10) or `--public`
    for flag in ("--push", "--public", "owner/--push", "-x"):
        dash = init(
            "publish", str(trial), "--remote", "github", f"--repo={flag}", "--dry-run", env=env
        )
        assert dash.returncode == 2, dash.stdout + dash.stderr
        assert f"{flag!r} is not a GitHub repo name" in dash.stderr
        assert "gh repo create" not in dash.stdout
    dotted = init(
        "publish", str(trial), "--remote", "github", "--repo=.github", "--dry-run", env=env
    )
    assert "  1. gh repo create .github --private" in dotted.stdout  # a real GitHub name
    local = init("publish", str(trial), "--repo", "a b", "--dry-run", env=env)
    assert local.returncode == 0  # no remote asked: the name is never used


def test_render_records_a_free_private_origin_once_and_the_quickstart_clones_it(
    tmp_path: Path,
) -> None:
    """An ADOPT with a GitHub origin (orca, helios): server_protection stayed `pending` forever.
    render now asks the protection API once, and P6's quickstart carries the clone line."""
    repo = tipcalc_like(tmp_path / "tipcalc")
    git(repo, "remote", "add", "origin", "https://github.com/test-owner/tipcalc.git")
    fake = tmp_path / "fakebin" / "gh"
    fake.parent.mkdir()
    fake.write_text(FAKE_GH, encoding="utf-8")
    fake.chmod(0o755)
    env = clean_env(PATH=f"{fake.parent}:{os.environ['PATH']}", FAKE_LOG=str(tmp_path / "gh.log"))
    refs = {**VALUES, "CHECKOUT_REF": "v4", "MISE_ACTION_REF": "v4"}
    offline = init("render", str(repo), "--offline", "--values", json.dumps(refs), env=env)
    assert offline.returncode == 0, offline.stdout + offline.stderr
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["server_protection"].startswith("pending:")  # offline: no gh call
    assert not (tmp_path / "gh.log").exists()

    first = init("render", str(repo), "--values", json.dumps(refs), env=env)
    assert first.returncode == 0, first.stdout + first.stderr
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["server_protection"] == "unavailable: Free private"
    assert init("render", str(repo), env=env).returncode == 0
    calls = (tmp_path / "gh.log").read_text(encoding="utf-8").splitlines()
    assert calls == ["gh api repos/test-owner/tipcalc/branches/main/protection"]  # never retried

    pro = tipcalc_like(tmp_path / "pro" / "tipcalc")
    git(pro, "remote", "add", "origin", "https://github.com/test-owner/tipcalc.git")
    done = init("render", str(pro), "--values", json.dumps(refs), env={**env, "FAKE_PLAN": "pro"})
    assert done.returncode == 0, done.stdout + done.stderr
    manifest = tomllib.loads((pro / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["server_protection"].startswith("pending:")  # 404: rules are possible

    tools = fake_tools(tmp_path)
    assert init("selftest", str(repo), "--start-args", "100", env=tools).returncode == 0
    front = render(repo, "--front-door")
    assert front.returncode == 0, front.stdout + front.stderr
    readme = (repo / "README.md").read_text(encoding="utf-8")
    assert (
        "```sh\ngit clone https://github.com/test-owner/tipcalc.git && cd tipcalc\n"
        "curl https://mise.run | sh      # once per machine\n"
    ) in readme


def test_the_clone_line_never_prints_credentials(tmp_path: Path) -> None:
    mod = load_init()
    assert mod.public_url("https://user:tok@github.com/o/r.git") == "https://github.com/o/r.git"
    assert mod.public_url("git@github.com:o/r.git") == "git@github.com:o/r.git"
    assert mod.url_tail("git@github.com:Owner/My-Repo.git") == "My-Repo"
    assert mod.url_tail("https://github.com/o/r/") == "r"
    assert mod.unsafe_values({"CLONE_URL": "https://x/`rm`"})


# ---------------------------------------------------------------------------------------------
# Brownfield rechecks: helios (v1 layout, backend/tests), orca (colocated tests, a stub start,
# module-constant env reads) and open-kit (no stack pack)

HELIOS_PYPROJECT = """[project]
name = "helios"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.pytest.ini_options]
testpaths = ["backend/tests"]
addopts = "-v --tb=short -ra"
"""
HELIOS_TEST = """import pytest
from experts.loader import load


@pytest.mark.spec("chat.loads")
def test_loads(word: str) -> None:
    assert load() == word


@pytest.mark.spec("chat.discipline-last")
@pytest.mark.xfail(strict=True, reason="chat.discipline-last: the discipline is not last yet")
def test_discipline_last() -> None:
    assert load() == "discipline"
"""
CHAT_CAPABILITY = """# Capability: chat

## Requirement: Loading
The loader SHALL load the experts.

### Scenario: chat.loads
- GIVEN the experts
- WHEN load runs
- THEN it returns ok
"""


def helios_like(root: Path, extra: dict[str, str] | None = None) -> Path:
    """helios's layout: the code in backend/ (packages and modules), the tests in the package
    backend/tests with a conftest.py of their own, pytest's testpaths = ["backend/tests"]."""
    make_repo(
        root,
        {
            "pyproject.toml": HELIOS_PYPROJECT,
            "backend/main.py": "from experts.loader import load\n\nprint(load())\n",
            "backend/experts/__init__.py": "",
            "backend/experts/loader.py": "def load() -> str:\n    return 'ok'\n",
            "backend/tests/__init__.py": "",
            "backend/tests/conftest.py": (
                "import pytest\n\n\n@pytest.fixture\ndef word() -> str:\n    return 'ok'\n"
            ),
            "backend/tests/unit/__init__.py": "",
            "backend/tests/unit/test_loader.py": HELIOS_TEST,
            **(extra or {}),
        },
    )
    git(root, "switch", "-q", "-c", "plan/project-init")
    write(root, {"specs/tech-stack.md": TECH_STACK, "specs/capabilities/chat.md": CHAT_CAPABILITY})
    return root


def test_the_spec_plugin_loads_for_testpaths_outside_tests(tmp_path: Path) -> None:
    """helios: testpaths = ["backend/tests"], so pytest never loaded tests/conftest.py and
    verify failed `no test results`. The plugin goes in the deepest free folder above every
    test root (backend/: backend/tests holds helios's own conftest.py), [paths] names the real
    roots, and a plain pytest run writes .cache/spec-results.json with real outcomes."""
    repo = helios_like(tmp_path / "helios")
    result = render(repo, values={**VALUES, "ENTRY": "python backend/main.py"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "spec plugin: backend/conftest.py, since the tests in backend/tests" in result.stdout
    hashes = generated(repo)
    assert "backend/conftest.py" in hashes and "tests/conftest.py" not in hashes
    assert not (repo / "tests").exists()
    plugin = (SKILL / "templates" / "tests" / "conftest.py").read_bytes()
    assert (repo / "backend" / "conftest.py").read_bytes() == plugin
    assert "def word()" in (repo / "backend/tests/conftest.py").read_text(encoding="utf-8")
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    # D4's Spec: rule and prove-red read [paths] src: the code beside the tests, never them
    assert manifest["paths"] == {
        "src": ["backend/experts", "backend/main.py"],
        "tests": ["backend/tests"],
    }
    tool = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["tool"]
    assert tool["ruff"]["extend-exclude"] == ["scripts/project.py", "backend/conftest.py"]

    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
        timeout=300,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    results = json.loads((repo / ".cache" / "spec-results.json").read_text(encoding="utf-8"))
    assert results["complete"] is True, results["partial"]
    outcomes = {sid: [n["outcome"] for n in nodes] for sid, nodes in results["ids"].items()}
    assert outcomes == {"chat.loads": ["passed"], "chat.discipline-last": ["xfailed"]}
    node = results["nodes"]["backend/tests/unit/test_loader.py::test_discipline_last"]
    assert (node["body"], node["raised_in"]) == ("AssertionError", "test")

    again = render(repo)  # the placement is stable: the plugin a render wrote is its own
    assert again.returncode == 0, again.stdout
    assert again.stdout.strip().endswith("render: 0 changes")


def test_the_spec_plugin_placement_rules(tmp_path: Path) -> None:
    """Every layout: tests/ (the standard), a root conftest.py when the test roots only share
    the root, and tests/conftest.py plus a note when the project's own conftest.py holds every
    folder above them (orca keeps one at the root and colocates tests in src/orca)."""
    mod = load_init()
    assert mod.spec_plugin_dest(tmp_path, ["tests", "tests/unit"], ["src"], {}) == (
        "tests/conftest.py",
        None,
    )
    two = tmp_path / "two"
    write(two, {"backend/tests/conftest.py": "", "frontend/tests/test_x.py": ""})
    dest, note = mod.spec_plugin_dest(two, ["backend/tests", "frontend/tests"], ["backend"], {})
    assert dest == "conftest.py" and "the repo root holds them all" in str(note)
    assert mod.ruff_exclude_path(dest) == "./conftest.py"  # a bare name excludes them all

    orca = tmp_path / "orca"
    write(
        orca,
        {
            "conftest.py": "import pytest\n",
            "tests/test_a.py": "",
            "src/orca/__init__.py": "",
            "src/orca/api/tests/test_b.py": "",
            "src/orca/api/app.py": "",
            "pytest.ini": "[pytest]\ntestpaths = tests src/orca\n",
            "pyproject.toml": '[tool.pytest.ini_options]\ntestpaths = ["ignored"]\n',
        },
    )
    testpaths = mod.pytest_testpaths(orca)
    assert testpaths == ["tests", "src/orca"]  # pytest.ini wins, as it does for pytest
    src = mod.src_roots(orca, testpaths)
    assert src == ["src"]
    # a testpath inside a source root counts by its tests/ folders: the whole package as a test
    # root would make every source edit a test edit (I7)
    tests = mod.test_roots(orca, testpaths, src)
    assert tests == ["tests", "src/orca/api/tests"]
    dest, note = mod.spec_plugin_dest(orca, tests, src, {})
    assert dest == "tests/conftest.py"
    assert "The tests in src/orca/api/tests never load it" in str(note)
    assert "project's own conftest.py (conftest.py)" in str(note)

    for name, text in (
        ("setup.cfg", "[tool:pytest]\ntestpaths =\n    it\n"),
        ("tox.ini", "[pytest]\ntestpaths = it\n"),
        ("pyproject.toml", '[tool.pytest]\ntestpaths = ["it"]\n'),
    ):
        folder = tmp_path / name
        write(folder, {name: text})
        assert mod.pytest_testpaths(folder) == ["it"], name
    assert mod.test_roots(tmp_path / "setup.cfg", [], ["src"]) == ["tests"]


COLOCATED_TEST = """from tipcalc import tip
import pytest


@pytest.mark.spec("cli.tip-default")
def test_tip_default() -> None:
    assert tip(100, 15) == 15.0
"""
OWN_CONFTEST = "import pytest\n\n\n@pytest.fixture\ndef word() -> str:\n    return 'ok'\n"
OWN_CONFTEST_TEST = """import pytest


@pytest.mark.spec("cli.tip-default")
def test_tip_default(word: str) -> None:
    assert word == "ok"
"""


@pytest.mark.parametrize(
    ("files", "tests", "why"),
    [
        (  # no testpaths: pytest collects from the root, and the tests sit in the package
            {"src/tipcalc/tests/__init__.py": "", "src/tipcalc/tests/test_cli.py": COLOCATED_TEST},
            ["src/tipcalc/tests"],
            "since the tests in src/tipcalc/tests reach outside tests/",
        ),
        (  # the standard layout, with the project's own tests/conftest.py
            {"tests/conftest.py": OWN_CONFTEST, "tests/test_cli.py": OWN_CONFTEST_TEST},
            ["tests"],
            "since tests/conftest.py is the project's own",
        ),
    ],
    ids=["colocated-no-testpaths", "own-tests-conftest"],
)
def test_the_spec_plugin_reaches_every_test_without_testpaths(
    tmp_path: Path, files: dict[str, str], tests: list[str], why: str
) -> None:
    """A project that sets no testpaths has pytest collect from the root. [paths] tests came
    out as "tests" wherever the tests sat, and the plugin went in tests/conftest.py: the
    colocated test recorded `notrun`, and a project's own tests/conftest.py got the
    customized-file question (render exit 3). Both now get the root conftest.py."""
    repo = tipcalc_like(tmp_path / "tipcalc", files)
    own = (repo / "tests" / "conftest.py").read_bytes() if "tests/conftest.py" in files else None
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"spec plugin: conftest.py, {why}" in result.stdout
    assert "(the repo root holds them all)" in result.stdout
    plugin = (SKILL / "templates" / "tests" / "conftest.py").read_bytes()
    assert (repo / "conftest.py").read_bytes() == plugin
    hashes = generated(repo)
    assert "conftest.py" in hashes and "tests/conftest.py" not in hashes
    if own is None:
        assert not (repo / "tests").exists()
    else:
        assert (repo / "tests" / "conftest.py").read_bytes() == own
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["paths"] == {"src": ["src"], "tests": tests}
    tool = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))["tool"]
    assert tool["ruff"]["extend-exclude"] == ["scripts/project.py", "./conftest.py"]

    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=repo,
        capture_output=True,
        text=True,
        env=clean_env(),
        check=False,
        timeout=300,
    )
    assert done.returncode == 0, done.stdout + done.stderr
    results = json.loads((repo / ".cache" / "spec-results.json").read_text(encoding="utf-8"))
    assert results["complete"] is True, results["partial"]
    outcomes = {sid: [n["outcome"] for n in nodes] for sid, nodes in results["ids"].items()}
    assert outcomes == {"cli.tip-default": ["passed"]}

    again = render(repo)  # stable: the root conftest.py is the plugin a render wrote
    assert again.returncode == 0, again.stdout
    assert again.stdout.strip().endswith("render: 0 changes")


def test_the_spec_plugin_placement_without_testpaths(tmp_path: Path) -> None:
    """No testpaths: the test roots are the tests/ folders under the root (top-level first),
    a loose test_*.py pulls the plugin up to a folder above it, a checkout named tests is
    never a test root, and a virtualenv is never searched. When every conftest.py that could
    carry the plugin is the project's own, the note says what render's question means."""
    mod = load_init()
    both = tmp_path / "both"
    write(
        both,
        {
            "tests/test_a.py": "",
            "src/app/__init__.py": "",
            "src/app/tests/test_b.py": "",
            "env/pyvenv.cfg": "",
            "env/lib/tests/test_c.py": "",
        },
    )
    assert mod.pytest_testpaths(both) == []
    tests = mod.test_roots(both, [], ["src"])
    assert tests == ["tests", "src/app/tests"]
    assert mod.loose_tests(both, [], tests) == []
    assert mod.spec_plugin_dest(both, tests, ["src"], {}, [])[0] == "conftest.py"

    loose = tmp_path / "loose"
    write(loose, {"tests/test_a.py": "", "src/app/__init__.py": "", "src/app/test_x.py": ""})
    found = mod.loose_tests(loose, [], ["tests"])
    assert found == ["src/app/test_x.py"]
    dest, note = mod.spec_plugin_dest(loose, ["tests"], ["src"], {}, found)
    assert dest == "conftest.py" and "the tests in src/app/test_x.py reach outside" in str(note)
    # a testpaths list scopes the search: pytest never collects src/app/test_x.py then
    assert mod.loose_tests(loose, ["tests"], ["tests"]) == []

    named = tmp_path / "tests"  # a checkout whose folder is named tests
    write(named, {"test_top.py": ""})
    assert mod.test_roots(named, [], ["src"]) == ["tests"]
    assert mod.loose_tests(named, [], ["tests"]) == ["test_top.py"]

    owned = tmp_path / "owned"
    write(owned, {"conftest.py": "", "tests/conftest.py": "", "tests/test_a.py": ""})
    dest, note = mod.spec_plugin_dest(owned, ["tests"], ["src"], {}, [])
    assert dest == "tests/conftest.py"
    assert "the project's own (tests/conftest.py, conftest.py)" in str(note)
    assert "render asks before it writes over tests/conftest.py" in str(note)
    # the plugin a render wrote is free: the placement never moves on its own
    dest, note = mod.spec_plugin_dest(owned, ["tests"], ["src"], {"conftest.py": "x"}, [])
    assert dest == "conftest.py"
    assert "since tests/conftest.py is the project's own and pytest loads" in str(note)

    app = make_repo(
        tmp_path / "app",
        {"app/main.py": "", "app/tests/__init__.py": "", "app/tests/test_x.py": ""},
    )
    src = mod.src_roots(app, [])  # the code beside the tests, found without testpaths too
    assert src == ["app/main.py"]
    assert mod.test_roots(app, [], src) == ["app/tests"]


TEST_CODES = ["S101", "S603", "S607"]
PROBE_TEST = "def test_probe() -> None:\n    assert 1 + 1 == 2\n"


def test_the_tests_lint_row_keys() -> None:
    """ruff's per-file-ignores row for the tests comes once per [paths] tests root and once per
    folder of loose tests; `./` anchors the root, where ruff would match a bare pattern
    against every file's name. The standard layout keeps the template's tests/** row."""
    mod = load_init()
    template = (SKILL / "templates" / "pyproject-additions.toml").read_text(encoding="utf-8")
    assert mod.pyproject_additions("tests/conftest.py", ["tests"], []) == template
    keys = mod.test_lint_keys(
        ["backend/tests", "src/app/tests"],
        ["test_top.py", "src/app/test_x.py", "src/app/y_test.py", "src/app/tests/test_in.py"],
    )
    assert keys == [
        "backend/tests/**",
        "src/app/tests/**",
        "./test_*.py",
        "src/app/test_*.py",
        "src/app/*_test.py",
    ]
    text = mod.pyproject_additions("backend/conftest.py", ["backend/tests"], [])
    ignores = tomllib.loads(text)["tool"]["ruff"]["lint"]["per-file-ignores"]
    assert ignores == {"backend/tests/**": TEST_CODES}
    assert '"backend/tests/**" = ["S101", "S603", "S607"]     # assert, and subprocess' in text


def test_the_tests_lint_row_follows_every_test_root(tmp_path: Path) -> None:
    """The row was fixed to tests/**: helios's pre-commit refused every assert in a new
    backend/tests file (S101), and the ruff baseline took a colocated project's own test
    asserts as lint debt. Now the row follows [paths] tests and the loose tests, and a row a
    later render adds lands above the baseline block, which doctor holds to shrink-only."""
    ruff = need(real_ruff(tmp_path), "no ruff binary in uv's cache")

    def staged_lint(repo: Path, path: str) -> subprocess.CompletedProcess[str]:
        """What pre-commit runs on a staged .py (project.py ruff_staged)."""
        argv = [ruff, "check", "--no-fix", "--output-format", "concise", "--no-cache"]
        return subprocess.run(
            [*argv, "--force-exclude", "--stdin-filename", path, "-"],
            cwd=repo,
            input=(repo / path).read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    def ignores_of(repo: Path) -> dict[str, list[str]]:
        text = (repo / "pyproject.toml").read_text(encoding="utf-8")
        return tomllib.loads(text)["tool"]["ruff"]["lint"]["per-file-ignores"]

    helios = helios_like(tmp_path / "helios")
    (helios / ".venv" / "bin").mkdir(parents=True)
    (helios / ".venv" / "bin" / "ruff").symlink_to(ruff)
    result = render(helios, values={**VALUES, "ENTRY": "python backend/main.py"})
    assert result.returncode == 0, result.stdout + result.stderr
    assert ignores_of(helios) == {"backend/tests/**": TEST_CODES}
    manifest = tomllib.loads((helios / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["ruff_baseline"] == "none: ruff check is clean"  # its asserts are no debt
    write(helios, {"backend/tests/unit/test_zz_probe.py": PROBE_TEST})
    probe = staged_lint(helios, "backend/tests/unit/test_zz_probe.py")
    assert probe.returncode == 0, probe.stdout + probe.stderr

    legacy = "import subprocess\n\n\ndef run(cmd):\n    return subprocess.call(cmd, shell=True)\n"
    repo = tipcalc_like(
        tmp_path / "tipcalc",
        {
            "src/tipcalc/legacy.py": legacy,
            "src/tipcalc/tests/__init__.py": "",
            "src/tipcalc/tests/test_cli.py": COLOCATED_TEST,
            "src/tipcalc/test_more.py": PROBE_TEST,
            "test_top.py": PROBE_TEST,
        },
    )
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "ruff").symlink_to(ruff)
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = tomllib.loads((repo / ".project.toml").read_text(encoding="utf-8"))
    assert manifest["paths"]["tests"] == ["src/tipcalc/tests"]
    ignores = ignores_of(repo)
    assert {k: v for k, v in ignores.items() if v == TEST_CODES} == {
        "src/tipcalc/tests/**": TEST_CODES,
        "src/tipcalc/test_*.py": TEST_CODES,
        "./test_*.py": TEST_CODES,
    }
    debt = {k: v for k, v in ignores.items() if v != TEST_CODES}
    assert "src/tipcalc/legacy.py" in debt
    assert not any("S101" in codes for codes in debt.values())  # no test assert is debt

    def baseline_keys() -> tuple[list[str], int]:
        """(the rows under the baseline mark, the mark's line), read the way doctor reads them."""
        lines = (repo / "pyproject.toml").read_text(encoding="utf-8").splitlines()
        mark = next(i for i, line in enumerate(lines) if "baseline: shrink only" in line)
        end = next(i for i in range(mark + 1, len(lines)) if lines[i][:1] == "[")
        return [line.split(" = ")[0] for line in lines[mark:end] if line[:1] == '"'], mark

    first_rows, _ = baseline_keys()
    assert '"src/tipcalc/legacy.py"' in first_rows

    # a folder of loose tests that came later: its row goes above the baseline mark, since
    # doctor reads every row under the mark as baseline and fails when that block grows
    write(repo, {"src/tipcalc/extra/__init__.py": "", "src/tipcalc/extra/test_new.py": PROBE_TEST})
    again = render(repo)
    assert again.returncode == 0, again.stdout + again.stderr
    lines = (repo / "pyproject.toml").read_text(encoding="utf-8").splitlines()
    row = lines.index('"src/tipcalc/extra/test_*.py" = ["S101", "S603", "S607"]')
    rows, mark = baseline_keys()
    assert row < mark
    assert rows == first_rows
    for path in ("src/tipcalc/extra/test_new.py", "src/tipcalc/test_more.py", "test_top.py"):
        probe = staged_lint(repo, path)
        assert probe.returncode == 0, path + probe.stdout + probe.stderr
    write(repo, {"src/tipcalc/notes.py": PROBE_TEST})  # not a test file: S101 still applies
    assert "S101" in staged_lint(repo, "src/tipcalc/notes.py").stdout


def test_the_verify_fingerprint_covers_a_module_source_root(tmp_path: Path) -> None:
    """[paths] src may name a module (helios's backend/main.py): an edit to it makes the
    verify.json P5 wrote stale, like an edit under a source folder."""
    mod = load_init()
    write(
        tmp_path,
        {
            ".project.toml": '[paths]\nsrc = ["backend/experts", "backend/main.py"]\n',
            "backend/main.py": "print(1)\n",
            "backend/experts/loader.py": "x = 1\n",
        },
    )
    before = mod.verify_fingerprint(tmp_path)
    write(tmp_path, {"backend/main.py": "print(2)\n"})
    assert mod.verify_fingerprint(tmp_path) != before


def test_selftest_gives_the_whole_suite_a_scaled_timeout(tmp_path: Path) -> None:
    """helios's verify takes 150-200 s, so the flat 60 s ended it at exit 124 every time.
    verify and test get max(600 s, twice the last run), or --suite-timeout."""
    mod = load_init()
    repo = tmp_path / "rendered"
    write(repo, {"scripts/project.py": STUB_PROJECT})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    timeouts = {c.name: c.timeout for c in mod.positive_checks(repo, ["100"], scratch)}
    assert (timeouts["mise run verify"], timeouts["mise install"]) == (600, 600)
    assert timeouts["mise run status"] == timeouts["mise run start -- 100"] == 60
    # orca: a happy path of `start -- --help` is that row, listed once (last, and required)
    helped = mod.positive_checks(repo, ["--help"], scratch)
    assert [c.name for c in helped].count("mise run start -- --help") == 1
    assert helped[-1].name == "mise run start -- --help" and helped[-1].required
    assert mod.suite_timeout(repo, None) == (600, "the floor")
    last = {"checks": [{"argv": ["mise", "run", "verify"], "seconds": 169.1}]}  # helios's
    write(repo, {".agent/project-init/verify.json": json.dumps(last)})
    assert mod.suite_timeout(repo, None) == (600, "the floor; the last run took 169 s")
    last = {"checks": [{"argv": ["mise", "run", "verify"], "seconds": 452.3}]}
    write(repo, {".agent/project-init/verify.json": json.dumps(last)})
    assert mod.suite_timeout(repo, None) == (905, "twice the 452 s the last run took")
    assert mod.suite_timeout(repo, 1200) == (1200, "--suite-timeout")

    env = fake_tools(tmp_path, uv=False, FAKE_VERIFY_SLEEP="5")
    result = init("selftest", str(repo), "--start-args", "100", "--suite-timeout", "1", env=env)
    assert result.returncode == 1, result.stdout + result.stderr
    assert (
        "timeouts .... 60 s per check; mise install 600 s; mise run verify and test 1 s "
        "(--suite-timeout): they run the whole test suite"
    ) in result.stdout
    assert "  FAIL  mise run verify (exit 124" in result.stdout
    assert "timed out after 1 s: the suite needs longer; re-run with --suite-timeout" in (
        result.stdout
    )
    checks = {c["name"]: c for c in verify_checks(repo)}
    assert checks["mise run verify"]["timeout"] == 1
    assert checks["mise run status"]["green"] is True
    assert init("selftest", str(repo), "--suite-timeout", "0", env=env).returncode == 2


ENV_CONSTANTS = {
    "src/app/http.py": (
        "import os\n"
        "from collections.abc import Mapping\n\n"
        'HOST_ENV = "APP_HOST"\n'
        'lower = "not_an_env_name"\n\n\n'
        "def host(env: Mapping[str, str] | None = None) -> str:\n"
        '    return (env if env is not None else os.environ).get(HOST_ENV, "").strip()\n\n\n'
        "def port() -> int:\n"
        '    return int((None or os.environ).get(PORT_ENV, "8765"))\n\n\n'
        'PORT_ENV = "APP_PORT"\n\n\n'
        "def any_key(name: str) -> str | None:\n"
        "    return os.environ.get(name)  # a parameter: no constant names it\n"
    ),
    "src/app/boe/config.py": 'CA_BUNDLE_ENV = "BOE_CA_BUNDLE"\nname = "APP_NOT_A_READ"\n',
    "src/app/boe/client.py": (
        "import os\n\n"
        "from app.boe import config\n"
        "from app.boe.config import CA_BUNDLE_ENV as BUNDLE\n\n"
        "EXTRA = os.environ.get(BUNDLE)\n"
        "AGAIN = os.environ.get(config.CA_BUNDLE_ENV)\n"
    ),
    "src/app/settings.py": (
        "from pydantic_settings import BaseSettings\n\n\n"
        "class Settings(BaseSettings):\n"
        "    anthropic_api_key: str | None = None\n"
        "    admin_token: str\n"
    ),
}


def test_env_reads_resolve_module_constants_and_secrets_take_required_from_code(
    tmp_path: Path,
) -> None:
    """orca: ORCA_MCP_HOST and friends are read through module constants, one of them through
    `(env if env is not None else os.environ)`, and BOE_CA_BUNDLE through a constant another
    module defines; the four `str | None = None` secrets rendered `required yes`, and doctor
    FAILed each while unset."""
    write(tmp_path, ENV_CONSTANTS)
    mod = load_init()
    reads = {r.name: r for r in mod.env_reads(tmp_path)}
    assert sorted(reads) == [
        "ADMIN_TOKEN",
        "ANTHROPIC_API_KEY",
        "APP_HOST",
        "APP_PORT",
        "BOE_CA_BUNDLE",
    ]  # not the parameter `name`, not the lower-case constant
    assert (reads["APP_HOST"].default, reads["APP_HOST"].where) == ("", ["src/app/http.py:9"])
    assert (reads["APP_PORT"].type, reads["APP_PORT"].default) == ("int", "8765")
    # read through an imported constant: the note names the file that spells the name out,
    # which doctor greps for it
    assert reads["BOE_CA_BUNDLE"].where == ["src/app/boe/config.py:1"] * 2
    rows = mod.env_rows(list(reads.values()))
    assert "# ANTHROPIC_API_KEY | secret | str | no | - | op:// pointer; read in " in rows
    assert "# ADMIN_TOKEN | secret | str | yes | - | op:// pointer; read in " in rows
    assert "# BOE_CA_BUNDLE | knob | str | no | - | read in src/app/boe/config.py" in rows


ENV_FALLBACKS = (
    "import os\n\n"
    'HOST_ENV = "APP_HOST"\n'
    'DEFAULT_HOST = "127.0.0.1"\n'
    "DEFAULT_PORT = 8765\n"
    'DEFAULT_LIMIT = "120/minute"\n\n\n'
    "def host() -> str:\n"
    '    value = os.environ.get(HOST_ENV, "").strip()\n'
    "    return value or DEFAULT_HOST\n\n\n"
    "def port() -> int:\n"
    '    raw = os.environ.get("APP_PORT", "").strip()\n'
    "    if not raw:\n"
    "        return DEFAULT_PORT\n"
    "    return int(raw)\n\n\n"
    'LIMIT = os.environ.get("APP_LIMIT", "") or DEFAULT_LIMIT\n'
    'MODE = os.environ.get("APP_MODE") or "fast"\n'
    'NAME = os.environ.get("APP_NAME", "") or os.getcwd()\n'
    'EMPTY = os.environ.get("APP_EMPTY", "")\n'
)


def test_an_empty_env_default_records_what_the_code_falls_back_to(tmp_path: Path) -> None:
    """orca re-check: ORCA_MCP_HOST, _PORT and _RATE_LIMIT rendered the default "" and doctor
    said `default "" applies`, while the code falls back to 127.0.0.1, 8765 and 120/minute.
    An empty read or-ed with a literal or a module constant, directly or through one variable
    of the function (`value or DEFAULT`, `if not raw: return DEFAULT`), records that value;
    a fallback that is no constant keeps the read's own default."""
    write(tmp_path, {"src/app/http.py": ENV_FALLBACKS})
    mod = load_init()
    defaults = {r.name: r.default for r in mod.env_reads(tmp_path)}
    assert defaults == {
        "APP_EMPTY": "",
        "APP_HOST": "127.0.0.1",
        "APP_LIMIT": "120/minute",
        "APP_MODE": "fast",
        "APP_NAME": "",
        "APP_PORT": "8765",
    }
    rows = mod.env_rows(mod.env_reads(tmp_path))
    assert "# APP_PORT | knob | str | no | 8765 | read in src/app/http.py\n#APP_PORT=8765" in rows


COMPOSE = """services:
  api:
    image: app
    command: ["uvicorn", "app.api:app", "--port", "${API_PORT:-8000}"]
    environment:
      DATABASE_URL: postgresql://app:${POSTGRES_PASSWORD}@db/app
      ESCAPED: $$NOT_A_KNOB
  worker:
    command:
      - python
      - -m
      - app.worker
  # ${COMMENTED_OUT}
"""
MAKEFILE = """COMPOSE := docker compose
SMOKE_PORT ?= 18765

dev:
\t@echo "make dev - start uvicorn"
\tuv run uvicorn app.api:app --reload

mcp:
\t@echo "port $${MCP_PORT:-8765} $(COMPOSE) $$COMPOSE"
"""


def test_adoption_carries_the_project_s_env_names_over(tmp_path: Path) -> None:
    """orca: taking the rendered .env.example dropped 9 names its old file, compose and Make
    use. They carry over as rows (not required, str, blank value), secret-named ones as
    op:// rows, and a second render keeps them."""
    repo = tipcalc_like(
        tmp_path / "tipcalc",
        {
            ".env.example": (
                "# Application\nAPP_NAME=Orca\nexport SOURCE_CKAN_ENABLED=true\n"
                "ADMIN_API_KEY=\n# COMMENTED=1\nTIPCALC_DEFAULT_PERCENT=15\n"
            ),
            "docker-compose.yml": COMPOSE,
            "Makefile": MAKEFILE,
        },
    )
    asked = render(repo, values=VALUES)
    assert asked.returncode == 3, asked.stdout  # the project's own .env.example: a question
    result = render(repo, "--force-file", ".env.example", values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (repo / ".env.example").read_text(encoding="utf-8")
    carried = "carried over from the project's .env.example"
    for row in (
        f"# APP_NAME | knob | str | no | - | {carried}\n#APP_NAME=\n",
        f"# SOURCE_CKAN_ENABLED | knob | str | no | - | {carried}\n#SOURCE_CKAN_ENABLED=\n",
        (
            f"# ADMIN_API_KEY | secret | str | no | - | op:// pointer; {carried}\n"
            "#ADMIN_API_KEY=op://<vault>/<item>/<field>\n"
        ),
        "# API_PORT | knob | str | no | - | named in docker-compose.yml\n#API_PORT=\n",
        "# POSTGRES_PASSWORD | secret | str | no | - | op:// pointer; named in docker-compose.yml",
        "# SMOKE_PORT | knob | str | no | - | named in Makefile\n",
        "# MCP_PORT | knob | str | no | - | named in Makefile\n",
    ):
        assert row in text, row
    for gone in ("NOT_A_KNOB", "COMMENTED", "COMPOSE |", "# ESCAPED"):
        assert gone not in text, gone
    # the code's own row wins over the old file's line: one row, from the scan
    assert text.count("# TIPCALC_DEFAULT_PERCENT |") == 1
    assert "Orca" not in text  # a value in the old file may be a real secret: never carried
    assert render(repo).stdout.strip().endswith("render: 0 changes")


KEYED_SETTINGS = (
    "from pydantic_settings import BaseSettings\n\n\n"
    "class Settings(BaseSettings):\n    api_key: str | None = None\n"
)


def test_a_secret_bearing_start_runs_without_a_dot_env(tmp_path: Path) -> None:
    """orca: `op run --env-file .env` exits 1 on a missing .env, so `start -- --help` failed on
    every fresh checkout. op run wraps start only when .env exists."""
    repo = tipcalc_like(tmp_path / "tipcalc", {"src/tipcalc/settings.py": KEYED_SETTINGS})
    assert render(repo, values=VALUES).returncode == 0
    contract = (repo / ".env.example").read_text(encoding="utf-8")
    assert "# API_KEY | secret | str | no | - | op:// pointer" in contract
    run_line = tomllib.loads((repo / "mise.toml").read_text(encoding="utf-8"))["tasks"]["start"]
    fake = tmp_path / "fakebin"
    for name in ("uv", "op"):
        write(fake, {name: f'#!/bin/sh\necho "{name} $*"\n'})
        (fake / name).chmod(0o755)
    env = clean_env(PATH=f"{fake}:/usr/bin:/bin")

    def start(*args: str) -> str:  # as mise runs it: sh -c "<run> <args, quoted>"
        line = f"{run_line['run']} {shlex.join(args)}"
        done = subprocess.run(
            ["sh", "-c", line], cwd=repo, env=env, capture_output=True, text=True, check=False
        )
        assert done.returncode == 0, done.stderr
        return done.stdout.strip()

    assert start("--help") == "uv run --locked tipcalc --help"
    write(repo, {".env": "API_KEY=op://vault/item/field\n"})
    assert start("--help", "a b") == "op run --env-file .env -- uv run --locked tipcalc --help a b"
    # an OP_RUN value an earlier render saved in [values] renders the guarded form
    again = render(repo, values={"OP_RUN": "op run --env-file .env -- "})
    assert again.returncode == 0, again.stdout + again.stderr
    assert tomllib.loads((repo / "mise.toml").read_text(encoding="utf-8"))["tasks"]["start"] == (
        run_line
    )


def test_a_renamed_repo_s_old_checkout_shares_the_origin(tmp_path: Path) -> None:
    """geo-context: its origin GeoContext.git redirects to orca, and it shares orca's root
    commit. The URL strings differ, so P0 missed it. Same owner and root commit count; a fork
    under another owner does not."""
    work = tmp_path / "work"
    orca = make_repo(work / "orca", {**PY, "app.py": "x = 1\n"})
    git(orca, "remote", "add", "origin", "https://github.com/someone/orca.git")
    old = work / "geo-context"
    git(tmp_path, "clone", "-q", str(orca), str(old))
    git(old, "remote", "set-url", "origin", "git@github.com:someone/GeoContext.git")
    fork = work / "forks" / "orca-fork"
    git(tmp_path, "clone", "-q", str(orca), str(fork))
    git(fork, "remote", "set-url", "origin", "https://github.com/other/orca.git")
    stranger = make_repo(work / "tool", {"t.py": "t = 1\n"})
    git(stranger, "remote", "add", "origin", "https://github.com/someone/tool.git")
    args = ("--offline", "--vault", str(tmp_path / "v"), "--search-root", str(work))

    result = init("preflight", str(orca), *args)
    assert result.returncode == 0, result.stdout  # origin's name is orca's: a note, no stop
    assert (
        f"another local repo also uses this origin: {old} (origin "
        "git@github.com:someone/GeoContext.git, same owner and root commit "
    ) in result.stdout
    assert "orca-fork" not in result.stdout and str(stranger) not in result.stdout
    result = init("preflight", str(old), *args)
    assert result.returncode == 1, result.stdout
    assert f"another local repo uses the same origin: {orca}" in result.stdout
    assert "2. Stop (Recommended: its origin belongs to" not in result.stdout  # no name matches
    assert "origin's name, geocontext, matches no single checkout" in result.stdout


def test_rotate_is_said_only_for_secret_findings(tmp_path: Path) -> None:
    """orca: all 134 history findings were personal paths, yet render said to rotate the
    secrets among them. A path is no secret: render says what the findings are."""
    mod = load_init()
    paths = [f"{'a' * 40}:docs/x.md:personal-home-path:3", f"{'b' * 40}:AGENTS.md:personal-path:1"]
    note = mod.leaks_note(paths)
    assert "(personal-home-path 1, personal-path 1)" in note
    assert "not secrets: nothing to rotate" in note and "rotate the secrets" not in note
    assert b"a vault or home path, not a secret" in mod.gitleaksignore_text(paths)
    both = [*paths, f"{'c' * 40}:a:b.env:generic-api-key:2"]
    note = mod.leaks_note(both)
    assert "rotate the secrets among them (punch list: the generic-api-key findings)" in note
    assert "the other 2 are vault paths and home folders, not secrets" in note
    assert b"Rotate the secrets among them" in mod.gitleaksignore_text(both)

    repo = tmp_path / "repo"
    write(repo, {".gitleaksignore": mod.gitleaksignore_text(paths).decode()})
    assert not [i for i in mod.publish_punch_list(repo, {}, False) if "rotate" in i]
    write(repo, {".gitleaksignore": mod.gitleaksignore_text(both).decode()})
    rotate = [i for i in mod.publish_punch_list(repo, {}, False) if "rotate" in i]
    assert rotate == [
        (
            "rotate the secrets .gitleaksignore fingerprints (generic-api-key 1; rule and file, "
            "never values)"
        )
    ]

    need(gitleaks_cmd(), "gitleaks is not runnable here")
    repo = tipcalc_like(tmp_path / "tipcalc", {"docs/notes.md": "see /home/someone/notes\n"})
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "(personal-home-path 1)" in result.stdout
    assert "they are home folders in committed files, not secrets: nothing to rotate" in (
        result.stdout
    )


def test_ruff_format_leaves_markdown_alone_and_the_baseline_only_shrinks(tmp_path: Path) -> None:
    """helios: `ruff format` rewrote the Python fences of 13 Markdown files. The rendered
    config leaves *.md out of the formatter; the lint baseline block stays where doctor reads
    it (the rows under its mark, up to the next table) and a second render keeps it."""
    ruff = need(real_ruff(tmp_path), "no ruff binary in uv's cache")
    repo = tipcalc_like(
        tmp_path / "tipcalc",
        {
            "docs/guide.md": "# Guide\n\n```python\nx=1\n```\n",
            "src/tipcalc/legacy.py": "import subprocess\n\n\ndef run(cmd):\n    "
            "return subprocess.call(cmd, shell=True)\n",
        },
    )
    (repo / ".venv" / "bin").mkdir(parents=True)
    (repo / ".venv" / "bin" / "ruff").symlink_to(ruff)
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    assert tomllib.loads(text)["tool"]["ruff"]["format"]["exclude"] == ["*.md"]

    def ruff_run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [ruff, *args, "--no-cache", "."],
            cwd=repo,
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )

    checked = ruff_run("format", "--check")
    assert "docs/guide.md" not in checked.stdout + checked.stderr
    assert ruff_run("check").returncode == 0  # the baseline absorbs the adoption-time debt
    spec = importlib.util.spec_from_file_location(
        "project_py_script", SKILL / "templates" / "scripts" / "project.py"
    )
    assert spec is not None and spec.loader is not None
    project = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = project
    spec.loader.exec_module(project)
    rows = project.baseline_rows(text)
    assert rows is not None and {"ANN001", "ANN201", "S602"} <= rows["src/tipcalc/legacy.py"]
    assert render(repo).returncode == 0
    assert project.baseline_rows((repo / "pyproject.toml").read_text(encoding="utf-8")) == rows
    # a root file's row, `./setup.py` now and `setup.py` from an older render: one file to N3
    block = '# project-init baseline: shrink only\n"{}" = ["ANN201"]\n'
    assert project.baseline_rows(block.format("./setup.py")) == {"setup.py": {"ANN201"}}
    assert project.baseline_rows(block.format("setup.py")) == {"setup.py": {"ANN201"}}


KNOWLEDGE = {
    "last_updated": "2026-04-20",
    "decisions": [
        {"date": "2026-04-04", "decision": "pgvector replaces ChromaDB", "rationale": "one box"},
        {"decided": "2026-04-05", "what": "Keep six routers"},
    ],
    "patterns": ["RAG service exposes one interface", "Notes live in [[helios-notes]]"],
    "gotchas": ["Logs land in /home/someone/work/helios/logs", "See ~/helm/05-projects/x"],
    "open_threads": ["Superset embedding"],
    "dependencies": {"added": {"pgvector": "2026-04-04"}, "removed": ["chromadb"]},
    "recent_files": ["backend/main.py"],
    "tags_index": ["rag"],
}
V1_SETTINGS = {
    "hooks": {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": "python3 .claude/hooks/project-session-recall.py",
                    },
                    {"type": "command", "command": "echo hi"},
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {"type": "command", "command": "python3 .claude/hooks/project-session-save.py"}
                ]
            }
        ],
    }
}
V1_GITIGNORE = """.venv/

# Project Memory (personal, not shared)
project_memory/pending/
project_memory/sessions/
project_memory/chromadb/
project_memory/summaries/

# Keep the structure and accumulated knowledge
!project_memory/accumulated_knowledge.json

# Offline bundle
bundle/
"""


def test_migrate_v1_applies_the_p4_moves(tmp_path: Path) -> None:
    """helios's v1 moves were agent-only: git rm of accumulated_knowledge.json and the two
    project-session hooks, the legacy .gitignore block, and the legacy knowledge report. They
    now run through init.py migrate-v1, like migrate-v2: a prompt, then --apply on the branch,
    after migrate-transcripts moved the stores."""
    repo = make_repo(
        tmp_path / "helios",
        {
            **PY,
            "app.py": "x = 1\n",
            ".gitignore": V1_GITIGNORE,
            "project_memory/accumulated_knowledge.json": json.dumps(KNOWLEDGE, indent=1),
            ".claude/hooks/project-session-recall.py": "print('recall')\n",
            ".claude/hooks/project-session-save.py": "print('save')\n",
            ".claude/settings.json": json.dumps(V1_SETTINGS, indent=2),
        },
    )
    committed = git(repo, "log", "-1", "--format=%cs").strip()
    write(repo, {"project_memory/sessions/raw.json": "{}\n"})  # gitignored, as in helios
    prompt = init("migrate-v1", str(repo))
    assert prompt.returncode == 0, prompt.stderr
    for line in (
        "migrate ..... v1 JSON memory -> v3, 5 items:",
        "project_memory/sessions                    migrate-transcripts: quarantine, redact",
        "project_memory/accumulated_knowledge.json  rendered once into specs/backlog/",
        ".claude/hooks/project-session-save.py      unregistered from the settings files",
        ".gitignore v1 block                        its lines removed, once the stores left",
        "1. Apply all (Recommended",
    ):
        assert line in prompt.stdout, line
    before = tree_hash(repo)
    refused = init("migrate-v1", str(repo), "--apply")
    assert refused.returncode == 1 and "HEAD is main" in refused.stderr
    git(repo, "switch", "-q", "-c", "plan/project-init")
    refused = init("migrate-v1", str(repo), "--apply")
    assert refused.returncode == 1
    assert "project_memory/sessions still in the repo. Run init.py migrate-transcripts" in (
        refused.stderr
    )
    shutil.rmtree(repo / "project_memory" / "sessions")  # migrate-transcripts moved it
    assert tree_hash(repo) != before  # only that folder went: refusals change nothing

    done = init("migrate-v1", str(repo), "--apply")
    assert done.returncode == 0, done.stdout + done.stderr
    report = repo / "specs" / "backlog" / f"{time.strftime('%Y-%m-%d')}-legacy-knowledge.md"
    assert f"specs/backlog/{report.name}: 2 decisions, 2 patterns, 2 gotchas" in done.stdout
    assert f"snapshot {committed}, from its last commit" in done.stdout
    assert "sanitized .. " not in done.stdout and "3 vault or home paths" in done.stdout
    text = report.read_text(encoding="utf-8")
    assert f"> Snapshot {committed} of `project_memory/accumulated_knowledge.json`" in text
    for line in (
        "- [ ] 2026-04-04: pgvector replaces ChromaDB. Why: one box",
        "- [ ] 2026-04-05: Keep six routers",
        "- [ ] Notes live in helios-notes",
        "- [ ] Logs land in ~/work/helios/logs",
        "- [ ] See <vault path>",
        "- [ ] added: pgvector (2026-04-04)",
        "- [ ] removed: chromadb",
        "Left out: recent_files, tags_index (file lists and tags, not knowledge).",
    ):
        assert line in text, line
    assert "backend/main.py" not in text and "/home/" not in text and "[[" not in text
    staged = git(repo, "diff", "--cached", "--name-status").splitlines()
    assert sorted(staged) == [
        "D\t.claude/hooks/project-session-recall.py",
        "D\t.claude/hooks/project-session-save.py",
        "D\tproject_memory/accumulated_knowledge.json",
    ]
    settings = json.loads((repo / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert settings == {
        "hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": "echo hi"}]}]}
    }
    assert (repo / ".gitignore").read_text(encoding="utf-8") == (
        ".venv/\n\n# Offline bundle\nbundle/\n"
    )
    again = init("migrate-v1", str(repo), "--apply")
    assert again.returncode == 0 and "migrate-v1: nothing left to apply" in again.stdout
    assert init("migrate-v1", str(repo)).returncode == 1  # no v1 layout left to prompt for


STUB_MAIN = '''"""Main entry point."""

import sys


def main() -> int:
    """Print the commands."""
    print("svc - the platform")
    print("  uv run uvicorn svc.api:app --reload  - Start the REST API")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
SVC_COMPOSE = """services:
  api:
    command: ["uvicorn", "svc.api:app", "--host", "0.0.0.0"]
  seed:
    command: ["dbt", "seed"]
"""
SVC_MAKEFILE = """help:
\t@echo "make dev - start uvicorn"

dev:
\tuv run uvicorn svc.api:app --reload

up:
\tdocker compose up -d api
"""


def test_the_run_skill_names_the_real_service_when_start_is_a_stub(tmp_path: Path) -> None:
    """orca: `start` runs a 28-line stub that prints usage and exits, yet run-orca said
    `mise run start` starts it. The skill now says so and names the service commands the
    repo's compose file and Makefile hold (a compose one-shot job, an echo and a compose
    call are not servers)."""
    pyproject = TIPCALC_PYPROJECT.replace(
        "dependencies = []", 'dependencies = ["fastapi"]'
    ).replace('tipcalc = "tipcalc:main"', 'tipcalc = "tipcalc.main:main"')
    repo = tipcalc_like(
        tmp_path / "tipcalc",
        {
            "pyproject.toml": pyproject,
            "src/tipcalc/main.py": STUB_MAIN,
            "docker-compose.yml": SVC_COMPOSE,
            "Makefile": SVC_MAKEFILE,
        },
    )
    result = render(repo, values=VALUES)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "run-tipcalc: `mise run start` runs tipcalc, which only prints its usage" in (
        result.stdout
    )
    skill = (repo / ".claude/skills/run-tipcalc/SKILL.md").read_text(encoding="utf-8")
    assert (
        "`mise run start` runs `tipcalc`, which prints its usage and exits: it does not start "
        "the service."
    ) in skill
    assert "starts it, and arguments go after" not in skill
    assert (  # render writes the skill before P5: it says what P5 checks, not that it passed
        "project-init's selftest runs `mise run start -- --help` and fails unless it exits 0, "
        "which proves only that usage text."
    ) in skill
    assert "green" not in skill
    assert "- `uvicorn svc.api:app --host 0.0.0.0` (docker-compose.yml, service `api`)" in skill
    assert "- `uv run uvicorn svc.api:app --reload` (Makefile, target `dev`)" in skill
    for gone in ("dbt seed", "echo", "docker compose up"):
        assert gone not in skill, gone
    assert not PLACEHOLDER.search(skill)

    # a start that really runs the service keeps the plain text
    real = tipcalc_like(tmp_path / "real", {"pyproject.toml": pyproject.replace(".main", "")})
    assert render(real, values=VALUES).returncode == 0
    text = (real / ".claude/skills/run-tipcalc/SKILL.md").read_text(encoding="utf-8")
    assert "`mise run start` starts it, and arguments go after `--`." in text
    assert "service commands" not in text
