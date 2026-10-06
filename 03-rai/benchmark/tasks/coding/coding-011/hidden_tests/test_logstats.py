import random
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import logstats
import pytest

ROOT = Path(__file__).resolve().parent.parent
UTC = timezone.utc


def line(
    ts="10/Mar/2026:13:55:36 +0300",
    req="GET /api/users/123 HTTP/1.1",
    status="200",
    size="512",
    secs="0.123",
    user="-",
    ip="203.0.113.9",
):
    return f'{ip} - {user} [{ts}] "{req}" {status} {size} {secs}'


def test_parse_line_fields():
    rec = logstats.parse_line(
        line(req="GET /api/users/123?verbose=1#top HTTP/1.1") + "\n"
    )
    assert rec == {
        "ip": "203.0.113.9",
        "user": None,
        "ts": datetime(2026, 3, 10, 13, 55, 36, tzinfo=timezone(timedelta(hours=3))),
        "method": "GET",
        "path": "/api/users/123",
        "status": 200,
        "bytes": 512,
        "ms": 123,
    }
    assert rec["ts"] == datetime(2026, 3, 10, 10, 55, 36, tzinfo=UTC)


def test_parse_line_user_and_dash_bytes():
    rec = logstats.parse_line(line(user="alice", size="-", status="304"))
    assert rec["user"] == "alice"
    assert rec["bytes"] == 0
    assert rec["status"] == 304


@pytest.mark.parametrize(
    "secs,ms",
    [
        ("1.005", 1005),
        ("0.0004", 0),
        ("2", 2000),
        ("0.29", 290),
        ("0.0016", 2),
        ("12.3456", 12346),
    ],
)
def test_duration_rounds_to_nearest_ms(secs, ms):
    assert logstats.parse_line(line(secs=secs))["ms"] == ms


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "garbage line from a crashed worker",
        line(status="abc"),
        line(status="20"),
        line(size="12k"),
        line(secs="fast"),
        line(secs="-1.0"),
        line(ts="32/Mar/2026:13:55:36 +0300"),
        line(ts="10/Foo/2026:13:55:36 +0300"),
        line(ts="10/Mar/2026:13:55:36"),
        line(req="GET /only-two"),
        line(req="GET /a HTTP/1.1 extra"),
        line() + " trailing",
        line().replace('"', ""),
    ],
)
def test_malformed_lines_return_none(bad):
    assert logstats.parse_line(bad) is None


@pytest.mark.parametrize(
    "path,expected",
    [
        ("/", "/"),
        ("/health", "/health"),
        ("/api/users/123", "/api/users/:id"),
        ("/api/users/123/", "/api/users/:id"),
        ("/api/users/", "/api/users"),
        ("/api//users///42", "/api/users/:id"),
        (
            "/api/v2/items/9b2f6c1e-0d6a-4c8e-9F51-3A7E2D1C0B4F/parts/7",
            "/api/v2/items/:uuid/parts/:id",
        ),
        (
            "/api/items/9b2f6c1e0d6a4c8e9f513a7e2d1c0b4f",
            "/api/items/9b2f6c1e0d6a4c8e9f513a7e2d1c0b4f",
        ),
        ("/api/items/12ab", "/api/items/12ab"),
        ("/Static/Logo.PNG", "/Static/Logo.PNG"),
    ],
)
def test_normalize_path(path, expected):
    assert logstats.normalize_path(path) == expected


