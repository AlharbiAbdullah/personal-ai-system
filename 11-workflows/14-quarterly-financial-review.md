# Quarterly Financial Review

**Triggered by:** "quarterly review" / "run the Q review" / "90-day statement review"
**Cadence:** Quarterly, first week of the month after a calendar quarter closes — next runs: Oct 2026 (2026-Q3), Jan 2027 (2026-Q4), Apr 2027 (2027-Q1). Schedule: `02-ana/financial/review-calendar.md`.
**Done when:** `reviews/YYYY-qN.md` is written, any operating bucket that drifted >10% is propagated to `budget.md` / `plan.md` / `cash-flow.md`, and the open watchlist is carried forward with progress noted.

The 90-day trend layer above the monthly close. The baseline ran once (May 2026); five
quarters now sit "pending". The steps that get skipped are the back half — drift
propagation and the watchlist carry — so this playbook front-loads the gates that make
the review actually change a number, not just describe one. The pull-and-write is the
mechanical part; the gates are the value.

```
Pull statements → Append raw block → Write review → Drift gate → Propagate → Carry watchlist → Leave for coordinator
```

> **Survival-phase frame (until ~Apr 2027):** defensive, debt-first. A drift that grows
> the credit-card balance ([your balance] USD @ ~30–36% APR) is the failure mode this review exists to
> catch — those cards are a guaranteed return no investment beats. Sources:
> `02-ana/financial/debt-plan.md`, `investment/07-tools/advisory-council.md`.

---

## Steps

### 1. Pull the statements

- [ ] Download **Main + Daily** account PDFs covering the **full quarter** (Q3 = Jul 1 → Sep 30)
      to `~/Downloads/`.
- [ ] Confirm the quarter's lumpy event(s) landed before reviewing — they skew the averages:
      Q3 = end-July school payment (−[your tuition half-payment]); Q4 = mid-Nov rent (−[your rent half-payment]); Q1 = Jan bonus
      (+[your annual bonus]) + end-Jan school (−[your tuition half-payment]). Source: `review-calendar.md` lumpy-events table.

### 2. Append the raw block to transactions.md

- [ ] Add a **`## YYYY-QN — <start> → <end>`** block to the **TOP** of
      `02-ana/financial/transactions.md`, same schema as the prior blocks. This is the
      append-only raw layer; do not edit older blocks.

### 3. Write the review file

- [ ] Create `02-ana/financial/reviews/YYYY-qN.md`, mirroring the structure of
      `reviews/2026-05-baseline.md`. Compute every bucket as a **delta vs the prior
      quarter**, not just an absolute.

> **Decision Point**: the review file is the artifact, but a review that only describes
> is half-done. Steps 4–6 are where it earns its keep. Do not call the run finished at
> step 3.

### 4. DRIFT GATE — the propagation that gets skipped

- [ ] For each operating bucket, check it against its 10% trigger in `review-calendar.md`
      ("What a drift > 10% looks like"). Key triggers:
      savings deposit below [your savings floor] (target [your savings]), weekly variable above [your variable cap]
      (target [your weekly variable target]), card auto-draw above [your card cap] (target [your card target]),
      surplus→cards below [your surplus floor].
- [ ] **Any bucket past its trigger → PROPAGATE the new number** into `budget.md`,
      `plan.md`, and/or `cash-flow.md`. A drift noted in the review but not written into
      the operating files is the exact step that has been missed every quarter.
- [ ] Ask **"what changed?"** for each drift — new subscription, new person supported,
      lifestyle creep, or a one-off skewing the average. Below-target → capture what worked.

### 5. Reconcile the lumpy events

- [ ] Tie the quarter's big movements to `cash-flow.md`: rent (−[your rent half-payment]), school
      (−[your tuition half-payment]), household allowances, bonus deployment ([your bonus split]).
      Confirm savings draws match the single-purpose rule (rent + school only).

### 6. Visa tripwire + watchlist carry

- [ ] Read the **Visa total carrying balance** trend across the quarter. Target: DOWN.
- [ ] **UP for 2 consecutive months → STOP and re-decide the passive-paydown strategy**
      (source: `debt-plan.md:46`). This overrides the rest of the review.
- [ ] Carry forward the **open watchlist** (W1–W8 in `review-calendar.md`) into the new
      review file, resolve where the quarter's data now allows (e.g. label IPS recipients,
      confirm the recurring family transfers), and leave the rest open with a progress note.
      Nothing is dropped — open items carry until closed.

### 7. Sync (leave for the coordinator)

- [ ] All vault edits (transactions block, review file, propagated budget/plan/cash-flow
      numbers) stay **local**. The Linux coordinator commits + pushes at its next
      maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Gating facts (verified, sourced)

| Fact | Value | Source |
|------|-------|--------|
| Savings lock | [your savings] USD/mo (drift below [your savings floor]) | `plan.md:43`, `review-calendar.md` |
| Weekly / monthly cap | [your weekly cap] / [your monthly cap] USD | `review-calendar.md` |
| Month-end surplus → your loan | ~[your surplus] USD | `plan.md:13,46` |
| credit-card balance | [your balance] USD | `debt-plan.md` |
| Visa tripwire | up 2 months → re-decide | `debt-plan.md:46` |
| Drift gate | any operating bucket >10% → propagate | `review-calendar.md` |
| Survival phase ends | ~Apr 2027 | `advisory-council.md` |

---

## Connections

- Schedule + drift table + watchlist: `02-ana/financial/review-calendar.md`
- Baseline to mirror: `02-ana/financial/reviews/2026-05-baseline.md`
- Monthly spine that feeds the quarters: [[09-monthly-money-close]]
- Portfolio read (paper-only, survival phase): `/investment → status`
- Real-money gate (separate, rare): [[19-bot-go-live-readiness]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
