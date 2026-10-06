import csv
import subprocess
import sys
from pathlib import Path

import clean_orders as co
import pytest

ROOT = Path(__file__).resolve().parent.parent
HEADER = ["order_id", "customer_email", "amount", "currency", "order_date", "status"]


def make_row(**overrides):
    row = {
        "order_id": "ORD-00001",
        "customer_email": "a@example.com",
        "amount": "10",
        "currency": "USD",
        "order_date": "2026-03-01",
        "status": "completed",
    }
    row.update(overrides)
    return row


def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(HEADER)
        writer.writerows(rows)


def read_csv(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.reader(fh))


def test_clean_row_normalizes_every_field():
    got = co.clean_row(
        make_row(
            order_id="  ord-12345 ",
            customer_email=" Jane.Doe@Example.COM ",
            amount=" $1,234.5 ",
            currency=" eur ",
            order_date="Mar 5, 2026",
            status=" Done ",
        )
    )
    assert got == {
        "order_id": "ORD-12345",
        "customer_email": "jane.doe@example.com",
        "amount": "1234.50",
        "currency": "EUR",
        "order_date": "2026-03-05",
        "status": "completed",
    }


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("12.345", "12.35"),
        ("2.675", "2.68"),
        ("1.005", "1.01"),
        ("0.125", "0.13"),
        ("1,000,000", "1000000.00"),
        ("$7", "7.00"),
        ("0", "0.00"),
        ("19.999", "20.00"),
        ("$0.994", "0.99"),
    ],
)
def test_amount_two_decimals_round_half_up(raw, expected):
    assert co.clean_row(make_row(amount=raw))["amount"] == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("2026-03-01", "2026-03-01"),
        ("2026/12/31", "2026-12-31"),
        ("05/03/2026", "2026-03-05"),
        ("31/01/2026", "2026-01-31"),
        ("feb 28, 2024", "2024-02-28"),
        ("Feb 29, 2024", "2024-02-29"),
        ("DEC 01, 2025", "2025-12-01"),
        (" 2026-07-04 ", "2026-07-04"),
    ],
)
def test_date_formats(raw, expected):
    assert co.clean_row(make_row(order_date=raw))["order_date"] == expected


@pytest.mark.parametrize(
    "raw",
    [
        "2026-02-30",
        "31/04/2026",
        "Feb 29, 2025",
        "2026-13-01",
        "03-05-2026",
        "yesterday",
        "",
    ],
)
def test_bad_dates(raw):
    with pytest.raises(ValueError) as err:
        co.clean_row(make_row(order_date=raw))
    assert str(err.value) == "bad date"


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("order_id", "ORD-1234", "bad order_id"),
        ("order_id", "ORD-123456", "bad order_id"),
        ("order_id", "ORDX12345", "bad order_id"),
        ("order_id", "", "bad order_id"),
        ("customer_email", "no-at-sign.com", "bad email"),
        ("customer_email", "a@@example.com", "bad email"),
        ("customer_email", "@example.com", "bad email"),
        ("customer_email", "a@localhost", "bad email"),
        ("customer_email", "a@.example.com", "bad email"),
        ("customer_email", "a@example.com.", "bad email"),
        ("customer_email", "a b@example.com", "bad email"),
        ("amount", "abc", "bad amount"),
        ("amount", "", "bad amount"),
        ("amount", "1.2.3", "bad amount"),
        ("amount", "12.", "bad amount"),
        ("amount", "-12.00", "negative amount"),
        ("amount", "$-3", "negative amount"),
        ("currency", "JPY", "bad currency"),
        ("currency", "US", "bad currency"),
        ("status", "shipped", "bad status"),
        ("status", "", "bad status"),
    ],
)
def test_rejection_reasons(field, value, reason):
    with pytest.raises(ValueError) as err:
        co.clean_row(make_row(**{field: value}))
    assert str(err.value) == reason


def test_empty_currency_defaults_to_usd():
    assert co.clean_row(make_row(currency="  "))["currency"] == "USD"
    assert co.clean_row(make_row(currency="gbp"))["currency"] == "GBP"


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("COMPLETE", "completed"),
        ("completed", "completed"),
        ("done", "completed"),
        ("Canceled", "cancelled"),
        ("cancelled", "cancelled"),
        (" pending", "pending"),
        ("REFUNDED", "refunded"),
    ],
)
def test_status_synonyms(raw, expected):
    assert co.clean_row(make_row(status=raw))["status"] == expected


