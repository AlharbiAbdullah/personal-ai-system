import hashlib
import json
import subprocess
import sys
from pathlib import Path

import ingest as ing
import pytest

ROOT = Path(__file__).resolve().parent.parent
HEADER = "txn_id,account,amount_cents\n"


def drop(root, name, body, header=HEADER):
    inbox = Path(root) / "inbox"
    inbox.mkdir(parents=True, exist_ok=True)
    path = inbox / name
    path.write_text(header + body)
    return path


def jsonl(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def txns(root):
    return jsonl(Path(root) / "transactions.jsonl")


def ledger(root):
    return jsonl(Path(root) / "ledger.jsonl")


def zero():
    return {
        "processed": 0,
        "duplicates": 0,
        "failed": 0,
        "rows_written": 0,
        "rows_skipped": 0,
    }


def test_empty_root_gets_layout(tmp_path):
    assert ing.ingest(tmp_path) == zero()
    for name in ("inbox", "processed", "failed"):
        assert (tmp_path / name).is_dir()


def test_processes_files_and_records_everything(tmp_path):
    a = drop(tmp_path, "a.csv", "T1,ACC-1,100\nT2,ACC-2,-50\n")
    digest = hashlib.sha256(a.read_bytes()).hexdigest()
    drop(tmp_path, "b.csv", " T3 , ACC-1 , 7 \n")
    result = ing.ingest(str(tmp_path))
    assert result == {
        "processed": 2,
        "duplicates": 0,
        "failed": 0,
        "rows_written": 3,
        "rows_skipped": 0,
    }
    assert txns(tmp_path) == [
        {"txn_id": "T1", "account": "ACC-1", "amount_cents": 100, "source": "a.csv"},
        {"txn_id": "T2", "account": "ACC-2", "amount_cents": -50, "source": "a.csv"},
        {"txn_id": "T3", "account": "ACC-1", "amount_cents": 7, "source": "b.csv"},
    ]
    assert ledger(tmp_path)[0] == {"sha256": digest, "name": "a.csv", "rows": 2}
    assert [r["name"] for r in ledger(tmp_path)] == ["a.csv", "b.csv"]
    assert list((tmp_path / "inbox").iterdir()) == []
    assert (tmp_path / "processed" / f"{digest[:12]}_a.csv").read_bytes() == (
        HEADER + "T1,ACC-1,100\nT2,ACC-2,-50\n"
    ).encode()
    assert len(list((tmp_path / "processed").iterdir())) == 2


def test_second_run_changes_nothing(tmp_path):
    drop(tmp_path, "a.csv", "T1,ACC-1,100\n")
    ing.ingest(tmp_path)
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert ing.ingest(tmp_path) == zero()
    after = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before


def test_resent_file_under_new_name_is_a_duplicate(tmp_path):
    drop(tmp_path, "monday.csv", "T1,ACC-1,100\nT2,ACC-1,200\n")
    ing.ingest(tmp_path)
    drop(tmp_path, "monday-resend.csv", "T1,ACC-1,100\nT2,ACC-1,200\n")
    drop(tmp_path, "monday-again.csv", "T1,ACC-1,100\nT2,ACC-1,200\n")
    assert ing.ingest(tmp_path) == {**zero(), "duplicates": 2}
    assert list((tmp_path / "inbox").iterdir()) == []
    assert len(txns(tmp_path)) == 2
    assert len(ledger(tmp_path)) == 1


def test_identical_files_in_one_run(tmp_path):
    drop(tmp_path, "x1.csv", "T9,ACC-1,1\n")
    drop(tmp_path, "x2.csv", "T9,ACC-1,1\n")
    assert ing.ingest(tmp_path) == {
        **zero(),
        "processed": 1,
        "duplicates": 1,
        "rows_written": 1,
    }
    assert [r["name"] for r in ledger(tmp_path)] == ["x1.csv"]


def test_overlapping_transactions_are_skipped_first_file_by_name_wins(tmp_path):
    drop(tmp_path, "b.csv", "T1,ACC-B,999\nT4,ACC-B,4\n")
    drop(tmp_path, "a.csv", "T1,ACC-A,1\nT2,ACC-A,2\nT2,ACC-A,2\n")
    result = ing.ingest(tmp_path)
    assert result == {
        "processed": 2,
        "duplicates": 0,
        "failed": 0,
        "rows_written": 3,
        "rows_skipped": 2,
    }
    assert [(t["txn_id"], t["account"]) for t in txns(tmp_path)] == [
        ("T1", "ACC-A"),
        ("T2", "ACC-A"),
        ("T4", "ACC-B"),
    ]
    assert [r["rows"] for r in ledger(tmp_path)] == [3, 2]


@pytest.mark.parametrize(
    "header,body,line_no",
    [
        (HEADER, "T1,ACC-1,100\nT2,ACC-1,12.5\n", 3),
        (HEADER, "T1,ACC-1,100\n,ACC-1,5\n", 3),
        (HEADER, "T1, ,100\n", 2),
        (HEADER, "T1,ACC-1,100,extra\n", 2),
        (HEADER, "T1,ACC-1\n", 2),
        (HEADER, "T1,ACC-1,100\nT2,ACC-1,abc\nT3,ACC-1,x\n", 3),
        ("id,account,amount\n", "T1,ACC-1,100\n", 1),
        ("", "", 1),
    ],
)
def test_invalid_files_go_to_failed_whole(tmp_path, header, body, line_no):
    bad = drop(tmp_path, "bad.csv", body, header=header)
    content = bad.read_bytes()
    drop(tmp_path, "good.csv", "G1,ACC-1,5\n")
    result = ing.ingest(tmp_path)
    assert result == {
        "processed": 1,
        "duplicates": 0,
        "failed": 1,
        "rows_written": 1,
        "rows_skipped": 0,
    }
    assert (tmp_path / "failed" / "bad.csv").read_bytes() == content
    error = (tmp_path / "failed" / "bad.csv.error").read_text()
    assert error.startswith(f"line {line_no}:")
    assert [t["txn_id"] for t in txns(tmp_path)] == ["G1"]
    assert [r["name"] for r in ledger(tmp_path)] == ["good.csv"]
    assert not bad.exists()


def test_fixed_file_after_failure_is_processed(tmp_path):
    drop(tmp_path, "day.csv", "T1,ACC-1,oops\n")
    assert ing.ingest(tmp_path)["failed"] == 1
    drop(tmp_path, "day.csv", "T1,ACC-1,10\n")
    assert ing.ingest(tmp_path) == {**zero(), "processed": 1, "rows_written": 1}


def test_rerun_after_crash_does_not_duplicate_rows(tmp_path):
    drop(tmp_path, "c.csv", "T1,ACC-1,1\nT2,ACC-1,2\nT3,ACC-1,3\n")
    (tmp_path / "transactions.jsonl").write_text(
        json.dumps(
            {"txn_id": "T1", "account": "ACC-1", "amount_cents": 1, "source": "c.csv"}
        )
        + "\n"
        + json.dumps(
            {"txn_id": "T2", "account": "ACC-1", "amount_cents": 2, "source": "c.csv"}
        )
        + "\n"
    )
    assert ing.ingest(tmp_path) == {
        "processed": 1,
        "duplicates": 0,
        "failed": 0,
        "rows_written": 1,
        "rows_skipped": 2,
    }
    assert [t["txn_id"] for t in txns(tmp_path)] == ["T1", "T2", "T3"]
    assert [r["rows"] for r in ledger(tmp_path)] == [3]


def test_rerun_after_crash_before_move(tmp_path):
    path = drop(tmp_path, "d.csv", "T1,ACC-1,1\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (tmp_path / "transactions.jsonl").write_text(
        json.dumps(
            {"txn_id": "T1", "account": "ACC-1", "amount_cents": 1, "source": "d.csv"}
        )
        + "\n"
    )
    (tmp_path / "ledger.jsonl").write_text(
        json.dumps({"sha256": digest, "name": "d.csv", "rows": 1}) + "\n"
    )
    assert ing.ingest(tmp_path) == {**zero(), "duplicates": 1}
    assert not path.exists()
    assert len(txns(tmp_path)) == 1


def test_other_inbox_entries_are_left_alone(tmp_path):
    drop(tmp_path, "notes.txt", "hello\n", header="")
    drop(tmp_path, "data.CSV.bak", "T1,ACC-1,1\n")
    (tmp_path / "inbox" / "nested.csv").mkdir()
    assert ing.ingest(tmp_path) == zero()
    assert sorted(p.name for p in (tmp_path / "inbox").iterdir()) == [
        "data.CSV.bak",
        "nested.csv",
        "notes.txt",
    ]


def test_blank_lines_are_ignored(tmp_path):
    drop(tmp_path, "e.csv", "T1,ACC-1,1\n\nT2,ACC-1,2\n\n")
    assert ing.ingest(tmp_path)["rows_written"] == 2
    assert [r["rows"] for r in ledger(tmp_path)] == [2]


def test_cli_prints_json(tmp_path):
    drop(tmp_path, "a.csv", "T1,ACC-1,1\n")
    proc = subprocess.run(
        [sys.executable, "ingest.py", str(tmp_path)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == json.dumps(
        {
            "duplicates": 0,
            "failed": 0,
            "processed": 1,
            "rows_skipped": 0,
            "rows_written": 1,
        },
        sort_keys=True,
    )