def nearest_rank(values, p):
    ordered = sorted(values)
    return ordered[(p * len(ordered) + 99) // 100 - 1]


def test_summarize_hand_made():
    durations = [
        "0.010",
        "0.020",
        "0.030",
        "0.040",
        "0.050",
        "0.060",
        "0.070",
        "0.080",
        "0.090",
        "1.000",
    ]
    lines = [
        line(
            req=f"GET /api/users/{i} HTTP/1.1",
            secs=s,
            status="500" if i < 3 else "200",
            size=str(i),
        )
        for i, s in enumerate(durations)
    ]
    lines += [
        line(req="POST /api/users HTTP/1.1", secs="0.300", status="503", size="-"),
        "",
        "nonsense",
        "  ",
    ]
    result = logstats.summarize(lines)
    assert result["malformed"] == 1
    assert result["endpoints"] == {
        "GET /api/users/:id": {
            "count": 10,
            "errors": 3,
            "error_rate": 0.3,
            "p50": 50,
            "p95": 1000,
            "max": 1000,
            "bytes": 45,
        },
        "POST /api/users": {
            "count": 1,
            "errors": 1,
            "error_rate": 1.0,
            "p50": 300,
            "p95": 300,
            "max": 300,
            "bytes": 0,
        },
    }


def test_error_rate_rounding_and_4xx_not_errors():
    lines = [line(status=s) for s in ["500", "404", "200"]]
    stats = logstats.summarize(lines)["endpoints"]["GET /api/users/:id"]
    assert stats["errors"] == 1
    assert stats["error_rate"] == 0.3333


def test_window_filter_compares_instants():
    lines = [
        line(ts="10/Mar/2026:12:59:59 +0300"),  # 09:59:59Z
        line(ts="10/Mar/2026:10:00:00 +0000"),  # 10:00:00Z  first inside
        line(ts="10/Mar/2026:06:30:00 -0400"),  # 10:30:00Z  inside
        line(ts="10/Mar/2026:14:00:00 +0300"),  # 11:00:00Z  end, excluded
        "broken",
    ]
    start = datetime(2026, 3, 10, 10, 0, tzinfo=UTC)
    end = datetime(2026, 3, 10, 11, 0, tzinfo=UTC)
    result = logstats.summarize(lines, start=start, end=end)
    assert result["endpoints"]["GET /api/users/:id"]["count"] == 2
    assert result["malformed"] == 1
    assert (
        logstats.summarize(lines, start=start)["endpoints"]["GET /api/users/:id"][
            "count"
        ]
        == 3
    )
    assert (
        logstats.summarize(lines, end=end)["endpoints"]["GET /api/users/:id"]["count"]
        == 3
    )
    assert logstats.summarize(lines, start=end + timedelta(days=1))["endpoints"] == {}


@pytest.mark.parametrize("seed", [8, 21, 1999])
def test_generated_logs_match_reference(seed):
    rng = random.Random(seed)
    paths = [
        "/api/users/{n}",
        "/api/orders/{n}/items",
        "/health",
        "/api/search",
        "/api/users/{n}/avatar/",
    ]
    expected = defaultdict(list)
    lines = []
    base = datetime(2026, 3, 1, tzinfo=UTC)
    for _ in range(600):
        method = rng.choice(["GET", "GET", "POST", "DELETE"])
        template = rng.choice(paths)
        path = template.format(n=rng.randrange(1, 10**6))
        status = rng.choice([200, 200, 200, 201, 301, 404, 500, 502, 503])
        ms = rng.randrange(0, 5000)
        size = rng.randrange(0, 10**5)
        when = (base + timedelta(seconds=rng.randrange(0, 86400 * 3))).astimezone(
            timezone(timedelta(hours=rng.choice([-7, 0, 3, 5])))
        )
        query = "?q=1" if rng.random() < 0.2 else ""
        lines.append(
            line(
                ts=when.strftime("%d/%b/%Y:%H:%M:%S %z"),
                req=f"{method} {path}{query} HTTP/1.1",
                status=str(status),
                size=str(size),
                secs=f"{ms / 1000:.3f}",
            )
        )
        key = f"{method} " + template.replace("{n}", ":id").rstrip("/")
        expected[key].append((ms, status, size))
        if rng.random() < 0.05:
            lines.append("corrupted " + str(rng.random()))
    result = logstats.summarize(lines)
    assert set(result["endpoints"]) == set(expected)
    for key, rows in expected.items():
        ms = [r[0] for r in rows]
        errors = sum(r[1] >= 500 for r in rows)
        assert result["endpoints"][key] == {
            "count": len(rows),
            "errors": errors,
            "error_rate": round(errors / len(rows), 4),
            "p50": nearest_rank(ms, 50),
            "p95": nearest_rank(ms, 95),
            "max": max(ms),
            "bytes": sum(r[2] for r in rows),
        }
    assert result["malformed"] == sum(1 for ln in lines if ln.startswith("corrupted"))


def test_cli_top_and_window(tmp_path):
    lines = (
        [line(req="GET /a/1 HTTP/1.1", secs="0.100", status="500")] * 1
        + [line(req="GET /a/2 HTTP/1.1", secs="0.200")] * 7
        + [line(req="GET /b HTTP/1.1", secs="0.050")] * 8
        + [line(req="GET /c HTTP/1.1", secs="0.300", status="502")] * 2
        + [line(req="GET /d HTTP/1.1", ts="11/Mar/2026:13:55:36 +0300")] * 30
        + ["junk", "more junk"]
    )
    log = tmp_path / "access.log"
    log.write_text("\n".join(lines) + "\n")
    proc = subprocess.run(
        [
            sys.executable,
            "logstats.py",
            str(log),
            "--top",
            "3",
            "--end",
            "2026-03-11T00:00:00+00:00",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "8\t200\t12.5%\tGET /a/:id",
        "8\t50\t0.0%\tGET /b",
        "2\t300\t100.0%\tGET /c",
        "malformed=2",
    ]
    proc = subprocess.run(
        [
            sys.executable,
            "logstats.py",
            str(log),
            "--start",
            "2026-03-11T00:00:00+00:00",
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )
    assert proc.stdout.splitlines() == ["30\t123\t0.0%\tGET /d", "malformed=2"]
