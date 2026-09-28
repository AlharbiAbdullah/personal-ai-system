#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Substack fallback collector: fetch every saved subscription feed over RSS.

Used when substack.com/inbox won't paginate (expired/half-dead web session).
Reads substack_subscriptions.json, pulls each publication's /feed in parallel,
keeps posts inside the age window, and writes .runs/<date>/substack.json in the
same shape the DOM observer emits (url/title/author/subtitle/date) plus `body`
from content:encoded — so _enrich_substack.py is optional, not required.
"""
import sys, os, re, json, time, html
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

DATE = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
MODE = sys.argv[2] if len(sys.argv) > 2 else "day"
BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, ".runs", DATE)
os.makedirs(RUN, exist_ok=True)
AGE_MAX = (48 if MODE == "day" else 7 * 24) * 3600
NOW = time.time()
UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0"
CONTENT = "{http://purl.org/rss/1.0/modules/content/}encoded"
DC = "{http://purl.org/dc/elements/1.1/}creator"


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    return re.sub(r"\s+", " ", s).strip()


def parse_date(s):
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            import datetime as dt
            return dt.datetime.strptime(s.strip(), fmt).timestamp()
        except Exception:
            pass
    return 0


def fetch(feed):
    url, name = feed["feed"], feed["name"]
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code != 200:
                time.sleep(1 + attempt)
                continue
            root = ET.fromstring(r.content)
            out = []
            for item in root.iter("item"):
                def txt(tag):
                    el = item.find(tag)
                    return (el.text or "") if el is not None and el.text else ""
                pub = parse_date(txt("pubDate"))
                if pub and NOW - pub > AGE_MAX:
                    continue
                link = txt("link").split("?")[0]
                if not link:
                    continue
                body_el = item.find(CONTENT)
                body = strip_html(body_el.text if body_el is not None else "") or strip_html(txt("description"))
                author_el = item.find(DC)
                author = (author_el.text if author_el is not None and author_el.text else "") or name
                out.append({
                    "url": link,
                    "title": strip_html(txt("title")),
                    "author": author.strip(),
                    "publication": name,
                    "subtitle": strip_html(txt("description"))[:300],
                    "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(pub)) if pub else None,
                    "body": body[:12000],
                })
            return name, out, None
        except Exception as e:
            if attempt == 2:
                return name, [], f"{type(e).__name__}:{e}"
            time.sleep(1 + attempt)
    return name, [], "exhausted"


def main():
    subs = json.load(open(os.path.join(BASE, "substack_subscriptions.json")))["feeds"]
    print(f"[substack-rss] START date={DATE} mode={MODE} feeds={len(subs)}", flush=True)
    items, seen, fails = [], set(), []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch, f): f for f in subs}
        for fu in as_completed(futs):
            name, got, err = fu.result()
            if err:
                fails.append((name, err))
                print(f"[substack-rss] {name}: FAIL {err}", flush=True)
                continue
            new = 0
            for it in got:
                if it["url"] in seen:
                    continue
                seen.add(it["url"])
                items.append(it)
                new += 1
            print(f"[substack-rss] {name}: {new}", flush=True)
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    with open(os.path.join(RUN, "substack.json"), "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    bodies = sum(1 for i in items if i.get("body"))
    print(f"[substack-rss] WROTE {len(items)} items -> substack.json "
          f"(bodies={bodies}, feed_failures={len(fails)})", flush=True)


if __name__ == "__main__":
    main()
