#!/usr/bin/env python3
"""Weighted random pick of an archived lesson for /retain. Stdlib only.

Weight = days since last rehearsal (never = NEVER_DAYS), x1.5 if last score <= 1,
x0.5 if the last two scores were 3. Output: topic, lesson path (relative to ~/helm),
last date, last score, weight. Tab-separated.
"""
import argparse
import json
import random
import re
from datetime import date
from pathlib import Path

HELM = Path.home() / "helm"
ARCHIVE = HELM / "13-archive" / "learning"
POOL = [
    "python-fundamentals",
    "python-programming-fundamentals",
    "systems-thinking",
    "claude-code-mastery",
    "personal-ai-infrastructure",
]
LEDGER = HELM / "06-learning" / "retention" / "ledger.jsonl"
LESSON_RE = re.compile(r"^(Lesson \d+|\d{2,3}) - ")
NEVER_DAYS = 180


def lessons():
    for topic in POOL:
        for p in sorted((ARCHIVE / topic).rglob("*.md")):
            if LESSON_RE.match(p.name) and not p.name.startswith("00 "):
                yield topic, p.relative_to(HELM).as_posix()


def history():
    h = {}
    if LEDGER.exists():
        for line in LEDGER.read_text().splitlines():
            if line.strip():
                r = json.loads(line)
                h.setdefault(r["lesson"], []).append(r)
    for entries in h.values():
        entries.sort(key=lambda r: r["date"])
    return h


def weigh(entries, today):
    if not entries:
        return NEVER_DAYS, "-", "-"
    last = entries[-1]
    w = max((today - date.fromisoformat(last["date"])).days, 1)
    scores = [r["score"] for r in entries]
    if scores[-1] <= 1:
        w *= 1.5
    if scores[-2:] == [3, 3]:
        w *= 0.5
    return w, last["date"], last["score"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--topic", help="substring filter on topic name")
    ap.add_argument("--lesson", help="substring filter on lesson filename")
    ap.add_argument("--list", action="store_true", help="print the weighted table")
    a = ap.parse_args()

    today = date.today()
    hist = history()
    rows = []
    for topic, rel in lessons():
        if a.topic and a.topic.lower() not in topic.lower():
            continue
        if a.lesson and a.lesson.lower() not in Path(rel).name.lower():
            continue
        w, last, score = weigh(hist.get(rel, []), today)
        rows.append((topic, rel, last, score, w))
    if not rows:
        raise SystemExit("no lesson matches the filter")

    if a.list:
        for topic, rel, last, score, w in sorted(rows, key=lambda r: -r[4]):
            print(f"{w:>7.1f}\t{last}\t{score}\t{topic}\t{rel}")
        return
    topic, rel, last, score, w = random.choices(rows, weights=[r[4] for r in rows])[0]
    print(f"{topic}\t{rel}\t{last}\t{score}\t{w:.1f}")


if __name__ == "__main__":
    main()
