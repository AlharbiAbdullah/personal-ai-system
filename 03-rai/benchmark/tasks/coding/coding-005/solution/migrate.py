"""Apply numbered SQL migrations (NNN_name.sql) to a SQLite database."""

from __future__ import annotations

import argparse
import hashlib
import re
import sqlite3
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

FILE_RE = re.compile(r"([0-9]{3})_([a-z0-9_]+)\.sql")
BOOKKEEPING = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL
)
"""


class MigrationError(Exception):
    """History does not match the files, or a migration failed."""


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    path: Path
    checksum: str

    @property
    def label(self) -> str:
        return f"{self.version:03d}_{self.name}"


def discover(directory: str | Path) -> list[Migration]:
    found: dict[int, Migration] = {}
    for path in sorted(Path(directory).iterdir()):
        match = FILE_RE.fullmatch(path.name)
        if not match or not path.is_file():
            continue
        version = int(match.group(1))
        if version in found:
            raise MigrationError(
                f"duplicate version {version:03d}: {found[version].path.name}, {path.name}"
            )
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        found[version] = Migration(version, match.group(2), path, checksum)
    return [found[v] for v in sorted(found)]


def applied(conn: sqlite3.Connection) -> dict[int, str]:
    conn.execute(BOOKKEEPING)
    conn.commit()
    return dict(
        conn.execute("SELECT version, checksum FROM schema_migrations ORDER BY version")
    )


def _check_history(migrations: list[Migration], done: dict[int, str]) -> None:
    by_version = {mig.version: mig for mig in migrations}
    for version, checksum in sorted(done.items()):
        mig = by_version.get(version)
        if mig is None:
            raise MigrationError(f"applied migration {version:03d} has no file")
        if mig.checksum != checksum:
            raise MigrationError(f"checksum mismatch for applied migration {mig.label}")


def _apply(conn: sqlite3.Connection, mig: Migration, applied_at: str) -> None:
    """Run one migration and its bookkeeping row in a single transaction.

    executescript() commits any open transaction before it runs, so the BEGIN goes inside the
    script; the transaction then stays open for the bookkeeping insert and the commit.
    """
    sql = mig.path.read_text(encoding="utf-8")
    try:
        conn.executescript("BEGIN;\n" + sql)
        conn.execute(
            "INSERT INTO schema_migrations (version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
            (mig.version, mig.name, mig.checksum, applied_at),
        )
        conn.commit()
    except sqlite3.Error as exc:
        if conn.in_transaction:
            conn.rollback()
        raise MigrationError(f"migration {mig.label} failed: {exc}") from exc


def migrate(
    conn: sqlite3.Connection,
    directory: str | Path,
    target: int | None = None,
    now: Callable[[], str] | None = None,
) -> list[int]:
    clock = now or (lambda: datetime.now(timezone.utc).isoformat())
    migrations = discover(directory)
    done = applied(conn)
    _check_history(migrations, done)
    highest = max(done, default=0)
    pending = [
        mig
        for mig in migrations
        if mig.version not in done and (target is None or mig.version <= target)
    ]
    for mig in pending:
        if mig.version < highest:
            raise MigrationError(
                f"migration {mig.label} is older than applied version {highest:03d}"
            )
    for mig in pending:
        _apply(conn, mig, clock())
    return [mig.version for mig in pending]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("db")
    parser.add_argument("--dir", default="migrations")
    parser.add_argument("--target", type=int)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args(argv)
    conn = sqlite3.connect(args.db)
    try:
        migrations = discover(args.dir)
        if args.status:
            done = applied(conn)
            for mig in migrations:
                print(f"{mig.label} {'applied' if mig.version in done else 'pending'}")
            return 0
        versions = migrate(conn, args.dir, target=args.target)
    except MigrationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()
    labels = {mig.version: mig.label for mig in migrations}
    for version in versions:
        print(f"applied {labels[version]}")
    if not versions:
        print("up to date")
    return 0


if __name__ == "__main__":
    sys.exit(main())
