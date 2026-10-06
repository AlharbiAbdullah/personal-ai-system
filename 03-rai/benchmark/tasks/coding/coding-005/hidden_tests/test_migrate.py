import hashlib
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import migrate as m
import pytest

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "migrations"
NOW = "2026-10-01T12:00:00+00:00"


def fixed_now():
    return NOW


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tables(conn):
    return {
        r[0]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }


def versions(path):
    conn = sqlite3.connect(path)
    try:
        return [
            r[0]
            for r in conn.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
        ]
    finally:
        conn.close()


@pytest.fixture
def mdir(tmp_path):
    target = tmp_path / "migrations"
    shutil.copytree(SAMPLE, target)
    return target


@pytest.fixture
def dbpath(tmp_path):
    return tmp_path / "app.db"


def cli(*args):
    return subprocess.run(
        [sys.executable, "migrate.py", *map(str, args)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )


def test_discover_sorts_filters_and_hashes(mdir):
    (mdir / "5_short.sql").write_text("SELECT 1;")
    (mdir / "006_Upper.sql").write_text("SELECT 1;")
    (mdir / "007_backup.sql.bak").write_text("SELECT 1;")
    (mdir / "010_add_flags.sql").write_text(
        "ALTER TABLE users ADD COLUMN flags INTEGER;"
    )
    found = m.discover(mdir)
    assert [(x.version, x.name) for x in found] == [
        (1, "create_users"),
        (2, "add_user_email_index"),
        (3, "create_orders"),
        (10, "add_flags"),
    ]
    assert found[0].checksum == sha(mdir / "001_create_users.sql")
    assert Path(found[3].path).resolve() == (mdir / "010_add_flags.sql").resolve()


def test_discover_rejects_duplicate_versions(mdir):
    (mdir / "002_other.sql").write_text("SELECT 1;")
    with pytest.raises(m.MigrationError):
        m.discover(mdir)


def test_applied_creates_bookkeeping_table(dbpath):
    conn = sqlite3.connect(dbpath)
    assert m.applied(conn) == {}
    cols = [r[1] for r in conn.execute("PRAGMA table_info(schema_migrations)")]
    assert cols == ["version", "name", "checksum", "applied_at"]


def test_migrate_applies_in_order_and_records(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    assert m.migrate(conn, mdir, now=fixed_now) == [1, 2, 3]
    check = sqlite3.connect(dbpath)
    assert {"users", "orders", "schema_migrations"} <= tables(check)
    rows = check.execute(
        "SELECT version, name, checksum, applied_at FROM schema_migrations ORDER BY version"
    ).fetchall()
    assert rows == [
        (1, "create_users", sha(mdir / "001_create_users.sql"), NOW),
        (2, "add_user_email_index", sha(mdir / "002_add_user_email_index.sql"), NOW),
        (3, "create_orders", sha(mdir / "003_create_orders.sql"), NOW),
    ]
    check.execute("INSERT INTO orders (user_id) VALUES (1)")
    assert check.execute("SELECT note FROM orders").fetchone() == ("none; really",)


def test_second_run_is_a_no_op(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    m.migrate(conn, mdir, now=fixed_now)
    assert m.migrate(conn, mdir, now=fixed_now) == []
    assert m.applied(conn) == {
        1: sha(mdir / "001_create_users.sql"),
        2: sha(mdir / "002_add_user_email_index.sql"),
        3: sha(mdir / "003_create_orders.sql"),
    }
    assert sqlite3.connect(dbpath).execute("SELECT COUNT(*) FROM users").fetchone() == (
        1,
    )


def test_target_stops_early(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    assert m.migrate(conn, mdir, target=2, now=fixed_now) == [1, 2]
    assert "orders" not in tables(sqlite3.connect(dbpath))
    assert m.migrate(conn, mdir, target=2, now=fixed_now) == []
    assert m.migrate(conn, mdir, now=fixed_now) == [3]


def test_default_now_is_utc_iso(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    m.migrate(conn, mdir, target=1)
    (value,) = (
        sqlite3.connect(dbpath)
        .execute("SELECT applied_at FROM schema_migrations")
        .fetchone()
    )
    assert datetime.fromisoformat(value).utcoffset() == timedelta(0)


def test_failing_migration_rolls_back_only_itself(mdir, dbpath):
    (mdir / "004_audit.sql").write_text(
        "CREATE TABLE audit (id INTEGER PRIMARY KEY);\n"
        "INSERT INTO users (email, created_at) VALUES ('x@example.com', 'now');\n"
        "INSERT INTO missing_table VALUES (1);\n"
    )
    (mdir / "005_later.sql").write_text("CREATE TABLE later (id INTEGER);\n")
    conn = sqlite3.connect(dbpath)
    with pytest.raises(m.MigrationError) as err:
        m.migrate(conn, mdir, now=fixed_now)
    assert "004" in str(err.value)
    check = sqlite3.connect(dbpath)
    assert "audit" not in tables(check)
    assert "later" not in tables(check)
    assert check.execute("SELECT COUNT(*) FROM users").fetchone() == (1,)
    assert versions(dbpath) == [1, 2, 3]
    (mdir / "004_audit.sql").write_text(
        "CREATE TABLE audit (id INTEGER PRIMARY KEY);\n"
    )
    assert m.migrate(conn, mdir, now=fixed_now) == [4, 5]
    assert {"audit", "later"} <= tables(sqlite3.connect(dbpath))


def test_failure_in_alter_keeps_previous_call_intact(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    m.migrate(conn, mdir, now=fixed_now)
    (mdir / "004_flags.sql").write_text(
        "ALTER TABLE users ADD COLUMN flags INTEGER NOT NULL DEFAULT 0;\nCREATE TABLE users (id INTEGER);\n"
    )
    with pytest.raises(m.MigrationError):
        m.migrate(conn, mdir, now=fixed_now)
    cols = [r[1] for r in sqlite3.connect(dbpath).execute("PRAGMA table_info(users)")]
    assert "flags" not in cols
    assert versions(dbpath) == [1, 2, 3]


def test_edited_applied_migration_blocks_everything(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    m.migrate(conn, mdir, target=2, now=fixed_now)
    path = mdir / "001_create_users.sql"
    path.write_text(path.read_text() + "\n-- edited later\n")
    with pytest.raises(m.MigrationError):
        m.migrate(conn, mdir, now=fixed_now)
    assert "orders" not in tables(sqlite3.connect(dbpath))
    assert versions(dbpath) == [1, 2]


def test_missing_applied_file_blocks_everything(mdir, dbpath):
    conn = sqlite3.connect(dbpath)
    m.migrate(conn, mdir, now=fixed_now)
    (mdir / "002_add_user_email_index.sql").unlink()
    (mdir / "004_more.sql").write_text("CREATE TABLE more (id INTEGER);\n")
    with pytest.raises(m.MigrationError):
        m.migrate(conn, mdir, now=fixed_now)
    assert "more" not in tables(sqlite3.connect(dbpath))


def test_out_of_order_file_is_refused(tmp_path, dbpath):
    d = tmp_path / "partial"
    d.mkdir()
    shutil.copy(SAMPLE / "001_create_users.sql", d)
    shutil.copy(SAMPLE / "003_create_orders.sql", d)
    conn = sqlite3.connect(dbpath)
    assert m.migrate(conn, d, now=fixed_now) == [1, 3]
    shutil.copy(SAMPLE / "002_add_user_email_index.sql", d)
    with pytest.raises(m.MigrationError):
        m.migrate(conn, d, now=fixed_now)
    assert versions(dbpath) == [1, 3]
    assert sqlite3.connect(dbpath).execute("SELECT COUNT(*) FROM users").fetchone() == (
        0,
    )


def test_cli_status_then_migrate(mdir, dbpath):
    proc = cli(dbpath, "--dir", mdir, "--status")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "001_create_users pending",
        "002_add_user_email_index pending",
        "003_create_orders pending",
    ]
    assert "users" not in tables(sqlite3.connect(dbpath))
    proc = cli(dbpath, "--dir", mdir, "--target", "1")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["applied 001_create_users"]
    proc = cli(dbpath, "--dir", mdir, "--status")
    assert proc.stdout.splitlines() == [
        "001_create_users applied",
        "002_add_user_email_index pending",
        "003_create_orders pending",
    ]
    proc = cli(dbpath, "--dir", mdir)
    assert proc.stdout.splitlines() == [
        "applied 002_add_user_email_index",
        "applied 003_create_orders",
    ]
    proc = cli(dbpath, "--dir", mdir)
    assert proc.returncode == 0
    assert proc.stdout.splitlines() == ["up to date"]


def test_cli_error_exits_1(mdir, dbpath):
    (mdir / "004_bad.sql").write_text("CREATE TABLE broken (;\n")
    proc = cli(dbpath, "--dir", mdir)
    assert proc.returncode == 1
    assert "004" in proc.stderr
    assert versions(dbpath) == [1, 2, 3]
