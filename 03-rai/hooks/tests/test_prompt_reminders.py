"""
test_prompt_reminders.py: the per-prompt reminders in response-format-reminder.py.

The [format] line always prints. The [workflows] line prints only in interactive work:
never in a headless `claude -p` run, never in a learning folder (the Socratic rule wins
there), never for a prompt under MIN_PROMPT characters.

Hermetic: the headless check is stubbed, and learning folders are built under tmp_path.

Run: uv run --with pytest pytest 03-rai/hooks/tests/test_prompt_reminders.py -q -p no:cacheprovider
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOKS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HOOKS))  # bind `lib` to THIS checkout

HOOK = HOOKS / "response-format-reminder.py"


def _load():
    spec = importlib.util.spec_from_file_location("prompt_reminders", HOOK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def rem():
    return _load()


@pytest.fixture
def interactive(monkeypatch):
    import lib.headless

    monkeypatch.setattr(lib.headless, "invoked_from_headless", lambda: False)


@pytest.mark.parametrize("rel", [
    "helm/06-learning",
    "helm/06-learning/python-programming",
    "helm/07-reading/some-book",
    "playground/scratch",
    "projects/taskflow-lab",
    "projects/taskflow-lab/src/taskflow",
])
def test_learning_folders_are_detected(rem, tmp_path, rel):
    (tmp_path / rel).mkdir(parents=True)
    assert rem.in_learning_folder(str(tmp_path / rel), home=tmp_path)


@pytest.mark.parametrize("rel", [
    "helm",
    "helm/11-workflows",
    "projects",
    "projects/orca",
    "projects/labour-costs",  # "-lab" must be a suffix of the repo name, not a prefix
    "work/helios",
])
def test_other_folders_are_not_learning(rem, tmp_path, rel):
    (tmp_path / rel).mkdir(parents=True)
    assert not rem.in_learning_folder(str(tmp_path / rel), home=tmp_path)


def test_empty_cwd_is_not_learning(rem):
    assert not rem.in_learning_folder("")


def test_workflow_line_in_interactive_work(rem, interactive, tmp_path):
    payload = {"prompt": "the news digest is empty today", "cwd": str(tmp_path)}
    assert rem.workflow_line_wanted(payload)


def test_no_workflow_line_for_short_prompts(rem, interactive, tmp_path):
    for prompt in ["yes", "1 2", "  go   ", ""]:
        assert not rem.workflow_line_wanted({"prompt": prompt, "cwd": str(tmp_path)})


def test_no_workflow_line_without_a_prompt(rem, interactive, tmp_path):
    assert not rem.workflow_line_wanted({"cwd": str(tmp_path)})
    assert not rem.workflow_line_wanted({"prompt": 42, "cwd": str(tmp_path)})


def test_no_workflow_line_in_headless_runs(rem, monkeypatch, tmp_path):
    import lib.headless

    monkeypatch.setattr(lib.headless, "invoked_from_headless", lambda: True)
    assert not rem.workflow_line_wanted({"prompt": "review my PR before I merge", "cwd": str(tmp_path)})


def test_no_workflow_line_in_a_learning_folder(rem, interactive, monkeypatch, tmp_path):
    lab = tmp_path / "projects" / "taskflow-lab"
    lab.mkdir(parents=True)
    monkeypatch.setattr(rem, "HOME", tmp_path)
    real = rem.in_learning_folder
    monkeypatch.setattr(rem, "in_learning_folder", lambda cwd: real(cwd, home=tmp_path))
    assert not rem.workflow_line_wanted({"prompt": "check my task 5 solution", "cwd": str(lab)})


def test_bad_payloads_read_as_empty(rem):
    assert rem.read_payload("") == {}
    assert rem.read_payload("not json") == {}
    assert rem.read_payload("[1, 2]") == {}
    assert rem.read_payload('{"prompt": "x"}') == {"prompt": "x"}


def test_workflow_line_names_the_folder_and_asks_to_name_it(rem):
    assert "~/helm/11-workflows/" in rem.WORKFLOW_LINE
    assert "name it" in rem.WORKFLOW_LINE
    assert "—" not in rem.WORKFLOW_LINE and "–" not in rem.WORKFLOW_LINE


def _run(payload: dict, env: dict) -> list[str]:
    out = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload), capture_output=True, text=True, timeout=10, env=env,
    )
    assert out.returncode == 0
    return out.stdout.strip().splitlines()


def test_end_to_end_headless_prints_only_the_format_line(tmp_path):
    env = dict(os.environ, RAI_HEADLESS="1", HOME=str(tmp_path))
    lines = _run({"prompt": "the news digest is empty today", "cwd": str(tmp_path)}, env)
    assert len(lines) == 1 and lines[0].startswith("[format]")


def test_end_to_end_bad_stdin_still_prints_the_format_line(tmp_path):
    env = dict(os.environ, RAI_HEADLESS="1", HOME=str(tmp_path))
    out = subprocess.run(
        [sys.executable, str(HOOK)], input="{broken", capture_output=True, text=True,
        timeout=10, env=env,
    )
    assert out.returncode == 0
    assert out.stdout.startswith("[format]")


def test_format_line_leads_with_the_length_rule(tmp_path):
    env = dict(os.environ, RAI_HEADLESS="1", HOME=str(tmp_path))
    line = _run({"prompt": "the news digest is empty today", "cwd": str(tmp_path)}, env)[0]
    assert line.startswith("[format] HARD RULE, deal breaker: SHORT.")
    assert "Length follows the need" in line
