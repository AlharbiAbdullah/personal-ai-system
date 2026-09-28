#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31"]
# ///
"""Sequential, paced Reddit RSS fetch — avoids the 6-worker burst that gets 403/rate-limited.
Fetches all subs one at a time with jittered delays, writes reddit.json in the same format
as _collect_reddit_rss.py."""
import sys, os, re, time, json, random
import xml.etree.ElementTree as ET
import requests

DATE = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
MODE = sys.argv[2] if len(sys.argv) > 2 else "day"
BASE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(BASE, ".runs", DATE)
NOW = time.time()
AGE_MAX = (48 if MODE == "day" else 7 * 24) * 3600
NS = "{http://www.w3.org/2005/Atom}"
UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0"

SUBS = ["dataengineering","devops","ClaudeCode","LocalLLM","ollama","mcp",
        "AI_Agents","aiagents","MachineLearning","mlops","PromptEngineering","Rag",
        "learnmachinelearning","dataops","datascience","softwarearchitecture",
        "artificial","ExperiencedDevs"]

def strip_html(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = re.sub(r"&#?\w+;", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def iso_to_epoch(s):
    try:
        return time.mktime(time.strptime(s.split("+")[0].split(".")[0], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return 0

def fetch_sub(sub):
    url = f"https://www.reddit.com/r/{sub}/hot/.rss?limit=100"
    r = None
    for attempt in range(5):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=25)
            if r.status_code == 200:
                break
            time.sleep(2.0 * (attempt + 1) + random.uniform(0, 1.5))
        except Exception:
            time.sleep(2.0 * (attempt + 1) + random.uniform(0, 1.5))
    if r is None or r.status_code != 200:
        return sub, [], f"fetch_failed:{getattr(r,'status_code','exc')}"
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
        if re.match(r"^(submitted by|\[link\]|\[comments\])", body, re.I) or len(body) < 40:
            body = ""
        out.append({
            "sub": sub,
            "id": (entry.findtext(f"{NS}id") or link).split("/")[-1] or link,
            "title": title,
            "url": link,
            "permalink": link,
            "score": 0,
            "num_comments": 0,
            "author": author.replace("/u/", "").replace("u/", ""),
            "created_utc": iso_to_epoch(published),
            "selftext": body[:2500],
            "is_self": bool(body),
            "top_comments": [],
            "engagement_source": "rss_unavailable",
        })
    return sub, out, "ok"

if __name__ == "__main__":
    print(f"[reddit-paced] START date={DATE} mode={MODE}", flush=True)
    raw, stats = [], {}
    for i, sub in enumerate(SUBS):
        sub, items, status = fetch_sub(sub)
        stats[sub] = (len(items), status)
        raw.extend(items)
        print(f"[reddit-paced] r/{sub}: {len(items)} ({status})", flush=True)
        if i < len(SUBS) - 1:
            time.sleep(random.uniform(2.5, 4.5))  # pace between subs

    ages = sorted(NOW - p["created_utc"] for p in raw if p["created_utc"])
    median_age = ages[len(ages) // 2] if ages else 0
    if median_age < -3600 or median_age > 30 * 24 * 3600:
        print(f"[reddit-paced] CLOCK SKEW (median {median_age/3600:.1f}h) — no age cut", flush=True)
        kept = raw
    else:
        kept = [p for p in raw if -3600 <= (NOW - p["created_utc"]) <= AGE_MAX]
        print(f"[reddit-paced] age filter (<{AGE_MAX//3600}h): {len(kept)}/{len(raw)} kept", flush=True)

    seen, dedup = set(), []
    for p in kept:
        if p["id"] in seen:
            continue
        seen.add(p["id"]); dedup.append(p)

    json.dump(dedup, open(f"{RUN}/reddit.json", "w"), ensure_ascii=False, indent=1)
    ok = sum(1 for _, (_, s) in stats.items() if s == "ok")
    print(f"[reddit-paced] WROTE {len(dedup)} items from {ok}/{len(SUBS)} subs -> reddit.json", flush=True)
