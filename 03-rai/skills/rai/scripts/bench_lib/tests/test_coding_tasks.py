"""
Proof for the coding suite of `/rai benchmark` (03-rai/benchmark/tasks/coding/).

For every task folder: task.json follows the schema in 03-rai/benchmark/AGENTS.md, the starter
alone FAILS the hidden tests, and starter + solution PASSES them, with the engine's own pytest
arguments (runner.PYTEST_ARGS, work folder as cwd); the engine adds only the sandbox around them.
Suite-wide: exactly 5 quick tasks, stdlib + pytest imports only, Latin script only.

Run: uv run --offline --python 3.12 --with pytest \
       python3 -m pytest 03-rai/skills/rai/scripts/bench_lib/tests/test_coding_tasks.py -q -p no:cacheprovider
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bench_lib.runner import PYTEST_ARGS  # noqa: E402

# tests -> bench_lib -> scripts -> rai -> skills -> 03-rai
RAI_ROOT = Path(__file__).resolve().parents[5]
SUITE = RAI_ROOT / "benchmark" / "tasks" / "coding"
TASK_DIRS = sorted(p for p in SUITE.iterdir() if p.is_dir()) if SUITE.is_dir() else []

REQUIRED_FIELDS = {
    "id",
    "area",
    "prompt",
    "cwd",
    "setup",
    "checks",
    "quick",
    "status",
    "source",
    "added",
}
COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache")
ARABIC = re.compile(
    "[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff\ufb50-\ufdff\ufe70-\ufeff]"
)
MAX_SECONDS = 10.0


def _load(task_dir: Path) -> dict:
    return json.loads((task_dir / "task.json").read_text(encoding="utf-8"))


def _run_hidden(
    task_dir: Path, work: Path, *, with_solution: bool
) -> tuple[subprocess.CompletedProcess, float]:
    """Build the work folder the way the engine does, then run the hidden tests in it."""
    shutil.copytree(task_dir / "starter", work, ignore=COPY_IGNORE)
    if with_solution:
        shutil.copytree(
            task_dir / "solution", work, dirs_exist_ok=True, ignore=COPY_IGNORE
        )
    shutil.copytree(
        task_dir / "hidden_tests", work / "hidden_tests", ignore=COPY_IGNORE
    )
    (work / "hidden_tests" / ".bench-pytest.ini").write_text("[pytest]\n")
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    started = time.monotonic()
    proc = subprocess.run(
        [sys.executable, *PYTEST_ARGS],
        cwd=work,
        capture_output=True,
        check=False,
        text=True,
        timeout=120,
        env=env,
    )
    return proc, time.monotonic() - started


def _tail(proc: subprocess.CompletedProcess) -> str:
    return "\n".join((proc.stdout + proc.stderr).splitlines()[-40:])


def test_suite_has_twenty_numbered_tasks() -> None:
    assert [p.name for p in TASK_DIRS] == [f"coding-{i:03d}" for i in range(1, 21)]


def test_exactly_five_quick_tasks() -> None:
    quick = [p.name for p in TASK_DIRS if _load(p)["quick"] is True]
    assert len(quick) == 5, quick


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_task_json_schema(task_dir: Path) -> None:
    task = _load(task_dir)
    assert REQUIRED_FIELDS <= task.keys(), REQUIRED_FIELDS - task.keys()
    assert task["id"] == task_dir.name
    assert re.fullmatch(r"coding-\d{3}", task["id"])
    assert task["area"] == "coding"
    assert task["cwd"] == "work"
    assert task["checks"] == [{"type": "pytest"}]
    assert isinstance(task["quick"], bool)
    assert task["status"] == "active"
    assert task["source"] == "written"
    assert task["added"] == "2026-10-01"
    assert isinstance(task["setup"], dict) and isinstance(
        task["setup"].get("files", {}), dict
    )
    assert isinstance(task["prompt"], str) and len(task["prompt"]) > 200
    assert not re.search(r"hidden[ _-]?tests?", task["prompt"], re.IGNORECASE)


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_task_folder_layout(task_dir: Path) -> None:
    for sub in ("starter", "hidden_tests", "solution"):
        files = [
            p
            for p in (task_dir / sub).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        ]
        assert files, f"{sub}/ is empty (git would drop it)"
    assert list((task_dir / "hidden_tests").glob("test_*.py"))


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_latin_script_only(task_dir: Path) -> None:
    for path in task_dir.rglob("*"):
        if path.is_file() and "__pycache__" not in path.parts:
            text = path.read_bytes().decode("utf-8", errors="ignore")
            assert not ARABIC.search(text), path


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_imports_are_stdlib_or_pytest(task_dir: Path) -> None:
    local = {
        p.stem if p.is_file() else p.name
        for p in task_dir.rglob("*")
        if "__pycache__" not in p.parts and (p.is_dir() or p.suffix == ".py")
    }
    allowed = set(sys.stdlib_module_names) | {"pytest", "_pytest", "__future__"} | local
    for path in task_dir.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names = [node.module]
            else:
                continue
            for name in names:
                assert name.split(".")[0] in allowed, f"{path}: import {name}"


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_starter_alone_fails_hidden_tests(task_dir: Path, tmp_path: Path) -> None:
    proc, _ = _run_hidden(task_dir, tmp_path / "work", with_solution=False)
    # 0 = passed, 4 = usage error, 5 = nothing collected: none of these is a real failure.
    assert proc.returncode not in (0, 4, 5), _tail(proc)


@pytest.mark.parametrize("task_dir", TASK_DIRS, ids=lambda p: p.name)
def test_starter_plus_solution_passes_hidden_tests(
    task_dir: Path, tmp_path: Path
) -> None:
    proc, seconds = _run_hidden(task_dir, tmp_path / "work", with_solution=True)
    assert proc.returncode == 0, _tail(proc)
    assert seconds < MAX_SECONDS, f"hidden tests took {seconds:.1f}s"
