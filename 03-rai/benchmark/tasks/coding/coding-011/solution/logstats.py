"""Per-endpoint latency and error stats from API gateway access logs."""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime

LINE_RE = re.compile(
    r'(?P<ip>\S+) \S+ (?P<user>\S+) \[(?P<ts>[^\]]+)\] "(?P<request>[^"]*)" '
    r"(?P<status>[0-9]{3}) (?P<bytes>[0-9]+|-) (?P<seconds>[0-9]+(?:\.[0-9]+)?)"
)
UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
DIGITS_RE = re.compile(r"[0-9]+")
TS_FORMAT = "%d/%b/%Y:%H:%M:%S %z"


def parse_line(line: str) -> dict | None:
    match = LINE_RE.fullmatch(line.rstrip("\r\n"))
    if match is None:
        return None
    parts = match["request"].split(" ")
    if len(parts) != 3 or not all(parts):
        return None
    method, target, _protocol = parts
    try:
        ts = datetime.strptime(match["ts"], TS_FORMAT)  # noqa: DTZ007 - TS_FORMAT ends in %z
    except ValueError:
        return None
    return {
        "ip": match["ip"],
        "user": None if match["user"] == "-" else match["user"],
        "ts": ts,
        "method": method,
        "path": re.split(r"[?#]", target, maxsplit=1)[0],
        "status": int(match["status"]),
        "bytes": 0 if match["bytes"] == "-" else int(match["bytes"]),
        "ms": round(float(match["seconds"]) * 1000),
    }


def normalize_path(path: str) -> str:
    segments = []
    for segment in path.split("/"):
        if not segment:
            continue
        if DIGITS_RE.fullmatch(segment):
            segment = ":id"
        elif UUID_RE.fullmatch(segment):
            segment = ":uuid"
        segments.append(segment)
    return "/" + "/".join(segments)


def _nearest_rank(ordered: list[int], p: int) -> int:
    return ordered[(p * len(ordered) + 99) // 100 - 1]


def summarize(
    lines: Iterable[str], start: datetime | None = None, end: datetime | None = None
) -> dict:
    groups: dict[str, list[dict]] = defaultdict(list)
    malformed = 0
    for line in lines:
        if not line.strip():
            continue
        record = parse_line(line)
        if record is None:
            malformed += 1
            continue
        if (start is not None and record["ts"] < start) or (
            end is not None and record["ts"] >= end
        ):
            continue
        groups[f"{record['method']} {normalize_path(record['path'])}"].append(record)
    endpoints = {}
    for key, records in groups.items():
        ms = sorted(r["ms"] for r in records)
        errors = sum(r["status"] >= 500 for r in records)
        endpoints[key] = {
            "count": len(records),
            "errors": errors,
            "error_rate": round(errors / len(records), 4),
            "p50": _nearest_rank(ms, 50),
            "p95": _nearest_rank(ms, 95),
            "max": ms[-1],
            "bytes": sum(r["bytes"] for r in records),
        }
    return {"endpoints": endpoints, "malformed": malformed}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("logfile")
    parser.add_argument("--top", type=int, default=10)
    parser.add_argument("--start", type=datetime.fromisoformat)
    parser.add_argument("--end", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    with open(args.logfile, encoding="utf-8", errors="replace") as fh:
        result = summarize(fh, start=args.start, end=args.end)
    ranked = sorted(
        result["endpoints"].items(), key=lambda kv: (-kv[1]["count"], kv[0])
    )
    for key, stats in ranked[: args.top]:
        percent = 100 * stats["errors"] / stats["count"]
        print(f"{stats['count']}\t{stats['p95']}\t{percent:.1f}%\t{key}")
    print(f"malformed={result['malformed']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
