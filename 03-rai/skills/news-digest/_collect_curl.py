#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests>=2.31", "beautifulsoup4>=4.12"]
# ///
"""Curl-source collector for news-digest: Hacker News + Reddit + GitHub Trending.

Runs all three concurrently. Writes hn.json / reddit.json / github.json into
.runs/<date>/. Per skill spec:
  - HN: topstories (day) / beststories (week), top 100, fetch items concurrently,
        top-2 comments when descendants >= threshold.
  - Reddit: 18 subs hot.json?limit=50, age filter, top-2 comments when num_comments >= threshold.
  - GitHub: trending?since=daily|weekly, parse repos, README first para for top N.

Clock-skew safe: if the host clock disagrees with live post timestamps (sandbox
clock != wall clock), the absolute age filter would reject everything. We detect
that (median post age negative or > history window) and fall back to hot-rank
order without a hard age cut. Raw + kept counts are always logged.
"""
import sys, os, json, time, re, html
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

DATE = sys.argv[1] if len(sys.argv) > 1 else time.strftime("%Y-%m-%d")
MODE = sys.argv[2] if len(sys.argv) > 2 else "day"
BASE = os.path.expanduser("~/helm/03-rai/skills/news-digest")
RUN = os.path.join(BASE, ".runs", DATE)
os.makedirs(RUN, exist_ok=True)

UA = "Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0"
NOW = time.time()
AGE_MAX = (48 if MODE == "day" else 7 * 24) * 3600

REDDIT_SUBS = [
    "dataengineering", "devops", "ClaudeCode", "LocalLLM", "ollama", "mcp",
    "AI_Agents", "aiagents", "MachineLearning", "mlops", "PromptEngineering",
    "Rag", "learnmachinelearning", "dataops", "datascience",
    "softwarearchitecture", "artificial", "ExperiencedDevs",
]

def log(src, msg):
    print(f"[{src}] {msg}", flush=True)

# ----------------------------------------------------------------- Hacker News
def collect_hn():
    src = "hn"
    feed = "beststories" if MODE == "week" else "topstories"
    try:
        ids = requests.get(f"https://hacker-news.firebaseio.com/v0/{feed}.json",
                           timeout=20).json()[:100]
    except Exception as e:
        log(src, f"FAILED to fetch story ids: {e}")
        json.dump([], open(f"{RUN}/hn.json", "w")); return
    log(src, f"{len(ids)} story ids")

    def fetch_item(i):
        try:
            return requests.get(f"https://hacker-news.firebaseio.com/v0/item/{i}.json",
                                timeout=15).json()
        except Exception:
            return None

    items = []
    with ThreadPoolExecutor(max_workers=20) as ex:
        for it in ex.map(fetch_item, ids):
            if it and it.get("type") == "story" and it.get("title"):
                items.append(it)
    log(src, f"{len(items)} stories fetched")

    # top-2 comments for high-discussion stories
    def top_comments(it):
        kids = (it.get("kids") or [])[:2]
        out = []
        for k in kids:
            c = fetch_item(k)
            if c and c.get("text"):
                out.append(html.unescape(re.sub("<[^>]+>", " ", c["text"]))[:1200])
        return out

    hot = [it for it in items if (it.get("descendants") or 0) >= 100]
    with ThreadPoolExecutor(max_workers=15) as ex:
        futs = {ex.submit(top_comments, it): it for it in hot}
        for f in as_completed(futs):
            futs[f]["top_comments"] = f.result()

    out = []
    for it in items:
        out.append({
            "id": it["id"],
            "title": it.get("title", ""),
            "url": it.get("url") or f"https://news.ycombinator.com/item?id={it['id']}",
            "hn_url": f"https://news.ycombinator.com/item?id={it['id']}",
            "score": it.get("score", 0),
            "descendants": it.get("descendants", 0),
            "by": it.get("by", ""),
            "time": it.get("time", 0),
            "text": html.unescape(re.sub("<[^>]+>", " ", it.get("text", ""))) if it.get("text") else "",
            "top_comments": it.get("top_comments", []),
        })
    out.sort(key=lambda x: x["score"], reverse=True)
    json.dump(out, open(f"{RUN}/hn.json", "w"), ensure_ascii=False, indent=1)
    log(src, f"WROTE {len(out)} items -> hn.json")

