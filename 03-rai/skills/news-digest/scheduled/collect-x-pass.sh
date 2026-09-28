#!/bin/bash
# X pre-pass collector for the daily news digest — deterministic, NO agent/MCP.
#
# Runs the headless-CDP X collector (_collect_x_headless.py) as a single GENTLE
# pass and ACCUMULATES into the upcoming digest's run dir via merge-write. Two of
# these fire per night from news-x-collect.timer (21:00 + 00:00); the 03:00
# digest run does the third pass + assembly. Spreading X across three fresh
# sessions hours apart defeats X's per-session timeline throttle (the feed
# freezes ~200 deep per session but refills between passes), turning a single
# ~350-tweet plateau into a ~1k cumulative pool. Premium raises the daily read
# cap, not this per-session throttle — so more sessions, not a bigger one.
#
# The collector re-clones the live Chrome's cookies each run (setup_profile), so
# the X login is inherited from the real browser; nothing to auth here. If the
# login is dead it writes x_LOGIN_FAILED.json and exits 3 — we just log and let
# the next pass (or the 03:00 run) try again.
set -uo pipefail
export PATH="$HOME/.local/bin:/usr/bin:/bin:$PATH"

# The 21:00 pass collects for TOMORROW's 03:00 digest; 00:00 collects for today.
HOUR=$(date +%-H)
if [ "$HOUR" -ge 20 ]; then
  DATE=$(date -d tomorrow +%F)
else
  DATE=$(date +%F)
fi

LOGDIR="$HOME/.local/state/news-digest/logs"   # OUT of the repo — no commit churn
mkdir -p "$LOGDIR"
LOG="$LOGDIR/$(date +%F)-x-passes.log"

{
  echo "════════ $(date '+%F %T') X pre-pass START → digest date $DATE ════════"
  uv run "$HOME/helm/03-rai/skills/news-digest/_collect_x_headless.py" \
    --date "$DATE" --target 700 --following-target 50 --phase both
  rc=$?
  echo "════════ $(date '+%F %T') X pre-pass END rc=$rc ════════"
  exit $rc
} >>"$LOG" 2>&1
