#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml>=6.0"]
# ///
"""Weekly magazine mining — buckets a Sun→Sat week of raw dumps into department briefs.

Reads raw source JSONs from 13-archive/news/dumps/<DATE>/ (fallback: .runs/<DATE>/)
for every day of the week and writes per-department candidate briefs for the
Bawaba Weekly magazine (SKILL.md § Weekly Magazine):

    .runs/weekly-<YYYY-WWW>/
        brief_cover.md      biggest story clusters of the week
        brief_models.md     model releases/updates, clustered per lab/model
        brief_lesson.md     recurring technical concepts (model clusters excluded)
        brief_stack.md      in-beat craft: data-eng / data / system-design / DevOps
        brief_workshop.md   tools + repos of the week
        brief_shelf.md      long reads whose full text sits in the dumps
        coverage.md         per-day per-source coverage table + load-bearing-claim verify-queue

Topic gravity only — this script does NOT know or care which items made a daily.
Standalone, read-only over the dumps. Engagement is percentile-ranked per source
so 50k-like X posts don't swamp 35-like Substack essays.

Usage:
    python weekly_mine.py                    # most recent Sun→Sat window
    python weekly_mine.py --week 2026-W24
    python weekly_mine.py --end 2026-06-13   # any day inside the wanted week
"""
import argparse
import html as _html
import json
import math
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

SKILL_DIR = Path(__file__).parent
RUNS_DIR = SKILL_DIR / ".runs"
DUMPS_DIR = Path.home() / "helm" / "13-archive" / "news" / "dumps"

SOURCES = ["hn", "reddit", "github", "substack", "medium", "x_foryou", "x_following"]

# ---------------------------------------------------------------------------
# Config (weekly.mining block; every key has a built-in fallback)
# ---------------------------------------------------------------------------
CONFIG = {}
_cfgp = SKILL_DIR / "config.yaml"
if yaml is not None and _cfgp.exists():
    try:
        CONFIG = yaml.safe_load(_cfgp.read_text()) or {}
    except Exception:
        CONFIG = {}
MCFG = ((CONFIG.get("weekly") or {}).get("mining") or {})

BRIEF_MAX_KB = int(MCFG.get("brief_max_kb", 60))
LESSON_MIN_DAYS = int(MCFG.get("lesson_min_days", 3))
LESSON_MIN_SOURCES = int(MCFG.get("lesson_min_sources", 2))
CLUSTER_MIN_ITEMS = int(MCFG.get("cluster_min_items", 5))
MODEL_MIN_ITEMS = int(MCFG.get("model_min_items", 2))
SHELF_MIN_BODY = int(MCFG.get("shelf_min_body_chars", 3000))
SHELF_TOP_N = int(MCFG.get("shelf_top_n", 15))
COVER_TOP_N = int(MCFG.get("cover_top_n", 5))
LESSON_TOP_N = int(MCFG.get("lesson_top_n", 10))

DEFAULT_MODEL_ENTITIES = [
    "anthropic", "claude", "opus", "sonnet", "haiku", "fable", "mythos",
    "openai", "gpt", "chatgpt", "sora", "o3", "o4",
    "gemini", "gemma", "deepmind", "veo", "imagen",
    "llama", "meta ai", "mistral", "mixtral", "magistral", "codestral",
    "qwen", "qwq", "deepseek", "kimi", "moonshot", "glm", "zhipu",
    "minimax", "ernie", "hunyuan", "grok", "xai",
    "phi-4", "phi-5", "copilot", "cohere", "command-r",
    "nemotron", "granite", "olmo", "falcon", "smollm", "amazon nova",
    "flux", "midjourney", "stable diffusion", "whisper",
]
MODEL_ENTITIES = MCFG.get("model_entities") or DEFAULT_MODEL_ENTITIES

