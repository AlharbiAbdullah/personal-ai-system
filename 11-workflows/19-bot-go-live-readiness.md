# Bot Go-Live Readiness

**Status: dormant.** No live or dry-run trading engine exists today. The spot-bot was
retired 2026-06-14 (`investment/02-crypto/spot-bot/README.md`). This playbook does not
apply to the paper-portfolio equity engine (`investment/paper-portfolio/`): that is a
local paper simulation, not a real-money bot. It stays here, unexecuted, as the gate a
future automated trading engine would have to clear before John puts real money
behind it. There is nothing to run until a new engine exists.

**Triggered by:** "is the bot ready for real money" / "go live with the bot"
**Cadence:** Per engine, rare. Most runs end at "not yet."
**Done when:** DEFAULT is **STAYS DRY-RUN**. It only flips to live if EVERY gate below passes AND John gives explicit, eyes-open sign-off. Rai is NOT a licensed advisor.

> **The most dangerous action in the vault, when there is an engine to flip.** The safe
> path is otherwise split across several files held together by prose. This playbook is
> the one ordering where skipping a step is structurally impossible: each gate
> short-circuits to STOP. Sources: `investment/02-crypto/spot-bot/GO-LIVE-CHECKLIST.md`
> (frozen reference), `investment/07-tools/advisory-council.md`, `02-ana/financial/debt-plan.md`.

```
Return-vs-cards gate → Advisory council → Walk GO-LIVE-CHECKLIST line-by-line
  → Keys → Tuition sleeve → Explicit sign-off → Flip (or stay dry-run) → Leave for coordinator
```

---

## Steps

### 1. Return-vs-cards gate (the gate that ends most runs)

- [ ] Run **`/investment → review`** — get the validated, after-fees edge of the engine.
- [ ] Compare it to the **cards: [your balance] USD @ ~30–36% APR, guaranteed** (`debt-plan.md`).

> **Decision Point**: does the validated edge beat ~30–36% APR *guaranteed*?
> - **No** (the usual answer) → **STOP. Pay the cards.** No strategy beats a guaranteed
>   30–36% return. Stay dry-run. End here.
> - **Yes, demonstrably** → continue to step 2. (Skepticism is the default; a paper
>   backtest is not "demonstrably.")

### 2. Convene the advisory council

- [ ] Run **`/investment → convene`** — the full council in
      `investment/07-tools/advisory-council.md`.
- [ ] **Default verdict = DO NOTHING.** The bar is unanimity to proceed.

> **Decision Point**: **ANY single NO short-circuits the whole playbook → STOP, stay
> dry-run.** One dissenting voice is enough. Do not average the council; do not overrule it.

### 3. Walk the GO-LIVE-CHECKLIST — LINE BY LINE

Open `investment/02-crypto/spot-bot/GO-LIVE-CHECKLIST.md` and tick each box **against
reality**, not from memory. Any single unchecked box → STOP.

- [ ] **Compliance still true:** spot only, no leverage, `can_short: false`, no leveraged
      tokens. Re-verify in config; do not assume it carried over.
- [ ] **Dry-run duration:** **WEEKS, not days**, of clean run on *live* market data.
- [ ] **Paper↔live parity proven:** one real fill/signal observed; fees modeled; the book
      reconciles **1:1**; slippage is realistic (not zero).
- [ ] **Strategy edge validated:** purged walk-forward; edge holds across **≥3 windows**.
      A single in-sample fit does not count.
- [ ] **Risk recalibrated to the *real* balance:** daily-loss + max-drawdown kill-switches
      wired AND **tested** (proven to actually halt the bot, not just configured).
- [ ] **Exchange filters clear:** per-symbol Binance min-notional / lot-size pass for every
      pair the engine trades.

> **Decision Point**: every box ticked from observed reality? **No → STOP, stay dry-run.**
> "Mostly ready" is not ready. This list is the gate; do not negotiate it down.

### 4. Spot-only API keys (only after every box in step 3)

- [ ] Create **new** Binance API keys scoped to **Spot Trading ONLY**.
- [ ] **Futures, margin, and withdrawals OFF.** Confirm in the key's permission matrix.
- [ ] **IP-restricted to the droplet** only.
- [ ] Supplied via **ENV** on the droplet. **Keys are NEVER committed** to the vault or any
      repo — not in config, not in a note, not in a comment.

### 5. Tuition sleeve only

- [ ] Funded from the **[a small learning cap]** only (`investment/08-practice/tuition-account.md`).
- [ ] This is **fully losable** money. **Never** from living-expense, savings-lock, or
      card-paydown money.
- [ ] **Auto-pullback:** down ~20% from peak → back to paper. No averaging down, no "give it
      more room."

### 6. Explicit, eyes-open sign-off

- [ ] John states **aloud / in writing** that he wants to put real money in AND that he
      accepts losing it. Capital-preservation framing first.

> **Decision Point**: anything **less than explicit** — a "sure", a shrug, an implied yes →
> treat as **NO. STOP, stay dry-run.** Rai is not a licensed advisor; the human owns this
> button.

### 7. Flip (or stay dry-run)

- [ ] Set **`dry_run: false` in `config-live.json` only.** Nothing else changes.
- [ ] **Tiny size** to start. Rollback ready: flipping back to `true` must be one edit.
- [ ] If ANY box above is unchecked or the sign-off was less than explicit → **do not flip.
      Stay dry-run.**

### 8. Sync (leave for the coordinator)

- [ ] Vault edits (review notes, council verdict, sleeve update) stay **local**. The Linux
      coordinator commits + pushes at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.
- [ ] **Keys are never part of any commit** — confirm nothing key-bearing landed in the
      working tree.

---

## Gating facts (verified, sourced)

| Fact | Value | Source |
|------|-------|--------|
| Cards (guaranteed return) | [your balance] USD @ ~30–36% APR | `debt-plan.md` |
| Council default verdict | DO NOTHING; any NO stops | `investment/07-tools/advisory-council.md` |
| Dry-run before live | WEEKS of clean live-data run | `spot-bot/GO-LIVE-CHECKLIST.md` |
| Tuition sleeve cap | [a small cap], fully losable | `investment/08-practice/tuition-account.md` |
| Pullback to paper | down ~20% from peak | `investment/08-practice/tuition-account.md` |
| Survival phase ends | ~Apr 2027 (debt-first) | `advisory-council.md` |

---

## Connections

- Return + edge read: `/investment → review`
- Advisory council: `/investment → convene`
- Live checklist: `investment/02-crypto/spot-bot/GO-LIVE-CHECKLIST.md`
- Routine money spine: [[09-monthly-money-close]]
- Deeper periodic review: [[14-quarterly-financial-review]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