def test_first_failing_rule_decides_reason():
    cases = [
        (make_row(order_id="bad", amount="abc"), "bad order_id"),
        (make_row(customer_email="x", status="nope"), "bad email"),
        (make_row(amount="abc", status="nope"), "bad amount"),
        (make_row(currency="XXX", order_date="nope"), "bad currency"),
        (make_row(order_date="nope", status="nope"), "bad date"),
    ]
    for row, reason in cases:
        with pytest.raises(ValueError) as err:
            co.clean_row(row)
        assert str(err.value) == reason


def test_clean_file_outputs_and_duplicates(tmp_path):
    src, out, rej = tmp_path / "in.csv", tmp_path / "out.csv", tmp_path / "rej.csv"
    write_csv(
        src,
        [
            ["ORD-00002", "B@Example.com", "$2,000", "", "2026/01/02", "Done"],
            ["ORD-00003", "broken", "5", "USD", "2026-01-03", "pending"],
            ["ORD-00003", "c@example.com", "5", "USD", "2026-01-03", "pending"],
            [" ord-00002 ", "b@example.com", "1", "USD", "2026-01-04", "pending"],
            ["ORD-00004", "d@example.com", "-1", "USD", "2026-01-05", "pending"],
            ["ORD-00005", "e@example.com", "3.333", "eur", "Jan 6, 2026", "canceled"],
            ["ORD-00003", "c@example.com", "5", "USD", "2026-01-03", "pending"],
        ],
    )
    assert co.clean_file(src, out, rej) == (3, 4)
    assert read_csv(out) == [
        HEADER,
        ["ORD-00002", "b@example.com", "2000.00", "USD", "2026-01-02", "completed"],
        ["ORD-00003", "c@example.com", "5.00", "USD", "2026-01-03", "pending"],
        ["ORD-00005", "e@example.com", "3.33", "EUR", "2026-01-06", "cancelled"],
    ]
    assert read_csv(rej) == [
        ["row", "order_id", "reason"],
        ["2", "ORD-00003", "bad email"],
        ["4", "ord-00002", "duplicate order_id"],
        ["5", "ORD-00004", "negative amount"],
        ["7", "ORD-00003", "duplicate order_id"],
    ]


def test_clean_file_accepts_str_paths_and_short_rows(tmp_path):
    src = tmp_path / "in.csv"
    with open(src, "w", newline="", encoding="utf-8") as fh:
        fh.write(",".join(HEADER) + "\n")
        fh.write("ORD-00009,z@example.com,4\n")
        fh.write("ORD-00010,y@example.com,4,usd,2026-02-01,pending\n")
    clean, rejected = co.clean_file(
        str(src), str(tmp_path / "o.csv"), str(tmp_path / "r.csv")
    )
    assert (clean, rejected) == (1, 1)
    assert read_csv(tmp_path / "r.csv")[1] == ["1", "ORD-00009", "bad date"]


def test_cli_end_to_end(tmp_path):
    src, out, rej = tmp_path / "in.csv", tmp_path / "out.csv", tmp_path / "rej.csv"
    write_csv(
        src,
        [
            ["ORD-00011", "a@example.com", "1", "USD", "2026-01-01", "pending"],
            ["ORD-00012", "a@example.com", "2", "USD", "2026-01-01", "lost"],
            ["ORD-00013", "a@example.com", "3", "GBP", "13/01/2026", "done"],
        ],
    )
    proc = subprocess.run(
        [
            sys.executable,
            "clean_orders.py",
            str(src),
            "--out",
            str(out),
            "--rejects",
            str(rej),
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert "clean=2 rejected=1" in proc.stdout
    assert len(read_csv(out)) == 3
    assert read_csv(rej)[1] == ["2", "ORD-00012", "bad status"]


def test_cli_missing_source_exits_1(tmp_path):
    proc = subprocess.run(
        [
            sys.executable,
            "clean_orders.py",
            str(tmp_path / "missing.csv"),
            "--out",
            str(tmp_path / "o.csv"),
            "--rejects",
            str(tmp_path / "r.csv"),
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 1
    assert proc.stderr.strip()