DEFAULT_RELEASE_MARKERS = [
    "release", "launch", "announc", "introduc", "unveil", "ship", "drop",
    "open weights", "open-weight", "open sourc", "weights", "checkpoint",
    "preview", "now available", "model card", "system card", "benchmark",
    "new model", "version", "update", "upgrade", "fine-tun", "frontier",
]
RELEASE_MARKERS = MCFG.get("release_markers") or DEFAULT_RELEASE_MARKERS

# Interest-area unigrams allowed as standalone phrases (bigrams/trigrams are
# always eligible). Keeps single-word clusters meaningful instead of generic.
DEFAULT_INTEREST_UNIGRAMS = [
    "rag", "mcp", "agents", "duckdb", "postgres", "sqlite", "clickhouse",
    "kafka", "flink", "airflow", "dagster", "dbt", "spark", "iceberg",
    "snowflake", "databricks", "lakehouse", "kubernetes", "terraform",
    "docker", "observability", "embeddings", "quantization", "inference",
    "finetuning", "evals", "tokenizer", "distillation", "cuda",
]
def _sing(tok):
    """Crude singularizer so 'agents'/'agent' cluster together."""
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok

INTEREST_UNIGRAMS = {_sing(t) for t in (MCFG.get("interest_unigrams") or DEFAULT_INTEREST_UNIGRAMS)}

# Evergreen phrases recur EVERY week — they are standing topics, not stories or
# lessons of a particular week, so they can't head a cluster. Tune in config.
DEFAULT_EVERGREEN_PHRASES = [
    "ai", "agent", "ai agent", "agentic", "llm", "ai model", "ai tool",
    "ai coding", "coding agent", "open source", "machine learning",
    "artificial intelligence", "software engineering", "claude code",
    "mcp", "vibe coding", "prompt engineering", "data engineering",
    "generative ai", "ai system", "use case", "real world", "united states",
    "world cup", "breaking news", "tech news",
]
EVERGREEN = {" ".join(_sing(w) for w in p.lower().split())
             for p in (MCFG.get("evergreen_phrases") or DEFAULT_EVERGREEN_PHRASES)}

VERSION_RE = re.compile(r"\bv?\d+(\.\d+)+\b|\b[a-z]+-?\d+(\.\d+)?b\b", re.I)

# The Stack beat: data-eng/data, DevOps/infra, system design. Filtered & ranked
# separately so beat craft isn't drowned by frontier-model hype (SKILL.md §
# Weekly Magazine → The Stack). Tune via config weekly.mining.stack_markers.
DEFAULT_STACK_MARKERS = {
    "Data engineering / data systems": [
        "data engineering", "data engineer", "etl", "elt", "data pipeline",
        "data warehouse", "lakehouse", "data lake", "dbt", "airflow", "dagster",
        "kafka", "flink", "spark", "iceberg", "delta lake", "snowflake",
        "databricks", "duckdb", "clickhouse", "postgres", "parquet", "medallion",
        "data quality", "data contract", "cdc", "change data capture",
        "streaming", "stream processing", "schema", "data modeling", "data mesh",
        "olap", "trino", "presto", "warehouse", "semantic layer", "metadata",
    ],
    "DevOps / infra / operating": [
        "kubernetes", "k8s", "docker", "container", "terraform", "ansible",
        "ci/cd", "cicd", "continuous integration", "continuous deployment",
        "observability", "prometheus", "grafana", "opentelemetry", "otel",
        "site reliability", " sre ", "devops", "platform engineering",
        "helm chart", "serverless", "infrastructure as code", "iac",
        "monitoring", "incident", "deployment", "orchestration", "service mesh",
        "rbac", "secrets", "circuit breaker", "autoscal",
    ],
    "System design / architecture": [
        "system design", "architecture", "scalability", "scalable", "latency",
        "throughput", "distributed system", "microservice", "event-driven",
        "event driven", "caching", " cache", "load balanc", "message queue",
        "sharding", "replication", "consistency", "api design", "rate limit",
        "fault toleran", "high availability", "back pressure", "idempoten",
    ],
}
STACK_MARKERS = MCFG.get("stack_markers") or DEFAULT_STACK_MARKERS

