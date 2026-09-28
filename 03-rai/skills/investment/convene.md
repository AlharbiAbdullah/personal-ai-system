---
name: convene
description: Run The Restraint Gate on a proposed investing decision. USE WHEN any strategy change, paper→real transition, reweight, or new candidate (stock/ETF/strategy) is on the table. Default verdict DO NOTHING; Sharia chair holds a hard veto.
allowed-tools: Read, Bash, WebSearch
---

# Investment Convene

Run **The Restraint Gate** — the council's mechanical voting rule — on one proposed decision. Not a debate club, not a panel of celebrity quotes: a standing gate whose **default verdict is DO NOTHING**. The job is to find the path-to-ruin *first*, never to forecast a return that justifies a yes. Convene before any strategy change, paper→real transition, reweight, or new candidate.

## Instructions

### Step 1: Load the method

Read both governance docs so you apply the real lenses and the real funnel, not a paraphrase:

```bash
cat ~/helm/02-ana/financial/investment/07-tools/advisory-council.md
cat ~/helm/02-ana/financial/investment/00-foundation/assessment-framework.md
```

Pull a branch doc only if the proposal needs it — `sharia-screening.md` for Gate 1, `risk-management.md` / `spot-strategy.md` for Gate 2, `strategy.md` + `order-of-operations.md` for Gate 3. State the proposal in one line before you run the gate (what is being added / changed / promoted).

### Step 2: Run the funnel — strict order, short-circuit on first NO

Adversarial posture throughout: the proposer (Rai) does **not** self-approve. In the gate seat you hunt hidden fragility and the path-to-ruin, never the upside. Run the gates in order; **any single NO = DO NOTHING** and you stop — do not score the later gates.

| Gate | Question | NO when… |
|------|----------|----------|
| **Gate 1 — Sharia (instrument + conduct)** | Rule-compliant instrument AND rule-compliant conduct (no maysir / churn-as-gambling)? | Any leverage/margin/futures/options/short/riba; or speculation dressed as investing. **Hard veto — a Sharia NO ends it, cannot be outvoted.** |
| **Gate 2 — Edge Honesty** | A statistically-validated, out-of-sample edge — not a story? | No backtest / empty results dirs, un-tuned thresholds, negative Sharpe/expectancy, a 41-trade anecdote, or recovery read into 2 green days (recency bias). A negative **entry** edge = STOP. |
| **Gate 3 — Portfolio Fit** | Fits allocation, correlation, and the *coded* risk controls? | Concentration masquerading as diversification (tech names duplicating ETF top-holdings); breaches the satellite cap; or relies on a control that lives in docs but not in code. A control that has never fired does not exist. |
| **Final — John's eyes-open sign-off** | (Reached only if Gates 1-3 all PASS, and only for a big gate.) | Never auto-passed. Escalate. |

### Step 3: Resolution rules

- **Default = DO NOTHING.** Silence, doubt, or a tie resolves to no action. Burden is on the proposal to clear all gates, not on the gate to justify a block.
- **Sharia chair = hard veto.** A Sharia NO (instrument *or* conduct/maysir) ends the run; enthusiasm or expected return cannot outvote it.
- **No self-approval.** Rai never forecasts returns to argue a yes; in the gate seat Rai argues the ruin case.

### Step 4: Full council vs. checklist

- **Routine paper iteration** (one variable, paper-only, no real money, no rule-compliant-line change) → just run the Gate 1-3 checklist. No fan-out.
- **Major decision** (a new engine, lifting the cap, paper→real, changing the rule-compliant line) → convene the **full deliberative council**: a genuine fan-out across the 14 lenses, each hunting its own failure mode, resolved by Step 3. Trim borrowed authority — the reasoning carries the weight, not the famous names.

### Step 5: Log the run

A gate that never blocks is theatre. Append every run — proposal, gate results, verdict, and (if blocked) the gate + reason — to the graveyard so the record bites:

```bash
cat ~/helm/02-ana/financial/investment/08-practice/strategy-graveyard.md   # confirm format, then append a dated entry
```

The frozen SpotV0 NO is the worked example: a counter-trend dip-buyer with no trend filter, barred from up-days by its regime gate, never backtested on spot (empty results dirs), -20.3% over a 41-trade anecdote. The exit stack itself is mechanically sound — it armed breakeven and trailed the 3 small winners out in profit — but the negative *entry* edge means most trades hit the -3% stop before the +2.4% that arms the profit ladder, so exits are stop-dominated. Documented drawdown/correlation halts exist in no code. Clean Gate 2 + Gate 3 NO → FROZEN paper classroom behind a high revival bar.

### Step 6: Escalate the big gates

Three gates are **never** auto-passed — they are John's money and destination, not trades:
1. Going paper → real money at all.
2. The size of the cap.
3. Any change to strategy, risk rules, or the rule-compliant line.

If the funnel reaches one of these with all gates PASS, the verdict is **PROCEED-TO-SIGN-OFF**, not "done" — hand John the plain-language case (including the ruin case you found) and wait for his explicit, eyes-open call.

### Output

A short verdict block — no essay:

```
PROPOSAL: <one line — what is being added / changed / promoted>
MODE: checklist (routine paper) | full council (major)

GATE RESULTS:
- Gate 1 — Sharia:         PASS | NO (HARD VETO) — <reason>   not professional advice — confirm with a qualified advisor.
- Gate 2 — Edge Honesty:   PASS | NO — <reason>
- Gate 3 — Portfolio Fit:  PASS | NO — <reason>

VERDICT: DO NOTHING — blocked at <gate>: <reason>
   | PROCEED-TO-SIGN-OFF (big gate → John's eyes-open call): <plain-language case + the ruin case>

Logged to strategy-graveyard.md: yes
```

## Rules

- **Default verdict is DO NOTHING.** First NO short-circuits the funnel; don't score the rest. PROCEED is the exception, never the reflex.
- **Rule-compliant by construction.** Spot-only, no leverage/margin/futures/options/short/riba. Sharia chair holds a hard veto. **Every Sharia verdict ends: "not professional advice — confirm with a qualified advisor."**
- **No guarantees.** No return here is guaranteed; state the uncertainty plainly.
- **Paper-first.** Real money only after paper-validation and John's eyes-open sign-off on the amount. SpotV0 is a FROZEN failed baseline behind a high revival bar. This skill decides; it never deploys.
- **No self-approval.** Rai argues the ruin case, not the return. The 3 big gates are always John's explicit, eyes-open sign-off — never auto-passed.
- **Log every run.** Verdict + reason → `strategy-graveyard.md`. A gate that never blocks is theatre.

## Related

- [[advisory-council]] · [[assessment-framework]] · [[strategy-graveyard]] · [[run-review-2026-06]]
- [[strategy]] · [[order-of-operations]] · [[risk-management]] · [[sharia-screening]] · [[spot-strategy]]
- [[paper-trading-journal]] · [[psychology]]
- [[02-ana/financial/investment/AGENTS|AGENTS]] · [[investment-moc]]
