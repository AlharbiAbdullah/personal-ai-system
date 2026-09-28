---
name: status
description: Read-only snapshot, "where do I stand?". Strategy posture + the local paper-portfolio (timer health, per-stream NAV and holdings) + real holdings, closing with the paper-first reminder
allowed-tools: Read, Bash
---

# Investment Status

A tight, one-screen snapshot. **Read-only**: this skill observes; it never starts the service, runs `portfolio.py` or `gold_skim.py`, edits state, or moves real money. Answers "where do I stand?" across strategy posture, the local paper-portfolio, and real holdings.

## Instructions

### Step 1: Strategy posture

Read `~/helm/02-ana/financial/investment/strategy.md` for the **target allocation** and the **current posture** (paper + learn: real money only after paper-validation and John's eyes-open sign-off on the amount). That's the yardstick for everything below.

### Step 2: Probe the local paper-portfolio (read-only, ONE bash block)

The engine runs on this box: `paper-portfolio.timer` fires `paper-portfolio.service` once a day, which runs `portfolio.py` in the folder's `.venv` and appends its output to `portfolio.log`.

```bash
PP=~/helm/02-ana/financial/investment/paper-portfolio

echo "== timer + service =="
systemctl --user status paper-portfolio.timer paper-portfolio.service --no-pager
journalctl --user -u paper-portfolio -n 50 --no-pager

echo "== latest run output =="
tail -n 20 "$PP/portfolio.log"

echo "== per-stream books (latest mark) =="
python3 - "$PP" <<'EOF'
import json, sys, pathlib
pp = pathlib.Path(sys.argv[1])
state = json.loads((pp / "portfolio_state.json").read_text())
seed = {s["key"]: s["init_usd"] for s in json.loads((pp / "universe.json").read_text())["streams"]}
for key, book in state.items():
    last = book["nav_history"][-1] if book.get("nav_history") else {}
    held = ", ".join(sorted(book.get("holdings") or {})) or "cash"
    print(f"{key:10} {last.get('date')} nav={last.get('nav_usd')} seed={seed.get(key)} holds: {held}")
EOF
```

If a file is missing or a command fails, say so plainly; don't guess.

### Step 3: Summarize the runtime (2-3 lines)

- **Timer healthy?** Timer `active (waiting)` with a next trigger; the last service run exited cleanly (no `failed` state, no traceback in the journal or the log tail).
- **Fresh?** The latest `nav_history` date should be the last scheduled run (today after the daily run, else yesterday). An older date means runs are being missed: flag it and point at `ops.md`.

### Step 4: Summarize the per-stream books

From `portfolio_state.json`: one paper book per stream (`etf`, `local`, `us_stocks`, `sukuk`), each seeded with its `init_usd` from `universe.json` and running its own `algo` on its own tickers. For each stream:
- Latest `nav_history[].nav_usd`, **P/L vs its seed**, and which tickers it currently **holds**.
- A `trend` stream moves below-trend names to **cash**, so it may hold fewer than its full list (or sit in cash). That's the algorithm working, not a bug.
- `sukuk` is a modeled hold (`hold_yield`), no tickers.
- Sum the four = total paper equity. There is no crypto sleeve; gold is manual.

### Step 4b: Profit->gold skim

The skim harness (`paper-portfolio/gold_skim.py`) has no scheduler and is **not running**. Say so in one line. Do not run it or schedule it; the design lives in `08-practice/gold-buffer-sweep.md`.

### Step 5: Real holdings

- **Real holdings**: look for `~/helm/02-ana/financial/investment/holdings.md`. If absent: **"No holdings note: none deployed, paper only."**
- **Gold**: manual (John buys and holds it himself), not tracked by the paper engine.

### Step 6: Close with the paper-first reminder (ALWAYS)

> Paper-first: every book above is simulated. Real money moves only after a strategy is paper-validated and John gives an explicit, eyes-open sign-off on the amount; any such step runs through `/investment convene`.

## Rules

- **Read-only.** No `systemctl --user start`, no runs of `portfolio.py` or `gold_skim.py`, no edits to state or `universe.json`. For operating, that's `ops.md`.
- One screen. Snapshot, not a report. If something can't be confirmed, say so; don't invent numbers.