# Load-bearing claim sniffer for the verify-queue: a sentence carrying a dollar
# figure, a percentage, an "N-year-old" age, or a large comma-grouped count.
CLAIM_RE = re.compile(
    r"[^.!?\n]*?(?:"
    r"\$\s?\d[\d,.]*\s?(?:trillion|billion|million|thousand|[bmkt])?\b"
    r"|\b\d[\d,.]*\s?(?:trillion|billion|million)\b"
    r"|\b\d+(?:\.\d+)?\s?%"
    r"|\b\d+[\-\s]year(?:s)?[\-\s]old\b"
    r"|\b\d{1,3}(?:,\d{3})+\b"
    r")[^.!?\n]*[.!?]?",
    re.I)

STOPWORDS = set("""
a about above after again against all am an and any are as at be because been
before being below between both but by can cannot could did do does doing down
during each few for from further had has have having he her here hers herself
him himself his how i if in into is it its itself just let me more most my
myself no nor not of off on once only or other ought our ours ourselves out
over own same she should so some such than that the their theirs them
themselves then there these they this those through to too under until up very
was we were what when where which while who whom why will with would you your
yours yourself yourselves
im ive dont doesnt didnt isnt arent wasnt werent wont cant couldnt shouldnt
also like get got gets getting one two three new now via using use used uses
vs etc way ways thing things really think know going go still even much many
lot bit see say said says people time today week year day days make makes made
making want wants need needs work works working good great big small right
amp http https www com html org reddit twitter tweet thread post posts
ago month months ever seen actually maybe pretty stuff every first last next
back better best look looks looking come comes coming take takes feel feels
""".split())

TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'\-\.]{1,38}")
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")

# ---------------------------------------------------------------------------
# Week resolution
# ---------------------------------------------------------------------------
def resolve_week(args):
    """Return (label, [iso dates Sun..Sat])."""
    if args.week:
        m = re.fullmatch(r"(\d{4})-W(\d{1,2})", args.week)
        if not m:
            raise SystemExit(f"--week must look like 2026-W24, got {args.week!r}")
        saturday = date.fromisocalendar(int(m[1]), int(m[2]), 6)
    else:
        anchor = date.fromisoformat(args.end) if args.end else date.today()
        since_sunday = (anchor.weekday() + 1) % 7
        saturday = anchor - timedelta(days=since_sunday) + timedelta(days=6)
    sunday = saturday - timedelta(days=6)
    iso = saturday.isocalendar()
    label = f"{iso[0]}-W{iso[1]:02d}"
    days = [(sunday + timedelta(days=i)).isoformat() for i in range(7)]
    return label, days

# ---------------------------------------------------------------------------
# Loading + normalization
# ---------------------------------------------------------------------------
def _read_json_list(path):
    try:
        data = json.loads(path.read_text())
    except Exception:
        return []
    return data if isinstance(data, list) else []

def load_source(day_dir, src):
    """Final file first; else merge attempt partials (dedup by id/url)."""
    final = day_dir / f"{src}.json"
    if final.exists():
        return _read_json_list(final)
    merged, seen = [], set()
    for attempt in sorted(day_dir.glob(f"{src}-attempt*.json")):
        for it in _read_json_list(attempt):
            if not isinstance(it, dict):
                continue
            key = it.get("id") or it.get("url") or it.get("permalink") or it.get("title")
            if key is None or key in seen:
                continue
            seen.add(key)
            merged.append(it)
    return merged

def clean_text(s):
    if not s:
        return ""
    s = _html.unescape(str(s))
    s = TAG_RE.sub(" ", s)
    return WS_RE.sub(" ", s).strip()

def _stars_today(s):
    m = re.search(r"([\d,]+)\s+stars", str(s or ""))
    return int(m.group(1).replace(",", "")) if m else 0

