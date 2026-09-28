#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Reddit collector via Atom RSS — fallback for when the JSON API 403s.

Reddit's /hot.json endpoint hard-blocks datacenter IPs (403 + bot page), and
the Chrome MCP extension blocks reddit.com navigation. But the public Atom RSS
(/r/<sub>/hot/.rss) is still served. RSS gives title/author/url/body/timestamp
but NOT score or num_comments — so engagement goes neutral and items are scored
on content alone. Volume + signal preserved; precision on "hotness" lost.
"""
import sys, os, json, time, re, html
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
import requests

DATE = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
MODE = sys.argv[2] if len(sys.argv) > 2 else "day"
BASE = os.path.expanduser("~/helm/03-rai/skills/news-digest")
RUN = os.path.join(BASE, ".runs", DATE)
os.makedirs(RUN, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0"
NS = "{http://www.w3.org/2005/Atom}"
NOW = time.time()
AGE_MAX = (48 if MODE == "day" else 7 * 24) * 3600

SUBS = [
    "dataengineering", "devops", "ClaudeCode", "LocalLLM", "ollama", "mcp",
    "AI_Agents", "aiagents", "MachineLearning", "mlops", "PromptEngineering",
    "Rag", "learnmachinelearning", "dataops", "datascience",
    "softwarearchitecture", "artificial", "ExperiencedDevs",
]

def strip_html(s):
    s = re.sub(r"(?s)<!--.*?-->", " ", s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def iso_to_epoch(s):
    try:
        return time.mktime(time.strptime(s.split("+")[0].split(".")[0], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0

def fetch_sub(sub):
    url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit=100"
    for attempt in range(4):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=20)
            if r.status_code == 200:
                break
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    else:
        return sub, [], "fetch_failed"
    try:
        root = ET.fromstring(r.content)
    except Exception as e:
        return sub, [], f"parse_failed:{e}"

    out = []
    for entry in root.findall(f"{NS}entry"):
        title = (entry.findtext(f"{NS}title") or "").strip()
        link_el = entry.find(f"{NS}link")
        link = link_el.get("href") if link_el is not None else ""
        author = ""
        ae = entry.find(f"{NS}author/{NS}name")
        if ae is not None and ae.text:
            author = ae.text.strip()
        published = entry.findtext(f"{NS}published") or entry.findtext(f"{NS}updated") or ""
        content_raw = entry.findtext(f"{NS}content") or ""
        body = strip_html(content_raw)
        # RSS body for link posts is just "submitted by /u/x [link][comments]" boilerplate
        if re.match(r"^(submitted by|\[link\]|\[comments\])", body, re.I) or len(body) < 40:
            body = ""
        out.append({
            "sub": sub,
            "id": (entry.findtext(f"{NS}id") or link).split("/")[-1] or link,
            "title": title,
            "url": link,
            "permalink": link,
            "score": 0,            # not available via RSS
            "num_comments": 0,     # not available via RSS
            "author": author.replace("/u/", "").replace("u/", ""),
            "created_utc": iso_to_epoch(published),
            "selftext": body[:2500],
            "is_self": bool(body),
            "top_comments": [],
            "engagement_source": "rss_unavailable",
        })
    return sub, out, "ok"

if __name__ == "__main__":
    print(f"[reddit-rss] START date={DATE} mode={MODE} via Atom RSS", flush=True)
    raw, stats = [], {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for sub, items, status in ex.map(fetch_sub, SUBS):
            stats[sub] = (len(items), status)
            raw.extend(items)
            print(f"[reddit-rss] r/{sub}: {len(items)} ({status})", flush=True)

    # clock-skew-safe age filter
    ages = sorted(NOW - p["created_utc"] for p in raw if p["created_utc"])
    median_age = ages[len(ages) // 2] if ages else 0
    if median_age < -3600 or median_age > 30 * 24 * 3600:
        print(f"[reddit-rss] CLOCK SKEW (median {median_age/3600:.1f}h) — no age cut", flush=True)
        kept = raw
    else:
        kept = [p for p in raw if -3600 <= (NOW - p["created_utc"]) <= AGE_MAX]
        print(f"[reddit-rss] age filter (<{AGE_MAX//3600}h): {len(kept)}/{len(raw)} kept", flush=True)

    # dedup by id
    seen, dedup = set(), []
    for p in kept:
        if p["id"] in seen:
            continue
        seen.add(p["id"]); dedup.append(p)

    json.dump(dedup, open(f"{RUN}/reddit.json", "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for _, (_, s) in stats.items() if s == "ok")
    print(f"[reddit-rss] WROTE {len(dedup)} items from {ok}/{len(SUBS)} subs -> reddit.json", flush=True)
