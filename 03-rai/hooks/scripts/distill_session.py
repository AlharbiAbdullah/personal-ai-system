#!/usr/bin/env python3
"""
distill_session.py — distill ONE session transcript into the DISTILL JSON using
SUBSCRIPTION Opus via the `claude` CLI in headless print mode. No external API. Memory v3.

Long sessions are CHUNKED (M4): >60k chars splits into ≤60k windows (cap 10; beyond the
cap, evenly spaced stratified windows across the whole transcript), each window distilled
separately, then ONE reduce pass merges the partials. The optional --bullets-file (the
session's live turn-capture observer map, coupling A) rides along in every prompt to tell
the distiller what mattered — it also covers ground the window sampling may skip.

Repo rule (H27, M10): a session whose cwd sits in a project-init repo (`.project.toml`,
see hooks/lib/sdd_repo.py) gets a prompt addendum plus a code-side guard, so the distill
keeps only preferences John states himself, cross-project lessons, and a summary
that is exactly one "worked in <repo>: <what>" pointer line; its decisions stay in the
repo's ADRs, so "decisions" is emptied. The cwd comes from the session JSON, else from
its native transcript (archived SessionEnd-hook captures carry cwd ''). Other sessions: unchanged.

Output schema: see semantic-memory/CHROMADB-SCHEMA.md.

Run: python3 distill_session.py --session-json <path> --out <path>
     [--model opus] [--bullets-file <path>]
"""

import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path.home() / "helm" / "03-rai" / "hooks"))
from lib.claude_cli import run_claude  # noqa: E402
from lib.sdd_repo import (
    POINTER_RE,
    leak_check,
    pointer_line,
    repo_name,
    routing_rule,
    sdd_root,
    session_cwd,
)

MAX_TRANSCRIPT_CHARS = 60000  # per-window size
MAX_WINDOWS = 10              # beyond this, stratified sampling across the transcript

PROMPT = """You are distilling ONE Rai work session into durable memory. Read the transcript below.
Extract ONLY what is genuinely durable and grounded in the text. For every fact/decision include 1-3 VERBATIM quotes from the transcript as evidence -- if you cannot quote it, do not claim it. Facts are atomic STATES ("John uses pi as his harness"), not events. Decisions include the rationale. Preferences are about how Rai should behave; standing rules John establishes about how Rai should work are the HIGHEST-value items — never drop them. Flag a supersedes only on an explicit contradiction/replacement of a prior belief. Score confidence honestly (high = explicit/repeated; medium = inferred; low = tangential). Prefer FEWER, higher-quality items over many weak ones. It is fine to return empty arrays for a thin session.

Output ONLY valid JSON (no markdown, no prose, no code fences) of exactly this shape:
{"session_id":"<id>","date":"<YYYY-MM-DD>","summary":"3-6 sentence summary","decisions":[{"content":"","confidence":"high|medium|low","evidence":["verbatim quote"],"category":"","tags":[],"supersedes":[]}],"facts":[{"content":"","confidence":"","evidence":[],"category":"technical|preference|project|reference","tags":[],"supersedes":[]}],"preferences":[{"content":"","confidence":"","evidence":[]}],"supersedes":[]}
__SDD____WINDOW_NOTE____BULLETS__
SESSION_ID: __SID__
DATE: __DATE__
TRANSCRIPT:
__TRANSCRIPT__
"""

REDUCE_PROMPT = """You are merging partial distill JSONs from consecutive windows of ONE long Rai session into a single final distill JSON of the SAME shape. Merge near-duplicate items (keep the strongest verbatim evidence), union tags, write one 3-6 sentence summary covering the WHOLE session, and keep every distinct decision/fact/preference. Output ONLY valid JSON, no prose.
__SDD____BULLETS__
SESSION_ID: __SID__
DATE: __DATE__
PARTIALS:
__PARTIALS__
"""


def sdd_note(repo: str) -> str:
    """H27 addendum for a session inside a project-init repo; '' keeps today's prompt."""
    if not repo:
        return ""
    return ("\n" + routing_rule(repo) + ' In the JSON: "summary" is that one pointer line and '
            'nothing else; "decisions" is always [] (a choice made here lives in the repo\'s ADRs; '
            'a preference John states as his own goes in "preferences"); "facts" hold only '
            'cross-project lessons (never category "project"; empty is the usual result here); '
            '"preferences" hold every preference or standing rule John states himself (never '
            "drop one; its evidence is his own words), and nothing inferred or picked for this "
            "repo.\n")


def apply_repo_rule(distill: dict, repo: str, leaks=None) -> dict:
    """Code-side H27 guard on the model output: the summary becomes exactly one pointer
    line; decisions (the repo's ADRs own them, whatever category the model gave), repo-scoped
    facts (category "project"), stray pointer items and items `leaks` flags (a repo scenario
    ID or file path) are dropped, and so are flagged evidence quotes of the kept items."""
    leaks = leaks or (lambda text: False)
    distill["summary"] = pointer_line(repo, str(distill.get("summary") or ""), leaks)
    distill["decisions"] = []
    for key in ("facts", "preferences"):
        kept = [
            i for i in (distill.get(key) or [])
            if isinstance(i, dict)
            and not (key == "facts" and str(i.get("category", "")).lower() == "project")
            and not POINTER_RE.match(str(i.get("content", "")))
            and not leaks(i.get("content", ""))
        ]
        for i in kept:
            if isinstance(i.get("evidence"), list):
                i["evidence"] = [e for e in i["evidence"] if not leaks(e)]
        distill[key] = kept
    distill["sdd_repo"] = repo
    return distill