def normalize(src, it, day):
    """Map a raw dump item to a common record. Returns None for junk."""
    if not isinstance(it, dict):
        return None
    rec = {"src": src, "days": {day}, "extra": {}}
    if src == "hn":
        comments = " ".join(clean_text(c) for c in (it.get("top_comments") or [])[:2])
        rec.update(title=clean_text(it.get("title")),
                   text=(clean_text(it.get("text")) + " " + comments).strip(),
                   url=it.get("url") or it.get("hn_url") or "",
                   author=it.get("by") or "",
                   eng=int(it.get("score") or 0) + int(it.get("descendants") or 0))
        rec["extra"]["hn_url"] = it.get("hn_url") or ""
    elif src == "reddit":
        comments = " ".join(clean_text(c) for c in (it.get("top_comments") or [])[:2])
        perma = it.get("permalink") or ""
        if perma and perma.startswith("/"):
            perma = "https://www.reddit.com" + perma
        rec.update(title=clean_text(it.get("title")),
                   text=(clean_text(it.get("selftext")) + " " + comments).strip(),
                   url=perma or it.get("url") or "",
                   author=f"r/{it.get('sub')}" if it.get("sub") else (it.get("author") or ""),
                   eng=int(it.get("score") or 0) + int(it.get("num_comments") or 0))
    elif src == "github":
        rec.update(title=it.get("repo") or "",
                   text=(clean_text(it.get("description")) + " " + clean_text(it.get("readme_head"))).strip(),
                   url=it.get("url") or "",
                   author="",
                   eng=_stars_today(it.get("stars_period")))
        rec["extra"].update(language=it.get("language") or "",
                            stars=int(it.get("stars") or 0))
    elif src in ("substack", "medium"):
        body = clean_text(it.get("body"))
        rec.update(title=clean_text(it.get("title")),
                   text=(clean_text(it.get("subtitle")) + " " + body).strip(),
                   url=it.get("url") or "",
                   author=it.get("author") or "")
        if src == "substack":
            rec["eng"] = (int(it.get("likes") or 0) + 2 * int(it.get("restacks") or 0)
                          + int(it.get("comments_count") or 0))
        else:
            rec["eng"] = int(it.get("claps") or 0)
        rec["extra"].update(body_len=len(body), published=it.get("date") or "")
    elif src in ("x_foryou", "x_following"):
        text = clean_text(it.get("text"))
        if len(text) < 30:          # media-only / junk posts carry no minable text
            return None
        rec.update(title=text[:110] + ("…" if len(text) > 110 else ""),
                   text=text,
                   url=it.get("url") or "",
                   author=f"{it.get('author') or ''} ({it.get('handle') or ''})".strip(),
                   eng=(int(it.get("likes") or 0) + 2 * int(it.get("reposts") or 0)
                        + int(it.get("replies") or 0) + int(it.get("bookmarks") or 0)))
    if not rec.get("title") and not rec.get("text"):
        return None
    return rec

def norm_url(u):
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = u.split("#")[0].split("?")[0].rstrip("/")
    return u

def load_week(days):
    """Load every day, merge to week-unique records. Returns (records, coverage)."""
    coverage = {}          # day -> {src: count}
    by_key = {}
    for day in days:
        day_dir = next((d for d in (DUMPS_DIR / day, RUNS_DIR / day) if d.is_dir()), None)
        if day_dir is None:
            continue
        coverage[day] = {}
        for src in SOURCES:
            items = load_source(day_dir, src)
            coverage[day][src] = len(items)
            for it in items:
                rec = normalize(src, it, day)
                if rec is None:
                    continue
                key = norm_url(rec["url"]) or f"{src}:{rec['title'][:80]}"
                prev = by_key.get(key)
                if prev is None:
                    by_key[key] = rec
                else:
                    prev["days"] |= rec["days"]
                    prev["eng"] = max(prev["eng"], rec["eng"])
                    if len(rec["text"]) > len(prev["text"]):
                        prev["text"] = rec["text"]
                    if rec["extra"].get("body_len", 0) > prev["extra"].get("body_len", 0):
                        prev["extra"]["body_len"] = rec["extra"]["body_len"]
    records = list(by_key.values())
    for rec in records:
        rec["days"] = sorted(rec["days"])
    # percentile rank within each source → cross-source comparable engagement
    by_src = defaultdict(list)
    for rec in records:
        by_src[rec["src"]].append(rec)
    for src_recs in by_src.values():
        src_recs.sort(key=lambda r: r["eng"])
        n = len(src_recs)
        i = 0
        while i < n:                  # tie-averaged percentile: an all-zero source
            j = i                     # (reddit via RSS fallback) lands at a flat 0.5
            while j < n and src_recs[j]["eng"] == src_recs[i]["eng"]:
                j += 1
            for k in range(i, j):
                src_recs[k]["eng_norm"] = (i + j) / 2 / n
            i = j
    return records, coverage

