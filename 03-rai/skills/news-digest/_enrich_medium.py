#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx>=0.27", "beautifulsoup4>=4.12"]
# ///
"""Medium article-body enrichment.

Medium collection runs via Chrome on the homepage and only captures URL+title
+ optional subtitle. This script fetches each article URL, extracts body text
and clap count from the article HTML, writes back into medium.json.

Without this step, Medium items score near 0 (subtitle is short and engagement
is unavailable) and rarely make it into the digest.

Note: Medium serves paywalled content for many articles. When paywalled, only
the preview portion is extracted — better than nothing.

Usage:
    python _enrich_medium.py <path/to/medium.json>
    python _enrich_medium.py --date 2026-05-08
    python _enrich_medium.py            # auto-detect latest .runs/<date>/medium.json
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
LIMITS = httpx.Limits(max_connections=15, max_keepalive_connections=8)
BODY_CAP = 5000

BODY_SELECTORS = [
    ("article", None),
    ("section", {"data-field": "body"}),
    ("div", {"data-testid": "storyContent"}),
]


def extract_body(soup: BeautifulSoup) -> str:
    for tag, attrs in BODY_SELECTORS:
        node = soup.find(tag, attrs) if attrs else soup.find(tag)
        if not node:
            continue
        for noise in node.find_all(["script", "style", "nav", "aside", "footer", "form", "header"]):
            noise.decompose()
        text = node.get_text(" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        if len(text) >= 80:
            return text[:BODY_CAP]
    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)
    return text[:BODY_CAP] if len(text) >= 80 else ""


_NUM_RE = re.compile(r"(\d[\d,]*\.?\d*)\s*([KMB]?)", re.IGNORECASE)


def _to_int(s: str | None) -> int:
    if not s:
        return 0
    m = _NUM_RE.search(s)
    if not m:
        return 0
    try:
        n = float(m.group(1).replace(",", ""))
        suffix = (m.group(2) or "").upper()
        mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(suffix, 1)
        return int(n * mult)
    except ValueError:
        return 0


def extract_claps(soup: BeautifulSoup) -> int:
    for sel in [
        "button[data-testid='headerClapButton'] span",
        "button[data-testid='footerClapButton'] span",
        "[aria-label*='clap']",
        "button[data-action='show-recommends'] span",
    ]:
        node = soup.select_one(sel)
        if not node:
            continue
        n = _to_int(node.get_text())
        if n:
            return n
    return 0


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
            claps = extract_claps(soup)
            return {"body": body, "claps": claps, "date": extract_pub_date(soup)}
        except (httpx.RequestError, httpx.TimeoutException) as e:
            return {"_error": f"{type(e).__name__}: {e}"}
        except Exception as e:
            return {"_error": f"parse: {type(e).__name__}: {e}"}


async def enrich(items: list[dict], log_path: Path) -> list[dict]:
    sem = asyncio.Semaphore(12)
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
        if "_error" in res:
            fails.append((it.get("url", "?"), res["_error"]))
            out.append(it)
            continue
        merged = dict(it)
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
        candidate = d / "medium.json"
        if candidate.exists():
            return candidate
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path", nargs="?", help="path to medium.json")
    ap.add_argument("--date", help="run date (e.g. 2026-05-08)")
    args = ap.parse_args()

    if args.path:
        p = Path(args.path).expanduser().resolve()
    elif args.date:
        p = Path(__file__).parent / ".runs" / args.date / "medium.json"
    else:
        p = find_default_path()
        if p is None:
            print("no medium.json found; pass --date or path", file=sys.stderr)
            sys.exit(2)

    if not p.exists():
        print(f"file not found: {p}", file=sys.stderr)
        sys.exit(2)

    with open(p) as f:
        items = json.load(f)
    if not isinstance(items, list):
        print(f"expected JSON list, got {type(items).__name__}", file=sys.stderr)
        sys.exit(2)

    print(f"enriching {len(items)} medium items from {p} ...")
    t0 = time.time()
    enriched = asyncio.run(enrich(items, p.parent / "medium_enrich.log"))
    elapsed = time.time() - t0

    body_count = sum(1 for it in enriched if (it.get("body") or "").strip())
    clap_count = sum(1 for it in enriched if it.get("claps", 0))
    date_count = sum(1 for it in enriched if it.get("date"))
    fails = len(items) - body_count
    print(f"  bodies extracted: {body_count}/{len(items)}")
    print(f"  clap signals: {clap_count}/{len(items)}")
    print(f"  dates extracted: {date_count}/{len(items)}")
    print(f"  fetch failures: {fails}")
    print(f"  elapsed: {elapsed:.1f}s")

    with open(p, "w") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=2)
    print(f"wrote {p}")


if __name__ == "__main__":
    main()
