# Monthly Money Close

**Use when:** payday: the monthly money run once the salary lands. It pays the bills, checks spend against the cap, confirms the savings commitment, routes the surplus and checks the debt trend.
**Not for:** 14 quarterly financial review, for the 90-day statement review. 26 purchase, for buying something.
**Done when:** every bill ticked in `bills.md`, the savings transfer confirmed, the surplus routed by your plan and the debt trend checked. The paper-portfolio snapshot is read with `/investment → status`.
**Cadence:** Monthly, on payday.

The monthly money spine. Without it, six separate actions run from memory, and a silent miss costs real money. This playbook is the order and the gates. The bill-pay itself is the `/routine → bills` skill. Every number lives in your own files under `02-ana/financial/`, never in this workflow.

```
Bills → Spend check → Savings → Surplus → Debt tripwire → Snapshot → Sync
```

---

## Steps

### 1. Pay the bills

- [ ] Run **`/routine → bills`**. It opens your providers' portals and pays each bill, then ticks the month's tracker block in `02-ana/financial/bills.md`.
- [ ] Pay any bill that has no portal by your usual route, and tick it too.

> **Decision Point**: any bill >20% above its average in `bills.md`?
> - Flag it inline in the tracker with the likely cause.
> - If structural (a new recurring cost), note it for step 2's cap math.

### 2. Spend check

- [ ] Check operating spend against the weekly and monthly caps in your plan.
- [ ] Under cap → the planned surplus is real and goes to step 4.
- [ ] Over cap → the surplus is reduced or skipped this month, and next month tightens.

### 3. Confirm the savings commitment

- [ ] Confirm this month's savings transfer moved, at the amount your plan locks.
- [ ] Savings spent on anything outside their stated purpose is a violation: flag it, never absorb it silently.

### 4. Route the surplus

- [ ] Send the month-end surplus where your plan says: the highest-cost debt first if you carry one, otherwise the next goal.

### 5. Debt tripwire

- [ ] Read the total revolving balance, if you carry one. Target: down month over month.
- [ ] **Up for 2 consecutive months → stop and re-decide the strategy.** Lifestyle creep through cards is the failure mode this step guards against.

### 6. Investment snapshot

- [ ] Run **`/investment → status`** for the paper-portfolio snapshot. The posture is paper-first, so this is a read, not a deploy. No real money moves here.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Gating facts

| Fact | Where it lives |
|------|----------------|
| Savings commitment | `02-ana/financial/plan.md` |
| Weekly / monthly cap | `02-ana/financial/plan.md` |
| Surplus routing | `02-ana/financial/plan.md` |
| Debt balances and tripwire | `02-ana/financial/debt-plan.md` |
| Bill averages | `02-ana/financial/bills.md` |

---

## Connections

- Bill-pay engine: `/routine → bills`
- Portfolio read: `/investment → status`
- Deeper periodic review: [[14-quarterly-financial-review]]
- Commit rule: `11-workflows/AGENTS.md`
