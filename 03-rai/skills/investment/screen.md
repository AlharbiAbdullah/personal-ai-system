---
name: screen
description: Sharia-screen a ticker John names — AAOIFI verdict (COMPLIANT / NOT / DEBATED) with ratios, purification note, and the "not professional advice" disclaimer.
allowed-tools: Read, Bash, WebSearch
---

# Sharia Screen

Run an AAOIFI-method Sharia screen on a single ticker. Returns a verdict, the underlying ratios, and a purification (tazkiyah) note. This is screening, not professional advice — always defer the final ruling to a qualified advisor.

## Instructions

### Step 1: Load the method

Read the canonical screening doc so you apply the right thresholds and exclusions:

```bash
cat ~/helm/02-ana/financial/investment/01-compliance/sharia-screening.md
```

Confirm the asset with John if ambiguous (ticker vs. company name, which exchange). Tickers only: coins are out of scope (see `SKILL.md`); if John names one, say so and do not screen it.

### Step 2: Get the verdict — plugin first

Prefer the **halalterminal-claude-skills** plugin for an AAOIFI verdict (it's the lowest-effort, highest-trust path).

- If it isn't keyed yet, tell John to run `/halal-setup` once for a free key, then proceed.
- Ask the plugin for the AAOIFI screen on the ticker. Capture the verdict + the three ratios it reports.

If the plugin is unavailable, fall back to **Step 3**.

### Step 3: Fallback — compute the 3 ratios manually (equities)

Pull fundamentals from SEC EDGAR or FMP, then compute each ratio against **market cap** (AAOIFI uses market cap; some boards use total assets — note which you used):

| Ratio | Formula | AAOIFI threshold |
|-------|---------|------------------|
| Interest-bearing borrowings | total interest-bearing borrowings ÷ market cap | **< 33%** |
| Cash + interest-bearing securities | (cash + interest-bearing investments) ÷ market cap | **< 33%** |
| Accounts receivable | accounts receivable ÷ market cap | **< 33%** |
| Impure / non-permissible revenue | non-rule-compliant revenue ÷ total revenue | **< 5%** |

Plus **sector exclusions** (hard NO regardless of ratios): conventional banking/insurance, riba lenders, alcohol, tobacco, pork, gambling, adult content, weapons-as-core, conventional music/media where it's the core business.

```bash
# Example data sources (set FMP_API_KEY in env; never hardcode keys in this file)
curl -s "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=AAPL&type=10-Q&output=atom" -H "User-Agent: rai screen john.doe@example.com"
curl -s "https://financialmodelingprep.com/api/v3/balance-sheet-statement/AAPL?period=quarter&limit=1&apikey=$FMP_API_KEY"
curl -s "https://financialmodelingprep.com/api/v3/profile/AAPL?apikey=$FMP_API_KEY"   # market cap
```

Use the most recent quarter. If any input is missing or stale, say so plainly rather than guessing.

### Step 4: Cross-check edge cases

If the verdict is borderline (a ratio within ~3 points of a threshold, or conflicting sources), cross-check a **second independent source** (e.g., a second screening provider via WebSearch, or recompute from a different filing) before committing to a verdict.

### Step 5: Output

Report in this shape:

```
ASSET: <ticker> — <name, exchange>
VERDICT: COMPLIANT | NOT COMPLIANT | DEBATED
Method: halalterminal plugin | manual (SEC EDGAR / FMP), as-of <quarter>

Ratios (equities):
- Interest-bearing borrowings:  XX.X%  (< 33%)  PASS/FAIL
- Cash + interest securities:   XX.X%  (< 33%)  PASS/FAIL
- Accounts receivable:          XX.X%  (< 33%)  PASS/FAIL
- Impure revenue:                X.X%  (< 5%)   PASS/FAIL
- Sector exclusion:             none | <which>

Purification (tazkiyah): purify ~X.X% of dividends/gains (impure-revenue share)
  by donating to charity, no expectation of reward.

Source(s) cross-checked: <plugin / EDGAR / FMP / second source>

⚠️ This is a screen, not professional advice — confirm with a qualified advisor.
```

## Rules

- **Always** end with: "not professional advice — confirm with a qualified advisor."
- Screening only — no buy/sell call here. Actions live in `recommend.md`; this skill just answers "is X rule-compliant?".
- State the threshold convention you used (market cap vs. total assets) so the number is auditable.
- If data is missing, say so. Never fabricate a ratio to force a verdict.
- Honor the standing guardrails: Sharia-compliant (spot / no leverage), paper-first. A COMPLIANT verdict is not a green light to deploy real money; that needs paper-validation and John's eyes-open sign-off on the amount.
