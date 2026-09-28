#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""V5 presentation — identity-aware scoring + cross-source ranking + diversity-enforced sections.

Reads raw source JSONs from .runs/<DATE>/ and writes a digest markdown.
Standalone — does not modify synthesize.py (v4.5 baseline) or config.yaml.

Usage:
    python present_v5.py --date 2026-05-06 --out test-news.md
    python present_v5.py --date 2026-05-06           # writes to <DATE>.md
"""
import argparse
import html as _html
import json
import math
import os
import re
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
ap = argparse.ArgumentParser()
ap.add_argument("--date", required=True, help="run date, e.g., 2026-05-06")
ap.add_argument("--out", default=None, help="output filename in 08-bawaba/ (default: <DATE>.md)")
ap.add_argument("--test", action="store_true",
                help="dry run: write to .runs/<date>/preview.md, skip archiving and ledger append")
args = ap.parse_args()

DATE = args.date
TEST_MODE = args.test
RUN_DIR = Path(os.path.expanduser(f"~/helm/03-rai/skills/news-digest/.runs/{DATE}"))
DIGEST_DIR = Path(os.path.expanduser("~/helm/08-bawaba/daily/"))
OUT_NAME = args.out or f"{DATE}.md"
OUT_PATH = (RUN_DIR / "preview.md") if TEST_MODE else (DIGEST_DIR / OUT_NAME)

# ---------------------------------------------------------------------------
# Config (source affinity, source caps, section sizes)
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(__file__).parent / "config.yaml"
CONFIG = {}
if yaml is not None and CONFIG_PATH.exists():
    try:
        with open(CONFIG_PATH) as _f:
            CONFIG = yaml.safe_load(_f) or {}
    except Exception:
        CONFIG = {}

SOURCE_AFFINITY = CONFIG.get("source_affinity", {}) or {}
MAX_SOURCE_PCT = float(CONFIG.get("max_source_pct", 0.35))
GITHUB_MAX = int(CONFIG.get("github_max", 4))
# Daily X-share target band — X is John's primary collection channel, so the personalized
# body (Top Shelf + Feed) is rebalanced into this band. See rebalance_x_share().
_X_SHARE_TARGET = CONFIG.get("x_share_target", [0.40, 0.55]) or [0.40, 0.55]
X_SHARE_LO = float(_X_SHARE_TARGET[0])
X_SHARE_HI = float(_X_SHARE_TARGET[1])

# ---------------------------------------------------------------------------
# KEYWORD DICTIONARIES
# ---------------------------------------------------------------------------

# Universal quality (any reader values)
TEACHES_MARKERS = [
    "explain", "how to", "guide to", "tutorial", "primer", "walkthrough",
    "what i learned", "intuition behind", "deep dive", "mental model",
    "first principles", "from scratch", "under the hood",
]
TOOL_DISCOVERY_MARKERS = [
    "introducing", "open-sourcing", "we built", "we're building",
    "show hn", "released", "v1.", "v2.", "library", "framework",
    "sdk", " cli ",
]
ARTIFACT_MARKERS = [
    "github.com", "gitlab.com", "arxiv.org", "doi.org",
    "documentation", "docs", "blog post", "writeup",
    "case study", "benchmark", "code snippet", "repo",
]
POSTMORTEM_MARKERS = [
    "postmortem", "post-mortem", "post mortem",
    "what went wrong", "incident report", "incident timeline",
    "outage report", "outage analysis", "we broke production",
    "lessons learned", "burned by", "we got burned",
    "retrospective", "in retrospect", "looking back",
    "we should have known", "we should have caught", "we underestimated",
    "in hindsight", "root cause", "the fix was",
    "we shipped a bug", "production failure",
]
CONTRARIAN_MARKERS = [
    "actually", "contrary to", "myth", "misconception",
    "common belief", "i disagree", "but really",
    "the truth is", "in fact",
]

# Identity (John-specific)
# Two kinds: substrings (matched plainly) and word-bounded (via regex \bword\b for short
# ambiguous tokens like mcp/llm/rag/k8s — to avoid false positives like "fragment" matching "rag").

AI_SUBSTRINGS = [
    "agentic", "multi-agent", "model context protocol",
    "retrieval-augmented", "embedding", "vector db", "vector database",
    "prompt engineering", "fine-tun", "foundation model",
    "transformer", "claude", "anthropic", "openai", "gemini",
    "deepseek", "qwen", "ollama", "llama.cpp",
    "eval harness", "tool use", "function calling",
    "claude code", "claude-code", "chatgpt", "copilot",
    "ai engineer", "ai system", "ml engineer", "ml system",
    "agent framework", "autogen", "langchain", "langgraph", "llamaindex",
]
AI_BOUNDED = ["mcp", "llm", "llms", "rag", "agi", "evals", "agent", "agents"]

DATA_ENG_SUBSTRINGS = [
    "data engineer", "data engineering",
    "pipeline", "orchestrat", "dagster", "airflow",
    "spark", "kafka", "flink", "iceberg", "delta lake",
    "lakehouse", "warehouse", "duckdb", "polars", "arrow", "parquet",
    "data quality", "data lineage", "dimensional model", "medallion",
    "data platform", "data mesh", "snowflake", "bigquery", "redshift",
    "clickhouse", "trino", "presto", "data catalog", "data observability",
]
DATA_ENG_BOUNDED = ["etl", "elt", "dbt", "olap", "oltp", "cdc"]

SYSTEM_DESIGN_SUBSTRINGS = [
    "system design", "distributed system", "scaling", "scale to",
    "latency", "throughput", "sharding", "consensus",
    "consistency", "cap theorem",
    "load balanc", "message broker", "event-driven",
    "event sourcing", "saga pattern", "back-pressure", "backpressure",
    "high availability", "fault toler", "replication",
    "design pattern", "architecture",
]
SYSTEM_DESIGN_BOUNDED = ["p99", "p95", "raft", "paxos", "cqrs", "rpc", "grpc"]

DEVOPS_SUBSTRINGS = [
    "kubernetes", "docker", "container",
    "terraform", "infrastructure as code",
    "observab", "prometheus", "grafana", "opentelemetry",
    "service mesh", "istio", "envoy",
    "mlops", "model serving", "vllm", "ray serve",
    "github actions", "argo workflow", "argocd",
    "helm chart", "helm ",
]
DEVOPS_BOUNDED = ["k8s", "iac", "ci/cd", "sre"]
ACTIVE_PROJECTS = [
    ("Rai",      ["rai brain", "personal ai system"]),
    ("OpenKit",  ["openkit", "open-kit"]),
    ("Helios",   ["helios"]),
    ("Taskflow", ["taskflow"]),
]
# EXAMPLE region-relevance keywords — CUSTOMIZE to your own city/country/region.
# Stories matching these get a local-relevance boost in scoring. Replace with yours.
REGION_SUBSTRINGS = [
    "yourcity", "yourcountry", "yourregion",
]
REGION_BOUNDED = ["localgov", "localmarket"]

# Hard filters (drop entirely)
CRYPTO_HARD_KEYWORDS = [
    "memecoin", "shitcoin", "to the moon", "rugpull",
    "tokeniz", " rwa ", "real world asset", "$btc", "$eth",
    " nft ", "non-fungible", " defi ", " web3 ",
    "ico ", "presale", "airdrop", "metamask",
]
LISTICLE_PATTERNS = [
    re.compile(r"\b(top|best)\s+\d+\s+(tools?|frameworks?|libraries|tips?|skills?|things?|ways?|reasons?)\b", re.I),
    re.compile(r"\b\d+\s+(tools?|frameworks?|libraries|tips?|skills?|things?|ways?|reasons?)\s+(every|you|i|that|to)\b", re.I),
    re.compile(r"\bbest\s+of\s+\d{4}\b", re.I),
    re.compile(r"\b\d+\s+things?\s+i\s+(wish|learned)\b", re.I),
]
SPAM_PATTERNS = [
    "claim 10 free", "free hol", "blockchain and digital assets",
    "free $", "join the discord to get early", "early access!",
    "vps hosting", "drop alert", "limited offer",
    "if you have a mouse", "must hide across", "snow white",
    "horoscope", "mercury retrograde",
]

# Heavy penalties (-25)
AI_HYPE_PHRASES = [
    "agi is here", "agi is coming", "the end of programming",
    "no more coders", "everyone will be unemployed",
    "ai takes over", "ai takeover",
]
CAREER_ADVICE_PHRASES = [
    "how i made $", "how i earn $", "salary negotiation",
    "10 skills hiring", "what recruiters want", "interview tips",
    "land your dream job", "salary range", "compensation report",
    "how to get a job", "leetcode grind",
]

# Light penalties (-10)
FRONTEND_KEYWORDS = [
    "tailwind", "css framework", "react component library",
    "svelte ", "next.js ", "frontend framework", "shadcn",
]
MOBILE_KEYWORDS = [
    "swiftui", "android jetpack", " ios 18", " ios 19",
    "kotlin multiplatform", "react native", "flutter ",
]
LIFESTYLE_KEYWORDS = [
    "morning routine", "productivity hack", "5am club",
    "atomic habits", "wellness tips", "mindfulness app",
]

# ---------------------------------------------------------------------------
# JSON loaders / source helpers
# ---------------------------------------------------------------------------

def load_json(name, default=None):
    p = RUN_DIR / name
    if not p.exists():
        return default if default is not None else []
    with open(p) as f:
        return json.load(f)

def merge_attempts(prefix, max_n):
    merged, seen = [], set()
    for n in range(1, max_n + 1):
        chunk = load_json(f"{prefix}-attempt{n}.json", [])
        for t in chunk:
            if not isinstance(t, dict):
                continue
            tid = t.get("id")
            if tid and tid in seen:
                continue
            if tid:
                seen.add(tid)
            merged.append(t)
    return merged

def attempts_count(prefix, max_n=3):
    return sum(1 for n in range(1, max_n + 1) if (RUN_DIR / f"{prefix}-attempt{n}.json").exists())

def get_title(item, src):
    if src in ("hn", "reddit", "github"):
        t = item.get("title", "") or item.get("name", "") or item.get("repo", "")
    elif src in ("x_foryou", "x_following"):
        text = (item.get("text", "") or "").strip()
        t = (text[:200] + "…") if len(text) > 200 else text
    elif src in ("substack", "medium"):
        t = item.get("title", "")
    else:
        t = ""
    # Flatten multi-line titles to single line
    return re.sub(r"\s+", " ", t).strip()

def _num(v):
    """Coerce numeric values to int — merged X dumps carry stringified numerics
    like "58279"; reddit created_utc can be a float string."""
    try:
        return int(float(str(v).replace(",", "").strip() or 0))
    except (ValueError, TypeError):
        return 0

def get_author(item, src):
    if src in ("substack", "medium"):
        return item.get("author") or ""
    if src in ("x_foryou", "x_following"):
        return (item.get("handle") or "").lstrip("@")
    if src == "reddit":
        return item.get("author") or ""
    if src == "hn":
        return item.get("by") or ""
    return ""

def get_pub_date(item, src):
    """ISO YYYY-MM-DD publish date or None."""
    from datetime import datetime, timezone
    if src in ("substack", "medium"):
        d = str(item.get("date") or "")
        return d[:10] if re.match(r"\d{4}-\d{2}-\d{2}", d) else None
    if src == "reddit" and _num(item.get("created_utc")) > 0:
        return datetime.fromtimestamp(_num(item["created_utc"]), tz=timezone.utc).strftime("%Y-%m-%d")
    if src == "hn" and _num(item.get("time")) > 0:
        return datetime.fromtimestamp(_num(item["time"]), tz=timezone.utc).strftime("%Y-%m-%d")
    if src in ("x_foryou", "x_following") and item.get("ts"):
        d = str(item["ts"])[:10]
        return d if re.match(r"\d{4}-\d{2}-\d{2}", d) else None
    return None

def get_url(item, src):
    if src == "hn":
        return item.get("url") or f"https://news.ycombinator.com/item?id={item.get('id')}"
    if src == "reddit":
        p = item.get("permalink", "")
        return f"https://reddit.com{p}" if p.startswith("/") else (item.get("url") or p)
    if src == "github":
        return item.get("href") or item.get("url") or f"https://github.com/{item.get('repo','')}"
    if src in ("x_foryou", "x_following"):
        return item.get("url", "")
    if src == "substack":
        u = item.get("url", "")
        return u if u.startswith("http") else f"https://substack.com{u}"
    if src == "medium":
        return item.get("url", "")
    return ""

def fmt_source_name(src, item):
    if src == "hn":
        return "HN"
    if src == "reddit":
        permalink = item.get("permalink") or ""
        sub = item.get("subreddit", "") or item.get("sub", "") or (
            permalink.split("/r/")[1].split("/")[0] if "/r/" in permalink else ""
        )
        return f"r/{sub}" if sub else "Reddit"
    if src == "github":
        name = item.get("name") or item.get("repo") or ""
        return name if name else "GitHub"
    if src in ("x_foryou", "x_following"):
        h = item.get("handle", "").lstrip("@")
        return f"@{h}" if h else "X"
    if src == "substack":
        return item.get("author", "") or "Substack"
    if src == "medium":
        return "Medium"
    return src

def fmt_engagement(item, src):
    if src == "hn":
        return f"{item.get('score', 0)} pts, {item.get('descendants', 0)}c"
    if src == "reddit":
        return f"{item.get('score', 0)} pts, {item.get('num_comments', 0)}c"
    if src == "github":
        s = item.get("stars") or item.get("stars_today") or item.get("stars_delta") or 0
        return f"{s} stars today" if isinstance(s, str) else f"{s} stars today"
    if src in ("x_foryou", "x_following"):
        likes = item.get("likes", 0) or 0
        return f"{likes} likes" if likes else "X"
    if src == "substack":
        return "Substack"
    if src == "medium":
        a = item.get("author", "")
        return f"by {a}" if a else "Medium"
    return src

def get_text_blob(item, src):
    parts = [
        get_title(item, src),
        item.get("text", "") or "",
        item.get("selftext", "") or "",
        item.get("body", "") or "",
        item.get("subtitle", "") or "",
        item.get("desc", "") or item.get("description", "") or "",
    ]
    cs = item.get("comments", []) or []
    if cs and isinstance(cs[0], dict):
        parts.append(cs[0].get("text", "") or "")
    return " ".join(p for p in parts if p)

def kw_count(text_lower, kws):
    return sum(1 for k in kws if k in text_lower)

def kw_any(text_lower, kws):
    return any(k in text_lower for k in kws)

# Cache compiled regexes for word-bounded keyword sets
_BOUNDED_CACHE = {}

def bounded_count(text_lower, words):
    """Count word-bounded matches for short ambiguous tokens (mcp/llm/rag/k8s)."""
    key = tuple(words)
    if key not in _BOUNDED_CACHE:
        # Build a single regex for efficiency: \b(word1|word2|...)\b
        escaped = "|".join(re.escape(w) for w in words)
        _BOUNDED_CACHE[key] = re.compile(r"\b(" + escaped + r")\b")
    return len(_BOUNDED_CACHE[key].findall(text_lower))

def bounded_any(text_lower, words):
    return bounded_count(text_lower, words) > 0

# ---------------------------------------------------------------------------
# Hard filters
# ---------------------------------------------------------------------------

def is_hard_filtered(item, src, text_blob_lower):
    title_lower = (get_title(item, src) or "").lower()
    if kw_any(text_blob_lower, SPAM_PATTERNS):
        return True
    if kw_any(text_blob_lower, CRYPTO_HARD_KEYWORDS):
        return True
    for pat in LISTICLE_PATTERNS:
        if pat.search(title_lower):
            return True
    return False

# ---------------------------------------------------------------------------
# V5 scoring
# ---------------------------------------------------------------------------

def score_universal(item, src, text_lower, title_lower):
    teaches = min(10, kw_count(text_lower, TEACHES_MARKERS) * 2)
    if any(m in title_lower for m in ["how i", "lesson", "guide to", "tutorial", "primer"]):
        teaches = min(10, teaches + 3)

    tool_discovery = min(8, kw_count(text_lower, TOOL_DISCOVERY_MARKERS) * 2)
    if src == "github":
        tool_discovery = max(tool_discovery, 6)

    artifact = min(8, kw_count(text_lower, ARTIFACT_MARKERS) * 3)
    url = (get_url(item, src) or "").lower()
    # X tweets link out via a card/t.co, so the code/paper host lives in the
    # observer-captured link_domain, not the tweet url. Treat it the same as a
    # github/arxiv url, and count a video as a light artifact (a demo). v5.7:
    # this only lifts genuinely rich X items into the candidate pool — the agent
    # still curates; nothing auto-promotes.
    x_dom = (item.get("link_domain") or "").lower() if isinstance(item, dict) else ""
    if any(d in url for d in ["github.com", "gitlab.com", "arxiv.org"]) or \
       any(d in x_dom for d in ["github.com", "gitlab.com", "arxiv.org", "huggingface.co"]):
        artifact = min(8, artifact + 4)
    if src in ("x_foryou", "x_following") and isinstance(item, dict) and item.get("has_video"):
        artifact = min(8, artifact + 2)

    eng = (item.get("descendants") or item.get("num_comments") or 0)
    discussion_quality = min(10, math.log10(eng + 1) * 4) if eng > 0 else 0

    postmortem = min(8, kw_count(text_lower, POSTMORTEM_MARKERS) * 3)
    if any(m in title_lower for m in POSTMORTEM_MARKERS):
        postmortem = min(8, postmortem + 3)

    contrarian = min(6, kw_count(text_lower, CONTRARIAN_MARKERS) * 1.5)

    return {
        "teaches": teaches,
        "tool_discovery": tool_discovery,
        "artifact": artifact,
        "discussion_quality": round(discussion_quality, 1),
        "postmortem": postmortem,
        "contrarian_evidence": contrarian,
        "total": round(teaches + tool_discovery + artifact + discussion_quality + postmortem + contrarian, 1),
    }

def score_identity(text_lower):
    # AI: substrings + word-bounded
    ai_hits = kw_count(text_lower, AI_SUBSTRINGS) + bounded_count(text_lower, AI_BOUNDED)
    ai = min(12, ai_hits * 2)

    # Data Engineering
    de_hits = kw_count(text_lower, DATA_ENG_SUBSTRINGS) + bounded_count(text_lower, DATA_ENG_BOUNDED)
    de = min(12, de_hits * 2.5)

    # System Design
    sd_hits = kw_count(text_lower, SYSTEM_DESIGN_SUBSTRINGS) + bounded_count(text_lower, SYSTEM_DESIGN_BOUNDED)
    sd = min(10, sd_hits * 2.5)

    # DevOps
    do_hits = kw_count(text_lower, DEVOPS_SUBSTRINGS) + bounded_count(text_lower, DEVOPS_BOUNDED)
    do = min(8, do_hits * 2)

    # Active projects (compounding)
    proj_matched = []
    for proj_name, kws in ACTIVE_PROJECTS:
        if any(k in text_lower for k in kws):
            proj_matched.append(proj_name)
    proj = min(10, len(proj_matched) * 5)

    # local/Arab context
    region_hits = kw_count(text_lower, REGION_SUBSTRINGS) + bounded_count(text_lower, REGION_BOUNDED)
    local = min(8, region_hits * 2.5)

    # Compounding bonus: items hitting >=2 distinct identity dimensions
    dims_hit = sum(1 for v in [ai, de, sd, do, proj, local] if v >= 4)
    bonus = 0
    if dims_hit >= 3:
        bonus = 6
    elif dims_hit >= 2:
        bonus = 3

    total = ai + de + sd + do + proj + local + bonus

    return {
        "ai": ai,
        "data_engineering": de,
        "system_design": sd,
        "devops": do,
        "active_project": proj,
        "region_context": local,
        "compounding_bonus": bonus,
        "projects_matched": proj_matched,
        "total": round(min(56, total), 1),  # ceiling 56 to allow compounding
    }

def score_engagement(item, src):
    if src in ("hn", "reddit"):
        pts = item.get("score", 0) or 0
        return min(10, math.log10(pts + 1) * 3)
    if src == "github":
        s = item.get("stars") or item.get("stars_today") or item.get("stars_delta") or 0
        if isinstance(s, str):
            s = int(re.sub(r"[^\d]", "", s) or "0")
        return min(10, math.log10(s + 1) * 3)
    if src in ("x_foryou", "x_following"):
        # field is "reposts" (not "retweets"); merged dumps may carry string numerics
        likes = _num(item.get("likes"))
        reposts = _num(item.get("reposts"))
        return min(10, math.log10(likes + reposts + 1) * 2.8)
    if src == "substack":
        likes = item.get("likes", 0) or 0
        restacks = item.get("restacks", 0) or 0
        comments = item.get("comments_count", 0) or 0
        signal = likes + restacks + comments
        return min(10, math.log10(signal + 1) * 3) if signal else 0
    if src == "medium":
        claps = item.get("claps", 0) or 0
        return min(10, math.log10(claps + 1) * 2.5) if claps else 0
    return 0

def compute_penalties(text_lower):
    p = 0
    if kw_any(text_lower, AI_HYPE_PHRASES):
        p += 25
    if kw_any(text_lower, CAREER_ADVICE_PHRASES):
        p += 25
    if kw_any(text_lower, FRONTEND_KEYWORDS):
        p += 10
    if kw_any(text_lower, MOBILE_KEYWORDS):
        p += 10
    if kw_any(text_lower, LIFESTYLE_KEYWORDS):
        p += 10
    return p

def score_v5(item, src):
    blob = get_text_blob(item, src)
    text_lower = blob.lower()
    title_lower = (get_title(item, src) or "").lower()
    universal = score_universal(item, src, text_lower, title_lower)
    identity = score_identity(text_lower)
    engagement = round(score_engagement(item, src), 1)
    penalty = compute_penalties(text_lower)
    raw = universal["total"] + identity["total"] + engagement - penalty
    affinity = float(SOURCE_AFFINITY.get(src, 1.0))
    final = max(0, min(100, raw * affinity))
    return {
        "final": round(final, 1),
        "universal": universal,
        "identity": identity,
        "engagement": engagement,
        "penalty": penalty,
        "blob": blob,
    }

# ---------------------------------------------------------------------------
# Topic + score-comment
# ---------------------------------------------------------------------------

def primary_topic(item, src, score_obj):
    text_lower = score_obj["blob"].lower()
    if score_obj["identity"]["projects_matched"]:
        return "project_" + score_obj["identity"]["projects_matched"][0].lower()
    if score_obj["identity"]["region_context"] >= 4:
        return "region"

    cands = {}
    raw = {
        "ai": kw_count(text_lower, AI_SUBSTRINGS) + bounded_count(text_lower, AI_BOUNDED),
        "data_engineering": kw_count(text_lower, DATA_ENG_SUBSTRINGS) + bounded_count(text_lower, DATA_ENG_BOUNDED),
        "system_design": kw_count(text_lower, SYSTEM_DESIGN_SUBSTRINGS) + bounded_count(text_lower, SYSTEM_DESIGN_BOUNDED),
        "devops": kw_count(text_lower, DEVOPS_SUBSTRINGS) + bounded_count(text_lower, DEVOPS_BOUNDED),
    }
    for k, v in raw.items():
        if v > 0:
            cands[k] = v

    if score_obj["universal"]["postmortem"] >= 5:
        cands["postmortem"] = max(cands.get("postmortem", 0), 4)

    title_lower = (get_title(item, src) or "").lower()
    if any(k in title_lower for k in ["career", "hiring", "interview", "junior", "senior eng", "60's"]):
        cands["career_culture"] = cands.get("career_culture", 0) + 3
    if any(k in title_lower for k in ["coinbase", "layoff", "merger", "acquisition", "ipo"]):
        cands["business_news"] = cands.get("business_news", 0) + 3

    if not cands:
        return "other"
    return max(cands, key=cands.get)

def score_to_grade(score):
    """0-100 → letter grade."""
    if score >= 35:
        return "S"
    if score >= 25:
        return "A"
    if score >= 18:
        return "B"
    if score >= 12:
        return "C"
    return "D"  # filtered from Top Shelf

def link_tags(score_obj):
    """Visible topic tags this item connects to. Multi-tag allowed."""
    ident = score_obj["identity"]
    tags = []
    # Project tags first (most specific)
    for p in ident["projects_matched"]:
        tags.append(p)
    # Identity dimensions, ordered by strength
    dim_pairs = [
        ("AI", ident["ai"], 5),
        ("Data Eng", ident["data_engineering"], 5),
        ("System Design", ident["system_design"], 4),
        ("DevOps", ident["devops"], 3),
        ("local", ident["region_context"], 3),
    ]
    dim_pairs.sort(key=lambda p: -p[1])
    for name, val, threshold in dim_pairs:
        if val >= threshold and name not in tags:
            tags.append(name)
    # Quality-signal tags (postmortem only — others are not "links" but signals)
    if score_obj["universal"]["postmortem"] >= 5:
        if "Postmortem" not in tags:
            tags.append("Postmortem")
    return tags[:4]  # cap at 4 tags

def grade_and_links_inline(score_obj):
    """Compact visible string: 'A · [AI] [System Design]' or 'C · no tags'."""
    grade = score_to_grade(score_obj["final"])
    tags = link_tags(score_obj)
    if tags:
        return f"**{grade}** · " + " ".join(f"`[{t}]`" for t in tags)
    return f"**{grade}** · _no link match_"

def x_media_tags(item, src):
    """Visible media/article signals for X candidates (v5.7) so the curating
    agent weighs demos, papers, articles and threads — not just text. Sourced
    from the x_observer.js enrichment fields; absent on pre-v5.7 dumps (returns
    []). `truncated` warns the visible text is partial (the source link has the
    rest)."""
    if src not in ("x_foryou", "x_following") or not isinstance(item, dict):
        return []
    tags = []
    if item.get("has_video"):
        tags.append("video")
    if item.get("is_article"):
        tags.append("article")
    dom = (item.get("link_domain") or "").strip()
    if dom:
        tags.append(f"→{dom}")
    if item.get("is_quote"):
        tags.append("quote")
    if (item.get("media_count") or 0) >= 2 or (item.get("has_image") and not item.get("has_video")):
        tags.append("img")
    if item.get("truncated"):
        tags.append("truncated")
    return tags[:4]

# ---------------------------------------------------------------------------
# Cross-source dedup
# ---------------------------------------------------------------------------

def normalize_title(t):
    return re.sub(r"[^\w\s]", "", (t or "").lower().strip())

def normalize_url(u):
    if not u:
        return ""
    u = u.split("?")[0].split("#")[0].rstrip("/").lower()
    return re.sub(r"^https?://(www\.)?", "", u)

def title_overlap_match(t1, t2):
    if not t1 or not t2:
        return False
    t1, t2 = normalize_title(t1), normalize_title(t2)
    if not t1 or not t2:
        return False
    if t1 == t2:
        return True
    short, lng = (t1, t2) if len(t1) <= len(t2) else (t2, t1)
    if short in lng and len(short) >= 0.8 * len(lng):
        return True
    w1, w2 = set(t1.split()), set(t2.split())
    if not w1 or not w2:
        return False
    inter = w1 & w2
    if len(inter) / min(len(w1), len(w2)) >= 0.8 and min(len(w1), len(w2)) >= 4:
        return True
    return False

def cross_source_dedup(entries):
    """entries: list of {item, src, score, ...}. Group dups, keep highest-score primary."""
    entries.sort(key=lambda e: -e["score"]["final"])
    groups = []
    for e in entries:
        title = get_title(e["item"], e["src"])
        nurl = normalize_url(get_url(e["item"], e["src"]))
        placed = False
        for g in groups:
            if nurl:
                for ge in g:
                    if normalize_url(get_url(ge["item"], ge["src"])) == nurl:
                        g.append(e); placed = True; break
                if placed:
                    break
            for ge in g:
                if title_overlap_match(title, get_title(ge["item"], ge["src"])):
                    g.append(e); placed = True; break
            if placed:
                break
        if not placed:
            groups.append([e])

    merged = []
    merged_count = 0
    for g in groups:
        g.sort(key=lambda e: -e["score"]["final"])
        primary = g[0]
        secondaries = g[1:]
        if secondaries:
            merged_count += len(secondaries)
            also = [(fmt_source_name(s["src"], s["item"]), fmt_engagement(s["item"], s["src"])) for s in secondaries]
            primary_item = dict(primary["item"]) if isinstance(primary["item"], dict) else {"_orig": primary["item"]}
            primary_item["_also_seen"] = also
            primary["item"] = primary_item
            # Boost score by 5% per secondary, capped at 4
            primary["score"]["final"] = min(100, primary["score"]["final"] * (1 + 0.05 * min(len(secondaries), 4)))
        merged.append(primary)
    return merged, merged_count

# ---------------------------------------------------------------------------
# Cross-day dedup — persistent seen-URL ledger (v5.4).
# Every displayed item is recorded forever in seen_ledger.jsonl. Anything with
# a record from a PRIOR date is dropped from the pool; same-date entries are
# ignored so a re-run on the same date is never self-suppressed.
# ---------------------------------------------------------------------------

LEDGER_PATH = Path(__file__).parent / CONFIG.get("dedup", {}).get("ledger_file", "seen_ledger.jsonl")

def parse_prior_digest_urls(digest_path):
    """Extract normalized URLs from a digest markdown (a ledger-rebuild helper; the daily run
    does not call it)."""
    urls = set()
    if not digest_path.exists():
        return urls
    text = digest_path.read_text()
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    wisdom_idx = text.find("\n## Wisdom")
    if wisdom_idx != -1:
        text = text[:wisdom_idx]
    for m in re.finditer(r"https?://\S+", text):
        urls.add(normalize_url(m.group(0).rstrip(").,;:>*_`'\"!")))
    return urls

def load_ledger():
    """Returns (prior_urls, prior_title_keys, all_urls). Prior = first_seen before DATE."""
    prior_urls, prior_title_keys, all_urls = set(), set(), set()
    if not LEDGER_PATH.exists():
        return prior_urls, prior_title_keys, all_urls
    for line in LEDGER_PATH.read_text().splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        u = rec.get("u", "")
        if u:
            all_urls.add(u)
        if rec.get("first_seen", "") < DATE:
            if u:
                prior_urls.add(u)
            if rec.get("t") and rec.get("a"):
                prior_title_keys.add((rec["t"], rec["a"]))
    return prior_urls, prior_title_keys, all_urls

# ---------------------------------------------------------------------------
# Hook formatting
# ---------------------------------------------------------------------------

def _clean_text(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = _html.unescape(s)
    s = (s.replace("&#x2F;", "/").replace("&#x27;", "'")
         .replace("&quot;", '"').replace("&amp;", "&")
         .replace("&gt;", ">").replace("&lt;", "<"))
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _truncate_at_sentence(s, cap):
    if len(s) <= cap:
        return s
    s = s[:cap]
    half = cap // 2
    for sep in (". ", "! ", "? ", "; "):
        idx = s.rfind(sep, half)
        if idx != -1:
            return s[:idx + 1]
    sp = s.rfind(" ")
    return (s[:sp] if sp > half else s).rstrip(".,;:!?") + "…"

def make_hook(item, src, cap):
    text = ""
    if src == "reddit":
        text = (item.get("selftext") or "").strip().split("\n")[0]
    elif src == "hn":
        cs = item.get("comments", []) or []
        if cs and isinstance(cs[0], dict):
            text = (cs[0].get("text") or "").strip()
    elif src in ("x_foryou", "x_following"):
        text = (item.get("text") or "").strip()
    elif src == "substack":
        text = (item.get("body") or item.get("subtitle") or "").strip()
    elif src == "medium":
        text = (item.get("body") or item.get("subtitle") or "").strip()
    elif src == "github":
        text = (item.get("desc") or item.get("description") or "").strip()
    text = _clean_text(text)
    return _truncate_at_sentence(text, cap)

# ---------------------------------------------------------------------------
# Section assembly: News Wire
# ---------------------------------------------------------------------------

def src_bucket(s):
    return "x" if s in ("x_foryou", "x_following") else s

# ---------------------------------------------------------------------------
# Citation system — every displayed entry gets a stable [src-N] tag.
# Used by the Hot Topics section (Claude-filled, not script-detected).
# ---------------------------------------------------------------------------

CITATION_SHORT = {
    "hn": "hn",
    "reddit": "r",
    "github": "gh",
    "x_foryou": "x",
    "x_following": "x",
    "substack": "sub",
    "medium": "m",
}

def assign_citations(*entry_lists):
    """Walk entries in display order; assign each a citation like 'hn-3' or 'r-12'.

    Returns dict {id(entry): "hn-3", ...}. Each source has its own counter.
    Counters reset per source. Order = News Wire → Top Shelf → Feed.
    """
    counters = Counter()
    citations = {}
    for entries in entry_lists:
        for e in entries:
            if id(e) in citations:
                continue  # already assigned (cross-section overlap, shouldn't happen)
            short = CITATION_SHORT.get(e["src"], e["src"])
            counters[short] += 1
            citations[id(e)] = f"{short}-{counters[short]}"
    return citations

def anti_cluster_reorder(items, max_consecutive=2):
    """Reorder a score-sorted list to break runs of >max_consecutive same-source items.

    Walks score-sorted, but if last `max_consecutive` items share a source bucket,
    pulls forward the next non-same-source item from up to `lookahead` positions.
    Preserves score order otherwise. Light visual interleave, not a full shuffle.
    """
    if len(items) <= max_consecutive:
        return list(items)
    pool = list(items)
    out = []
    while pool:
        if len(out) < max_consecutive:
            out.append(pool.pop(0))
            continue
        last_buckets = [src_bucket(e["src"]) for e in out[-max_consecutive:]]
        if len(set(last_buckets)) == 1:
            current_bucket = last_buckets[0]
            # Find next item with different source bucket within next 5 positions
            chosen = -1
            for i, e in enumerate(pool[:6]):
                if src_bucket(e["src"]) != current_bucket:
                    chosen = i
                    break
            if chosen >= 0:
                out.append(pool.pop(chosen))
            else:
                out.append(pool.pop(0))
        else:
            out.append(pool.pop(0))
    return out

def has_min_quality(e, min_universal=8, min_or_identity=4):
    """Substantive enough for News Wire mandate. Joke tweets / single-axis-noise items fail."""
    s = e["score"]
    return s["universal"]["total"] >= min_universal or s["identity"]["total"] >= min_or_identity

def wire_trend_score(e):
    """General-trend signal: cross-source convergence + engagement. NO identity term.

    The wire is the day's tech-world brief, not a personalized pick — what is
    everyone talking about, regardless of whether it maps to John's stack.
    """
    s = e["score"]
    item = e["item"] if isinstance(e["item"], dict) else {}
    convergence = min(len(item.get("_also_seen") or []), 3)
    eng = s["engagement"]
    if e["src"] in ("x_foryou", "x_following"):
        # views are X's best trend proxy; likes-based engagement undercounts reach
        views = _num(item.get("views"))
        eng = max(eng, min(10, math.log10(views + 1) * 1.3))
    return 3.0 * convergence + 2.0 * eng + 0.3 * s["universal"]["total"]

def build_news_wire_general(pool, n=12, x_share=0.55):
    """GENERAL tech-world brief (v5.4): trend/engagement-ranked, X-majority.

    Deliberately dropped vs the old build_news_wire: the identity score term,
    the local guarantee, the project guarantee. Personalization lives in
    Top Shelf / Feed; the wire answers "what happened in tech today".
    """
    scored = sorted(((wire_trend_score(e), e) for e in pool), key=lambda t: -t[0])

    def qualifies(e):
        # Tech-relevance gate, NOT personalization: the topic keyword scores
        # double as an "is this tech?" detector. Without it, raw engagement
        # ranking fills the wire with whatever is viral on X (sports, celebs).
        s = e["score"]
        return s["universal"]["total"] >= 4 or s["identity"]["total"] >= 4

    out, used = [], set()
    x_min = math.ceil(n * x_share)  # ~7 of 12 from X — the trend firehose

    # Phase 1: top X items by trend score
    for ws, e in scored:
        if sum(1 for o in out if src_bucket(o["src"]) == "x") >= x_min:
            break
        if src_bucket(e["src"]) == "x" and qualifies(e) and id(e) not in used:
            out.append(e)
            used.add(id(e))

    # Phase 2: one each from hn / reddit / github (best by trend score, if available)
    for req in ("hn", "reddit", "github"):
        for ws, e in scored:
            if id(e) in used or src_bucket(e["src"]) != req or not qualifies(e):
                continue
            out.append(e)
            used.add(id(e))
            break

    # Phase 3: fill remaining purely by trend score, max 2 per non-X bucket
    non_x_counts = Counter(src_bucket(e["src"]) for e in out if src_bucket(e["src"]) != "x")
    for ws, e in scored:
        if len(out) >= n:
            break
        if id(e) in used or not qualifies(e):
            continue
        b = src_bucket(e["src"])
        if b != "x" and non_x_counts[b] >= 2:
            continue
        out.append(e)
        used.add(id(e))
        if b != "x":
            non_x_counts[b] += 1

    out.sort(key=lambda e: -wire_trend_score(e))
    return out[:n]

# ---------------------------------------------------------------------------
# Section assembly: Top Shelf
# ---------------------------------------------------------------------------

def is_identity_match(e):
    ident = e["score"]["identity"]
    return (ident["active_project"] >= 5 or
            ident["region_context"] >= 5 or
            (ident["ai"] + ident["data_engineering"] + ident["system_design"] + ident["devops"]) >= 5)


def is_on_beat(e):
    """On the DAILY beat: AI / data-eng / system-design / devops, or an active project.

    Deliberately EXCLUDES the region_context dimension (regional is out of the news beat) and
    pure-engagement virality — so the X-share rebalance can only pull genuinely on-beat X, not
    regional-institutional, finance, or viral-meme junk that the quality filters normally suppress.
    """
    ident = e["score"]["identity"]
    return ((ident["ai"] + ident["data_engineering"] + ident["system_design"] + ident["devops"]) >= 5
            or ident["active_project"] >= 5)

def build_top_shelf(pool, used_in_news_wire, n=30, min_score=12):
    """Top Shelf: cross-source ranked, diversity-enforced, score floor.

    Constraints:
      - score >= min_score (filter weak fillers; better to have 24 great than 30 mediocre)
      - max 4 items per topic (avoid r/ClaudeCode-style monoculture)
      - max ceil(n * MAX_SOURCE_PCT) items per source bucket (proportional, not hardcoded)
      - min 1 item per source bucket if any in pool (mandatory cross-source mix)
      - ≥50% identity-matched (project / AI / DE / SysDesign / DevOps)
    """
    used_ids = {id(e) for e in used_in_news_wire}
    candidates = [e for e in pool if id(e) not in used_ids and e["score"]["final"] >= min_score]
    candidates.sort(key=lambda e: -e["score"]["final"])

    MAX_TOPIC = 4
    MAX_SOURCE = max(3, math.ceil(n * MAX_SOURCE_PCT))

    # Phase 1: mandatory source representation — pull top item per source bucket
    out = []
    overflow_set = set()  # ids that are explicitly bumped from greedy
    topic_counts = Counter()
    src_counts = Counter()
    used_in_top = set()

    available_buckets = set(src_bucket(e["src"]) for e in candidates)
    # Priority order for mandatory representation
    priority_buckets = ["hn", "reddit", "x", "github", "substack", "medium"]
    for b in priority_buckets:
        if b not in available_buckets:
            continue
        for e in candidates:
            if id(e) in used_in_top:
                continue
            if src_bucket(e["src"]) != b:
                continue
            topic = e["topic"]
            # Even mandatory picks respect topic cap (relaxed: max+1 acceptable for mandate)
            if topic_counts[topic] >= MAX_TOPIC:
                continue
            out.append(e)
            used_in_top.add(id(e))
            topic_counts[topic] += 1
            src_counts[b] += 1
            break  # 1 per bucket in this phase

    # Phase 2: greedy fill respecting both caps
    for e in candidates:
        if len(out) >= n:
            break
        if id(e) in used_in_top:
            continue
        topic = e["topic"]
        b = src_bucket(e["src"])
        if topic_counts[topic] >= MAX_TOPIC:
            continue
        if src_counts[b] >= MAX_SOURCE:
            continue
        out.append(e)
        used_in_top.add(id(e))
        topic_counts[topic] += 1
        src_counts[b] += 1

    # Phase 2.5: top-up if under target — relax topic cap by +1 to fill
    if len(out) < n:
        for e in candidates:
            if len(out) >= n:
                break
            if id(e) in used_in_top:
                continue
            topic = e["topic"]
            b = src_bucket(e["src"])
            if topic_counts[topic] >= MAX_TOPIC + 2:  # relaxed
                continue
            if src_counts[b] >= MAX_SOURCE:
                continue
            out.append(e)
            used_in_top.add(id(e))
            topic_counts[topic] += 1
            src_counts[b] += 1

    overflow = [e for e in candidates if id(e) not in used_in_top]

    # Phase 3: enforce ≥50% identity match via swaps
    target_identity = max(0, n // 2)
    current_identity = sum(1 for e in out if is_identity_match(e))
    if current_identity < target_identity:
        ident_overflow = [e for e in overflow if is_identity_match(e)]
        ident_overflow.sort(key=lambda e: -e["score"]["final"])
        non_ident_in_out = [e for e in out if not is_identity_match(e)]
        non_ident_in_out.sort(key=lambda e: e["score"]["final"])  # weakest first

        for repl in list(ident_overflow):
            if current_identity >= target_identity:
                break
            if not non_ident_in_out:
                break
            for victim in list(non_ident_in_out):
                new_topic = repl["topic"]
                new_src = src_bucket(repl["src"])
                old_topic = victim["topic"]
                old_src = src_bucket(victim["src"])
                # Counts after swap
                if new_topic == old_topic:
                    after_topic = topic_counts[new_topic]
                else:
                    after_topic = topic_counts[new_topic] + 1
                if new_src == old_src:
                    after_src = src_counts[new_src]
                else:
                    after_src = src_counts[new_src] + 1
                # Source mandate must hold: old_src must have > 1 if removing it
                if new_src != old_src and src_counts[old_src] - 1 < 1:
                    continue
                if after_topic <= MAX_TOPIC and after_src <= MAX_SOURCE:
                    out.remove(victim)
                    overflow.append(victim)
                    out.append(repl)
                    if repl in overflow:
                        overflow.remove(repl)
                    # Update counts correctly (only adjust differing keys)
                    if new_topic != old_topic:
                        topic_counts[new_topic] = after_topic
                        topic_counts[old_topic] -= 1
                    if new_src != old_src:
                        src_counts[new_src] = after_src
                        src_counts[old_src] -= 1
                    non_ident_in_out.remove(victim)
                    current_identity += 1
                    break

    out.sort(key=lambda e: -e["score"]["final"])
    return out, overflow

# ---------------------------------------------------------------------------
# Section assembly: Feed
# ---------------------------------------------------------------------------

def build_feed(pool, used_ids, target=60):
    """Feed: score-ranked, with proportional per-source soft cap.

    Without a cap, the highest-scoring source sweeps the entire 60-slot feed.
    Cap at ceil(target * MAX_SOURCE_PCT); relax to 1.5x if under target.
    """
    candidates = [e for e in pool if id(e) not in used_ids]
    candidates.sort(key=lambda e: -e["score"]["final"])
    max_per_src = max(8, math.ceil(target * MAX_SOURCE_PCT))
    out = []
    chosen_ids = set()
    src_counts = Counter()
    for e in candidates:
        if len(out) >= target:
            break
        b = src_bucket(e["src"])
        if src_counts[b] >= max_per_src:
            continue
        out.append(e)
        chosen_ids.add(id(e))
        src_counts[b] += 1
    if len(out) < target:
        relaxed = math.ceil(max_per_src * 1.5)
        for e in candidates:
            if len(out) >= target:
                break
            if id(e) in chosen_ids:
                continue
            b = src_bucket(e["src"])
            if src_counts[b] >= relaxed:
                continue
            out.append(e)
            chosen_ids.add(id(e))
            src_counts[b] += 1
    return out


def rebalance_x_share(top_shelf, feed, pool, lo, hi, reserved_ids):
    """Flex the Feed so the personalized body (Top Shelf + Feed) leans to the UPPER end of the
    lo..hi X-share band — X is John's primary channel, so we want more of it.

    X is John's primary collection channel, so the daily should reflect that. News Wire is
    excluded (it is already X-majority by design and would only push the overall higher) and
    Top Shelf is left untouched (quality-curated + anti-clustered). Only the pure-score Feed
    flexes: when X is under the band we swap the lowest-scoring non-X feed items for the
    highest-scoring unused X items in the pool that are ON-BEAT (is_on_beat — overriding the
    per-source soft cap for X, but never padding with regional/finance/viral X junk); when X is over
    the band we do the reverse. Feed size is preserved. On throttled-X days there may not be
    enough on-beat X to reach the floor — the band is a target, not a guarantee, and a clean
    sub-floor day beats a padded junk day.

    Returns (new_feed, body_x_share).
    """
    feed = list(feed)
    is_x = lambda e: src_bucket(e["src"]) == "x"
    used = set(reserved_ids) | {id(e) for e in top_shelf} | {id(e) for e in feed}

    def share():
        body = list(top_shelf) + feed
        return (sum(1 for e in body if is_x(e)) / len(body)) if body else 0.0

    cur = share()
    if cur < hi:
        # Lean to the UPPER end of the band — John's primary channel is X, so add on-beat X
        # up toward `hi`, not just until the `lo` floor. The is_on_beat gate keeps it clean, so on
        # a thin/throttled-X day this naturally stops below the band rather than padding with junk.
        spare = sorted((e for e in pool if is_x(e) and id(e) not in used and is_on_beat(e)),
                       key=lambda e: -e["score"]["final"])
        while cur < hi and spare:
            non_x = [e for e in feed if not is_x(e)]
            if not non_x:
                break
            victim = min(non_x, key=lambda e: e["score"]["final"])
            add = spare.pop(0)
            feed[feed.index(victim)] = add
            used.add(id(add))
            cur = share()
    elif cur > hi:
        spare = sorted((e for e in pool if not is_x(e) and id(e) not in used),
                       key=lambda e: -e["score"]["final"])
        while cur > hi and spare:
            x_in = [e for e in feed if is_x(e)]
            if not x_in:
                break
            victim = min(x_in, key=lambda e: e["score"]["final"])
            add = spare.pop(0)
            feed[feed.index(victim)] = add
            used.add(id(add))
            cur = share()
    return feed, cur

# ---------------------------------------------------------------------------
# Section assembly: Wisdom
# ---------------------------------------------------------------------------

def is_wisdom_text(text):
    if not text:
        return False
    text = text.strip()
    if len(text) < 80 or len(text) > 400:
        return False
    if text.startswith("http"):
        return False
    return True

def extract_wisdom_text(item, src):
    if src in ("x_foryou", "x_following"):
        return (item.get("text") or "").strip()
    if src == "reddit":
        # Try selftext first paragraph, fallback to top comment
        st = (item.get("selftext") or "").strip()
        if st:
            return st.split("\n\n")[0]
        cs = item.get("comments", []) or []
        if cs and isinstance(cs[0], dict):
            return (cs[0].get("text") or "").strip().split("\n")[0]
    if src == "hn":
        cs = item.get("comments", []) or []
        if cs and isinstance(cs[0], dict):
            return _clean_text((cs[0].get("text") or "").strip())
    if src == "substack":
        return (item.get("body") or item.get("subtitle") or "").strip()
    if src == "medium":
        return (item.get("body") or item.get("subtitle") or "").strip()
    if src == "github":
        return (item.get("desc") or item.get("description") or "").strip()
    return ""

def categorize_wisdom(item, src, score_obj):
    """Bucket: postmortem | architecture | product | other."""
    if score_obj["universal"]["postmortem"] >= 5 or score_obj["universal"]["contrarian_evidence"] >= 4:
        return "postmortem_contrarian"
    ident = score_obj["identity"]
    if ident["system_design"] >= 4 or ident["devops"] >= 4 or ident["data_engineering"] >= 6:
        return "architecture"
    if score_obj["universal"]["teaches"] >= 6 or ident["ai"] >= 6:
        return "product_leadership"
    return "other"

def build_wisdom(pool, used_ids, prior_wisdom_norms, k=3):
    candidates = []
    for e in pool:
        if id(e) in used_ids:
            continue
        text = extract_wisdom_text(e["item"], e["src"])
        text = _clean_text(text)
        if not is_wisdom_text(text):
            continue
        s = e["score"]
        if not (s["universal"]["teaches"] >= 6 or
                s["universal"]["postmortem"] >= 5 or
                s["universal"]["contrarian_evidence"] >= 4 or
                s["identity"]["total"] >= 12):
            continue
        norm = normalize_title(text)
        if norm in prior_wisdom_norms:
            continue
        category = categorize_wisdom(e["item"], e["src"], s)
        candidates.append({"entry": e, "text": text, "category": category, "norm": norm})

    # Diversify: pick 1 from each preferred category, fill rest by score
    by_cat = {"postmortem_contrarian": [], "architecture": [], "product_leadership": [], "other": []}
    for c in candidates:
        by_cat[c["category"]].append(c)
    for cat in by_cat:
        by_cat[cat].sort(key=lambda c: -c["entry"]["score"]["final"])

    picked = []
    seen_norms = set()
    for cat in ["postmortem_contrarian", "architecture", "product_leadership"]:
        if len(picked) >= k:
            break
        for c in by_cat[cat]:
            if c["norm"] in seen_norms:
                continue
            picked.append(c)
            seen_norms.add(c["norm"])
            break

    if len(picked) < k:
        rest = [c for cat in by_cat for c in by_cat[cat] if c["norm"] not in seen_norms]
        rest.sort(key=lambda c: -c["entry"]["score"]["final"])
        for c in rest:
            if len(picked) >= k:
                break
            picked.append(c)
            seen_norms.add(c["norm"])

    return picked[:k]

# ---------------------------------------------------------------------------
# Section assembly: Deep Dive
# ---------------------------------------------------------------------------

def build_deep_dive(pool, used_in_top_shelf_ids, k=3):
    candidates = []
    for e in pool:
        if id(e) not in used_in_top_shelf_ids:
            continue
        s = e["score"]
        # Long-form filter
        body_len = len(s["blob"])
        if body_len < 400:
            continue
        if s["identity"]["total"] < 10:
            continue
        if s["universal"]["artifact"] < 4:
            continue
        candidates.append(e)
    candidates.sort(key=lambda e: -e["score"]["final"])

    if not candidates:
        return []

    primary = candidates[0]
    primary_topic_val = primary["topic"]
    rest = []
    seen_topics = {primary_topic_val}
    for e in candidates[1:]:
        if e["topic"] in seen_topics:
            continue
        rest.append(e)
        seen_topics.add(e["topic"])
        if len(rest) >= k - 1:
            break

    return [primary] + rest

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

print(f"V5 Presentation — date={DATE}, out={OUT_PATH.name}")

# Load all dumps
hn_data = load_json("hn.json", {})
hn_items = hn_data.get("items", []) if isinstance(hn_data, dict) else hn_data
reddit_data = load_json("reddit.json", {})
reddit_items = reddit_data.get("items", []) if isinstance(reddit_data, dict) else reddit_data
github_data = load_json("github.json", {})
github_items = github_data.get("items", []) if isinstance(github_data, dict) else github_data
substack_items = load_json("substack.json", [])
medium_items = load_json("medium.json", [])
# X For You / Following: attempts files preferred (multi-window collection),
# but fall back to merged single-file dump if attempts aren't present.
x_foryou_items = merge_attempts("x_foryou", 6)  # v5.1 supports up to 6 windows
if not x_foryou_items:
    raw = load_json("x_foryou.json", [])
    x_foryou_items = raw.get("items", []) if isinstance(raw, dict) else raw
x_following_items = merge_attempts("x_following", 3)
if not x_following_items:
    raw = load_json("x_following.json", [])
    x_following_items = raw.get("items", []) if isinstance(raw, dict) else raw

print(f"Loaded: HN={len(hn_items)}, Reddit={len(reddit_items)}, GitHub={len(github_items)}, "
      f"Substack={len(substack_items)}, Medium={len(medium_items)}, "
      f"X For You={len(x_foryou_items)}, X Following={len(x_following_items)}")

# ---------------------------------------------------------------------------
# Build initial pool: hard-filter + score
# ---------------------------------------------------------------------------

raw_pool = []
hard_filtered_count = 0

def add_items(items, src):
    global hard_filtered_count
    for it in items:
        if not isinstance(it, dict):
            continue
        blob = get_text_blob(it, src)
        text_lower = blob.lower()
        if is_hard_filtered(it, src, text_lower):
            hard_filtered_count += 1
            continue
        score = score_v5(it, src)
        if score["final"] <= 0:
            continue
        topic = primary_topic(it, src, score)
        raw_pool.append({"item": it, "src": src, "score": score, "topic": topic})

add_items(hn_items, "hn")
add_items(reddit_items, "reddit")
add_items(github_items, "github")
add_items(x_foryou_items, "x_foryou")
add_items(x_following_items, "x_following")
add_items(substack_items, "substack")
add_items(medium_items, "medium")

pool_identity = sum(1 for e in raw_pool if is_identity_match(e))
print(f"Pool after hard-filter + score: {len(raw_pool)} (dropped {hard_filtered_count} hard-filtered, "
      f"{pool_identity} identity-matched = {100*pool_identity//max(1,len(raw_pool))}%)")

# ---------------------------------------------------------------------------
# Cross-source dedup
# ---------------------------------------------------------------------------

merged_pool, cross_source_merged_count = cross_source_dedup(raw_pool)
print(f"Cross-source dedup: merged {cross_source_merged_count} duplicates")

# ---------------------------------------------------------------------------
# Cross-day dedup
# ---------------------------------------------------------------------------

ledger_prior_urls, ledger_title_keys, ledger_all_urls = load_ledger()
print(f"Ledger: {len(ledger_prior_urls)} prior URLs ({LEDGER_PATH.name})")

cross_day_dropped = 0
final_pool = []
for e in merged_pool:
    u = normalize_url(get_url(e["item"], e["src"]))
    tkey = (normalize_title(get_title(e["item"], e["src"])),
            (get_author(e["item"], e["src"]) or "").lower())
    if (u and u in ledger_prior_urls) or (tkey[0] and tkey[1] and tkey in ledger_title_keys):
        cross_day_dropped += 1
        continue
    final_pool.append(e)

print(f"Cross-day dedup: dropped {cross_day_dropped} items already in the ledger")
print(f"Final pool size: {len(final_pool)}")

# Sort globally by final score
final_pool.sort(key=lambda e: -e["score"]["final"])

# Cap GitHub items in the pool. GitHub Trending is pre-filtered (~12/day);
# without a digest-wide ceiling it overrepresents. Keep top GITHUB_MAX by
# score; drop the rest before any section sees them.
_gh_in_pool = [e for e in final_pool if e["src"] == "github"]
if len(_gh_in_pool) > GITHUB_MAX:
    _gh_in_pool.sort(key=lambda e: -e["score"]["final"])
    _gh_drop_ids = {id(e) for e in _gh_in_pool[GITHUB_MAX:]}
    final_pool = [e for e in final_pool if id(e) not in _gh_drop_ids]
    print(f"GitHub cap: kept top {GITHUB_MAX} of {len(_gh_in_pool)}; dropped {len(_gh_drop_ids)}")

# ---------------------------------------------------------------------------
# Build sections
# ---------------------------------------------------------------------------

_nw_count_range = CONFIG.get("output", {}).get("news_wire_count", [10, 15])
_ts_count_range = CONFIG.get("output", {}).get("top_shelf_count", [20, 30])
_feed_target = int(CONFIG.get("output", {}).get("feed_count", 60))
NEWS_WIRE_N = int(_nw_count_range[1] if isinstance(_nw_count_range, list) else _nw_count_range)
TOP_SHELF_N = int(_ts_count_range[1] if isinstance(_ts_count_range, list) else _ts_count_range)

# Overselect: the keyword gate can't fully judge "is this tech news" (viral
# politics/sports leak through false-positive matches). Claude trims the
# candidate list to the best NEWS_WIRE_N during post-fill.
news_wire_picks = build_news_wire_general(final_pool, n=NEWS_WIRE_N + 6)
news_wire_ids = {id(e) for e in news_wire_picks}
print(f"News Wire (general): {len(news_wire_picks)} candidates (Claude trims to ≤{NEWS_WIRE_N})")

# Top Shelf takes from items NOT in news wire
top_shelf_picks, top_shelf_overflow = build_top_shelf(final_pool, news_wire_picks, n=TOP_SHELF_N)
top_shelf_ids = {id(e) for e in top_shelf_picks}
print(f"Top Shelf: {len(top_shelf_picks)} picks (overflow: {len(top_shelf_overflow)})")

# Anti-cluster reorder for visual diversity (preserves score-sort except where >2 same-source consecutive)
top_shelf_picks = anti_cluster_reorder(top_shelf_picks, max_consecutive=2)
# News Wire is NOT reordered (v5.4) — it's X-majority by design; breaking runs would fight that.

used_so_far = news_wire_ids | top_shelf_ids
feed_picks = build_feed(final_pool, used_so_far, target=_feed_target)
print(f"Feed: {len(feed_picks)} picks")

# X-share target: X is John's primary collection channel, so flex the Feed to keep the
# personalized body (Top Shelf + Feed) inside the configured X band. News Wire is already
# X-majority and excluded; Top Shelf is untouched.
feed_picks, _body_x_share = rebalance_x_share(
    top_shelf_picks, feed_picks, final_pool, X_SHARE_LO, X_SHARE_HI, news_wire_ids)
print(f"Feed after X-rebalance: {len(feed_picks)} picks · "
      f"body X-share {_body_x_share:.0%} (target {X_SHARE_LO:.0%}-{X_SHARE_HI:.0%})")

all_used_ids = used_so_far | {id(e) for e in feed_picks}

# Wisdom can pull from anywhere in pool (incl items already shown)
prior_wisdom_norms = set()  # TODO: parse from prior digests if needed
wisdom_picks = build_wisdom(final_pool, set(), prior_wisdom_norms, k=3)
print(f"Wisdom: {len(wisdom_picks)} picks")

deep_dive_picks = build_deep_dive(final_pool, top_shelf_ids, k=3)
print(f"Deep Dive: {len(deep_dive_picks)} candidates")

# ---------------------------------------------------------------------------
# Build markdown output
# ---------------------------------------------------------------------------

# Counts
HN_COUNT = len(hn_items); RED_COUNT = len(reddit_items); GH_COUNT = len(github_items)
SUB_COUNT = len(substack_items); MED_COUNT = len(medium_items)
XF_COUNT = len(x_foryou_items); XFL_COUNT = len(x_following_items)

# Status thresholds derive from config targets (×0.9) so a retarget never desyncs them.
_SRC_CFG = CONFIG.get("sources", {}) or {}

def _ok_floor(key, default_target):
    t = int((_SRC_CFG.get(key, {}) or {}).get("target", default_target))
    return math.ceil(t * 0.9)

_xf_cfg = _SRC_CFG.get("x_foryou", {}) or {}
_XF_OK = int(_xf_cfg.get("success_threshold", _ok_floor("x_foryou", 600)))
_XF_BURN = int((_xf_cfg.get("burn_detection", {}) or {}).get("confirmed_burn_yield", 60))
XF_STATUS = "ok" if XF_COUNT >= _XF_OK else ("partial" if XF_COUNT >= _XF_BURN else "session_burned")
XFL_STATUS = "ok" if XFL_COUNT >= _ok_floor("x_following", 180) else "partial"
SUB_STATUS = "ok" if SUB_COUNT >= _ok_floor("substack", 200) else "partial"
MED_STATUS = "ok" if MED_COUNT >= _ok_floor("medium", 30) else "partial"
GH_STATUS = "ok" if GH_COUNT >= _ok_floor("github_trending", 20) else "partial"

XF_ATTEMPTS = attempts_count("x_foryou", 3) or 1
XFL_ATTEMPTS = attempts_count("x_following", 2) or 1

NEWS_WIRE_TRIM_TO = NEWS_WIRE_N  # Claude trims candidates down to this
TOP_SHELF_N = len(top_shelf_picks)
FEED_N = len(feed_picks)
WISDOM_N = len(wisdom_picks)
DEEP_DIVE_N = len(deep_dive_picks)

# Citation IDs — assigned in display order across News Wire → Top Shelf → Feed.
citations = assign_citations(news_wire_picks, top_shelf_picks, feed_picks)

# Per-source breakdown of items actually displayed in the digest (NW + Top Shelf + Feed)
displayed_src_counts = Counter()
for e in list(news_wire_picks) + list(top_shelf_picks) + list(feed_picks):
    short = CITATION_SHORT.get(e["src"], e["src"])
    displayed_src_counts[short] += 1

# X total = x_foryou + x_following collected
X_TOTAL = XF_COUNT + XFL_COUNT

header = f"""---
date: {DATE}
---

