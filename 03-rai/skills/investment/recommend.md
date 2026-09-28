---
name: recommend
description: >
  Give concrete, ranked next investing actions inside the constraints. USE WHEN John asks
  "what should I do": DCA, rebalance, what to screen, what to watch in the paper-portfolio, or
  paper-to-real readiness.
allowed-tools: Read, Bash, WebSearch
---

# Investment Recommend

Hand John a short, ranked list of next actions, never an essay. Every line is rule-compliant (spot only) and paper-first by construction: real money moves only after a strategy is paper-validated and John gives an explicit, eyes-open sign-off on the amount.

## Instructions

### Step 1: Load the target

Read the master strategy for the branch list and target allocation:

```bash
cat ~/helm/02-ana/financial/investment/strategy.md
```

Read the relevant branch doc only if a recommendation needs its detail (e.g. `order-of-operations.md` for sequencing, `risk-management.md` for position-sizing, `sharia-screening.md` for the ratios). Check for the holdings note `~/helm/02-ana/financial/investment/holdings.md`. If it doesn't exist, say so plainly (none deployed, paper only); do not invent positions.

### Step 2: Optional: pull the paper-portfolio status

If the ask is "what now" rather than a pure plan question, glance at the local engine before recommending:

```bash
PP=~/helm/02-ana/financial/investment/paper-portfolio
systemctl --user status paper-portfolio.timer paper-portfolio.service --no-pager
journalctl --user -u paper-portfolio -n 50 --no-pager
tail -n 20 "$PP/portfolio.log"
```

Read `portfolio_state.json` (latest `nav_history` per stream) and `universe.json` (each stream's tickers) if a recommendation depends on them. If the timer is failing or runs are being missed, that is item #1 on the list (fix via `ops.md`).

### Step 3: Paper / learning actions

The core of the list. Pick the 2-4 highest-leverage of:

- **DCA on paper** toward the draft target allocation in `strategy.md`: name the under-weight sleeve(s) and the instrument (ETF / local-exchange name / sukuk / gold), as a *paper* entry, not a buy.
- **Sharia-screen a candidate** before it ever enters a paper book (the local-exchange and US-stock tickers in `universe.json` are starter placeholders pending screening). Prefer the `halalterminal-claude-skills` plugin (`/halal-setup` for a free key) for an AAOIFI verdict; else compute the ratios from SEC EDGAR / FMP per `sharia-screening.md`. End every verdict with: *"not professional advice — confirm with a qualified advisor."*
- **What to watch in the paper-portfolio** this week: a stream sitting in cash, drawdown creeping toward the 20% trip-wire, a missed or failed daily run, an assumption to validate against the marks.

### Step 4: Real-money actions (only if real money exists)

Skip this block entirely if the holdings note is absent or empty. If real positions exist:

- **Rebalance** toward target only when a sleeve drifts past its band (see `risk-management.md`): name the trim/add, spot only.
- **Position-size** any new real entry within the amount John signed off (see `risk-management.md`).

### Step 5: Paper-to-real readiness (only if asked)

Going paper -> real money is a big gate, never a trade. Run `/investment convene` on the proposal and hand John the plain-language case, including the ruin case. Real money stays off until the strategy is paper-validated AND he signs off, eyes open, on the amount. This skill never moves money.

### Step 6: Output

A ranked list, most important first:

```markdown
## Recommendations: {date}
1. {Highest-leverage paper/learning action, or a runtime fix if the engine is failing}
2. {Next paper action / screen candidate}
3. {Paper-portfolio watch item}
4. {Real-money rebalance, if applicable}
```

Keep it to 3-5 lines. No essay.

## Rules

- Rule-compliant by construction: spot only, no options / futures / leverage / shorts / riba. Never recommend an excluded instrument.
- Paper-first: default every "buy" to a paper entry. Real money only after paper-validation and John's eyes-open sign-off on the amount.
- No holdings note = say so. Do not fabricate positions or numbers.
- Every Sharia verdict ends with: "not professional advice — confirm with a qualified advisor."
