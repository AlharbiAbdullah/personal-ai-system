#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Medium fallback collector: beat-relevant tag feeds over RSS.

Used when medium.com/me/following-feed/all is signed out (the personalized feed
needs a live session). Tag feeds are public, so this keeps Medium in the digest
instead of dropping the source. Output matches the DOM observer's shape
(url/title/author/date) plus `body` from content:encoded.
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

TAGS = ["data-engineering", "llm", "ai-agents", "machine-learning", "devops",
        "software-architecture", "mlops", "kubernetes", "rag", "system-design",
        "apache-spark", "data-science"]


def strip_html(s):
    s = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s or "", flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(s):
    import datetime as dt
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return dt.datetime.strptime(s.strip(), fmt).timestamp()
        except Exception:
            pass
    return 0


def fetch(tag):
    url = f"https://medium.com/feed/tag/{tag}"
    for attempt in range(3):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code != 200:
                time.sleep(1 + attempt)
                continue
            root = ET.fromstring(r.content)
            out = []
            for item in root.iter("item"):
                def txt(t):
                    el = item.find(t)
                    return (el.text or "") if el is not None and el.text else ""
                pub = parse_date(txt("pubDate"))
                if pub and NOW - pub > AGE_MAX:
                    continue
                link = txt("link").split("?")[0]
                if not link:
                    continue
                body_el = item.find(CONTENT)
                a = item.find(DC)
                out.append({
                    "url": link,
                    "title": strip_html(txt("title")),
                    "author": (a.text.strip() if a is not None and a.text else ""),
                    "tag": tag,
                    "date": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(pub)) if pub else None,
                    "body": strip_html(body_el.text if body_el is not None else "")[:12000],
                })
            return tag, out, None
        except Exception as e:
            if attempt == 2:
                return tag, [], f"{type(e).__name__}:{e}"
            time.sleep(1 + attempt)
    return tag, [], "exhausted"


def main():
    print(f"[medium-rss] START date={DATE} mode={MODE} tags={len(TAGS)}", flush=True)
    items, seen, fails = [], set(), []
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fu in as_completed({ex.submit(fetch, t): t for t in TAGS}):
            tag, got, err = fu.result()
            if err:
                fails.append((tag, err))
                print(f"[medium-rss] {tag}: FAIL {err}", flush=True)
                continue
            new = 0
            for it in got:
                if it["url"] in seen:
                    continue
                seen.add(it["url"])
                items.append(it)
                new += 1
            print(f"[medium-rss] {tag}: {new}", flush=True)
    items.sort(key=lambda x: x.get("date") or "", reverse=True)
    with open(os.path.join(RUN, "medium.json"), "w") as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    print(f"[medium-rss] WROTE {len(items)} items -> medium.json "
          f"(bodies={sum(1 for i in items if i.get('body'))}, tag_failures={len(fails)})", flush=True)


if __name__ == "__main__":
    main()