def message_text(entry: dict) -> str:
    m = entry.get("message")
    if isinstance(m, str):
        return m
    if isinstance(m, dict):
        c = m.get("content")
        if isinstance(c, str):
            return c
        if isinstance(c, list):
            return "\n".join(
                b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text"
            )
    return ""


def build_transcript(session: dict) -> str:
    out = []
    for m in session.get("messages", []):
        t = message_text(m).strip()
        if t:
            out.append(f"{m.get('type', '').upper()}: {t}")
    return "\n\n".join(out)


def windows(text: str):
    """(windows, sampled) — ≤60k windows; beyond MAX_WINDOWS pick evenly spaced ones
    across the WHOLE transcript (never first+last only)."""
    if len(text) <= MAX_TRANSCRIPT_CHARS:
        return [text], False
    n = math.ceil(len(text) / MAX_TRANSCRIPT_CHARS)
    ws = [text[i * MAX_TRANSCRIPT_CHARS:(i + 1) * MAX_TRANSCRIPT_CHARS] for i in range(n)]
    if len(ws) <= MAX_WINDOWS:
        return ws, False
    idx = sorted({round(i * (len(ws) - 1) / (MAX_WINDOWS - 1)) for i in range(MAX_WINDOWS)})
    return [ws[i] for i in idx], True


def extract_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    i = text.find("{")
    if i < 0:
        raise ValueError("no JSON object in model output")
    # raw_decode parses the FIRST complete JSON object and ignores any trailing text
    # (Opus sometimes appends a stray char/line after the object).
    obj, _ = json.JSONDecoder().raw_decode(text[i:])
    return obj


def _call(prompt: str, model: str, sid: str, label: str):
    """One model call -> parsed distill dict, or None (error already printed)."""
    try:
        out = run_claude(prompt, model=model, timeout=300, effort=None)
    except subprocess.TimeoutExpired:
        print(f"distill: TIMEOUT {sid} ({label})", file=sys.stderr)
        return None
    except subprocess.CalledProcessError as e:
        print(f"distill: claude error {sid} ({label}): {str(e.stderr)[:200]}", file=sys.stderr)
        return None
    try:
        return extract_json(out)
    except Exception as e:
        print(f"distill: parse error {sid} ({label}): {e}\n--- raw ---\n{out[:500]}",
              file=sys.stderr)
        return None


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--session-json", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--model", default="opus")
    p.add_argument("--bullets-file", default="")
    a = p.parse_args()

    d = json.loads(Path(a.session_json).read_text())
    sid = d.get("session_id") or Path(a.session_json).stem
    date = (d.get("timestamp", "") or "")[:10]
    transcript = build_transcript(d)
    if len(transcript.strip()) < 200:
        print(f"distill: skip {sid} (too thin)", file=sys.stderr)
        return 2  # signal: gated out

    bullets = ""
    if a.bullets_file and Path(a.bullets_file).exists():
        raw = Path(a.bullets_file).read_text().strip()
        if raw:
            bullets = ("\nTURN-BY-TURN OBSERVER MAP (live notes from this session — "
                       "use to prioritize what mattered):\n" + raw[:8000] + "\n")

    root = sdd_root(session_cwd(d))  # H27: None outside a project-init repo -> today's prompt
    repo = repo_name(root) if root else ""
    sdd = sdd_note(repo)
    ws, sampled = windows(transcript)

    def render(win: str, note: str) -> str:
        return (PROMPT.replace("__SID__", sid).replace("__DATE__", date).replace("__SDD__", sdd)
                .replace("__WINDOW_NOTE__", note).replace("__BULLETS__", bullets)
                .replace("__TRANSCRIPT__", win))

    if len(ws) == 1:
        distill = _call(render(ws[0], ""), a.model, sid, "single")
        if distill is None:
            return 1
    else:
        partials = []
        for i, w in enumerate(ws, 1):
            note = (f"\nNOTE: this is window {i} of {len(ws)} from a longer session"
                    f"{' (stratified sample of the full transcript)' if sampled else ''};"
                    " distill THIS window only.\n")
            part = _call(render(w, note), a.model, sid, f"window {i}/{len(ws)}")
            if part is not None:
                partials.append(part)
        if not partials:
            return 1
        compact = json.dumps(partials, ensure_ascii=False)[:180000]
        reduce_prompt = (REDUCE_PROMPT.replace("__SID__", sid).replace("__DATE__", date)
                         .replace("__SDD__", sdd).replace("__BULLETS__", bullets)
                         .replace("__PARTIALS__", compact))
        distill = _call(reduce_prompt, a.model, sid, "reduce")
        if distill is None:
            return 1
        if sampled:
            distill["sampling"] = f"stratified {len(ws)} windows of a {len(transcript)}-char transcript"

    if repo:
        apply_repo_rule(distill, repo, leak_check(root))
    distill["session_id"] = sid
    distill["date"] = date
    Path(a.out).write_text(json.dumps(distill, indent=2, ensure_ascii=False))
    print(
        f"distill: {sid} ({len(ws)} window{'s' if len(ws) > 1 else ''}) -> "
        f"{len(distill.get('decisions', []))} decisions, "
        f"{len(distill.get('facts', []))} facts, {len(distill.get('preferences', []))} preferences"
        + (f" [repo rule: {repo}]" if repo else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
