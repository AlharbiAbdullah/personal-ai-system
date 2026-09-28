---
name: learning
description: Rehearse one random lesson from a finished curriculum in 13-archive/learning/. Weighted toward what has gone longest without rehearsal, real randomness via script, mode chosen by the material.
allowed-tools: Read, Bash, Write, Edit, AskUserQuestion
---

# Retain: learning archive

One lesson, some work by John, 2-4 findings, one ledger line. Done.

## Pool

Durable topics only (decided 2026-08-26). Paths under `~/helm/13-archive/learning/`:
- `python-fundamentals/` (33 lessons, textbook era)
- `python-programming-fundamentals/` (15 lessons, build-first era, archived 2026-09-02; weak-areas log in its progress.md is the question bank)
- `systems-thinking/` (9 lessons, session-record era)
- `claude-code-mastery/` (43 lessons across `Module N - Name/`)
- `personal-ai-infrastructure/` (13 lessons)

Excluded on purpose: `omarchy`, `opencode-cli` (retired tools), `adapting-pai` (superseded by the live brain). Do not widen the pool in-session; the pool list lives in `scripts/pick.py`.

Lesson files are `Lesson NNN - *.md` or `NN - *.md`; `00 - *`, `progress.md`, `README.md` are not lessons.

## Step 1: pick

```
python3 ~/helm/03-rai/skills/retain/scripts/pick.py            # random, weighted
python3 ~/helm/03-rai/skills/retain/scripts/pick.py --topic systems
python3 ~/helm/03-rai/skills/retain/scripts/pick.py --lesson "018"
python3 ~/helm/03-rai/skills/retain/scripts/pick.py --list     # audit the weights
```

Weight = days since last rehearsal (never rehearsed = 180), x1.5 if the last score was 0-1, x0.5 if the last two were 3. The script does the randomness; Rai never "picks something interesting" by hand. Honor an explicit topic or lesson from John as a filter, nothing more.

Read the chosen lesson fully. It is Rai's answer key. John does not see it.

## Step 2: choose the mode (Rai judges, one per session)

| Material | Default | Alternatives |
|----------|---------|--------------|
| Python lesson | **Build from memory**: a small real task derived from the lesson's own "Do This Now" / drills, scaffolded as a runnable file in `~/playground/python-playground/retain/<slug>.py` with a docstring spec. Easy tier mandatory, mid/hard by his call. | **Review mode** when the lesson is about conventions (type hints, ruff/mypy, logging, config): Rai writes a realistic function or module, maybe clean, maybe not; he reviews it. |
| Systems-thinking lesson | **Teach-back**: he explains the concept to Rai playing a junior on a data-pipeline team; Rai asks the junior's confused questions, then grades. | **Blind reconstruction** (title only, he writes concept + traps, Rai diffs against the lesson). **Concept boundary** ("when would you NOT use X", the answer must be a scenario). **Transfer** (apply to a real project of his, news-digest, or Rai memory; Rai draws any diagram, never asks him to draw). |
| Claude-code-mastery / PAI lesson | **Blind reconstruction**. | **Transfer**: design or write the hook / skill / config for Rai from memory in scratch, then compare with the lesson. |
| Any lesson already scored 3 twice | **Interleave**: fuse it with a second random lesson from another topic (e.g. a feedback loop written as python, a hook designed with PAI's decision hierarchy). | Opt-in otherwise. |

John can name a mode; otherwise Rai's judgment stands and is not debated.

## Step 3: run the session

1. **Announce** in at most 10 lines: subject, mode, the task. No preamble about why retention matters.
2. **He works.** Rai waits. Socratic nudges are allowed only while he is mid-build; never after he hands in.
3. **Findings, not questions.** Rai states 2-4 findings: kept / lost / invented / mechanism missing. Then a score:
   - 0 gone: could not produce or recognize it
   - 1 recognized: knew it when shown, could not produce it
   - 2 produced with gaps: got the shape, missed a mechanism or trap
   - 3 clean
   Wrong answers get the right answer plus the mechanism. No "good try". A miss never triggers a re-read; it triggers a later rehearsal.
4. **Write back** (if this step is skipped, the session did not happen):
   - Append one line to `~/helm/06-learning/retention/ledger.jsonl`:
     `{"date":"YYYY-MM-DD","topic":"systems-thinking","lesson":"13-archive/learning/systems-thinking/Lesson 004 - Stocks and Flows.md","mode":"teach-back","score":2,"weak_spots":["..."],"artifact":null}`
     `lesson` is the path relative to `~/helm`, exactly as `pick.py` prints it. `artifact` is the playground file path or null.
   - Append each weak spot to that topic's `progress.md` weak-areas log with the date and `(retain)`, same wording rules as `/learning quiz`. That log is what `/learning quiz` re-tests later; the ledger only drives selection.
5. **Close** in one line. If he says "more", go back to Step 1. Never propose a next date, streak, or target.

## Rules

- No gotcha drills and no spot-the-bug with a guaranteed bug (rejected 2026-08-26). Build and Review are the drill shapes.
- Examples anchor in ETL / pipelines / his real systems, not money and not toy domains.
- Scores are selection signals, never targets. Do not report streaks or averages unless asked.
- Never re-ask the lesson's own wording; same mechanism, new surface.
- Keep the whole session under the size of one lesson drill. If it starts to feel like a lesson, it is too big.

## Examples

- "test me" → `pick.py`, lands on python L019 Generators → Build: `retain/lazy_batches.py`, write a generator that yields fixed-size batches from an iterator of records; findings; ledger line.
- "/retain systems" → lands on L06 Delays → Teach-back to a junior asking why the autoscaler oscillates.
- "/retain claude code hooks" → lands on CCM 14 Command Hooks → Blind reconstruction: write down the hook events, the JSON contract, and the exit-code semantics from memory.
- "/retain --mode transfer" → lands on PAI 02 Decision Hierarchy → apply it to how Rai should resolve a conflict between a learned rule and a steering rule.
