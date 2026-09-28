---
name: investment
description: >
  Investment router. USE WHEN John wants the status of his investments and the local
  paper-portfolio, a recommendation on what to do (DCA, rebalance, what to screen), a Sharia
  screen on a ticker, a periodic portfolio review, the paper-portfolio runbook, or a Restraint
  Gate verdict on a proposed decision. Strictly Sharia-compliant (spot, no leverage), paper-first,
  local runtime. Strategy + branches live in `~/helm/02-ana/financial/investment/`.
---

# Investment

John's investing command center. Strictly Sharia-compliant (spot only, no leverage), paper-first. The runtime is the local paper-portfolio (`paper-portfolio.timer`, a systemd user timer on this box). The master plan is `~/helm/02-ana/financial/investment/strategy.md`; rules are in that folder's `AGENTS.md`.

Crypto trading and the trading bot were retired 2026-06-14; do not re-propose them.

**This subsystem is optional and not shipped.** None of `02-ana/financial/investment/` exists in this kit (no strategy, no paper-portfolio engine, no branch docs). You build it yourself before this skill is usable. Until then, treat every path below as a target to create, not a file that already exists.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| "Where do I stand?" (strategy posture + paper-portfolio snapshot) | status | `status.md` |
| "What should I do?" (actions, DCA targets, rebalancing) | recommend | `recommend.md` |
| "Is X rule-compliant to invest in?" (AAOIFI screen of a ticker) | screen | `screen.md` |
| Weekly/monthly portfolio review | review | `review.md` |
| Run or check the local paper-portfolio (timer, service, logs, state files) | ops | `ops.md` |
| Run the council's Restraint Gate on a decision (buy/sell, strategy change, reweight, new candidate) | convene | `convene.md` |

## How to use

1. Pick the sub-skill by task.
2. `Read` the matching file in this directory.
3. Follow its instructions, and always honor the guardrails: **Sharia-compliant (spot, no leverage), paper-first.** Real money moves only after a strategy is paper-validated and John gives an explicit, eyes-open sign-off on the amount (see `strategy.md` and the folder's `AGENTS.md`).
