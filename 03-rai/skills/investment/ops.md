---
name: ops
description: >
  Runbook for the local paper-portfolio: timer and service status, run the daily mark once by
  hand, read the logs, find the state files and the universe. USE WHEN John wants to check,
  run, or debug the paper-portfolio engine.
allowed-tools: Read, Bash
---

# Paper-portfolio Ops

The engine is `portfolio.py` in `~/helm/02-ana/financial/investment/paper-portfolio/`. A systemd user timer (`paper-portfolio.timer`, daily at 17:00 local time, `Persistent=true`) starts `paper-portfolio.service`, a oneshot that runs the script with the folder's `.venv/bin/python` and appends stdout and stderr to `portfolio.log`. A failed run triggers `alert@paper-portfolio.service`. Everything is paper; nothing here touches real money.

```bash
PP=~/helm/02-ana/financial/investment/paper-portfolio
```

## Status

```bash
systemctl --user status paper-portfolio.timer paper-portfolio.service --no-pager
systemctl --user list-timers paper-portfolio.timer --no-pager
```

Healthy = timer `active (waiting)` with a next trigger, service `inactive (dead)` after a clean exit (not `failed`).

## Run once by hand

```bash
systemctl --user start paper-portfolio.service
systemctl --user show -p ActiveState,Result paper-portfolio.service
```

The start blocks until the oneshot finishes. `Result=success` is a clean run. Use it when the day's scheduled run was missed or failed. A second run on the same day replaces that day's `nav_history` entry but accrues one more day of cash yield, so avoid repeat runs on one day. Rebalancing happens on the first run of each month (`last_rebal`).

## Logs

```bash
journalctl --user -u paper-portfolio -n 50 --no-pager   # unit start/stop, exit status
tail -n 40 "$PP/portfolio.log"                          # the script's own output + tracebacks
```

## State and config files

| File | What |
|---|---|
| `portfolio_state.json` | per-stream books: `holdings`, `cash_usd`, `nav_history` (`date`, `nav_usd`), `last_rebal`, `started` |
| `portfolio.log` | appended output of every run |
| `universe.json` | the streams: `key`, `label`, `init_usd`, `algo`, `tickers` (where the universe lives) |
| `portfolio.py` | the engine |
| `.venv/` | the interpreter the service runs |
| `research/` | backtests (local venv under `research/strategy_search/.venv`) |

Unit files: `~/.config/systemd/user/paper-portfolio.{service,timer}`.

## Rules

- Changing `universe.json` or `portfolio.py` is a strategy change: run `/investment convene` first, and screen any new ticker with `/investment screen`.
- The profit->gold skim harness (`gold_skim.py`) has no scheduler. Do not schedule or run it from here.
- Secrets never enter the vault.
