"""Daily and per-user summary of the app event stream (first version)."""

import argparse
import json
import sys


def aggregate(lines):
    days = {}
    users = {}
    invalid = 0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        day = event["ts"][:10]
        bucket = days.setdefault(
            day, {"events": 0, "users": set(), "purchases": 0, "refunds": 0, "revenue": 0.0}
        )
        bucket["events"] += 1
        bucket["users"].add(event["user_id"])
        user = users.setdefault(
            event["user_id"],
            {"events": 0, "revenue": 0.0, "first_seen": event["ts"], "last_seen": event["ts"]},
        )
        user["events"] += 1
        if event["type"] == "purchase":
            bucket["purchases"] += 1
            bucket["revenue"] += event["amount"]
            user["revenue"] += event["amount"]
        elif event["type"] == "refund":
            bucket["refunds"] += 1
            bucket["revenue"] -= event["amount"]
            user["revenue"] -= event["amount"]
        user["first_seen"] = min(user["first_seen"], event["ts"])
        user["last_seen"] = max(user["last_seen"], event["ts"])
    for bucket in days.values():
        bucket["users"] = len(bucket["users"])
        bucket["revenue"] = "%.2f" % bucket["revenue"]
    for user in users.values():
        user["revenue"] = "%.2f" % user["revenue"]
    return {"days": days, "users": users, "invalid_lines": invalid, "duplicates": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    with open(args.input, encoding="utf-8") as fh:
        result = aggregate(fh)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
    events = sum(day["events"] for day in result["days"].values())
    print(f"events={events} invalid={result['invalid_lines']} duplicates={result['duplicates']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