# ---------------------------------------------------------------------------
# Phrase clustering (cover + lesson)
# ---------------------------------------------------------------------------
def phrases_of(rec):
    """Set of candidate phrases from title + leading text."""
    text = f"{rec['title']} {rec['text'][:1500]}".lower()
    tokens = TOKEN_RE.findall(text)
    out = set()
    run = []
    for tok in tokens + ["."]:                      # sentinel flushes last run
        bare = tok.strip("'-.")
        if bare in STOPWORDS or len(bare) < 2 or bare.isdigit():
            run = []
            continue
        bare = _sing(bare)
        run.append(bare)
        if bare in INTEREST_UNIGRAMS:
            out.add(bare)
        if len(run) >= 2:
            out.add(" ".join(run[-2:]))
        if len(run) >= 3:
            out.add(" ".join(run[-3:]))
    return out

def build_phrase_clusters(records, days_found):
    # A thin week (missing dumps, X burn) can't demand 3-day recurrence.
    min_days = min(LESSON_MIN_DAYS, max(1, days_found - 1))
    stats = {}
    for idx, rec in enumerate(records):
        for ph in phrases_of(rec):
            st = stats.get(ph)
            if st is None:
                st = stats[ph] = {"days": set(), "srcs": set(), "recs": [], "eng": 0.0,
                                  "count": 0}
            st["days"] |= set(rec["days"])
            st["srcs"].add(rec["src"])
            st["count"] += 1
            if len(st["recs"]) < 300:
                st["recs"].append(idx)
            st["eng"] += rec["eng_norm"]
    clusters = []
    for ph, st in stats.items():
        if ph in EVERGREEN:
            continue
        if (st["count"] >= CLUSTER_MIN_ITEMS and len(st["days"]) >= min_days
                and len(st["srcs"]) >= LESSON_MIN_SOURCES):
            score = len(st["days"]) * len(st["srcs"]) * (1 + math.log1p(st["eng"]))
            clusters.append({"phrase": ph, "score": score, **st})
    clusters.sort(key=lambda c: -c["score"])
    # containment dedup: drop clusters whose item set mostly overlaps a kept one
    kept = []
    for c in clusters:
        c_set = set(c["recs"])
        if any(len(c_set & set(k["recs"])) / max(1, len(c_set | set(k["recs"]))) >= 0.6
               for k in kept):
            continue
        kept.append(c)
        if len(kept) >= 80:
            break
    return kept

# ---------------------------------------------------------------------------
# Model clusters
# ---------------------------------------------------------------------------
def compile_entities():
    pats = []
    for name in MODEL_ENTITIES:
        esc = re.escape(name.lower())
        pats.append((name, re.compile(rf"(?<![a-z0-9]){esc}(?![a-z])")))
    return pats

