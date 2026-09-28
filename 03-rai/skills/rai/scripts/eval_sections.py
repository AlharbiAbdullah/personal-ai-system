#!/usr/bin/env python3
"""
eval_sections.py — the judged sections of /rai eval (b/c/d/e/f/smokes).

All judging goes through judge() -> lib/claude_cli.run_claude (Opus, xhigh effort —
decisions.md). Transcript parsing reuses lib/session_extract + lib/session_gate;
daily-log parsing reuses lib/daily_log. No store writes, ever.
"""

import json
import random
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path.home() / "helm" / "03-rai"
CLAUDE_PROJECTS = Path.home() / ".claude" / "projects"
ARCHIVE = Path.home() / "helm" / "13-archive" / "historical-sessions"

sys.path.insert(0, str(ROOT / "hooks"))
from lib.claude_cli import run_claude                      # noqa: E402
from lib.daily_log import DAILY_DIR, parse_blocks          # noqa: E402
from lib.session_extract import normalize_transcript       # noqa: E402
from lib.session_gate import _human_text, message_text     # noqa: E402

JUDGE_TMPL = """You are a strict evaluation judge for a personal AI memory system.
{rubric}

Respond with ONLY valid JSON, no prose, matching: {schema}

PAYLOAD:
{payload}"""


def judge(rubric: str, payload, schema: str, timeout: int = 600):
    """One place owns judging: prompt envelope, Opus xhigh, JSON-parse retry (1)."""
    prompt = JUDGE_TMPL.format(rubric=rubric, schema=schema,
                               payload=json.dumps(payload, ensure_ascii=False, indent=1))
    last = ""
    for _ in range(2):
        last = run_claude(prompt, model="opus", timeout=timeout, effort="xhigh")
        try:
            start = min(x for x in (last.find("["), last.find("{")) if x >= 0)
            end = max(last.rfind("]"), last.rfind("}")) + 1
            return json.loads(last[start:end])
        except (ValueError, json.JSONDecodeError):
            continue
    raise RuntimeError(f"judge: unparseable output after retry: {last[:200]}")


def _recent_transcripts(n: int = 40):
    """Most recent interactive-session transcripts across all projects."""
    files = sorted(CLAUDE_PROJECTS.glob("*/*.jsonl"),
                   key=lambda f: f.stat().st_mtime, reverse=True)
    return [f for f in files if f.stat().st_size > 10_000][:n]


# ---------------------------------------------------------------- b · injection

def section_b(run_id: str):
    from lib import memory_retrieval as mr
    prompts, seen = [], set()
    for t in _recent_transcripts(40):
        d = normalize_transcript(t)
        if d.get("entrypoint") == "sdk-cli":
            continue
        for m in d["messages"]:
            ht = _human_text(m)
            if ht and 40 <= len(ht) <= 1500 and ht[:80] not in seen:
                seen.add(ht[:80])
                prompts.append(ht)
    sample = random.Random(run_id).sample(prompts, min(20, len(prompts)))
    pairs = []
    for pr in sample:
        # replicate memory-injection.py: top-3 semantic + top-2 episodic, 0.35 floor
        ptr = [h["content"][:130] for h in mr.query_semantic(pr, 3) if h["relevance"] >= 0.35]
        ptr += [f"past session {h['date']} {h.get('context') or ''}"
                for h in mr.query_episodic(pr, 2) if h["relevance"] >= 0.35]
        pairs.append({"prompt": pr[:400], "pointers": ptr})
    with_ptr = [p for p in pairs if p["pointers"]]
    verdicts = judge(
        "For each pair: the user typed `prompt` and the memory system auto-injected "
        "`pointers`. Judge whether at least one pointer is GENUINELY relevant and useful "
        "context for that prompt (not generic, not off-topic).",
        with_ptr, '[{"idx": 0, "useful": true, "relevant_pointers": 1}]',
    ) if with_ptr else []
    useful = sum(1 for v in verdicts if v.get("useful"))
    score = round(useful / len(with_ptr), 3) if with_ptr else 0.0
    return {"score": score, "prompts": len(pairs), "with_pointers": len(with_ptr),
            "useful": useful,
            "coverage": round(len(with_ptr) / max(1, len(pairs)), 3),
            "issues": [f"pointer noise: only {useful}/{len(with_ptr)} pointer sets useful"]
            if with_ptr and useful / len(with_ptr) < 0.6 else []}


# ---------------------------------------------------------------- c · adherence

_EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")
_ARABIC = re.compile("[؀-ۿ]")
_CODE = re.compile(r"```.*?```|`[^`\n]+`", re.DOTALL)


def _banned_words():
    """Parse the list from response-format.md at runtime — single source of truth."""
    for ln in (ROOT / "identity" / "response-format.md").read_text().splitlines():
        if ln.lower().startswith("never use:"):
            return [w.strip().rstrip(".").lower() for w in ln[10:].split(",") if w.strip()]
    return []


