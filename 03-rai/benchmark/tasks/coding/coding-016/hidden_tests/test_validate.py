import json
import subprocess
import sys
from pathlib import Path

import pytest
import validate as v

ROOT = Path(__file__).resolve().parent.parent


def schema(fields, allow_extra=False):
    return v.check_schema({"fields": fields, "allow_extra": allow_extra})


def write_json(tmp_path, data, name="schema.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data) if not isinstance(data, str) else data)
    return path


def test_load_sample_schema():
    loaded = v.load_schema(ROOT / "schema.json")
    assert list(loaded["fields"]) == [
        "id",
        "email",
        "name",
        "age",
        "plan",
        "score",
        "active",
        "signup",
    ]
    assert v.load_schema(str(ROOT / "schema.json")) == loaded


@pytest.mark.parametrize(
    "data",
    [
        "{not json",
        [],
        {"fields": {}},
        {"fields": {"a": {"type": "str"}}, "strict": True},
        {"fields": {"a": {"type": "decimal"}}},
        {"fields": {"a": {}}},
        {"fields": {"a": {"type": "str", "min": 1}}},
        {"fields": {"a": {"type": "int", "pattern": "x"}}},
        {"fields": {"a": {"type": "int", "colour": "red"}}},
        {"fields": {"a": {"type": "str", "pattern": "(unclosed"}}},
        {"fields": {"a": {"type": "str", "enum": "free"}}},
        {"fields": {"a": {"type": "int", "required": "yes"}}},
        {"fields": {"a": {"type": "date", "min": "2026-02-30"}}},
        {"fields": {"a": {"type": "int", "max": "10"}}},
        {"fields": {"a": {"type": "str", "max_length": -1}}},
        {"fields": {"a": {"type": "bool", "min": 0}}},
        {"fields": {"a": {"type": "str"}}, "allow_extra": "no"},
    ],
)
def test_bad_schemas(tmp_path, data):
    with pytest.raises(v.SchemaError):
        v.load_schema(write_json(tmp_path, data))
    assert issubclass(v.SchemaError, ValueError)


def test_check_header():
    s = schema({"id": {"type": "int", "required": True}, "note": {"type": "str"}})
    v.check_header(["id", "note"], s)
    v.check_header(["note", "id"], s)
    v.check_header(["id"], s)
    with pytest.raises(v.HeaderError, match="missing required column: id"):
        v.check_header(["note"], s)
    with pytest.raises(v.HeaderError, match="unexpected column: extra"):
        v.check_header(["id", "extra"], s)
    with pytest.raises(v.HeaderError, match="duplicate column: id"):
        v.check_header(["id", "id"], s)
    v.check_header(
        ["id", "extra"],
        schema({"id": {"type": "int", "required": True}}, allow_extra=True),
    )
    assert issubclass(v.HeaderError, ValueError)


@pytest.mark.parametrize(
    "spec,cell,message",
    [
        ({"type": "int", "required": True}, "", "required"),
        ({"type": "int", "required": True}, "   ", "required"),
        ({"type": "int"}, "", None),
        ({"type": "int"}, " 42 ", None),
        ({"type": "int"}, "+7", None),
        ({"type": "int"}, "4.0", "not an int"),
        ({"type": "int"}, "1e3", "not an int"),
        ({"type": "int", "min": 1}, "0", "below min"),
        ({"type": "int", "max": 10}, "11", "above max"),
        ({"type": "int", "min": 1, "max": 10}, "10", None),
        ({"type": "float"}, "1e-3", None),
        ({"type": "float"}, "nan", "not a float"),
        ({"type": "float"}, "inf", "not a float"),
        ({"type": "float"}, "1,5", "not a float"),
        ({"type": "float", "min": 0, "max": 1}, "1.0000001", "above max"),
        ({"type": "float", "min": 0.5}, "0.25", "below min"),
        ({"type": "bool"}, "YES", None),
        ({"type": "bool"}, "0", None),
        ({"type": "bool"}, "False", None),
        ({"type": "bool"}, "y", "not a bool"),
        ({"type": "date"}, "2024-02-29", None),
        ({"type": "date"}, "2025-02-29", "not a date"),
        ({"type": "date"}, "2024-2-9", "not a date"),
        ({"type": "date"}, "20240229", "not a date"),
        ({"type": "date", "min": "2020-01-01"}, "2019-12-31", "below min"),
        ({"type": "date", "max": "2020-01-01"}, "2020-01-02", "above max"),
        ({"type": "str", "min_length": 3}, "ab", "too short"),
        ({"type": "str", "max_length": 3}, "abcd", "too long"),
        ({"type": "str", "max_length": 3}, "  abc  ", None),
        ({"type": "str", "pattern": "[A-Z]{3}"}, "ABCD", "pattern mismatch"),
        ({"type": "str", "pattern": "[A-Z]{3}"}, "ABC", None),
        ({"type": "str", "enum": ["a", "b"]}, "A", "not in enum"),
        ({"type": "int", "enum": [1, 2]}, "02", None),
        ({"type": "int", "enum": [1, 2]}, "3", "not in enum"),
        ({"type": "date", "enum": ["2026-01-01"]}, "2026-01-01", None),
        ({"type": "date", "enum": ["2026-01-01"]}, "2026-01-02", "not in enum"),
        ({"type": "int", "min": 5, "enum": [1, 2]}, "1", "below min"),
        ({"type": "str", "min_length": 5, "pattern": "[0-9]+"}, "abc", "too short"),
        ({"type": "str", "pattern": "[a-z]+", "enum": ["xyz"]}, "abc", "not in enum"),
    ],
)
def test_single_cell_rules(spec, cell, message):
    errors = v.validate_rows([{"f": cell}], schema({"f": spec}))
    assert errors == ([] if message is None else [(1, "f", message)])


def test_missing_optional_column_counts_as_empty():
    s = schema({"a": {"type": "int"}, "b": {"type": "int", "required": True}})
    assert v.validate_rows([{"a": "1"}], s) == [(1, "b", "required")]


def test_unique_uses_converted_values_and_skips_bad_cells():
    s = schema({"id": {"type": "int", "unique": True, "min": 1}})
    rows = [{"id": v_} for v_ in ["1", "01", "", "", "0", "0", "x", "2", "+2"]]
    assert v.validate_rows(rows, s) == [
        (2, "id", "duplicate"),
        (5, "id", "below min"),
        (6, "id", "below min"),
        (7, "id", "not an int"),
        (9, "id", "duplicate"),
    ]


def test_errors_ordered_by_row_then_schema_field_order():
    s = schema({"b": {"type": "int"}, "a": {"type": "int"}, "c": {"type": "bool"}})
    rows = [
        {"a": "x", "b": "y", "c": "1"},
        {"a": "1", "b": "2", "c": "maybe"},
        {"c": "no", "b": "z"},
    ]
    assert v.validate_rows(rows, s) == [
        (1, "b", "not an int"),
        (1, "a", "not an int"),
        (2, "c", "not a bool"),
        (3, "b", "not an int"),
    ]


def cli(*args):
    return subprocess.run(
        [sys.executable, "validate.py", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


SAMPLE_ERRORS = [
    (2, "email", "pattern mismatch"),
    (2, "name", "too short"),
    (2, "age", "above max"),
    (2, "plan", "not in enum"),
    (2, "score", "above max"),
    (2, "active", "not a bool"),
    (2, "signup", "below min"),
    (3, "email", "duplicate"),
    (3, "signup", "not a date"),
    (4, "id", "not an int"),
]


def test_cli_text_report_on_sample():
    proc = cli("schema.json", "data/users.csv")
    assert proc.returncode == 1
    assert proc.stdout.splitlines() == [
        f"row {r}: {f}: {m}" for r, f, m in SAMPLE_ERRORS
    ]


def test_cli_json_and_max_errors():
    proc = cli("schema.json", "data/users.csv", "--format", "json", "--max-errors", "3")
    assert proc.returncode == 1
    assert json.loads(proc.stdout) == [
        {"row": r, "field": f, "message": m} for r, f, m in SAMPLE_ERRORS[:3]
    ]
    proc = cli("schema.json", "data/users.csv", "--max-errors", "1")
    assert proc.stdout.splitlines() == ["row 2: email: pattern mismatch"]


def test_cli_valid_file(tmp_path):
    data = tmp_path / "ok.csv"
    data.write_text("id,email,plan\n1,a@b.io,pro\n2,c@d.io,free\n")
    proc = cli(ROOT / "schema.json", data)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    proc = cli(ROOT / "schema.json", data, "--format", "json")
    assert proc.returncode == 0
    assert json.loads(proc.stdout) == []


def test_cli_header_and_schema_errors(tmp_path):
    data = tmp_path / "bad.csv"
    data.write_text("id,email,plan,colour\n1,a@b.io,pro,red\n")
    proc = cli(ROOT / "schema.json", data)
    assert proc.returncode == 2
    assert "header error: unexpected column: colour" in proc.stderr
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    assert cli(ROOT / "schema.json", empty).returncode == 2
    bad_schema = write_json(tmp_path, {"fields": {"a": {"type": "money"}}})
    proc = cli(bad_schema, data)
    assert proc.returncode == 2
    assert proc.stderr.startswith("schema error:")
