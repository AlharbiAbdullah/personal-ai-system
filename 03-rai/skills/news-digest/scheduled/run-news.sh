#!/bin/bash
# news scheduled runner — drives /news (or /news week) in an unattended,
# interactive, Chrome-paired Claude session via WezTerm, then cleans up.
#
# Usage:  run-news.sh [daily|weekly]
# Env:    BYPASS_AC=1   run even on battery (for explicit manual runs)
#         NO_CLEANUP=1  leave the window + Chrome open after (manual runs)
#
# Why interactive (not `claude -p`): the claude-in-chrome extension only pairs
# with an interactive session, and skills (/news) don't exist in -p mode.
# WezTerm gives the real PTY launchd lacks. Verified working 2026-05-29.
#
# recovery-prompt.txt (the old X-scroller diagnostic prompt) is deleted from
# the repo; this runner never had a RECOVERY mode and never read that file.

set -uo pipefail

MODE="${1:-daily}"
CLAUDE="$HOME/.local/bin/claude"
WT="/Applications/WezTerm.app/Contents/MacOS/wezterm"
HELM="$HOME/helm"
SCHED="$HELM/03-rai/skills/news-digest/scheduled"
mkdir -p "$SCHED/logs"
LOG="$SCHED/logs/$(date +%Y-%m-%d)-$MODE.log"
exec >>"$LOG" 2>&1

echo "════════ $(date '+%F %T') START mode=$MODE ════════"

# 1. Power guard — skip silently on battery (the scheduled-run policy)
if [ "${BYPASS_AC:-0}" != "1" ]; then
  if ! pmset -g ps | grep -q "AC Power"; then
    echo "Not on AC power — skipping silently."
    echo "════════ $(date '+%F %T') SKIP (battery) ════════"
    exit 0
  fi
fi

# 2. Ensure the logged-in Chrome profile is running
open -a "Google Chrome" || true
sleep 6

# 3. Mode-specific command + expected output file
# NOTE: a literal "/news" passed at launch is NOT recognized as a slash command
# (slash commands only resolve when typed into the live REPL). So we drive the
# skill with a plain-English instruction — the model invokes the news-digest
# skill directly. This is the form that auto-submits reliably at startup.
if [ "$MODE" = "weekly" ]; then
  PROMPT="Run your news-digest skill in WEEKLY mode now. Read this past Sunday-to-Saturday week's daily digests from ~/helm/08-bawaba/daily/, skip any missing days silently, synthesize them, and save the weekly digest to ~/helm/08-bawaba/weekly/. Do not ask for confirmation. Do not scrape fresh sources — read daily/ only."
  OUT="$HELM/08-bawaba/weekly/$(date +%G)-W$(date +%V).md"
else
  PROMPT="Run your news-digest skill now to generate today's full daily digest. Collect all sources and save the digest to ~/helm/08-bawaba/daily/. Do not ask for confirmation; run fully autonomously per the skill's rules. BROWSER SELECTION (2026-06-05 fix): if the Chrome MCP reports multiple connected browsers, I pre-authorize you to call list_connected_browsers and then select_browser with the deviceId whose isLocal is true — that is the Chrome this script just launched on this Mac. Do not call AskUserQuestion for browser selection and do not wait; this run is unattended and stalling on the picker is how the 2026-06-05 run died. CRITICAL: you are not finished until the POST-FILL pass is complete — every <CLAUDE_FILL_*> placeholder replaced with real prose and every <!-- raw: --> scaffolding line stripped. Before you end, run 'grep -c CLAUDE_FILL' and 'grep -c \"<!-- raw:\"' on the output file; both MUST be 0. A digest shipped with placeholders is a failed run."
  OUT="$HELM/08-bawaba/daily/$(date +%Y-%m-%d).md"
fi
FAIL_ROOT="$HELM/08-bawaba/.news-failed-$(date +%Y-%m-%d).md"
FAIL_DAILY="$HELM/08-bawaba/daily/.news-failed-$(date +%Y-%m-%d).md"
echo "Expecting output: $OUT"

