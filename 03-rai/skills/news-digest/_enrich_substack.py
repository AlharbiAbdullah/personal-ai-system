#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "beautifulsoup4>=4.12"]
# ///
"""Substack article-body enrichment.

Substack collection runs via Chrome on /inbox and only captures URL+title from the
listing — no body, no engagement signal. This script is a post-collection step:
fetches each article URL in parallel, extracts body + engagement (likes,
comments_count) from the article HTML, writes the enriched fields back into
substack.json.

Without this step, all Substack items score 0 in present_v5.py (empty subtitle
→ zero universal axes) and never make it into the digest.

Usage:
    python _enrich_substack.py <path/to/substack.json>
    python _enrich_substack.py --date 2026-05-08
    python _enrich_substack.py            # auto-detect latest .runs/<date>/substack.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/120.0.0.0 Safari/537.36")
TIMEOUT = httpx.Timeout(20.0, connect=10.0)
LIMITS = httpx.Limits(max_connections=20, max_keepalive_connections=10)
BODY_CAP = 5000

BODY_SELECTORS = [
    ("div", {"class": "available-content"}),
    ("div", {"class": "markup"}),
    ("div", {"class": "post-content"}),
    ("div", {"class": "body"}),
    ("article", None),
]


def extract_body(soup: BeautifulSoup) -> str:
    for tag, attrs in BODY_SELECTORS:
        node = soup.find(tag, attrs) if attrs else soup.find(tag)
        if not node:
            continue
        for noise in node.find_all(["script", "style", "nav", "aside", "footer", "form"]):
            noise.decompose()
        text = node.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        if len(text) >= 60:
            return text[:BODY_CAP]
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:BODY_CAP] if len(text) >= 60 else ""


_NUM_RE = re.compile(r"(\d[\d,]*)")


def _to_int(s: str | None) -> int:
    if not s:
        return 0
    m = _NUM_RE.search(s)
    if not m:
        return 0
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return 0


def extract_engagement(soup: BeautifulSoup) -> tuple[int, int, int]:
    likes = 0
    restacks = 0
    comments = 0
    for sel in [".like-button .label", "button[aria-label*='Like'] .label",
                "[data-component-name='LikeButton'] .label"]:
        node = soup.select_one(sel)
        if node:
            likes = _to_int(node.get_text())
            if likes:
                break
    for sel in ["[data-component-name='RestackButton'] .label",
                "[aria-label*='Restack'] .label", ".restack-button .label"]:
        node = soup.select_one(sel)
        if node:
            restacks = _to_int(node.get_text())
            if restacks:
                break
    for sel in [".comments-link .label", "[data-component-name='CommentsButton'] .label",
                ".comment-count"]:
        node = soup.select_one(sel)
        if node:
            comments = _to_int(node.get_text())
            if comments:
                break
    return likes, restacks, comments


def extract_pub_date(soup: BeautifulSoup) -> str | None:
    """ISO YYYY-MM-DD from JSON-LD datePublished, article:published_time meta, or <time datetime>."""
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(s.string or "")
        except (json.JSONDecodeError, TypeError):
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if not isinstance(obj, dict):
                continue
            d = obj.get("datePublished") or next(
                (g.get("datePublished") for g in obj.get("@graph", [])
                 if isinstance(g, dict) and g.get("datePublished")), None)
            if d:
                return str(d)[:10]
    m = (soup.find("meta", attrs={"property": "article:published_time"})
         or soup.find("meta", attrs={"name": "article:published_time"}))
    if m and m.get("content"):
        return m["content"][:10]
    t = soup.find("time", attrs={"datetime": True})
    if t:
        return t["datetime"][:10]
    return None


async def fetch_one(client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore):
    async with sem:
        try:
            r = await client.get(url, follow_redirects=True)
            if r.status_code >= 400:
                return {"_error": f"HTTP {r.status_code}"}
            soup = BeautifulSoup(r.text, "html.parser")
            body = extract_body(soup)
            likes, restacks, comments = extract_engagement(soup)
            return {
                "body": body,
                "likes": likes,
                "restacks": restacks,
                "comments_count": comments,
                "date": extract_pub_date(soup),
            }
        except (httpx.RequestError, httpx.TimeoutException) as e:
            return {"_error": f"{type(e).__name__}: {e}"}
        except Exception as e:
            return {"_error": f"parse: {type(e).__name__}: {e}"}


async def enrich(items: list[dict], log_path: Path) -> list[dict]:
    sem = asyncio.Semaphore(15)
    headers = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml"}
    async with httpx.AsyncClient(headers=headers, timeout=TIMEOUT, limits=LIMITS) as client:
        tasks = []
        for it in items:
            url = (it.get("url") or "").strip()
            if not url or not url.startswith("http"):
                tasks.append(asyncio.sleep(0, result={"_error": "no_url"}))
            else:
                tasks.append(fetch_one(client, url, sem))
        results = await asyncio.gather(*tasks, return_exceptions=False)
    fails = []
    out = []
    for it, res in zip(items, results):
        merged = dict(it)
        if str(merged.get("date")) in ("None", ""):  # collector emits the string "None"
            merged["date"] = None
        if "_error" in res:
            fails.append((it.get("url", "?"), res["_error"]))
            out.append(merged)
            continue
        merged.update({k: v for k, v in res.items() if not k.startswith("_")})
        out.append(merged)
    if fails:
        with open(log_path, "w") as f:
            for url, err in fails:
                f.write(f"{url}\t{err}\n")
    return out


def find_default_path() -> Path | None:
    runs = Path(__file__).parent / ".runs"
    if not runs.exists():
        return None
    dated = sorted([p for p in runs.iterdir() if p.is_dir()], reverse=True)
    for d in dated:
        candidate = d / "substack.json"
        if candidate.exists():
            return candidate
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="path to substack.json")
    ap.add_argument("--date", help="run date (e.g. 2026-05-08)")
    args = ap.parse_args()

    if args.path:
        p = Path(args.path).expanduser().resolve()
    elif args.date:
        p = Path(__file__).parent / ".runs" / args.date / "substack.json"
    else:
        p = find_default_path()
        if p is None:
            print("no substack.json found; pass --date or path", file=sys.stderr)
            sys.exit(2)

    if not p.exists():
        print(f"file not found: {p}", file=sys.stderr)
        sys.exit(2)

    with open(p) as f:
        items = json.load(f)
    if not isinstance(items, list):
        print(f"expected JSON list, got {type(items).__name__}", file=sys.stderr)
        sys.exit(2)

    print(f"enriching {len(items)} substack items from {p} ...")
    t0 = time.time()
    enriched = asyncio.run(enrich(items, p.parent / "substack_enrich.log"))
    elapsed = time.time() - t0

    body_count = sum(1 for it in enriched if (it.get("body") or "").strip())
    eng_count = sum(1 for it in enriched if any(it.get(k, 0) for k in ("likes", "restacks", "comments_count")))
    date_count = sum(1 for it in enriched if it.get("date"))
    fails = len(items) - body_count
    print(f"  bodies extracted: {body_count}/{len(items)}")
    print(f"  engagement signals: {eng_count}/{len(items)}")
    print(f"  dates extracted: {date_count}/{len(items)}")
    print(f"  fetch failures: {fails}")
    print(f"  elapsed: {elapsed:.1f}s")

    with open(p, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