|               |  x  | sub |  m  |  hn |  r  | gh  |
|---------------|----:|----:|----:|----:|----:|----:|
| **collected** | {X_TOTAL:>3} | {SUB_COUNT:>3} | {MED_COUNT:>3} | {HN_COUNT:>3} | {RED_COUNT:>3} | {GH_COUNT:>3} |
| **in digest** | {displayed_src_counts['x']:>3} | {displayed_src_counts['sub']:>3} | {displayed_src_counts['m']:>3} | {displayed_src_counts['hn']:>3} | {displayed_src_counts['r']:>3} | {displayed_src_counts['gh']:>3} |

**Sections:** news_wire: <CLAUDE_FILL_NW_COUNT> · hot_topics: <CLAUDE_FILL_HT_COUNT> · top_shelf: {TOP_SHELF_N} · feed: {FEED_N} · wisdom: {WISDOM_N} · deep_dive: {DEEP_DIVE_N}

"""

# News Wire — GENERAL tech-world brief (v5.4)
STALE_LABEL_DAYS = int(CONFIG.get("dedup", {}).get("stale_label_days", 3))

def stale_date_label(e):
    """'· *published YYYY-MM-DD*' when the item is older than STALE_LABEL_DAYS, else ''."""
    pub = get_pub_date(e["item"] if isinstance(e["item"], dict) else {}, e["src"])
    if not pub:
        return ""
    from datetime import date as _date
    try:
        age = (_date.fromisoformat(DATE) - _date.fromisoformat(pub)).days
    except ValueError:
        return ""
    return f" · *published {pub}*" if age > STALE_LABEL_DAYS else ""

news_wire_lines = [
    "## News Wire", "",
    "<!-- CLAUDE INSTRUCTIONS (News Wire — voice differs from gem hooks):",
    "This section is a GENERAL brief: what is the tech world talking about today.",
    f"The script overselected ~{len(news_wire_picks)} candidates by trend signal; keyword",
    "gates can't judge newsworthiness. YOUR FIRST JOB IS EDITORIAL:",
    f"1. DELETE candidate bullets that are not tech news — viral sports, celebrity,",
    "   engagement-bait, ads. (Up to 1-2 genuinely major world events may stay if",
    f"   today demands it.) Keep at most {NEWS_WIRE_TRIM_TO}, prefer fewer over filler.",
    "2. For each kept item write ONE neutral newsroom sentence under it: the",
    "   concrete event/claim + why the tech world cares. NO ties to John's",
    "   projects or interests, NO second person, no advice, no hedging.",
    "   Wire-service abstract, not a personal note.",
    "3. Set news_wire: <count of kept items> in the Sections line up top",
    "   (replace CLAUDE_FILL_NW_COUNT).",
    "Delete this comment block when done. -->",
    "",
]
for e in news_wire_picks:
    item = e["item"]; src = e["src"]; s = e["score"]
    title = get_title(item, src)
    if not title:
        continue
    url = get_url(item, src)
    cite = citations.get(id(e), "")
    cite_part = f" `[{cite}]`" if cite else ""
    grade = score_to_grade(s["final"])
    tags = link_tags(s)
    tag_part = " · " + " ".join(f"`[{t}]`" for t in tags) if tags else ""
    title_link = f"[{title.strip()[:160]}]({url})" if url else f"**{title.strip()[:160]}**"
    news_wire_lines.append(
        f"- **{title_link}**{cite_part} · **{grade}**{tag_part}{stale_date_label(e)}"
        f"\n  > <CLAUDE_FILL_WIRE_BRIEF>"
    )
news_wire_lines.append("")

# ---------------------------------------------------------------------------
# Hot Topics — Claude-filled section. Script provides scaffold + instructions.
# ---------------------------------------------------------------------------
hot_topics_lines = [
    "---",
    "",
    "## Hot Topics",
    "",
    "<!-- CLAUDE INSTRUCTIONS:",
    "Read every item across News Wire, Top Shelf, and Feed below. Identify 1–3 dominant",
    "themes that ACTUALLY emerged today (not pre-defined keyword buckets). A theme",
    "qualifies only if ≥5 items converge on the same story/release/incident/pattern.",
    "Skip the section entirely if no clear hot topic — quiet days are real.",
    "",
    "For each hot topic, write:",
    "  ### <one-line title that names the theme>",
    "  <2–3 paragraph synthesis: what's the story, why it matters today, what to take away>",
    "  **sources:** [hn-3](url), [r-12](url), [x-1](url), …  (use the citation IDs printed",
    "  next to each item, in markdown-link form pointing to that item's URL)",
    "",
    "Replace this whole comment + the placeholder below with your filled output. -->",
    "",
    "<CLAUDE_FILL_HOT_TOPICS>",
    "",
]

# Gems: Top Shelf + Feed
def gem_heading_label(src, item):
    """Single author/source label for the heading row.

    Citation tag (e.g. `[sub-1]`, `[r-5]`) already encodes the source, so we
    don't add a `(Substack)` / `(Medium)` qualifier — that's redundant noise.
    """
    if src in ("x_foryou", "x_following"):
        h = item.get("handle", "").lstrip("@")
        return f"@{h}" if h else "X"
    if src == "hn":
        return "HN"
    if src == "reddit":
        permalink = item.get("permalink") or ""
        sub = item.get("subreddit", "") or item.get("sub", "") or (
            permalink.split("/r/")[1].split("/")[0] if "/r/" in permalink else ""
        )
        return f"r/{sub}" if sub else "Reddit"
    if src == "github":
        return item.get("name") or item.get("repo") or "GitHub"
    if src == "substack":
        return item.get("author", "") or "Substack"
    if src == "medium":
        return item.get("author", "") or "Medium"
    return src

def emit_gem(out, n, e, tier):
    item = e["item"]; src = e["src"]; s = e["score"]
    title = get_title(item, src)
    if not title:
        return False

    label = gem_heading_label(src, item)
    url = get_url(item, src)
    cite = citations.get(id(e), "")
    grade = score_to_grade(s["final"])
    tags = link_tags(s)

    # Heading row: #N · author/source · grade
    # Engagement counts (likes/points/comments) are scoring inputs, not reader inputs —
    # the grade already captures that signal. Keep the heading clean.
    # Old-but-unseen items (passed the ledger once) carry their real publish date.
    heading = f"**#{n}** · **{label}** · {grade}{stale_date_label(e)}"

    # Meta row: tags · media · cite (no engagement)
    meta_parts = []
    if tags:
        meta_parts.append(" ".join(f"`[{t}]`" for t in tags))
    mtags = x_media_tags(item, src)
    if mtags:
        meta_parts.append(" ".join(f"`[{t}]`" for t in mtags))
    if cite:
        meta_parts.append(f"`[{cite}]`")
    meta = " · ".join(meta_parts)

    # Also-seen (cross-source dup note)
    also_seen = item.get("_also_seen") if isinstance(item, dict) else None
    also_line = ""
    if also_seen:
        also_line = "*also seen: " + ", ".join(f"{nm} {en}" for nm, en in also_seen[:3]) + "*"

    # Title cap — feed gets a tighter cap for compactness
    title_cap = 300 if tier == "top_shelf" else 140
    title_line = f'"{title.strip()[:title_cap]}"'

    # Raw scaffolding for hook synthesis
    raw = make_hook(item, src, cap=280) if tier == "top_shelf" else make_hook(item, src, cap=140)
    title_prefix = title.strip().lower()[:60]
    raw_prefix = (raw or "").strip().lower()[:60]
    if raw and raw_prefix and raw_prefix == title_prefix:
        raw_comment = ""
    elif raw:
        raw_comment = f"<!-- raw: {raw} -->"
    else:
        raw_comment = ""

    src_link = f"[source]({url})" if url else ""

    out.append("---")
    out.append(heading)
    if meta:
        out.append(meta)
    if also_line:
        out.append(also_line)
    out.append(title_line)
    if raw_comment:
        out.append(raw_comment)
    out.append("> <CLAUDE_FILL_HOOK>")
    if src_link:
        out.append(src_link)
    out.append("")
    return True

gem_lines = [
    "", "---", "", "## Gems", "",
    "<!-- CLAUDE INSTRUCTIONS (hooks): one claim, not a summary. Lead with the",
    "non-obvious mechanism / number / failure mode inside the item. Ground it in",
    "John's interest areas (data engineering, DevOps, AI, system design) —",
    "NOT in project names; name a project (Helios, Taskflow, OpenKit, Rai)",
    "only when it is currently active AND the connection is genuinely real.",
    "End with a so-what: what to steal, watch, or decide.",
    "BANNED: restating the title; 'This post/thread/repo…' openers; hedge filler",
    "('worth a look', 'interesting take'); reflexive project name-drops.",
    "Cover-the-title test: hide the title — the hook must still add information.",
    "Self-review every hook against this before the grep check. Junk gets an",
    "honest 'skip — <reason>'. Delete this comment block when done. -->",
    "",
]
n = 0
for e in top_shelf_picks:
    n += 1
    emit_gem(gem_lines, n, e, "top_shelf")

if feed_picks:
    gem_lines.append("### Feed")
    gem_lines.append("")
    for e in feed_picks:
        n += 1
        emit_gem(gem_lines, n, e, "feed")

# Wisdom
wisdom_lines = ["", "---", "", "## Wisdom", ""]
for c in wisdom_picks:
    e = c["entry"]
    item = e["item"]; src = e["src"]
    label = gem_heading_label(src, item)
    category = c["category"].replace("_", " ")
    wisdom_lines.append("---")
    wisdom_lines.append(f'**"{c["text"]}"**')
    wisdom_lines.append(f"{label} — _{category}_")
    wisdom_lines.append("")
    wisdom_lines.append("**Model:** <CLAUDE_FILL_MODEL>")
    wisdom_lines.append("**Insight:** <CLAUDE_FILL_INSIGHT>")
    wisdom_lines.append("")

# Deep Dive
deep_lines = ["", "---", "", "## Deep Dive", ""]
if deep_dive_picks:
    primary = deep_dive_picks[0]
    alts = deep_dive_picks[1:]
    p_title = get_title(primary["item"], primary["src"])
    p_n = next((i + 1 for i, e in enumerate(top_shelf_picks) if id(e) == id(primary)), None)
    p_label = f"Gem #{p_n}" if p_n else f"({fmt_source_name(primary['src'], primary['item'])})"
    deep_lines.append("### <CLAUDE_FILL_TITLE>")
    deep_lines.append("")
    triggered = p_label
    if alts:
        a_n = next((i + 1 for i, e in enumerate(top_shelf_picks) if id(e) == id(alts[0])), None)
        if a_n:
            triggered += f" + Gem #{a_n}"
    deep_lines.append(f"**Triggered by:** {triggered}")
    deep_lines.append("")
    deep_lines.append("<CLAUDE_FILL_ESSAY>")
    deep_lines.append("")
    deep_lines.append("### Also considered")
    for alt in alts[:2]:
        a_title = get_title(alt["item"], alt["src"]).strip()[:80]
        a_n = next((i + 1 for i, e in enumerate(top_shelf_picks) if id(e) == id(alt)), None)
        prefix = f"Gem #{a_n}" if a_n else f"({fmt_source_name(alt['src'], alt['item'])})"
        deep_lines.append(f"- {prefix} ({a_title}) — <CLAUDE_FILL_REASON>")
    deep_lines.append("")

content = (header
           + "\n".join(news_wire_lines)
           + "\n".join(hot_topics_lines)
           + "\n".join(gem_lines)
           + "\n".join(wisdom_lines)
           + "\n".join(deep_lines))

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

# Move previous dated digests (daily YYYY-MM-DD.md, weekly YYYY-Www.md) to the archive.
# Pure vault hygiene since v5.4 — dedup reads the ledger, not these files.
if not TEST_MODE:
    _HISTORY_DIR = Path(os.path.expanduser("~/helm/13-archive/news/daily"))
    _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    _DIGEST_NAME_RE = re.compile(r"^\d{4}-(?:\d{2}-\d{2}|W\d{2})\.md$")
    _moved = 0
    for _f in DIGEST_DIR.iterdir():
        if _f.is_file() and _f.name != OUT_NAME and _DIGEST_NAME_RE.match(_f.name):
            _f.rename(_HISTORY_DIR / _f.name)
            _moved += 1
    if _moved:
        print(f"Archived {_moved} previous digest(s) to {_HISTORY_DIR}")

OUT_PATH.write_text(content)
print(f"\nWrote: {OUT_PATH}{' (TEST MODE — no archive, no ledger append)' if TEST_MODE else ''}")
print(f"Size: {len(content)} chars, {content.count(chr(10))} lines")
print(f"Placeholders to fill: {content.count('CLAUDE_FILL')}")

# Archive the day's raw dumps — every collected item (not just the displayed
# ~100) is kept forever, git-tracked, synced Mac↔Ubuntu. .runs/ stays as the
# working scratch dir; this copy is the durable record.
if not TEST_MODE and RUN_DIR.exists():
    import shutil
    _DUMPS_DIR = Path(os.path.expanduser(f"~/helm/13-archive/news/dumps/{DATE}"))
    _DUMPS_DIR.mkdir(parents=True, exist_ok=True)
    _copied = 0
    for _f in RUN_DIR.iterdir():
        if _f.is_file():
            shutil.copy2(_f, _DUMPS_DIR / _f.name)
            _copied += 1
    print(f"Dumps archived: {_copied} files → {_DUMPS_DIR}")

# Ledger append — record every displayed item so it never repeats.
# After write_text so the skeleton is durably on disk first; guarded by
# ledger_all_urls so a same-date re-run appends 0 duplicates.
if not TEST_MODE:
    _new_recs = []
    for e in list(news_wire_picks) + list(top_shelf_picks) + list(feed_picks):
        u = normalize_url(get_url(e["item"], e["src"]))
        if not u or u in ledger_all_urls:
            continue
        ledger_all_urls.add(u)
        _new_recs.append(json.dumps({
            "u": u,
            "t": normalize_title(get_title(e["item"], e["src"])),
            "a": (get_author(e["item"], e["src"]) or "").lower(),
            "src": e["src"],
            "first_seen": DATE,
            "published": get_pub_date(e["item"] if isinstance(e["item"], dict) else {}, e["src"]),
        }, ensure_ascii=False))
    if _new_recs:
        with open(LEDGER_PATH, "a") as _lf:
            _lf.write("\n".join(_new_recs) + "\n")
    print(f"Ledger: appended {len(_new_recs)} records")

# ---------------------------------------------------------------------------
# Spot-check stats
# ---------------------------------------------------------------------------

print("\n--- Spot-checks ---")
nw_src_counts = Counter(src_bucket(e["src"]) for e in news_wire_picks)
print(f"News Wire source mix: {dict(nw_src_counts)} ({len(nw_src_counts)} distinct buckets)")
ts_src_counts = Counter(src_bucket(e["src"]) for e in top_shelf_picks)
ts_topic_counts = Counter(e["topic"] for e in top_shelf_picks)
print(f"Top Shelf source mix: {dict(ts_src_counts)}")
print(f"Top Shelf topic mix:  {dict(ts_topic_counts)}")
ts_identity = sum(1 for e in top_shelf_picks if is_identity_match(e))
print(f"Top Shelf identity-matched: {ts_identity}/{len(top_shelf_picks)} ({100*ts_identity//max(1,len(top_shelf_picks))}%)")
print(f"Top Shelf score range: {top_shelf_picks[0]['score']['final']:.1f} → {top_shelf_picks[-1]['score']['final']:.1f}")

print("\n--- Top 10 scored items (any section) ---")
for i, e in enumerate(final_pool[:10]):
    s = e["score"]
    title = (get_title(e["item"], e["src"]) or "")[:75]
    ident_dims = []
    if s["identity"]["ai"] >= 4:    ident_dims.append(f"ai={s['identity']['ai']:.0f}")
    if s["identity"]["data_engineering"] >= 4: ident_dims.append(f"de={s['identity']['data_engineering']:.0f}")
    if s["identity"]["system_design"] >= 4: ident_dims.append(f"sd={s['identity']['system_design']:.0f}")
    if s["identity"]["devops"] >= 4: ident_dims.append(f"do={s['identity']['devops']:.0f}")
    if s["identity"]["active_project"] >= 4: ident_dims.append(f"proj={s['identity']['active_project']:.0f}")
    if s["identity"]["region_context"] >= 4: ident_dims.append(f"sa={s['identity']['region_context']:.0f}")
    ident_str = ",".join(ident_dims) if ident_dims else "no-id"
    print(f"  #{i+1}: {s['final']:.1f} U={s['universal']['total']:.0f} I={s['identity']['total']:.0f}({ident_str}) E={s['engagement']:.1f} | [{e['src']}] {title}")