def section_c(run_id: str):
    banned = _banned_words()
    outputs = []
    for t in _recent_transcripts(30):
        d = normalize_transcript(t)
        if d.get("entrypoint") == "sdk-cli":
            continue
        for m in d["messages"]:
            if m.get("type") == "assistant":
                txt = message_text(m)
                if len(txt) >= 200:
                    outputs.append(txt)
    sample = random.Random(run_id).sample(outputs, min(30, len(outputs)))
    lint = []
    for txt in sample:
        prose = _CODE.sub("", txt)  # banned words inside code/quotes are not voice
        low = prose.lower()
        hits = [w for w in banned if re.search(rf"\b{re.escape(w)}\b", low)]
        v = {"banned": hits, "em_dash": prose.count("—"),
             "emoji": bool(_EMOJI.search(prose)), "arabic": bool(_ARABIC.search(prose))}
        v["clean"] = not (hits or v["em_dash"] or v["emoji"] or v["arabic"])
        lint.append(v)
    clean = sum(1 for v in lint if v["clean"])
    tone = judge(
        "Score each output 0-10 against this voice contract: direct, plain speech, "
        "lead with the answer, no corporate language, no fluff, teammate tone.",
        [{"idx": i, "output": s[:1200]} for i, s in
         enumerate(random.Random(run_id + "t").sample(sample, min(5, len(sample))))],
        '[{"idx": 0, "tone": 8}]',
    ) if sample else []
    tone_avg = round(sum(v.get("tone", 0) for v in tone) / max(1, len(tone)), 1)
    score = round(0.7 * clean / max(1, len(lint)) + 0.3 * tone_avg / 10, 3)
    top_banned = sorted({w for v in lint for w in v["banned"]})
    return {"score": score, "sampled": len(lint), "clean": clean, "tone_avg": tone_avg,
            "issues": ([f"banned words appearing: {', '.join(top_banned[:8])}"] if top_banned else [])
            + ([f"em-dashes in {sum(1 for v in lint if v['em_dash'])} outputs"]
               if any(v["em_dash"] for v in lint) else [])}


# ---------------------------------------------------------------- d · bullets

def _turn_near(transcript: Path, when_local: datetime, span_min: int = 12) -> str:
    lo = when_local.astimezone(timezone.utc) - timedelta(minutes=span_min)
    hi = when_local.astimezone(timezone.utc) + timedelta(minutes=span_min)
    out = []
    for line in transcript.read_text().splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = e.get("timestamp")
        if not ts or e.get("type") not in ("user", "assistant"):
            continue
        try:
            t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            continue
        if lo <= t <= hi:
            txt = message_text(e)
            if txt.strip():
                out.append(f"[{e['type']}] {txt[:600]}")
    return "\n".join(out)[:3000]


def section_d(run_id: str):
    blocks = []
    for f in sorted(DAILY_DIR.glob("*.md")):
        for t, sid, text in parse_blocks(f):
            blocks.append({"date": f.stem, "time": t, "session": sid, "bullets": text})
    sample = random.Random(run_id).sample(blocks, min(10, len(blocks)))
    pairs = []
    for b in sample:
        hits = list(CLAUDE_PROJECTS.glob(f"*/{b['session']}*.jsonl"))
        if not hits:
            continue
        when = datetime.strptime(f"{b['date']} {b['time']}", "%Y-%m-%d %H:%M").astimezone()
        turn = _turn_near(hits[0], when)
        if turn:
            pairs.append({"bullets": b["bullets"][:1200], "turn_excerpt": turn})
    verdicts = judge(
        "Each pair: `bullets` were written by an observer model to summarize `turn_excerpt` "
        "(a conversation window). Score accuracy 0-10 (do the bullets truthfully reflect the "
        "turn?), count hallucinated bullets (claims absent from the excerpt) and missed "
        "important events.",
        pairs, '[{"idx": 0, "accuracy": 8, "hallucinated": 0, "missed": 1}]',
    ) if pairs else []
    acc = round(sum(v.get("accuracy", 0) for v in verdicts) / max(1, len(verdicts)) / 10, 3)
    halluc = sum(v.get("hallucinated", 0) for v in verdicts)
    return {"score": acc, "pairs": len(pairs), "hallucinated_total": halluc,
            "issues": [f"{halluc} hallucinated bullets across {len(pairs)} sampled turns"]
            if halluc else []}


# ---------------------------------------------------------------- e · distill

