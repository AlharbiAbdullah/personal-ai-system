"""Idempotent ingest of bank transaction CSV files from ROOT/inbox."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
from pathlib import Path

HEADER = ["txn_id", "account", "amount_cents"]
AMOUNT_RE = re.compile(r"-?[0-9]+")


class InvalidFile(Exception):
    def __init__(self, line: int, reason: str) -> None:
        super().__init__(f"line {line}: {reason}")


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _append_jsonl(path: Path, records: list[dict]) -> None:
    if not records:
        return
    with path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def parse_rows(data: bytes) -> list[dict]:
    """Return the rows of a valid file, or raise InvalidFile for the first problem."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise InvalidFile(1, "not valid UTF-8") from None
    reader = csv.reader(io.StringIO(text, newline=""))
    if next(reader, None) != HEADER:
        raise InvalidFile(1, "bad header")
    rows = []
    for cells in reader:
        if not cells:
            continue
        line = reader.line_num
        if len(cells) != 3:
            raise InvalidFile(line, f"expected 3 fields, got {len(cells)}")
        txn_id, account, amount = (cell.strip() for cell in cells)
        if not txn_id:
            raise InvalidFile(line, "empty txn_id")
        if not account:
            raise InvalidFile(line, "empty account")
        if not AMOUNT_RE.fullmatch(amount):
            raise InvalidFile(line, f"amount_cents is not an integer: {amount!r}")
        rows.append({"txn_id": txn_id, "account": account, "amount_cents": int(amount)})
    return rows


def ingest(root: str | Path) -> dict[str, int]:
    root = Path(root)
    inbox, processed, failed = root / "inbox", root / "processed", root / "failed"
    for folder in (inbox, processed, failed):
        folder.mkdir(parents=True, exist_ok=True)
    ledger_path, txn_path = root / "ledger.jsonl", root / "transactions.jsonl"
    seen_files = {record["sha256"] for record in _read_jsonl(ledger_path)}
    seen_txns = {record["txn_id"] for record in _read_jsonl(txn_path)}
    counts = dict.fromkeys(
        ["processed", "duplicates", "failed", "rows_written", "rows_skipped"], 0
    )

    for path in sorted(
        p for p in inbox.iterdir() if p.suffix == ".csv" and p.is_file()
    ):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest in seen_files:
            path.unlink()
            counts["duplicates"] += 1
            continue
        try:
            rows = parse_rows(data)
        except InvalidFile as exc:
            os.replace(path, failed / path.name)
            (failed / f"{path.name}.error").write_text(f"{exc}\n", encoding="utf-8")
            counts["failed"] += 1
            continue
        new_rows = []
        for row in rows:
            if row["txn_id"] in seen_txns:
                counts["rows_skipped"] += 1
                continue
            seen_txns.add(row["txn_id"])
            new_rows.append({**row, "source": path.name})
        # Order matters for crash safety: rows first, then the ledger record, then the move.
        _append_jsonl(txn_path, new_rows)
        _append_jsonl(
            ledger_path, [{"sha256": digest, "name": path.name, "rows": len(rows)}]
        )
        os.replace(path, processed / f"{digest[:12]}_{path.name}")
        seen_files.add(digest)
        counts["rows_written"] += len(new_rows)
        counts["processed"] += 1
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root")
    args = parser.parse_args(argv)
    print(json.dumps(ingest(args.root), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
