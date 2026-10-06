"""Merge CRM and billing customer records into one golden record per person."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}
SOURCE_RANK = {"crm": 0, "billing": 1}
FIELDS = ("name", "email", "phone", "city")


def normalize_email(raw: str | None) -> str | None:
    value = (raw or "").strip().lower()
    if value.count("@") != 1:
        return None
    local, domain = value.split("@")
    local = local.split("+", 1)[0]
    if domain in GMAIL_DOMAINS:
        local, domain = local.replace(".", ""), "gmail.com"
    if not local or not domain:
        return None
    return f"{local}@{domain}"


def normalize_phone(raw: str | None) -> str | None:
    digits = re.sub(r"[^0-9]", "", raw or "")
    digits = digits.removeprefix("00")
    if len(digits) == 10:
        digits = "1" + digits
    if not 11 <= len(digits) <= 15:
        return None
    return "+" + digits


def _timestamp(raw: str) -> datetime:
    value = datetime.fromisoformat(raw.strip())
    if value.utcoffset() is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _record(source: str, id_: str, name, email, phone, city, updated_at: str) -> dict:
    return {
        "source": source,
        "id": str(id_),
        "name": name or "",
        "email": email or "",
        "phone": phone or "",
        "city": city or "",
        "updated_at": _timestamp(updated_at),
    }


def load_crm(path: str | Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        return [
            _record(
                "crm",
                r["crm_id"],
                r.get("name"),
                r.get("email"),
                r.get("phone"),
                r.get("city"),
                r["updated_at"],
            )
            for r in csv.DictReader(fh)
        ]


def load_billing(path: str | Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        rows = json.load(fh)
    records = []
    for r in rows:
        contact, address = r.get("contact") or {}, r.get("address") or {}
        records.append(
            _record(
                "billing",
                r["billing_id"],
                r.get("full_name"),
                contact.get("email"),
                contact.get("phone"),
                address.get("city"),
                r["last_modified"],
            )
        )
    return records


def _clusters(records: list[dict]) -> list[list[int]]:
    parent = list(range(len(records)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_seen: dict[tuple[str, str], int] = {}
    for i, rec in enumerate(records):
        for key in (
            ("email", normalize_email(rec["email"])),
            ("phone", normalize_phone(rec["phone"])),
        ):
            if key[1] is None:
                continue
            if key in first_seen:
                parent[find(i)] = find(first_seen[key])
            else:
                first_seen[key] = i
    groups: dict[int, list[int]] = {}
    for i in range(len(records)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def _value(rec: dict, field: str) -> str | None:
    if field == "email":
        return normalize_email(rec["email"])
    if field == "phone":
        return normalize_phone(rec["phone"])
    return rec[field].strip() or None


def _priority(rec: dict) -> tuple:
    return (-rec["updated_at"].timestamp(), SOURCE_RANK[rec["source"]], rec["id"])


def merge(records: list[dict]) -> list[dict]:
    merged = []
    for members in _clusters(records):
        group = sorted((records[i] for i in members), key=_priority)
        out: dict = {"ids": sorted(f"{r['source']}:{r['id']}" for r in group)}
        for field in FIELDS:
            out[field] = next(
                (v for r in group if (v := _value(r, field)) is not None), None
            )
        out["updated_at"] = (
            group[0]["updated_at"]
            .astimezone(timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ")
        )
        merged.append(out)
    return sorted(merged, key=lambda m: m["ids"][0])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--crm", required=True)
    parser.add_argument("--billing", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    merged = merge(load_crm(args.crm) + load_billing(args.billing))
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(merged, fh, indent=2)
    print(f"records={sum(len(m['ids']) for m in merged)} customers={len(merged)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