def section_e(run_id: str):
    from lib import memory_retrieval as mr
    col = mr._collection("rai-semantic")
    files = sorted(ARCHIVE.glob("session_2026*.json"))[-60:]
    rnd = random.Random(run_id)
    rnd.shuffle(files)
    checked, results = 0, []
    for fp in files:
        if checked >= 5:
            break
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        sid = d.get("session_id", "")
        rows = col.get(where={"source_session": sid}, include=["metadatas"])
        if not rows.get("ids"):
            continue
        texts = [message_text(m) for m in d.get("messages", [])]
        convo = "\n".join(t for t in texts if t.strip())
        if len(convo) < 2000:
            continue
        distilled = [f"[{(m or {}).get('type')}] {(m or {}).get('content', '')[:200]}"
                     for m in rows["metadatas"]]
        v = judge(
            "The `distilled` list is what a batch pipeline extracted into long-term memory "
            "from the conversation `transcript`. Score coverage 0-10 (are the important "
            "decisions/facts captured?) and list up to 3 important things it missed.",
            {"distilled": distilled[:40], "transcript": convo[:6000] + "\n...\n" + convo[-3000:]},
            '{"coverage": 7, "missed": ["..."]}', timeout=600,
        )
        results.append({"session": sid[:8], "coverage": v.get("coverage", 0),
                        "missed": v.get("missed", [])})
        checked += 1
    score = round(sum(r["coverage"] for r in results) / max(1, len(results)) / 10, 3)
    return {"score": score, "sessions": results,
            "issues": [f"{r['session']}: missed {m}" for r in results for m in r["missed"][:2]]}


# ---------------------------------------------------------------- f · self-evolve

def section_f(run_id: str):
    active = [ln.lstrip("- ").strip()
              for ln in (ROOT / "identity" / "learned.md").read_text().splitlines()
              if ln.startswith("- ")]
    cands = []
    cand_file = ROOT / "semantic-memory" / "learned-candidates.jsonl"
    for line in cand_file.read_text().splitlines():
        try:
            c = json.loads(line)
        except json.JSONDecodeError:
            continue
        if c.get("status") == "probation":
            cands.append({"content": c.get("content", ""), "evidence": c.get("evidence", [])[:2],
                          "re_confirmations": c.get("re_confirmations", 1)})
    sample = random.Random(run_id).sample(cands, min(20, len(cands)))
    payload = {"active": active, "probation_sample": sample}
    v = judge(
        "`active` preferences steer an AI assistant's behavior EVERY session; "
        "`probation_sample` are candidates. For each active item: endorse=true if it is a "
        "durable, correct, safely-generalizable preference of the user; endorse=false with a "
        "reason if it is one-off, task-specific, wrong, or risky. For probation: flag only "
        "items that should NEVER be promoted.",
        payload,
        '{"active": [{"idx": 0, "endorse": true, "reason": ""}], '
        '"probation_flags": [{"idx": 0, "reason": ""}]}',
    )
    act_v = v.get("active", [])
    endorsed = sum(1 for x in act_v if x.get("endorse"))
    score = round(endorsed / max(1, len(act_v)), 3)
    flags = [f"ACTIVE #{x.get('idx')}: {x.get('reason')}" for x in act_v if not x.get("endorse")]
    flags += [f"probation: {x.get('reason')}" for x in v.get("probation_flags", [])[:5]]
    return {"score": score, "active_total": len(active), "endorsed": endorsed,
            "probation_sampled": len(sample),
            "issues": flags}  # flags only — John demotes (decisions.md)


# ---------------------------------------------------------------- smokes

def section_smokes(run_id: str):
    golden = [json.loads(x) for x in
              (ROOT / "semantic-memory" / "eval" / "golden.jsonl").read_text().splitlines()
              if x.strip()]
    pos = [g for g in golden if g.get("kind") == "positive"]
    sample = random.Random(run_id).sample(pos, min(5, len(pos)))
    runs = []
    for g in sample:
        try:
            out = run_claude(f"/recall {g['question']}", model="sonnet", effort="high",
                             timeout=420, cwd=str(Path.home() / "helm"))
        except Exception as e:  # a dead smoke is a finding, not a crash
            out = f"SMOKE-ERROR: {e}"
        runs.append({"question": g["question"], "expected": g["expected"],
                     "answer": out[:1500]})
    verdicts = judge(
        "Each item: `question` was asked to an assistant with tiered memory recall; "
        "`answer` is what it said; `expected` describes the ground truth. "
        "correct=true only if the answer actually contains the expected information.",
        runs, '[{"idx": 0, "correct": true}]',
    ) if runs else []
    correct = sum(1 for v in verdicts if v.get("correct"))
    return {"score": round(correct / max(1, len(runs)), 3), "runs": len(runs),
            "issues": [f"smoke miss: {runs[v['idx']]['question'][:80]}"
                       for v in verdicts if not v.get("correct") and v.get("idx", 99) < len(runs)]}


SECTIONS = {"b": section_b, "c": section_c, "d": section_d,
            "e": section_e, "f": section_f, "smokes": section_smokes}


def run(section: str, run_id: str, write_partial):
    data = SECTIONS[section](run_id)
    write_partial(run_id, section, data)
    return 0
