---
name: bills
description: Monthly bill-pay run. Opens every bill-pay portal in browser tabs so all recurring bills can be paid in one sitting. Also surfaces non-portal bills (household help, a household helper) as reminders.
allowed-tools: Bash, Read
---

# Bills

Monthly cadence. Run when salary lands (~26-27th) or whenever bills are due. Opens every customer portal at once, then walks John through `bills.md` to tick each one off.

## Instructions

### Step 1: Read the manifest

Read `~/helm/02-ana/financial/bills.md` for the current state — amounts, account numbers, which lines are on autopay, the current month's tracker.

If the current month's tracker block doesn't exist yet, **append a fresh dated block** to `bills.md` under `## Monthly tracker`:

```markdown
### {{YYYY-MM}} ({{Month name}})

- [ ] Electricity — _amount_
- [ ] Water — _amount_
- [ ] Internet — _amount_
- [ ] Phone — John — _amount_
- [ ] Phone — second line — _amount_
- [ ] Household help — _amount_
- [ ] (digital subs auto-debit — no action)
```

### Step 2: Open all bill-pay portals

Run via Bash. `xdg-open` opens the default browser on Linux, `open` on macOS:

```bash
OPEN=$(command -v xdg-open || command -v open)
"$OPEN" "https://electric-provider.example/login"
"$OPEN" "https://water-provider.example/login"
"$OPEN" "https://internet-provider.example/account"
"$OPEN" "https://phone-provider.example/account"
```

That opens four tabs. Put your own providers' portal URLs here; one phone portal can cover both lines.

If any portal has migrated, fall back to the alternates:

| Provider | Primary URL | Fallback |
|----------|-------------|----------|
| Electricity | https://electric-provider.example/login | the provider's guest bill-view page |
| Water | https://water-provider.example/login | the provider's quick-pay page |
| Internet | https://internet-provider.example/account | the provider's quick-pay page |
| Phones | https://phone-provider.example/account | the provider's app |

### Step 3: Remind John of the non-portal bills

After the tabs are open, tell John explicitly:

> **Non-portal bills to handle this round:**
> - **Household help** — [amount] — internal transfer or cash.
> - **Digital subscriptions** — already on card ending XXXX, no action needed. (See `financial/subscriptions.md`.)

### Step 4: Pay-day flow

Suggest the order: utilities → telecom → household services.

1. Electricity tab → log in → pay current bill.
2. Water tab → log in → pay.
3. Internet tab → log in → pay.
4. Phone tab → log in → pay the first line → switch line → pay the second line.
5. Open banking app → internal transfer to household help.

After each, **tick the checkbox** in `bills.md` for the current month's tracker.

### Step 5: Capture anomalies

If any bill is unusually high (>20% above the average in `bills.md`), flag it inline in the tracker entry, e.g.:

```markdown
- [x] Electricity — 410 ⚠ +60% vs avg, likely AC season starting
```

These flags become the input for next quarter's financial review.

### Step 6: Update autopay status if changed

If John turns on autopay for any bill during this session, update the **Autopay?** column in `bills.md` from `_TBD_` / `no` → `yes` and note the bank.

## When to use

- Once per month, right after salary lands (around the 26-27th).
- Or whenever a specific bill is overdue — same flow, ignore the ones already paid.

## Don't use for

- Salary or income tracking (that's `cash-flow.md`).
- Budget category review (that's `budget.md`).
- One-off purchases (no routine skill for that — just bank app).