# ---------------------------------------------------------------------- Reddit
def collect_reddit():
    src = "reddit"
    sess = requests.Session()
    sess.headers["User-Agent"] = UA

    def fetch_sub(sub):
        for attempt in range(3):
            try:
                r = sess.get(f"https://www.reddit.com/r/{sub}/hot.json?limit=50", timeout=20)
                if r.status_code == 200:
                    return sub, r.json().get("data", {}).get("children", [])
                time.sleep(2 ** attempt)
            except Exception:
                time.sleep(2 ** attempt)
        return sub, []

    raw = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        for sub, children in ex.map(fetch_sub, REDDIT_SUBS):
            n = 0
            for ch in children:
                d = ch.get("data", {})
                if d.get("stickied") or d.get("pinned"):
                    continue
                raw.append({
                    "sub": sub,
                    "id": d.get("id"),
                    "title": d.get("title", ""),
                    "url": d.get("url_overridden_by_dest") or ("https://www.reddit.com" + d.get("permalink", "")),
                    "permalink": "https://www.reddit.com" + d.get("permalink", ""),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "author": d.get("author", ""),
                    "created_utc": d.get("created_utc", 0),
                    "selftext": (d.get("selftext", "") or "")[:2500],
                    "is_self": d.get("is_self", False),
                })
                n += 1
            log(src, f"r/{sub}: {n}")
    log(src, f"{len(raw)} raw posts across {len(REDDIT_SUBS)} subs")

    # clock-skew-safe age filter
    ages = [NOW - p["created_utc"] for p in raw if p["created_utc"]]
    ages.sort()
    median_age = ages[len(ages) // 2] if ages else 0
    skewed = median_age < 0 or median_age > 30 * 24 * 3600
    if skewed:
        log(src, f"CLOCK SKEW detected (median age {median_age/3600:.1f}h) — keeping hot-rank, no age cut")
        kept = raw
    else:
        kept = [p for p in raw if 0 <= (NOW - p["created_utc"]) <= AGE_MAX]
        log(src, f"age filter (<{AGE_MAX//3600}h): {len(kept)}/{len(raw)} kept")

    # top-2 comments for high-discussion posts
    hot = [p for p in kept if p["num_comments"] >= 50]
    def fetch_comments(p):
        try:
            r = sess.get(p["permalink"].rstrip("/") + ".json?limit=3&depth=1", timeout=15)
            if r.status_code != 200:
                return p["id"], []
            data = r.json()
            cs = data[1]["data"]["children"] if len(data) > 1 else []
            out = []
            for c in cs:
                body = c.get("data", {}).get("body")
                if body and c.get("kind") == "t1":
                    out.append(body[:1200])
                if len(out) >= 2:
                    break
            return p["id"], out
        except Exception:
            return p["id"], []

    if hot:
        cmap = {}
        with ThreadPoolExecutor(max_workers=8) as ex:
            for pid, cs in ex.map(fetch_comments, hot):
                cmap[pid] = cs
        for p in kept:
            p["top_comments"] = cmap.get(p["id"], [])
        log(src, f"fetched comments for {len(hot)} high-discussion posts")
    else:
        for p in kept:
            p["top_comments"] = []

    kept.sort(key=lambda x: x["score"], reverse=True)
    json.dump(kept, open(f"{RUN}/reddit.json", "w"), ensure_ascii=False, indent=1)
    log(src, f"WROTE {len(kept)} items -> reddit.json")

# ------------------------------------------------------------- GitHub Trending
def collect_github():
    src = "github"
    since = "weekly" if MODE == "week" else "daily"
    try:
        r = requests.get(f"https://github.com/trending?since={since}",
                         headers={"User-Agent": UA}, timeout=20)
        htmltext = r.text
    except Exception as e:
        log(src, f"FAILED to fetch trending: {e}")
        json.dump([], open(f"{RUN}/github.json", "w")); return

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(htmltext, "html.parser")
    repos = []
    for art in soup.select("article.Box-row"):
        a = art.select_one("h2 a")
        if not a:
            continue
        repo = re.sub(r"\s+", "", a.get_text())
        desc_el = art.select_one("p")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        lang_el = art.select_one('[itemprop="programmingLanguage"]')
        lang = lang_el.get_text(strip=True) if lang_el else ""
        stars_el = art.select_one('a[href$="/stargazers"]')
        stars = stars_el.get_text(strip=True).replace(",", "") if stars_el else "0"
        today_el = art.select_one("span.d-inline-block.float-sm-right")
        today = today_el.get_text(strip=True) if today_el else ""
        repos.append({
            "repo": repo, "url": f"https://github.com/{repo}",
            "description": desc, "language": lang,
            "stars": int(stars) if stars.isdigit() else stars,
            "stars_period": today, "readme_head": "",
        })
    log(src, f"{len(repos)} trending repos")

    # README first paragraph for top N
    def readme_head(repo):
        for branch in ("main", "master"):
            for fn in ("README.md", "readme.md", "README.rst"):
                try:
                    u = f"https://raw.githubusercontent.com/{repo}/{branch}/{fn}"
                    rr = requests.get(u, headers={"User-Agent": UA}, timeout=12)
                    if rr.status_code == 200 and rr.text.strip():
                        txt = re.sub(r"^[#>*\-\s\[\]!].*$", "", rr.text, flags=re.MULTILINE)
                        for para in txt.split("\n\n"):
                            p = para.strip().replace("\n", " ")
                            if len(p) > 60:
                                return p[:600]
                        return ""
                except Exception:
                    continue
        return ""

    top = repos[:10]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(readme_head, rp["repo"]): rp for rp in top}
        for f in as_completed(futs):
            futs[f]["readme_head"] = f.result()

    json.dump(repos, open(f"{RUN}/github.json", "w"), ensure_ascii=False, indent=1)
    log(src, f"WROTE {len(repos)} items -> github.json")

# ------------------------------------------------------------------------ main
if __name__ == "__main__":
    log("curl", f"START date={DATE} mode={MODE}")
    with ThreadPoolExecutor(max_workers=3) as ex:
        futs = [ex.submit(collect_hn), ex.submit(collect_reddit), ex.submit(collect_github)]
        for f in as_completed(futs):
            try:
                f.result()
            except Exception as e:
                log("curl", f"source crashed: {e}")
    log("curl", "DONE — all curl sources complete")
