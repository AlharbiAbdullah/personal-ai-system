---
name: monthly-mirror
description: >
  Monthly look-back written by Rai, not John: analytics on the past month
  through Rai's eyes. Drift check against stated priorities, the good, the bad,
  the ugly, the funny, and which ideas deserve following. USE WHEN the user asks
  "how was my month", "am I drifting", "run the monthly mirror / monthly review /
  month analytics", or a new month has started and last month is unreviewed.
---

# Monthly Mirror

John looking back at his month through Rai's eyes. Rai reads everything the
vault recorded, then writes an honest outside-perspective verdict. This is NOT
the weekly retro (his voice, his memory); the mirror is Rai's voice, built from
receipts.

## Window

Default: the previous calendar month if it is unreviewed, otherwise the trailing
30 days ending today. An explicit range from the user always wins.

## Sources (all of them, every run)

1. **Daily observer logs**: `03-rai/semantic-memory/daily/YYYY-MM-DD.md` in the
   window. The richest source: per-session bullets already written through Rai's
   eyes.
2. **Git history**: `~/helm` log for the window. Separate HUMAN work from
   AUTOMATED churn (news-digest, memory drains, NAV snapshots, `.obsidian`).
   Volume, hour-of-day patterns, folder ranking by real content churn,
   shipped/abandoned/reverted.
3. **Life OS**: `02-ana/`, its journal entries, todos, financial state changes,
   shopping decisions, health, family, travel, soul.
4. **Trajectory**: `06-learning/` progress, `09-ideas/`
   status movement, `05-projects/` movement, `04-work/` footprint,
   `07-reading/`, `10-knowledge/` growth.
5. **Last month's mirror**: `02-ana/monthly/` previous file, if any. Check
   whether its "one change" actually happened; say so either way.

## Process

1. Confirm the window. Read last month's mirror first.
2. Fan out parallel subagents, one per source slice above (split the daily logs
   in half if the window is large). Each returns raw structured findings with
   dates: timeline, wins, failures/friction, funny moments, drift signals,
   decisions made or re-litigated, mood/energy signals.
3. Rai synthesizes alone. The judgment and the voice are Rai's, never delegated.
   Anchor the drift check against stated priorities: `02-ana/identity/goals.md`
   and the locked plans (the locked plans in your goals).
4. Write the report to `02-ana/monthly/YYYY-MM.md` (the month reviewed, not the
   month of writing). Leave the tree dirty; Linux commits.

## Report structure

The Short rule in `identity/response-format.md` applies: each section holds only what
matters, with a date or a number per claim. No fixed length. `2026-09.md` is the model.

```markdown
# Monthly Mirror — 2026-07 (written 2026-08-16)

## The Verdict
On track / drifting / mixed — two or three sentences, no hedging.

## Where the month actually went
Short narrative timeline + the numbers (human commits, active days,
folders ranked by real churn, tinkering days vs substance days).

## The Good
Concrete wins with dates.

## The Bad
Stalls, rabbit holes, repeated friction, priorities starved.

## The Ugly
The thing he would rather not look at. One item, named plainly.

## The Funny
Genuinely amusing moments from the logs. Specific, quoted if good.

## Drift Meter
Stated priorities vs observed time, one line each: priority — verdict — evidence.

## Ideas worth following
From 09-ideas/, landing, or session sparks: which deserve energy next month, why.

## Last month's change: did it happen?
Honest yes/no with evidence. Skip on the first run.

## One change for next month
One. Specific. Testable next mirror.
```

## Honesty rules

- Receipts on every claim: dates, filenames, commit subjects.
- Not flattering. A slow month is called slow; a tinkering binge is named.
- Deliberate choices are not drift: occasional journaling, no hard daily
  targets and any money strategy in your plan are settled policy. Judge against the policy,
  not against productivity culture.
- Funny is allowed to be at Rai's expense too.

## Anti-patterns

- Padding the Good to soften the Bad.
- Drift verdicts without receipts.
- Delegating synthesis or voice to a subagent.
- Turning the mirror into a task list. It produces exactly ONE change.

## Examples

- "Run the monthly mirror"
- "How did my month go? Am I drifting?"
- "Monthly mirror for July 16 to August 16"
- "Did I follow through on last month's change?"
