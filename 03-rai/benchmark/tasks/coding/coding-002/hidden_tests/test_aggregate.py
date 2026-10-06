import json
import random
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import aggregate as agg
import pytest

ROOT = Path(__file__).resolve().parent.parent


def ev(event_id, user_id, typ, ts, amount=None):
    data = {"event_id": event_id, "user_id": user_id, "type": typ, "ts": ts}
    if amount is not None:
        data["amount"] = amount
    return json.dumps(data)


def test_days_are_utc_calendar_days():
    result = agg.aggregate(
        [
            ev("a", "u1", "view", "2026-03-01T01:30:00+03:00"),  # 2026-02-28T22:30Z
            ev("b", "u1", "view", "2026-02-28T23:59:59-01:00"),  # 2026-03-01T00:59:59Z
            ev("c", "u2", "click", "2026-03-01T00:00:00Z"),
        ]
    )
    assert sorted(result["days"]) == ["2026-02-28", "2026-03-01"]
    assert result["days"]["2026-02-28"]["events"] == 1
    assert result["days"]["2026-03-01"] == {
        "events": 2,
        "users": 2,
        "purchases": 0,
        "refunds": 0,
        "revenue": "0.00",
    }


def test_revenue_is_exact_and_rounds_half_up():
    result = agg.aggregate(
        [
            ev("a", "u1", "purchase", "2026-03-01T10:00:00Z", 0.125),
            ev("b", "u2", "purchase", "2026-03-02T10:00:00Z", 1.005),
            ev("c", "u3", "purchase", "2026-03-03T10:00:00Z", 0.1),
            ev("d", "u3", "purchase", "2026-03-03T11:00:00Z", 0.2),
            ev("e", "u3", "refund", "2026-03-03T12:00:00Z", 0.3),
        ]
    )
    assert result["days"]["2026-03-01"]["revenue"] == "0.13"
    assert result["days"]["2026-03-02"]["revenue"] == "1.01"
    assert result["days"]["2026-03-03"]["revenue"] == "0.00"
    assert result["days"]["2026-03-03"]["purchases"] == 2
    assert result["days"]["2026-03-03"]["refunds"] == 1
    assert result["users"]["u1"]["revenue"] == "0.13"


def test_refund_only_day_is_negative():
    result = agg.aggregate(
        [
            ev("a", "u1", "purchase", "2026-03-01T10:00:00Z", 5),
            ev("b", "u1", "refund", "2026-03-02T10:00:00Z", 5),
        ]
    )
    assert result["days"]["2026-03-02"]["revenue"] == "-5.00"
    assert result["users"]["u1"]["revenue"] == "0.00"


@pytest.mark.parametrize(
    "line",
    [
        "not json",
        "[1, 2, 3]",
        '"just a string"',
        json.dumps({"user_id": "u1", "type": "view", "ts": "2026-03-01T10:00:00Z"}),
        json.dumps(
            {
                "event_id": "",
                "user_id": "u1",
                "type": "view",
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": 7,
                "user_id": "u1",
                "type": "view",
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": 12,
                "type": "view",
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "signup",
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": ["view"],
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "view",
                "ts": "2026-03-01T10:00:00",
            }
        ),
        json.dumps(
            {"event_id": "x", "user_id": "u1", "type": "view", "ts": "2026-03-01"}
        ),
        json.dumps(
            {"event_id": "x", "user_id": "u1", "type": "view", "ts": "yesterday"}
        ),
        json.dumps(
            {"event_id": "x", "user_id": "u1", "type": "view", "ts": 1772359200}
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "purchase",
                "ts": "2026-03-01T10:00:00Z",
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "purchase",
                "ts": "2026-03-01T10:00:00Z",
                "amount": True,
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "purchase",
                "ts": "2026-03-01T10:00:00Z",
                "amount": 0,
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "refund",
                "ts": "2026-03-01T10:00:00Z",
                "amount": -3,
            }
        ),
        json.dumps(
            {
                "event_id": "x",
                "user_id": "u1",
                "type": "purchase",
                "ts": "2026-03-01T10:00:00Z",
                "amount": "9.99",
            }
        ),
    ],
)
def test_invalid_lines_are_counted_and_ignored(line):
    result = agg.aggregate([line, ev("ok", "u9", "view", "2026-03-05T10:00:00Z")])
    assert result["invalid_lines"] == 1
    assert result["duplicates"] == 0
    assert list(result["days"]) == ["2026-03-05"]
    assert list(result["users"]) == ["u9"]


def test_amount_ignored_on_non_money_events():
    result = agg.aggregate(
        [
            json.dumps(
                {
                    "event_id": "a",
                    "user_id": "u1",
                    "type": "view",
                    "ts": "2026-03-01T10:00:00Z",
                    "amount": "n/a",
                }
            )
        ]
    )
    assert result["invalid_lines"] == 0
    assert result["days"]["2026-03-01"]["revenue"] == "0.00"


def test_blank_lines_are_skipped():
    result = agg.aggregate(
        ["", "   ", "\n", ev("a", "u1", "view", "2026-03-01T10:00:00Z") + "\n"]
    )
    assert result["invalid_lines"] == 0
    assert result["days"]["2026-03-01"]["events"] == 1