def build_model_clusters(records, entity_pats):
    clusters = defaultdict(lambda: {"days": set(), "srcs": set(), "recs": [], "eng": 0.0})
    for idx, rec in enumerate(records):
        low = f"{rec['title']} {rec['text'][:2000]}".lower()
        hits = [name for name, pat in entity_pats if pat.search(low)]
        if not hits:
            continue
        if not (any(m in low for m in RELEASE_MARKERS) or VERSION_RE.search(low)):
            continue
        for name in hits:
            st = clusters[name]
            st["days"] |= set(rec["days"])
            st["srcs"].add(rec["src"])
            if len(st["recs"]) < 40:
                st["recs"].append(idx)
            st["eng"] += rec["eng_norm"]
    out = [{"phrase": name, "score": st["eng"], **st}
           for name, st in clusters.items() if len(st["recs"]) >= MODEL_MIN_ITEMS]
    out.sort(key=lambda c: -c["score"])
    return out[:20]

# ---------------------------------------------------------------------------
# Brief rendering
# ---------------------------------------------------------------------------
def fmt_rec(records, idx, excerpt_len):
    rec = records[idx]
    days = ",".join(d[5:] for d in rec["days"][:3]) + ("+" if len(rec["days"]) > 3 else "")
    head = rec["title"] or rec["text"][:80]
    excerpt = rec["text"][:excerpt_len].strip()
    by = f" · {rec['author']}" if rec["author"] else ""
    lines = [f"- **{head}**",
             f"  `{rec['src']}` · {days}{by} · eng {rec['eng']:,} · {rec['url']}"]
    if excerpt and excerpt not in head:
        lines.append(f"  > {excerpt}")
    return "\n".join(lines)

def render_clusters(title, intro, clusters, records, top_n, per_cluster, excerpt_len):
    out = [f"# {title}", "", intro, ""]
    for i, c in enumerate(clusters[:top_n], 1):
        days = len(c["days"])
        srcs = "/".join(sorted(c["srcs"]))
        out.append(f"## {i}. “{c['phrase']}” — {days} days · {srcs} · "
                   f"{c.get('count', len(c['recs']))} items · score {c['score']:.1f}")
        ranked = sorted(c["recs"], key=lambda idx: (-records[idx]["eng_norm"],
                                                    -len(records[idx]["text"])))
        for idx in ranked[:per_cluster]:
            out.append(fmt_rec(records, idx, excerpt_len))
        out.append("")
    return "\n".join(out)

def write_brief(out_dir, name, text):
    cap = BRIEF_MAX_KB * 1024
    if len(text.encode()) > cap:
        text = text.encode()[:cap].decode(errors="ignore") + "\n\n[TRUNCATED at brief_max_kb]\n"
    path = out_dir / name
    path.write_text(text)
    return path, len(text.encode())

# ---------------------------------------------------------------------------
# Department builders
# ---------------------------------------------------------------------------
def brief_workshop(records, label):
    gh = [r for r in records if r["src"] == "github"]
    gh.sort(key=lambda r: (-len(r["days"]), -r["eng"]))
    out = [f"# Workshop candidates — {label}", "",
           "GitHub trending aggregated across the week (eng = stars-today on the best day;",
           "days = how many trending days), plus Show HN and high-engagement repo links.", ""]
    out.append("## GitHub trending (week-aggregated)")
    for rec in gh[:30]:
        lang = rec["extra"].get("language") or "?"
        stars = rec["extra"].get("stars", 0)
        out.append(f"- **{rec['title']}** ({lang}, {stars:,}★ total) · "
                   f"{len(rec['days'])} trending day(s) · {rec['url']}")
        desc = rec["text"][:300].strip()
        if desc:
            out.append(f"  > {desc}")
    out.append("")
    out.append("## Show HN")
    show = [r for r in records if r["src"] == "hn" and r["title"].lower().startswith("show hn")]
    show.sort(key=lambda r: -r["eng"])
    for rec in show[:15]:
        out.append(fmt_rec(records, records.index(rec), 250))
    out.append("")
    out.append("## Tool launches linked elsewhere (github.com links, high engagement)")
    linked = [r for r in records
              if r["src"] not in ("github", "hn")
              and "github.com/" in (r["url"] + " " + r["text"][:500])
              and r["eng_norm"] >= 0.7]
    linked.sort(key=lambda r: -r["eng_norm"])
    for rec in linked[:15]:
        out.append(fmt_rec(records, records.index(rec), 250))
    return "\n".join(out)

