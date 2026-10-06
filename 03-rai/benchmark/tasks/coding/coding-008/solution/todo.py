"""A command-line todo list stored in one JSON file."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from datetime import date
from pathlib import Path

PAST_TENSE = {"done": "done", "remove": "removed", "edit": "edited"}


class CorruptDatabase(Exception):
    pass


def due_date(value: str) -> str:
    try:
        if len(value) != 10:
            raise ValueError
        return date.fromisoformat(value).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}") from None


def norm_tags(tags: list[str] | None) -> list[str]:
    out: list[str] = []
    for tag in tags or []:
        tag = tag.strip().lower()
        if tag and tag not in out:
            out.append(tag)
    return out


def load(path: Path) -> dict:
    if not path.exists():
        return {"next_id": 1, "tasks": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError) as exc:
        raise CorruptDatabase from exc
    if not (
        isinstance(data, dict)
        and isinstance(data.get("next_id"), int)
        and isinstance(data.get("tasks"), list)
        and all(
            isinstance(t, dict) and isinstance(t.get("id"), int) for t in data["tasks"]
        )
    ):
        raise CorruptDatabase
    return data


def save(path: Path, data: dict) -> None:
    data["tasks"].sort(key=lambda t: t["id"])
    fd, tmp = tempfile.mkstemp(
        dir=path.parent or Path("."), prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
            fh.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="todo.py", description=__doc__)
    parser.add_argument("--db", type=Path, default=Path("todo.json"))
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("text")
    add.add_argument("--tag", action="append", default=[])
    add.add_argument("--due", type=due_date)

    lst = sub.add_parser("list")
    lst.add_argument("--status", choices=["open", "done", "all"], default="open")
    lst.add_argument("--tag")
    lst.add_argument("--overdue", action="store_true")
    lst.add_argument("--today", type=due_date)

    for name in ("done", "remove"):
        sub.add_parser(name).add_argument("id", type=int)

    edit = sub.add_parser("edit")
    edit.add_argument("id", type=int)
    edit.add_argument("--text")
    dues = edit.add_mutually_exclusive_group()
    dues.add_argument("--due", type=due_date)
    dues.add_argument("--no-due", action="store_true")
    edit.add_argument("--add-tag", action="append", default=[])
    edit.add_argument("--remove-tag", action="append", default=[])
    return parser


def find(data: dict, task_id: int) -> dict:
    for task in data["tasks"]:
        if task["id"] == task_id:
            return task
    raise KeyError(task_id)


def cmd_list(data: dict, args: argparse.Namespace) -> None:
    tag = args.tag.strip().lower() if args.tag else None
    tasks = [
        t
        for t in data["tasks"]
        if (args.status == "all" or t["done"] == (args.status == "done"))
        and (tag is None or tag in t["tags"])
        and (not args.overdue or (t["due"] is not None and t["due"] < args.today))
    ]
    tasks.sort(key=lambda t: (t["due"] is None, t["due"] or "", t["id"]))
    for t in tasks:
        mark = "x" if t["done"] else "-"
        print(
            f"{t['id']}\t{mark}\t{t['text']}\t{','.join(t['tags'])}\t{t['due'] or '-'}"
        )


def apply_edit(task: dict, args: argparse.Namespace) -> None:
    if args.text is not None:
        task["text"] = args.text.strip()
    if args.no_due:
        task["due"] = None
    elif args.due:
        task["due"] = args.due
    removed = set(norm_tags(args.remove_tag))
    task["tags"] = [
        t for t in norm_tags(task["tags"] + args.add_tag) if t not in removed
    ]


def run(args: argparse.Namespace) -> int:
    data = load(args.db)
    if args.command == "list":
        cmd_list(data, args)
        return 0
    if args.command == "add":
        task = {
            "id": data["next_id"],
            "text": args.text.strip(),
            "tags": norm_tags(args.tag),
            "due": args.due,
            "done": False,
        }
        data["tasks"].append(task)
        data["next_id"] += 1
        save(args.db, data)
        print(f"added {task['id']}")
        return 0
    try:
        task = find(data, args.id)
    except KeyError:
        print(f"no such task: {args.id}", file=sys.stderr)
        return 1
    if args.command == "done":
        task["done"] = True
    elif args.command == "remove":
        data["tasks"].remove(task)
    else:
        apply_edit(task, args)
    save(args.db, data)
    print(f"{PAST_TENSE[args.command]} {args.id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "add" and not args.text.strip():
        parser.error("task text must not be empty")
    if args.command == "list" and args.overdue and args.today is None:
        parser.error("--overdue needs --today")
    if args.command == "edit" and not (
        args.text is not None
        or args.due
        or args.no_due
        or args.add_tag
        or args.remove_tag
    ):
        parser.error("edit needs at least one change")
    if args.command == "edit" and args.text is not None and not args.text.strip():
        parser.error("task text must not be empty")
    try:
        return run(args)
    except CorruptDatabase:
        print(f"corrupt database: {args.db}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
