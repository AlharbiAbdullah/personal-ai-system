"""Validate a CSV file against a small JSON schema."""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path
from typing import Any

INT_RE = re.compile(r"[+-]?[0-9]+")
DATE_RE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
BOOLS = {"true": True, "yes": True, "1": True, "false": False, "no": False, "0": False}
COMMON_RULES = {"type", "required", "enum", "unique"}
TYPE_RULES = {
    "str": {"min_length", "max_length", "pattern"},
    "int": {"min", "max"},
    "float": {"min", "max"},
    "date": {"min", "max"},
    "bool": set(),
}
TYPE_NAMES = {"int": "an int", "float": "a float", "bool": "a bool", "date": "a date"}


class SchemaError(ValueError):
    pass


class HeaderError(ValueError):
    pass


def _to_int(raw: str) -> int:
    if not INT_RE.fullmatch(raw):
        raise ValueError(raw)
    return int(raw)


def _to_float(raw: str) -> float:
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(raw)
    return value


def _to_bool(raw: str) -> bool:
    try:
        return BOOLS[raw.lower()]
    except KeyError:
        raise ValueError(raw) from None


def _to_date(raw: str) -> date:
    if not DATE_RE.fullmatch(raw):
        raise ValueError(raw)
    return date.fromisoformat(raw)


CONVERTERS: dict[str, Callable[[str], Any]] = {
    "str": str,
    "int": _to_int,
    "float": _to_float,
    "bool": _to_bool,
    "date": _to_date,
}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_field(name: str, spec: Any) -> None:
    if not isinstance(spec, dict) or spec.get("type") not in TYPE_RULES:
        raise SchemaError(f"{name}: unknown or missing type")
    kind = spec["type"]
    unknown = set(spec) - COMMON_RULES - TYPE_RULES[kind]
    if unknown:
        raise SchemaError(f"{name}: rule {min(unknown)!r} not allowed for {kind}")
    for flag in ("required", "unique"):
        if flag in spec and not isinstance(spec[flag], bool):
            raise SchemaError(f"{name}: {flag} must be true or false")
    if "enum" in spec and not isinstance(spec["enum"], list):
        raise SchemaError(f"{name}: enum must be a list")
    for bound in ("min", "max"):
        if bound not in spec:
            continue
        value = spec[bound]
        ok = (
            (kind == "int" and isinstance(value, int) and not isinstance(value, bool))
            or (kind == "float" and _is_number(value))
            or (kind == "date" and isinstance(value, str) and _safe(_to_date, value))
        )
        if not ok:
            raise SchemaError(f"{name}: bad {bound}")
    for bound in ("min_length", "max_length"):
        if bound in spec and not (
            isinstance(spec[bound], int)
            and not isinstance(spec[bound], bool)
            and spec[bound] >= 0
        ):
            raise SchemaError(f"{name}: bad {bound}")
    if "pattern" in spec:
        try:
            re.compile(spec["pattern"])
        except (re.error, TypeError) as exc:
            raise SchemaError(f"{name}: bad pattern") from exc


def _safe(fn: Callable[[str], Any], value: str) -> bool:
    try:
        fn(value)
    except ValueError:
        return False
    return True


def check_schema(data: Any) -> dict:
    if not isinstance(data, dict) or set(data) - {"fields", "allow_extra"}:
        raise SchemaError(
            "schema must be an object with 'fields' and optional 'allow_extra'"
        )
    fields = data.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise SchemaError("'fields' must be a non-empty object")
    if not isinstance(data.get("allow_extra", False), bool):
        raise SchemaError("'allow_extra' must be true or false")
    for name, spec in fields.items():
        _check_field(name, spec)
    return data


def load_schema(path: str | Path) -> dict:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SchemaError(f"cannot read schema: {exc}") from exc
    return check_schema(data)


def check_header(header: list[str], schema: dict) -> None:
    fields = schema["fields"]
    seen: set[str] = set()
    for column in header:
        if column in seen:
            raise HeaderError(f"duplicate column: {column}")
        seen.add(column)
    for name, spec in fields.items():
        if spec.get("required") and name not in seen:
            raise HeaderError(f"missing required column: {name}")
    if not schema.get("allow_extra", False):
        for column in header:
            if column not in fields:
                raise HeaderError(f"unexpected column: {column}")


def _bound(spec: dict, key: str) -> Any:
    return _to_date(spec[key]) if spec["type"] == "date" else spec[key]


def _cell_error(raw: str, spec: dict, seen: set | None) -> str | None:
    if raw == "":
        return "required" if spec.get("required") else None
    kind = spec["type"]
    try:
        value = CONVERTERS[kind](raw)
    except ValueError:
        return f"not {TYPE_NAMES[kind]}"
    if "min" in spec and value < _bound(spec, "min"):
        return "below min"
    if "max" in spec and value > _bound(spec, "max"):
        return "above max"
    if "min_length" in spec and len(value) < spec["min_length"]:
        return "too short"
    if "max_length" in spec and len(value) > spec["max_length"]:
        return "too long"
    if "pattern" in spec and not re.fullmatch(spec["pattern"], value):
        return "pattern mismatch"
    if "enum" in spec:
        allowed = (
            [_to_date(v) for v in spec["enum"]] if kind == "date" else spec["enum"]
        )
        if value not in allowed:
            return "not in enum"
    if seen is not None:
        if value in seen:
            return "duplicate"
        seen.add(value)
    return None


def validate_rows(
    rows: Iterable[dict[str, str]], schema: dict
) -> list[tuple[int, str, str]]:
    fields = schema["fields"]
    seen = {name: set() for name, spec in fields.items() if spec.get("unique")}
    errors = []
    for number, row in enumerate(rows, start=1):
        for name, spec in fields.items():
            message = _cell_error((row.get(name) or "").strip(), spec, seen.get(name))
            if message:
                errors.append((number, name, message))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema")
    parser.add_argument("csv")
    parser.add_argument("--max-errors", type=int)
    parser.add_argument("--format", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)
    try:
        schema = load_schema(args.schema)
    except SchemaError as exc:
        print(f"schema error: {exc}", file=sys.stderr)
        return 2
    with open(args.csv, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        try:
            if reader.fieldnames is None:
                raise HeaderError("empty file")
            check_header(list(reader.fieldnames), schema)
        except HeaderError as exc:
            print(f"header error: {exc}", file=sys.stderr)
            return 2
        rows = list(reader)
    errors = validate_rows(rows, schema)
    shown = errors if args.max_errors is None else errors[: args.max_errors]
    if args.format == "json":
        print(json.dumps([{"row": r, "field": f, "message": m} for r, f, m in shown]))
    elif errors:
        for row, field, message in shown:
            print(f"row {row}: {field}: {message}")
    else:
        print(f"valid: {len(rows)} rows")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