def brief_shelf(records, label, days):
    cands = [r for r in records
             if r["src"] in ("substack", "medium")
             and r["extra"].get("body_len", 0) >= SHELF_MIN_BODY]
    for r in cands:
        r["_shelf"] = r["eng_norm"] * (1 + math.log1p(r["extra"]["body_len"] / SHELF_MIN_BODY))
    cands.sort(key=lambda r: -r["_shelf"])
    out = [f"# Reading Shelf candidates — {label}", "",
           f"Long reads (body ≥ {SHELF_MIN_BODY:,} chars) ranked by engagement × substance.",
           "Full text lives in the day's dump file — match by url in "
           "`13-archive/news/dumps/<day>/substack.json` (or medium.json).", ""]
    for i, rec in enumerate(cands[:SHELF_TOP_N], 1):
        pub = rec["extra"].get("published") or "?"
        out.append(f"## {i}. {rec['title']}")
        out.append(f"`{rec['src']}` · {rec['author']} · published {pub} · "
                   f"eng {rec['eng']:,} · {rec['extra']['body_len']:,} chars · "
                   f"seen {','.join(d[5:] for d in rec['days'])}")
        out.append(f"{rec['url']}")
        out.append(f"> {rec['text'][:400].strip()}")
        out.append("")
    return "\n".join(out)

def brief_stack(records, label):
    """In-beat craft: data-eng/data, DevOps/infra, system design. Each family
    filtered by topic markers, ranked by recurrence × engagement, so beat
    material the cover/model briefs drown out gets its own surface."""
    fams = {fam: [re.compile(rf"(?<![a-z0-9]){re.escape(m.strip())}", re.I)
                  for m in markers]
            for fam, markers in STACK_MARKERS.items()}
    out = [f"# The Stack candidates — {label}", "",
           "In-beat craft of the week — data engineering, data systems, system",
           "design, DevOps/operating — filtered by topic markers and ranked by",
           "recurrence × engagement. This is where the beat lives; if a family is",
           "empty, that is a real coverage gap to note, not a brief to skip.", ""]
    for fam, pats in fams.items():
        hits = []
        for i, rec in enumerate(records):
            low = f"{rec['title']} {rec['text'][:1200]}".lower()
            if any(p.search(low) for p in pats):
                hits.append(i)
        hits.sort(key=lambda i: (-len(records[i]["days"]), -records[i]["eng_norm"],
                                 -len(records[i]["text"])))
        out.append(f"## {fam} ({len(hits)} items)")
        if not hits:
            out.append("_(nothing surfaced this week — coverage gap to note)_")
        for i in hits[:12]:
            out.append(fmt_rec(records, i, 320))
        out.append("")
    return "\n".join(out)

def verify_queue(records, top_n=90, max_claims=45):
    """Pull load-bearing quantified claims from the week's top items so the
    enrich step has an explicit fact-check checklist (SKILL.md § Fact protocol).
    Restricted to citable analytical sources — the X feeds are off-beat viral
    noise (sports, politics) the in-beat weekly never quotes."""
    CITE_SRCS = {"hn", "reddit", "substack", "medium", "github"}
    citable = [r for r in records if r["src"] in CITE_SRCS]
    ranked = sorted(citable, key=lambda r: -r.get("eng_norm", 0))[:top_n]
    seen, rows = set(), []
    for rec in ranked:
        blob = f"{rec['title']}. {rec['text'][:1200]}"
        for m in CLAIM_RE.finditer(blob):
            snip = WS_RE.sub(" ", m.group(0)).strip(" .,-—")
            if not (12 <= len(snip) <= 220):
                continue
            key = snip.lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            rows.append((snip, rec))
            if len(rows) >= max_claims:
                break
        if len(rows) >= max_claims:
            break
    out = ["", "## Load-bearing claims — verify before print", "",
           "Numbers/dates/vendor stats pulled from the week's top items. Fetch the",
           "primary source for any you cite; round or attribute if unverifiable;",
           "never print as fact unconfirmed. (See SKILL.md § Fact protocol.)", ""]
    for snip, rec in rows:
        out.append(f"- [ ] “{snip}” — `{rec['src']}` · {rec['url']}")
    if not rows:
        out.append("_(no quantified claims surfaced)_")
    return "\n".join(out)

