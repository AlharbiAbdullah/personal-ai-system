---
name: review
description: Periodic (weekly/monthly) investment review + improvement loop. Paper-portfolio performance, risk check, paper-journal lessons, allocation drift, and ONE falsifiable challenger change to test on paper. USE WHEN John wants a portfolio review.
allowed-tools: Read, Bash
---

# Investment Review

The reflection loop. Pull the paper-portfolio's numbers from the local runtime, grade the paper journal, check allocation drift against the target, and propose exactly ONE falsifiable change to test on a paper challenger. Output a dated review note John can save under `reviews/`. This skill never edits the engine or its state.

**Guardrails (non-negotiable):** paper-first, Sharia-compliant (spot, no leverage/options/futures/shorts/riba), never edit `portfolio.py`, `universe.json` or `portfolio_state.json` here. The review *proposes* a challenger; it does not promote one.

## Instructions

### Step 1: Pull paper-portfolio performance (local)

The engine runs on this box (`paper-portfolio.timer` -> `paper-portfolio.service`). Read, never run:

```bash
PP=~/helm/02-ana/financial/investment/paper-portfolio
systemctl --user status paper-portfolio.timer paper-portfolio.service --no-pager
journalctl --user -u paper-portfolio -n 50 --no-pager
tail -n 40 "$PP/portfolio.log"
cat "$PP/universe.json"
cat "$PP/portfolio_state.json"
```

For each stream defined in `universe.json`, from `nav_history` over the period under review (week or month; ask if unclear): start and end NAV, return %, the peak-to-current drawdown, and current holdings vs its ticker list. Note any missed or failed daily runs (gaps in `nav_history` dates, `failed` in the journal). This is **paper**; numbers are tuition, not money.

### Step 2: Risk check (the 20% drawdown trip-wire)

If any paper stream or satellite pick is **down ~20% from its peak**, the rule fires: **recommend pulling that strategy back** and re-qualifying it before any further size. State it plainly: drawdown is the signal the rules (or the discipline) broke, per [[risk-management]]. Never rationalize past 20%.

### Step 3: Review the paper-trading journal, by regime

Read `~/helm/02-ana/financial/investment/08-practice/paper-trading-journal.md`. Grade the *decisions*, not the P&L:

- **What worked, by regime**: group entries by market condition (trend up / chop / down). Which setups actually paid in which regime?
- **Repeated mistakes**: the same losing decision 3+ times is the edge bleeding out. Name it.
- **Emotion column**: flag high-emotion entries (>=7); if the "I'm sure" calls keep losing, the enemy is discipline, not the market.
- **Skips logged**: a logged FOMO-skip is a win; count them.

### Step 4: Allocation drift vs the target

Read `~/helm/02-ana/financial/investment/strategy.md`. Real money begins only after paper-validation and John's eyes-open sign-off on the amount, so most "drift" is on paper / in the plan. Compare the paper books and any real holdings against the architecture and flag:

- Satellite sleeve over its **<=25% hard cap** -> flag for rebalance.
- Real money deployed without a recorded sign-off -> guardrail violation, call it out.
- Holdings live in `~/helm/02-ana/financial/investment/holdings.md`. If it doesn't exist, **say so plainly**: none deployed, paper only. There's no brokerage API; holdings are tracked manually.

"Rebalance" here usually means *adjust the paper plan*, not move money.

### Step 5: Champion / challenger (propose ONE falsifiable change)

Discipline: the paper-portfolio as configured (`universe.json` + `portfolio.py`) is the **champion**. Propose exactly **ONE** concrete, falsifiable change to test on a **paper challenger**; never edit the champion here.

- One variable only (e.g., "trend filter on a 12-month average instead of 10").
- **Falsifiable success criterion** stated up front (e.g., "over the backtest window and 60 days of forward paper, the challenger must beat the champion's return at equal-or-lower drawdown, else discard").
- The test path is a backtest in `paper-portfolio/research/` (local venv). Changing the champion is a strategy change: it runs through `/investment convene` and John's sign-off, never here.

### Step 6: Write the dated review note

```bash
mkdir -p ~/helm/02-ana/financial/investment/08-practice/reviews
date +%F   # the review date
```

Write to `~/helm/02-ana/financial/investment/08-practice/reviews/{YYYY-MM-DD}-review.md`. Match the folder's house style: **no YAML frontmatter**, `# h1` + `>` summary + `**Last updated:**`, tables for numbers, `## Related` wiki-links at the end:

```markdown
# Investment Review: {YYYY-MM-DD} ({weekly|monthly})

> {one-line verdict: is the loop healthy, and what's the single thing to change?}

**Last updated:** {YYYY-MM-DD}

## Paper-portfolio performance
{per stream: start/end NAV, return %, peak->current drawdown, holdings; missed or failed runs}

## Risk check
{20% trip-wire: clear, or fired -> pull the strategy back}

## Paper journal, by regime
{what worked where; repeated mistakes; emotion flags; skips logged}

## Allocation vs target
{drift, satellite-cap check, guardrail violations, or "no holdings note; none deployed, paper only"}

## Challenger proposal (paper only)
- Change: {one variable}
- Hypothesis: {what improves and why}
- Success criterion (falsifiable): {metric + threshold + window}
- Test: backtest in paper-portfolio/research/; promotion only via /investment convene + sign-off.

## Related
- [[strategy]], [[risk-management]], [[paper-trading-journal]], [[order-of-operations]]
```

## Rules

- **Never** edit `portfolio.py`, `universe.json` or `portfolio_state.json`, and never start the service here. This skill reviews and proposes; changes run through `/investment convene` with John's explicit, eyes-open sign-off.
- **One challenger per review.** More than one change = you can't tell which one worked.
- Honest and grounded: if a stream is losing or a guardrail is breached, say it first, not last.
