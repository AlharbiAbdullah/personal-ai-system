# Monthly Money Close

**Triggered by:** "close the month" / "payday" / "salary landed" / "monthly money run"
**Cadence:** Monthly, right after salary lands (~26–27th)
**Done when:** every bill ticked in `bills.md`, savings lock confirmed, surplus routed to your loan, Visa trend checked, and an `/investment status` snapshot taken.

The monthly money spine. Today this is six disconnected actions done from memory; a
silent miss costs real money in the survival phase. This playbook is the ordering +
the gates — the actual bill-pay is the `/routine → bills` skill.

```
Bills → Spend check → Savings lock → Surplus to your loan → Visa tripwire → Snapshot → Leave for coordinator
```

> **Survival-phase frame (until ~Apr 2027):** defensive, debt-first. The cards
> ([your balance] USD @ ~30–36% APR) are a guaranteed return no investment beats. Source:
> `02-ana/financial/debt-plan.md`, `investment/07-tools/advisory-council.md`.

---

## Steps

### 1. Pay the bills

- [ ] Run **`/routine → bills`** — opens your utility and telecom portals, pays utilities →
      telecom → household, ticks the month's tracker block in
      `02-ana/financial/bills.md`.
- [ ] Non-portal bills: household help ([amount], internal transfer)
      Digital subs already on your card: no action.

> **Decision Point**: any bill >20% above its average in `bills.md`?
> - Flag it inline in the tracker with the likely cause (e.g. `⚠ +60% AC season`).
> - If structural (a new recurring cost), note it for step 3's cap math.

### 2. Weekly-spend reconciliation

- [ ] Check operating spend against the cap: **≤[your weekly cap] USD/week, ≤[your monthly cap] USD/month**
      (source: `02-ana/financial/review-calendar.md`).
- [ ] Under cap → the ~[your surplus] USD surplus is real and goes to step 4.
- [ ] Over cap → surplus to your loan is reduced/skipped this month; next month tightens.

### 3. Confirm the savings lock

- [ ] **[your savings] USD/mo to savings** — LOCKED commitment (source: `plan.md:43`). Confirm it
      moved. This is the structural floor for rent + school; it is not optional.
- [ ] Savings is single-purpose (rent + school only). Any drift >6K/yr here is a
      violation — flag it, do not absorb it silently.

### 4. Route the surplus to your loan

- [ ] Deploy the month-end surplus (~[your surplus] USD when under cap) to **extra your loan
      principal** (source: `plan.md:13,46`). Variable underspend → cards, never your loan
      vs the locked split.

### 5. Visa tripwire (the one that bites)

- [ ] Read total credit-card balance (Platinum + Signature). Baseline: [your balance] USD.
- [ ] **Is it trending down month-over-month?** Target: down.
- [ ] **If UP for 2 consecutive months → STOP and re-decide the passive-paydown
      strategy** (source: `debt-plan.md:46`). Lifestyle creep through cards is the
      failure mode this whole phase guards against.

### 6. Investment snapshot

- [ ] Run **`/investment → status`** for a portfolio + cloud-bot snapshot. Survival
      phase = paper-only; this is a read, not a deploy. No real money moves here.

### 7. Sync (leave for the coordinator)

- [ ] Vault edits (bills tracker, any flags) stay **local**. The Linux coordinator
      commits + pushes at its next maintenance run (04/10/16/22:00).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Gating facts (verified, sourced)

| Fact | Value | Source |
|------|-------|--------|
| Savings lock | [your savings] USD/mo | `plan.md:43` |
| Weekly / monthly cap | [your weekly cap] / [your monthly cap] USD | `review-calendar.md` |
| Month-end surplus → your loan | ~[your surplus] USD | `plan.md:13,46` |
| credit-card balance | [your balance] USD | `debt-plan.md:25` |
| Visa tripwire | up 2 months → re-decide | `debt-plan.md:46` |
| Survival phase ends | ~Apr 2027 | `advisory-council.md:30` |

---

## Connections

- Bill-pay engine: `/routine → bills`
- Portfolio read: `/investment → status`
- Deeper periodic review: [[14-quarterly-financial-review]]
- Real-money gate (separate, rare): [[19-bot-go-live-readiness]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