def coverage_table(coverage, days, n_unique):
    out = ["# Coverage", "", "| day | " + " | ".join(SOURCES) + " |",
           "|---|" + "---|" * len(SOURCES)]
    for day in days:
        row = coverage.get(day)
        if row is None:
            out.append(f"| {day} (no dump) | " + " | ".join("—" for _ in SOURCES) + " |")
        else:
            out.append(f"| {day} | " + " | ".join(str(row.get(s, 0)) for s in SOURCES) + " |")
    out.append("")
    out.append(f"Week-unique records after URL dedup: **{n_unique:,}** "
               f"(dump days found: {len(coverage)}/7)")
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", default=None, help="ISO week label, e.g. 2026-W24")
    ap.add_argument("--end", default=None, help="any date inside the wanted week (YYYY-MM-DD)")
    args = ap.parse_args()

    label, days = resolve_week(args)
    records, coverage = load_week(days)
    if not records:
        raise SystemExit(f"No dump data found for {label} ({days[0]}..{days[-1]}) "
                         f"under {DUMPS_DIR} or {RUNS_DIR}")

    out_dir = RUNS_DIR / f"weekly-{label}"
    out_dir.mkdir(parents=True, exist_ok=True)

    entity_pats = compile_entities()
    phrase_clusters = build_phrase_clusters(records, len(coverage))
    model_clusters = build_model_clusters(records, entity_pats)
    is_modelish = lambda ph: any(pat.search(ph) for _, pat in entity_pats)
    lesson_clusters = [c for c in phrase_clusters if not is_modelish(c["phrase"])]

    written = []
    written.append(write_brief(out_dir, "brief_cover.md", render_clusters(
        f"Cover Story candidates — {label}",
        "Biggest recurring story clusters of the week (all topics, models included).",
        phrase_clusters, records, COVER_TOP_N, per_cluster=10, excerpt_len=500)))
    written.append(write_brief(out_dir, "brief_models.md", render_clusters(
        f"Model State candidates — {label}",
        "Items naming a lab/model plus a release/version marker, clustered per entity.",
        model_clusters, records, len(model_clusters), per_cluster=6, excerpt_len=300)))
    written.append(write_brief(out_dir, "brief_lesson.md", render_clusters(
        f"The Lesson candidates — {label}",
        "Recurring technical concepts (model-release clusters excluded). "
        "Pick the one with real teaching depth, not the loudest.",
        lesson_clusters, records, LESSON_TOP_N, per_cluster=8, excerpt_len=400)))
    written.append(write_brief(out_dir, "brief_stack.md", brief_stack(records, label)))
    written.append(write_brief(out_dir, "brief_workshop.md", brief_workshop(records, label)))
    written.append(write_brief(out_dir, "brief_shelf.md", brief_shelf(records, label, days)))
    written.append(write_brief(out_dir, "coverage.md",
                               coverage_table(coverage, days, len(records))
                               + "\n" + verify_queue(records)))

    print(f"Week {label} ({days[0]} → {days[-1]})")
    print(f"Dump days found: {len(coverage)}/7 · week-unique records: {len(records):,}")
    print(f"Clusters: cover {len(phrase_clusters)} · models {len(model_clusters)} · "
          f"lesson {len(lesson_clusters)}")
    for path, size in written:
        print(f"  {path.name:<20} {size/1024:6.1f} KB")

if __name__ == "__main__":
    main()
