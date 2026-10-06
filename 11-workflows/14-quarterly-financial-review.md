# Quarterly Financial Review

**Use when:** the 90-day bank-statement review, once a calendar quarter closes: the trend layer above the monthly close.
**Not for:** 09 monthly money close, for payday.
**Done when:** `reviews/YYYY-qN.md` is written, and any operating bucket that drifted >10% is propagated to `budget.md` and `plan.md`. The open watchlist is carried forward with progress noted.
**Cadence:** Quarterly, first week of the month after a calendar quarter closes. Schedule: `02-ana/financial/review-calendar.md`.

The 90-day trend layer above the monthly close. The steps that get skipped are the back half: drift propagation and the watchlist carry. So this playbook front-loads the gates that make the review actually change a number, not just describe one. The pull-and-write is the mechanical part; the gates are the value. Every number lives in your own files under `02-ana/financial/`, never in this workflow.

```
Pull statements → Append raw block → Write review → Drift gate → Propagate → Carry watchlist → Sync
```

---

## Steps

### 1. Pull the statements

- [ ] Download the statements for every account covering the **full quarter** to `~/Downloads/`.
- [ ] Confirm the quarter's lumpy events landed before reviewing, since they skew the averages. List them once in `review-calendar.md` (for example an insurance renewal or a tax payment).

### 2. Append the raw block to transactions.md

- [ ] Add a **`## YYYY-QN — <start> → <end>`** block to the **TOP** of
      `02-ana/financial/transactions.md`, same schema as the prior blocks. This is the
      append-only raw layer; do not edit older blocks.

### 3. Write the review file

- [ ] Create `02-ana/financial/reviews/YYYY-qN.md`, mirroring the structure of the
      previous review. Compute every bucket as a **delta vs the prior quarter**, not just
      an absolute.

> **Decision Point**: the review file is the artifact, but a review that only describes
> is half-done. Steps 4 to 6 are where it earns its keep. Do not call the run finished at
> step 3.

### 4. DRIFT GATE: the propagation that gets skipped

- [ ] Check each operating bucket against its 10% trigger in `review-calendar.md`.
- [ ] **Any bucket past its trigger → PROPAGATE the new number** into `budget.md` and
      `plan.md`. A drift noted in the review but not written into the operating files is
      the step that gets missed.
- [ ] Ask **"what changed?"** for each drift: a new subscription, a new commitment,
      lifestyle creep, or a one-off skewing the average. Below target → capture what worked.

### 5. Reconcile the lumpy events

- [ ] Tie the quarter's big movements to the plan, and confirm any draw on savings matches
      the purpose those savings are for.

### 6. Debt tripwire + watchlist carry

- [ ] Read the revolving-balance trend across the quarter, if you carry one. Target: down.
- [ ] **Up for 2 consecutive months → stop and re-decide the strategy.** This overrides the rest of the review.
- [ ] Carry the **open watchlist** in `review-calendar.md` into the new review file.
      Resolve what the quarter's data now allows, and leave the rest open with a progress
      note. Nothing is dropped: open items carry until closed.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Gating facts

| Fact | Where it lives |
|------|----------------|
| Caps and savings commitment | `02-ana/financial/plan.md` |
| Drift triggers, lumpy events, watchlist | `02-ana/financial/review-calendar.md` |
| Debt balances and tripwire | `02-ana/financial/debt-plan.md` |
| Drift gate | any operating bucket >10% → propagate |

---

## Connections

- Schedule, drift table and watchlist: `02-ana/financial/review-calendar.md`
- Monthly spine that feeds the quarters: [[09-monthly-money-close]]
- Portfolio read (paper-first): `/investment → status`
- Commit rule: `11-workflows/AGENTS.md`
