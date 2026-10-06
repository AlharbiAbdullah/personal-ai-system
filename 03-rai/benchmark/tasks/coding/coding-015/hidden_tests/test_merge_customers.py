import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import merge_customers as mc
import pytest

ROOT = Path(__file__).resolve().parent.parent
UTC = timezone.utc


def rec(source, id_, name="", email="", phone="", city="", ts=(2026, 1, 1)):
    return {
        "source": source,
        "id": id_,
        "name": name,
        "email": email,
        "phone": phone,
        "city": city,
        "updated_at": datetime(*ts, tzinfo=UTC),
    }


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" Ann.Lee+promo@GMail.com ", "annlee@gmail.com"),
        ("ann.lee@googlemail.com", "annlee@gmail.com"),
        ("A.N.N.LEE@gmail.com", "annlee@gmail.com"),
        ("Bob.Smith+x@Example.org", "bob.smith@example.org"),
        ("bob.smith@example.org", "bob.smith@example.org"),
        ("no-at-sign", None),
        ("a@b@c.com", None),
        ("@example.com", None),
        ("+tag@example.com", None),
        ("x@", None),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalize_email(raw, expected):
    assert mc.normalize_email(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("(415) 555-0100", "+14155550100"),
        ("+1 415 555 0100", "+14155550100"),
        ("415.555.0100", "+14155550100"),
        ("0044 20 7946 0958", "+442079460958"),
        ("+44 20 7946 0958", "+442079460958"),
        ("+966 50 123 4567", "+966501234567"),
        ("555-0100", None),
        ("123456789", None),
        ("1234567890123456", None),
        ("", None),
        (None, None),
        ("call me", None),
    ],
)
def test_normalize_phone(raw, expected):
    assert mc.normalize_phone(raw) == expected


def test_transitive_matching_across_sources():
    records = [
        rec("crm", "C-1", name="One", email="e1@example.com"),
        rec("billing", "B-1", email="E1@Example.com", phone="415 555 0101"),
        rec("crm", "C-2", phone="+1 (415) 555-0101", email="e3@example.com"),
        rec("billing", "B-2", email="e3+shop@example.com"),
        rec("crm", "C-3", name="Loner", email="other@example.com"),
    ]
    merged = mc.merge(records)
    assert [m["ids"] for m in merged] == [
        ["billing:B-1", "billing:B-2", "crm:C-1", "crm:C-2"],
        ["crm:C-3"],
    ]


def test_missing_contact_details_never_match_each_other():
    records = [
        rec("crm", "C-1", name="A"),
        rec("crm", "C-2", name="B", email="  "),
        rec("billing", "B-1", name="C", phone="12"),
    ]
    assert [m["ids"] for m in mc.merge(records)] == [
        ["billing:B-1"],
        ["crm:C-1"],
        ["crm:C-2"],
    ]


def test_fields_come_from_latest_record_that_has_them():
    records = [
        rec(
            "crm",
            "C-1",
            name="Old Name",
            email="x@example.com",
            phone="4155550100",
            city="Austin",
            ts=(2026, 1, 1),
        ),
        rec(
            "billing",
            "B-1",
            name="New Name",
            email="X@example.com",
            phone="",
            city="  ",
            ts=(2026, 3, 1),
        ),
        rec(
            "crm",
            "C-2",
            name=" Middle ",
            email="x@example.com",
            phone="999",
            city="Dallas ",
            ts=(2026, 2, 1),
        ),
    ]
    (m,) = mc.merge(records)
    assert m == {
        "ids": ["billing:B-1", "crm:C-1", "crm:C-2"],
        "name": "New Name",
        "email": "x@example.com",
        "phone": "+14155550100",
        "city": "Dallas",
        "updated_at": "2026-03-01T00:00:00Z",
    }


def test_missing_everywhere_is_none():
    (m,) = mc.merge([rec("billing", "B-7", email="only@example.com")])
    assert m == {
        "ids": ["billing:B-7"],
        "name": None,
        "email": "only@example.com",
        "phone": None,
        "city": None,
        "updated_at": "2026-01-01T00:00:00Z",
    }


def test_ties_prefer_crm_then_smaller_id():
    same = (2026, 5, 5)
    records = [
        rec("billing", "B-1", name="Billing Name", email="t@example.com", ts=same),
        rec("crm", "C-9", name="Crm Nine", email="t@example.com", city="Nine", ts=same),
        rec("crm", "C-10", name="Crm Ten", email="t@example.com", ts=same),
    ]
    (m,) = mc.merge(records)
    assert m["name"] == "Crm Ten"
    assert m["city"] == "Nine"


