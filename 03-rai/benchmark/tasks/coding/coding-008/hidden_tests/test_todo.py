import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


class Todo:
    def __init__(self, db):
        self.db = db

    def __call__(self, *args):
        return subprocess.run(
            [sys.executable, "todo.py", "--db", str(self.db), *map(str, args)],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )

    def ok(self, *args):
        proc = self(*args)
        assert proc.returncode == 0, proc.stderr
        return proc.stdout

    def rows(self, *args):
        return [line.split("\t") for line in self.ok("list", *args).splitlines()]

    def data(self):
        return json.loads(self.db.read_text())


@pytest.fixture
def todo(tmp_path):
    return Todo(tmp_path / "todo.json")


def test_add_assigns_ids_and_writes_file(todo):
    assert todo.ok("add", "Buy milk") == "added 1\n"
    assert (
        todo.ok(
            "add",
            "  Plan sprint  ",
            "--tag",
            "Work",
            "--tag",
            " PLANNING",
            "--tag",
            "work",
            "--due",
            "2026-10-03",
        )
        == "added 2\n"
    )
    assert todo.data() == {
        "next_id": 3,
        "tasks": [
            {"id": 1, "text": "Buy milk", "tags": [], "due": None, "done": False},
            {
                "id": 2,
                "text": "Plan sprint",
                "tags": ["work", "planning"],
                "due": "2026-10-03",
                "done": False,
            },
        ],
    }


def test_ids_are_never_reused(todo):
    todo.ok("add", "a")
    todo.ok("add", "b")
    assert todo.ok("remove", "2") == "removed 2\n"
    assert todo.ok("add", "c") == "added 3\n"
    assert [t["id"] for t in todo.data()["tasks"]] == [1, 3]


def test_list_format_and_order(todo):
    todo.ok("add", "no due")
    todo.ok("add", "late", "--due", "2026-11-20", "--tag", "b")
    todo.ok("add", "soon", "--due", "2026-10-02", "--tag", "a", "--tag", "b")
    todo.ok("add", "also late", "--due", "2026-11-20")
    todo.ok("add", "another no due")
    assert todo.rows() == [
        ["3", "-", "soon", "a,b", "2026-10-02"],
        ["2", "-", "late", "b", "2026-11-20"],
        ["4", "-", "also late", "", "2026-11-20"],
        ["1", "-", "no due", "", "-"],
        ["5", "-", "another no due", "", "-"],
    ]


def test_status_and_tag_filters(todo):
    todo.ok("add", "one", "--tag", "Home")
    todo.ok("add", "two", "--tag", "work")
    todo.ok("add", "three", "--tag", "home", "--tag", "urgent")
    assert todo.ok("done", "1") == "done 1\n"
    assert todo.ok("done", "1") == "done 1\n"
    assert [r[0] for r in todo.rows()] == ["2", "3"]
    assert [r[0] for r in todo.rows("--status", "done")] == ["1"]
    assert [r[:2] for r in todo.rows("--status", "all")] == [
        ["1", "x"],
        ["2", "-"],
        ["3", "-"],
    ]
    assert [r[0] for r in todo.rows("--status", "all", "--tag", "HOME")] == ["1", "3"]
    assert [r[0] for r in todo.rows("--tag", "home")] == ["3"]
    assert todo.ok("list", "--tag", "none") == ""


def test_overdue_needs_today_and_filters(todo):
    todo.ok("add", "past", "--due", "2026-09-30")
    todo.ok("add", "today", "--due", "2026-10-01")
    todo.ok("add", "future", "--due", "2026-10-02")
    todo.ok("add", "undated")
    todo.ok("add", "done past", "--due", "2026-09-01")
    todo.ok("done", "5")
    assert [r[2] for r in todo.rows("--overdue", "--today", "2026-10-01")] == ["past"]
    assert [
        r[2] for r in todo.rows("--overdue", "--today", "2026-10-01", "--status", "all")
    ] == ["done past", "past"]
    assert [r[2] for r in todo.rows("--overdue", "--today", "2027-01-01")] == [
        "past",
        "today",
        "future",
    ]
    assert todo("list", "--overdue").returncode == 2


def test_edit(todo):
    todo.ok("add", "draft", "--tag", "a", "--tag", "b", "--due", "2026-10-10")
    assert (
        todo.ok(
            "edit",
            "1",
            "--text",
            "final",
            "--add-tag",
            "C",
            "--add-tag",
            "a",
            "--remove-tag",
            "B",
        )
        == "edited 1\n"
    )
    assert todo.data()["tasks"][0] == {
        "id": 1,
        "text": "final",
        "tags": ["a", "c"],
        "due": "2026-10-10",
        "done": False,
    }
    todo.ok("edit", "1", "--no-due")
    assert todo.data()["tasks"][0]["due"] is None
    todo.ok("edit", "1", "--due", "2026-12-24")
    assert todo.data()["tasks"][0]["due"] == "2026-12-24"
    assert todo("edit", "1", "--due", "2026-12-24", "--no-due").returncode == 2
    assert todo("edit", "1").returncode == 2


@pytest.mark.parametrize("command", ["done", "remove", "edit"])
def test_unknown_id(todo, command):
    todo.ok("add", "only")
    before = todo.db.read_bytes()
    extra = ["--text", "x"] if command == "edit" else []
    proc = todo(command, "42", *extra)
    assert proc.returncode == 1
    assert "no such task: 42" in proc.stderr
    assert todo.db.read_bytes() == before


@pytest.mark.parametrize(
    "args",
    [
        ["add", "x", "--due", "2026-02-30"],
        ["add", "x", "--due", "tomorrow"],
        ["add", "x", "--due", "2026-1-5"],
        ["add", "   "],
        ["add"],
        ["done", "abc"],
        ["list", "--status", "maybe"],
        ["frobnicate"],
        [],
    ],
)
def test_usage_errors_exit_2_and_write_nothing(todo, args):
    proc = todo(*args)
    assert proc.returncode == 2
    assert not todo.db.exists()


def test_list_on_missing_db_creates_nothing(todo):
    assert todo.ok("list") == ""
    assert not todo.db.exists()


@pytest.mark.parametrize(
    "content", ["not json", "[]", '{"tasks": "nope", "next_id": 1}', '{"tasks": []}']
)
def test_corrupt_database(todo, content):
    todo.db.write_text(content)
    for args in (["list"], ["add", "x"]):
        proc = todo(*args)
        assert proc.returncode == 1
        assert f"corrupt database: {todo.db}" in proc.stderr
        assert todo.db.read_text() == content


def test_reads_existing_file_and_leaves_no_temp_files(todo):
    todo.db.write_text((ROOT / "example-todo.json").read_text())
    assert todo.ok("add", "new one") == "added 4\n"
    assert [r[0] for r in todo.rows("--status", "all")] == ["1", "3", "4"]
    assert sorted(p.name for p in todo.db.parent.iterdir()) == ["todo.json"]