def test_duplicates_count_once_and_invalid_first_copy_does_not_block():
    result = agg.aggregate(
        [
            ev("a", "u1", "purchase", "2026-03-01T10:00:00Z", 10),
            ev("a", "u1", "purchase", "2026-03-01T10:00:00Z", 10),
            ev("a", "u2", "view", "2026-03-02T10:00:00Z"),
            json.dumps(
                {
                    "event_id": "b",
                    "user_id": "u1",
                    "type": "purchase",
                    "ts": "2026-03-01T11:00:00Z",
                }
            ),
            ev("b", "u1", "purchase", "2026-03-01T11:00:00Z", 2.5),
        ]
    )
    assert result["duplicates"] == 2
    assert result["invalid_lines"] == 1
    assert result["days"] == {
        "2026-03-01": {
            "events": 2,
            "users": 1,
            "purchases": 2,
            "refunds": 0,
            "revenue": "12.50",
        }
    }
    assert list(result["users"]) == ["u1"]


def test_first_and_last_seen_compare_instants_not_strings():
    result = agg.aggregate(
        [
            ev("a", "u1", "view", "2026-03-01T05:00:00Z"),
            ev("b", "u1", "view", "2026-03-01T09:00:00+05:00"),  # 04:00Z, earliest
            ev(
                "c", "u1", "view", "2026-03-01T22:00:00-03:00"
            ),  # 2026-03-02T01:00Z, latest
            ev("d", "u1", "view", "2026-03-02T00:30:00Z"),
        ]
    )
    user = result["users"]["u1"]
    assert user == {
        "events": 4,
        "revenue": "0.00",
        "first_seen": "2026-03-01T04:00:00Z",
        "last_seen": "2026-03-02T01:00:00Z",
    }


def _reference(events):
    """Independent expected values for generated, always-valid events."""
    days, users, seen, dups = {}, {}, set(), 0
    for e in events:
        if e["event_id"] in seen:
            dups += 1
            continue
        seen.add(e["event_id"])
        when = datetime.fromisoformat(e["ts"]).astimezone(timezone.utc)
        day = days.setdefault(
            when.date().isoformat(),
            {
                "events": 0,
                "users": set(),
                "purchases": 0,
                "refunds": 0,
                "revenue": Decimal(0),
            },
        )
        user = users.setdefault(
            e["user_id"], {"events": 0, "revenue": Decimal(0), "times": []}
        )
        sign = {"purchase": 1, "refund": -1}.get(e["type"], 0)
        amount = Decimal(str(e.get("amount", 0))) * sign
        day["events"] += 1
        day["users"].add(e["user_id"])
        day["purchases"] += e["type"] == "purchase"
        day["refunds"] += e["type"] == "refund"
        day["revenue"] += amount
        user["events"] += 1
        user["revenue"] += amount
        user["times"].append(when)
    q = lambda d: str(d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    fmt = lambda t: t.strftime("%Y-%m-%dT%H:%M:%SZ")
    return (
        {
            k: {
                "events": v["events"],
                "users": len(v["users"]),
                "purchases": v["purchases"],
                "refunds": v["refunds"],
                "revenue": q(v["revenue"]),
            }
            for k, v in days.items()
        },
        {
            k: {
                "events": v["events"],
                "revenue": q(v["revenue"]),
                "first_seen": fmt(min(v["times"])),
                "last_seen": fmt(max(v["times"])),
            }
            for k, v in users.items()
        },
        dups,
    )


@pytest.mark.parametrize("seed", [3, 17, 2026])
def test_generated_stream_matches_reference(seed):
    rng = random.Random(seed)
    start = datetime(2026, 3, 1, tzinfo=timezone.utc)
    events = []
    for i in range(400):
        offset = timedelta(hours=rng.choice([-5, -3, 0, 1, 3, 5.5, 9]))
        when = (start + timedelta(minutes=rng.randrange(0, 6 * 24 * 60))).astimezone(
            timezone(offset)
        )
        typ = rng.choice(["view", "view", "click", "purchase", "refund"])
        event = {
            "event_id": f"e{rng.randrange(0, 350)}",
            "user_id": f"u{rng.randrange(0, 12)}",
            "type": typ,
            "ts": when.isoformat(),
        }
        if typ in ("purchase", "refund"):
            event["amount"] = round(rng.uniform(0.01, 80), rng.choice([0, 1, 2, 3]))
            if event["amount"] <= 0:
                event["amount"] = 1
        events.append(event)
    lines = [json.dumps(e) for e in events]
    lines.insert(50, "{broken")
    lines.insert(120, "")
    days, users, dups = _reference(events)
    result = agg.aggregate(lines)
    assert result["invalid_lines"] == 1
    assert result["duplicates"] == dups
    assert result["days"] == days
    assert result["users"] == users


def test_cli_writes_sorted_json_and_prints_summary(tmp_path):
    src = tmp_path / "events.jsonl"
    src.write_text(
        "\n".join(
            [
                ev("a", "u2", "purchase", "2026-03-01T10:00:00Z", 3),
                ev("a", "u2", "purchase", "2026-03-01T10:00:00Z", 3),
                "oops",
                ev("b", "u1", "view", "2026-03-01T11:00:00+01:00"),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, "aggregate.py", str(src), "--out", str(out)],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "events=2 invalid=1 duplicates=1"
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["days"]["2026-03-01"] == {
        "events": 2,
        "users": 2,
        "purchases": 1,
        "refunds": 0,
        "revenue": "3.00",
    }
    assert out.read_text(encoding="utf-8").rstrip("\n") == json.dumps(
        data, indent=2, sort_keys=True
    )