def test_timestamps_compare_as_instants():
    records = [
        rec("crm", "C-1", name="Earlier", email="z@example.com"),
        rec("billing", "B-1", name="Later", email="z@example.com"),
    ]
    records[0]["updated_at"] = datetime(
        2026, 4, 1, 12, 0, tzinfo=timezone(timedelta(hours=5))
    )  # 07:00Z
    records[1]["updated_at"] = datetime(
        2026, 4, 1, 8, 0, tzinfo=timezone(timedelta(hours=-1))
    )  # 09:00Z
    (m,) = mc.merge(records)
    assert m["name"] == "Later"
    assert m["updated_at"] == "2026-04-01T09:00:00Z"


def test_loaders(tmp_path):
    crm = tmp_path / "crm.csv"
    crm.write_text(
        "crm_id,name,email,phone,city,updated_at\n"
        "C-1,Ann,ann@example.com,,Austin,2026-02-11 08:30:00+03:00\n"
        "C-2,Ben,,4155550100,,2026-03-02T00:00:00\n"
    )
    billing = tmp_path / "billing.json"
    billing.write_text(
        json.dumps(
            [
                {
                    "billing_id": "B-1",
                    "full_name": "Cy",
                    "contact": {"email": "cy@example.com"},
                    "address": {},
                    "last_modified": "2026-01-05T00:00:00Z",
                },
                {
                    "billing_id": "B-2",
                    "full_name": "Di",
                    "contact": None,
                    "address": {"city": "Reno"},
                    "last_modified": "2026-01-06T00:00:00+01:00",
                },
            ]
        )
    )
    crm_records = mc.load_crm(crm)
    assert crm_records[0] == {
        "source": "crm",
        "id": "C-1",
        "name": "Ann",
        "email": "ann@example.com",
        "phone": "",
        "city": "Austin",
        "updated_at": datetime(2026, 2, 11, 5, 30, tzinfo=UTC),
    }
    assert crm_records[1]["updated_at"] == datetime(2026, 3, 2, tzinfo=UTC)
    billing_records = mc.load_billing(str(billing))
    assert billing_records[0] == {
        "source": "billing",
        "id": "B-1",
        "name": "Cy",
        "email": "cy@example.com",
        "phone": "",
        "city": "",
        "updated_at": datetime(2026, 1, 5, tzinfo=UTC),
    }
    assert billing_records[1]["email"] == "" and billing_records[1]["city"] == "Reno"
    assert billing_records[1]["updated_at"] == datetime(2026, 1, 5, 23, 0, tzinfo=UTC)


def test_cli_on_sample_data(tmp_path):
    out = tmp_path / "merged.json"
    proc = subprocess.run(
        [
            sys.executable,
            "merge_customers.py",
            "--crm",
            "data/crm.csv",
            "--billing",
            "data/billing.json",
            "--out",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert json.loads(out.read_text()) == [
        {
            "ids": ["billing:B-10", "crm:C-1", "crm:C-3"],
            "name": "Ann M. Lee",
            "email": "annlee@gmail.com",
            "phone": "+14155550100",
            "city": "Oakland",
            "updated_at": "2026-03-04T08:00:00Z",
        },
        {
            "ids": ["billing:B-11", "crm:C-4"],
            "name": "Carla Diaz",
            "email": "carla@diaz.example",
            "phone": "+442079460958",
            "city": "London",
            "updated_at": "2026-03-05T12:00:00Z",
        },
        {
            "ids": ["billing:B-12"],
            "name": "Eve Moss",
            "email": "eve@moss.example",
            "phone": None,
            "city": "Denver",
            "updated_at": "2026-01-05T00:00:00Z",
        },
        {
            "ids": ["crm:C-2"],
            "name": "Bob Stone",
            "email": "bob@stone.example",
            "phone": None,
            "city": "Austin",
            "updated_at": "2026-02-11T05:30:00Z",
        },
        {
            "ids": ["crm:C-5"],
            "name": "Dev Patel",
            "email": "dev@patel.example",
            "phone": None,
            "city": None,
            "updated_at": "2026-03-02T00:00:00Z",
        },
    ]
