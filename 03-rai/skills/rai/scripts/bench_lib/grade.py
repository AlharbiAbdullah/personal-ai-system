"""Deterministic checks. Each returns (ok, detail). A `judge` check is left pending here
(ok None) and settled by judge.py; a `pytest` check is settled by the runner, which owns the
sandbox the hidden tests run in."""

import json
import re

EM_DASH = "—"
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-⛿✅❌❎✨⭐⭕"
                      "‼⁉⏩-⏺⌚⌛️]")
ARABIC_RE = re.compile("[؀-ۿݐ-ݿࢠ-ࣿﭐ-﷿ﹰ-﻿]")


def _strings(obj):
    """Every string inside a tool call's input, however nested."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _strings(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _strings(v)


def _skill_hit(call: dict, name: str) -> bool:
    inp = call.get("input") or {}
    if call.get("name") == "Skill":
        s = str(inp.get("skill") or inp.get("name") or "")
        if name == "*" or s == name or s.startswith((name + ":", name + "/")) or s.endswith(":" + name):
            return True
    pat = "skills/" if name == "*" else f"skills/{name}/"
    return any(pat in s for s in _strings(inp))


# Checks that pass on what the answer lacks: an empty answer gives them nothing to judge.
TEXT_NEGATIVE = {"no_em_dash", "no_emoji", "english_only", "max_lines", "not_contains"}


def check(c: dict, text: str, tool_calls: list, files) -> tuple:
    """(ok, detail) for one check. ok None means another module settles it."""
    t = c["type"]
    low = text.lower()
    if t in TEXT_NEGATIVE and not text.strip():
        return False, "empty answer"
    if t == "no_em_dash":
        n = text.count(EM_DASH)
        return n == 0, f"{n} em dash(es)" if n else ""
    if t == "no_emoji":
        hits = EMOJI_RE.findall(text)
        return not hits, f"emoji: {''.join(hits[:5])}" if hits else ""
    if t == "english_only":
        n = len(ARABIC_RE.findall(text))
        return n == 0, f"{n} Arabic-script chars" if n else ""
    if t == "arabic":
        letters = [ch for ch in text if ch.isalpha()]
        ratio = (len([ch for ch in letters if ARABIC_RE.match(ch)]) / len(letters)) if letters else 0.0
        need = float(c.get("min_ratio", 0.6))
        return ratio >= need, f"Arabic ratio {ratio:.2f} (need {need})"
    if t == "max_lines":
        n = len([ln for ln in text.splitlines() if ln.strip()])
        return n <= int(c["n"]), f"{n} lines (max {c['n']})"
    if t == "contains":
        if "all" in c:
            miss = [s for s in c["all"] if s.lower() not in low]
            return not miss, f"missing: {miss}" if miss else ""
        ok = any(s.lower() in low for s in c["any"])
        return ok, "" if ok else f"none of {c['any']}"
    if t == "not_contains":
        hit = [s for s in c["any"] if s.lower() in low]
        return not hit, f"found: {hit}" if hit else ""
    if t == "regex":
        ok = re.search(c["pattern"], text, re.I | re.M) is not None
        return ok, "" if ok else f"no match for /{c['pattern']}/"
    if t == "skill_used":
        ok = any(_skill_hit(tc, c["name"]) for tc in tool_calls)
        return ok, "" if ok else f"skill {c['name']} not used ({len(tool_calls)} tool calls)"
    if t == "skill_not_used":
        hits = [tc.get("name") for tc in tool_calls if _skill_hit(tc, c["name"])]
        return not hits, f"skill used via {hits}" if hits else ""
    if t == "file_read":
        ok = any(c["path"] in s for tc in tool_calls for s in _strings(tc.get("input") or {}))
        return ok, "" if ok else f"{c['path']} never named in a tool call"
    if t == "file_exists":
        ok = files.exists(c["path"])
        return ok, "" if ok else f"{c['path']} missing"
    if t == "file_absent":
        ok = not files.exists(c["path"])
        return ok, "" if ok else f"{c['path']} still exists"
    if t == "file_contains":
        data = files.after(c["path"])
        if data is None:
            return False, f"{c['path']} missing"
        body = data.decode("utf-8", "replace").lower()
        if "all" in c:
            miss = [s for s in c["all"] if s.lower() not in body]
            return not miss, f"{c['path']} missing: {miss}" if miss else ""
        ok = any(s.lower() in body for s in c["any"])
        return ok, "" if ok else f"{c['path']} has none of {c['any']}"
    if t == "file_unchanged":
        ok = files.before(c["path"]) == files.after(c["path"])
        return ok, "" if ok else f"{c['path']} changed"
    if t == "writes_within":
        prefixes = c["paths"]
        stray = [r for r in files.changes() if not any(r == p.rstrip("/") or r.startswith(p.rstrip("/") + "/")
                                                       for p in prefixes)]
        return not stray, f"writes outside {prefixes}: {stray[:5]}" if stray else ""
    if t in ("judge", "pytest"):
        return None, "pending"
    return False, f"unknown check type {t}"


def grade(task, text: str, tool_calls: list, files) -> list:
    """One result per check, in task order: {type, ok, detail}. A check that raises fails."""
    out = []
    for c in task.checks:
        try:
            ok, detail = check(c, text, tool_calls, files)
        except Exception as e:  # a broken check is a finding, never a silent pass
            ok, detail = False, f"check error: {e!r}"
        out.append({"type": c["type"], "ok": ok, "detail": detail})
    return out


def score(checks: list, view: str) -> tuple:
    """(score 0..1, passed) for one attempt under one judge's view ('opus' or 'gemini').
    A judge check counts with that judge's verdict; a verdict the judge could not give is left
    out of the score rather than counted as a fail."""
    vals = []
    for r in checks:
        if r["type"] == "judge":
            v = (r.get("judges") or {}).get(view)
            if v is None:
                continue
            vals.append(bool(v))
        elif r["ok"] is not None:
            vals.append(bool(r["ok"]))
    if not vals:
        return 0.0, False
    return sum(vals) / len(vals), all(vals)


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
