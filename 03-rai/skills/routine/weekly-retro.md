---
name: weekly-retro
description: >
  Structured end-of-week personal retrospective. USE WHEN the week is
  closing and the user wants to capture what shipped, what blocked, what
  they learned, and what to change next week. Sits between occasional journaling
  and life-level telos updates.
---

# Weekly Retro

A disciplined weekly review. 20–30 minutes. Written down. Retrievable later.

## When to use

- End of work week (Friday evening or Saturday morning)
- Before major decisions that need week-level context
- Before 1:1s or status updates to your manager / partner / coach
- As input to monthly or quarterly reviews

## When NOT to use

- Mid-week reflection — use `/routine/journal` for single-day reflection
- Long-term goals / belief updates — use `/life/telos`
- Task planning for tomorrow — use `/routine/tomorrow-prep`

## Structure — 5 sections

### 1. Shipped
What reached "done" this week? Concrete artifacts.
- Code merged
- Docs written
- Meetings held
- Decisions made
- Personal milestones hit

Don't pad. If the week was slow, say so.

### 2. Blocked
What stalled or slowed you?
- External dependency (waiting on X)
- Technical debt that resurfaced
- Unclear requirements
- Energy / health / family
- Context-switching overhead

Pattern-match: does this blocker show up often? What would kill it permanently?

### 3. Energy audit
Rate the week's energy on a 1–10 scale. Then:
- High-energy moments — what was I doing? With whom?
- Low-energy moments — same questions
- What's trending up / down vs last week?

Use this to shape next week. Put high-energy work early; protect low-energy time.

### 4. One learning
One thing I didn't know Monday. Could be:
- Technical (new tool, pattern, insight)
- About the project (what the data showed)
- About a person (teammate's motivation, customer's pain)
- About myself (this trigger drains me; this habit serves me)

Write it down so future-me can encode it.

### 5. Change
What will I do DIFFERENTLY next week? One thing. Specific.

Not "be more productive" — "block the first 90 minutes of Mon/Wed/Fri for deep work on Helios."

## Output

```markdown
# Weekly Retro — 2026-04-25 (Week 17)

## 1. Shipped
- Landed skills reorg Phase A–G (22 top-level entries)
- Demo'd Helios to Acme Corp leadership on Thu
- Wrote OpenKit Phase 0 PRD

## 2. Blocked
- Helios prod deploy pending on sec-ops signoff
- Dataforge work idle (no time)

## 3. Energy: 7/10
- High: Wed morning reorg sprint (4h deep work, flow)
- Low: Fri late-afternoon stakeholder update (40 min, drain)
- Trend: steady, not exhausted

## 4. Learning
RAG pipelines need eval loops FROM DAY ONE. Without RAGAS baselines,
we can't detect regressions. Applying to OpenKit.

## 5. Change
Block Mon/Wed/Fri 9–11am as deep-work slots. No meetings, no Slack.
```

Save to: `~/helm/02-ana/weekly/YYYY-WW.md` or similar. Cross-link to any journal entries from that week (there may be none).

## Process

1. Read last week's retro first — did you follow through on the "change"?
2. Scan the week's journal entries (if any) + commits + calendar
3. Fill each section — don't skip any
4. Commit the file
5. Set reminder to open next Friday

## Anti-patterns

- Retro that's all "shipped" with no blockers — you're either flexing or forgetting
- Vague changes ("work harder") — not actionable
- Skipping the energy audit — it's the early warning system
- Same blocker every week with no action — this retro failed; escalate
- Retro as performance review for external eyes — kills honesty

## Cross-references

- Daily rhythm → `/routine/journal`, `/routine/today-prep`, `/routine/tomorrow-prep`
- Monthly/quarterly self-model update → `/life/telos`
- Session memory for pattern detection → `/recall/history`

## Examples

- "Run the weekly retro for this week"
- "What did I ship, block, and learn this week?"
- "Compare this week's energy to last week"
- "Weekly retro — 2026-04-22 through 2026-04-28"