# 4. Ensure a WezTerm mux exists, then spawn interactive claude --chrome.
#    The positional prompt auto-submits in interactive mode (verified).
"$WT" cli list >/dev/null 2>&1 || { open -a WezTerm; sleep 6; }
PANE="$("$WT" cli spawn --new-window --cwd "$HELM" -- "$CLAUDE" --chrome "$PROMPT" 2>/dev/null)"
if [ -z "$PANE" ]; then echo "ERROR: WezTerm spawn failed"; exit 1; fi
echo "Spawned WezTerm pane $PANE running: claude --chrome \"$PROMPT\""

# 5. Wait for completion: output file stable AND fully post-filled, OR failure
#    marker, OR 120-min cap.
#
#    The skill writes the SKELETON (with <CLAUDE_FILL_*> placeholders + <!-- raw: -->
#    scaffolding) to $OUT first, then reads it back and post-fills the prose IN PLACE.
#    There is a multi-minute reading/thinking gap between skeleton-write and the first
#    fill-write, so size-stability ALONE fires during that gap — which is how the
#    2026-06-01 run shipped a digest full of raw <CLAUDE_FILL_*> placeholders: the
#    watcher declared "stable" at the skeleton and killed Chrome mid-synthesis.
#
#    Completion now requires BOTH: size stable AND no unfilled markers left — i.e. the
#    skill's own done-definition (grep -c 'CLAUDE_FILL' == 0, raw comments stripped).
#    Weekly digests carry no such markers, so this reduces to pure size-stability there.
DEADLINE=$(( $(date +%s) + 7200 ))
LAST=-1; STABLE=0; DONE=0
while [ "$(date +%s)" -lt "$DEADLINE" ]; do
  sleep 30
  if [ -f "$FAIL_ROOT" ] || [ -f "$FAIL_DAILY" ]; then
    echo "Failure marker present — run aborted (likely X). Cleaning up."; DONE=1; break
  fi
  if [ -f "$OUT" ]; then
    SZ="$(stat -f%z "$OUT" 2>/dev/null || echo 0)"
    if grep -qE 'CLAUDE_FILL|<!-- raw:' "$OUT" 2>/dev/null; then FILLED=0; else FILLED=1; fi
    if [ "$SZ" -eq "$LAST" ] && [ "$SZ" -gt 2000 ] && [ "$FILLED" -eq 1 ]; then STABLE=$((STABLE+1)); else STABLE=0; fi
    LAST="$SZ"
    if [ "$STABLE" -ge 4 ]; then echo "Output stable at $SZ bytes, post-fill complete (no placeholders, ~2 min) — done."; DONE=1; break; fi
  fi
done
[ "$DONE" = 0 ] && echo "Timed out after 120 min — cleaning up anyway (digest may be incomplete)."

# 6. Saturday bridge: keep the Mac awake from the ~6am daily until the 7am weekly
if [ "$MODE" = "daily" ] && [ "$(date +%u)" -eq 6 ]; then
  echo "Saturday — holding Mac awake (~90 min) so the 07:00 weekly run fires."
  nohup caffeinate -s -t 5400 >/dev/null 2>&1 &
  disown 2>/dev/null || true
fi

# 7. Cleanup — close the digest window + Chrome (unless suppressed)
if [ "${NO_CLEANUP:-0}" != "1" ]; then
  "$WT" cli send-text --pane-id "$PANE" --no-paste $'\n/exit\n' 2>/dev/null || true
  sleep 4
  "$WT" cli kill-pane --pane-id "$PANE" 2>/dev/null && echo "Closed digest window."
  osascript -e 'quit app "Google Chrome"' 2>/dev/null && echo "Closed Chrome."
else
  echo "NO_CLEANUP set — leaving window + Chrome open."
fi

echo "════════ $(date '+%F %T') END mode=$MODE ════════"
