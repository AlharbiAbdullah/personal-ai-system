#!/bin/bash
# news scheduled runner (UBUNTU) — HEADLESS: drives the news-digest skill via
# `claude -p` (no terminal mux, no WezTerm, no browser MCP). Runs on the 24/7 Ubuntu box.
#
# Usage:  run-news-ubuntu.sh [daily|weekly|digest]
#         digest = only the short digest of today's daily (08-bawaba/digest/);
#         daily mode runs it on its own after a complete daily
# Env:    RECOVERY=1         skip the git pull + run ONE attempt with the
#                            budget-protecting retry prompt (no auto-retry)
#         WATCHDOG_SEC=N     hard cap per digest attempt (default 7200 = 120 min)
#         RETRY_DELAY_SEC=N  wait before the automatic retry (default 600 = 10 min)
#         NO_RETRY=1         disable the automatic retry
#         DIGEST_WATCHDOG_SEC=N  hard cap per short-digest attempt (default 900 = 15 min)
#         DIGEST_QUIET_FAIL=1    no desktop alert on a failed digest (the coordinator's catch-up)
#
# Why headless `-p` (2026-06-09): the old path spawned an INTERACTIVE
# `claude --chrome` session in a WezTerm pane. That hit a one-time "Bypass
# Permissions mode → Yes, I accept" prompt that BLOCKS an unattended session
# forever (unsuppressable in interactive, not persisted) — THAT is what hung the
# 03:00 runs for the full 120-min watchdog. `claude -p --chrome` shows no such
# prompt, loads skills fine (the Skill tool works in -p), drives the local Chrome,
# and runs to completion (verified: 773 items, all sources, post-filled). So the
# whole WezTerm layer is gone (John moved to Ghostty anyway). Completion =
# the `-p` process exiting; `timeout` is the watchdog. No PTY, no pane, no socket.
#
# Auto-retry (2026-06-10): a run can be killed mid-flight by a per-request API
# Usage Policy block (Fable 5 cyber-classifier false positive on security-news
# content — see logs/2026-06-10-daily.log, req_011CbtdKnb3971pqXadnh8mz). The
# block is probabilistic per request, so one delayed retry usually passes. On a
# failed attempt 1 the runner waits RETRY_DELAY_SEC and re-runs ONCE with a
# budget-protecting prompt that reuses same-day .runs/ dumps instead of
# re-collecting — critically X, whose account-level read budget does NOT reset
# within the day (re-scraping after the 03:24 kill is what capped X at 264/2000
# on 2026-06-10). recovery-prompt.txt (the one-off X-scroller diagnostic prompt)
# is deleted: that collection bug is fixed, and RECOVERY=1 uses the same
# built-in retry prompt.
#
# Browser (v5.9, 2026-08-24): NO paired browser, NO claude-in-chrome MCP. All
# three browser sources are headless-CDP collectors that clone cookies from the
# on-disk Chrome profile: X via _collect_x_headless.py (since v5.6), Substack +
# Medium via _collect_web_headless.py. Trigger for the change: the Claude Chrome
# extension auto-updated to 1.0.85 on the night of Aug 18 and MCP pairing failed
# at 03:00 for seven straight nights, killing every digest at the old preflight
# (see memory news-digest-chrome-pairing). The desktop Chrome does not even need
# to be running; only its cookie DB is read, and the user must stay logged into
# x.com / substack.com / medium.com in it.
# Scheduled by systemd user timers news-daily.timer (03:00) and news-weekly.timer
# (Sat 07:00); graphical env comes from the systemd user environment (Hyprland).

set -uo pipefail
export PATH="$HOME/.local/bin:/usr/bin:/bin:$PATH"

MODE="${1:-daily}"
CLAUDE="$HOME/.local/bin/claude"
HELM="$HOME/helm"
SCHED="$HELM/03-rai/skills/news-digest/scheduled"
WATCHDOG_SEC="${WATCHDOG_SEC:-7200}"
RETRY_DELAY_SEC="${RETRY_DELAY_SEC:-600}"
RUNS_DIR="$HELM/03-rai/skills/news-digest/.runs/$(date +%Y-%m-%d)"
LOGDIR="$HOME/.local/state/news-digest/logs"   # OUT of the repo — no per-run log-commit churn
mkdir -p "$LOGDIR"
LOG="$LOGDIR/$(date +%Y-%m-%d)-$MODE.log"
exec >>"$LOG" 2>&1

echo "════════ $(date '+%F %T') START mode=$MODE (headless -p) ════════"

# 1. Sync with origin: fetch + fast-forward-only merge. This box is the sole
#    writer to origin, so the merge is a no-op in steady state and fails cleanly
#    (no half-done rebase) if origin ever diverges. An incoming commit carrying
#    a path that exists locally as UNTRACKED still aborts the merge (how the
#    2026-06-06 pulls failed): identical -> drop local; divergent -> move aside.
COLLISION_BACKUP="$HOME/.local/state/helm-pull-collisions/$(date +%Y%m%d-%H%M%S)"
resolve_untracked_collisions() {
  git -C "$HELM" fetch origin main || return 1
  local p
  while IFS= read -r p; do
    [ -e "$HELM/$p" ] || continue
    git -C "$HELM" ls-files --error-unmatch "$p" >/dev/null 2>&1 && continue
    if git -C "$HELM" show "origin/main:$p" 2>/dev/null | cmp -s - "$HELM/$p"; then
      rm -f "$HELM/$p"; echo "collision (identical): dropped local untracked $p"
    else
      mkdir -p "$COLLISION_BACKUP/$(dirname "$p")"
      mv "$HELM/$p" "$COLLISION_BACKUP/$p"
      echo "COLLISION (divergent): moved local untracked $p -> $COLLISION_BACKUP/$p"
    fi
  done < <(git -C "$HELM" diff --name-only HEAD origin/main)
}
if [ "${RECOVERY:-0}" = "1" ]; then
  echo "RECOVERY MODE: skipping git pull to preserve locally-seeded dedup priors."
else
  resolve_untracked_collisions || echo "WARN: fetch failed — attempting pull anyway."
  { git -C "$HELM" fetch origin main && git -C "$HELM" merge --ff-only FETCH_HEAD; } || echo "WARN: ff-only pull failed, continuing with local state."
fi

# 2. Chrome lifecycle + MCP pairing preflight: REMOVED in v5.9 (2026-08-24).
#    Substack + Medium moved to the headless-CDP collector (_collect_web_headless.py),
#    joining X (_collect_x_headless.py, v5.6). Nothing in the run touches the
#    claude-in-chrome extension anymore, so there is nothing to pair and nothing
#    to abort on. History: the extension's 1.0.85 auto-update (night of Aug 18)
#    broke 03:00 pairing and the old preflight killed 7 digests in a row.

# 3. Mode-specific prompt + expected output file + failure markers.
#    HEADLESS_NOTE (2026-06-12): both attempts that morning died because the agent
#    ended its turn to "wait" for a background X collector — under `claude -p`,
#    ending the turn EXITS the process (and systemd then kills the whole cgroup,
#    including "detached" collectors). The collector had hit its 2,003-tweet
#    target 12s before the run died. This clause is the fix; keep it in every
#    prompt this script sends.
HEADLESS_NOTE="HEADLESS -p MODE (critical): this session runs under claude -p — the process TERMINATES the instant you end your turn, and background-task completion will NOT re-invoke you; any background processes you spawned are killed with the session. NEVER end your turn to wait for a background collector, monitor, timer, or notification. If you start a long-running background process, poll it from the FOREGROUND (a blocking Bash loop: sleep 30-60s, check its status file, repeat) until it completes, then continue in the same turn. Ending your turn before the digest file is written and verified = failed run."
FAIL_ROOT="$HELM/08-bawaba/.news-failed-$(date +%Y-%m-%d).md"

# 3a. The short digest (08-bawaba/digest/): what he needs to know today, written
#     from the finished daily by a second, short headless run. Its whole brief is
#     news-digest/digest_style.md. Daily mode runs it after a complete daily; the
#     `digest` mode runs it alone, and does nothing when today's digest is already
#     complete. Two attempts, no delay. A failed digest never fails the daily, and
#     it never touches the daily file. It heals itself: the coordinator runs
#     `digest` mode at each of its runs while today's daily is on disk.
TODAY="$(date +%Y-%m-%d)"
DAILY_FILE="$HELM/08-bawaba/daily/$TODAY.md"
DIGEST_FILE="$HELM/08-bawaba/digest/$TODAY.md"
DIGEST_WATCHDOG_SEC="${DIGEST_WATCHDOG_SEC:-900}"
DIGEST_PROMPT="Read ~/helm/03-rai/skills/news-digest/digest_style.md and follow it exactly. Input: today's daily, $DAILY_FILE. Output: $DIGEST_FILE, that one file only. Run fully autonomously; ask nothing. $HEADLESS_NOTE"

digest_file_ok() {                # newer than its daily, all six callouts, and digest_style.md's leak check is clean
  [ -f "$DIGEST_FILE" ] && [ "$DIGEST_FILE" -nt "$DAILY_FILE" ] \
    && [ "$(stat -c%s "$DIGEST_FILE" 2>/dev/null || echo 0)" -gt 1000 ] || return 1
  local title
  for title in 'Bottom line' 'News Wire' 'Hot Topics' 'Gems' 'Wisdom' 'Deep Dive'; do
    grep -qE "^> \[![a-z]+\] $title\$" "$DIGEST_FILE" || return 1
  done
  ! grep -qE '^#|https?://|@[A-Za-z0-9_]|\[(x|r|hn|gh|sub|m)-[0-9]|—|–|For you|CLAUDE_FILL' "$DIGEST_FILE"
}

archive_old_digests() {           # only today's digest stays in 08-bawaba/digest/, like daily/
  local dst="$HELM/13-archive/news/digest" f
  mkdir -p "$dst"
  for f in "$HELM"/08-bawaba/digest/????-??-??.md; do
    [ -e "$f" ] && [ "$(basename "$f")" != "$TODAY.md" ] || continue
    if [ -e "$dst/$(basename "$f")" ]; then
      echo "WARN: 13-archive/news/digest/$(basename "$f") already exists, kept both copies"
    else
      mv "$f" "$dst/" && echo "Archived digest $(basename "$f") to 13-archive/news/digest/"
    fi
  done
}

run_digest() {                    # 0 = today's digest is on disk and complete
  if [ ! -s "$DAILY_FILE" ]; then
    echo "DIGEST: no daily at $DAILY_FILE, nothing to shorten."
    return 1
  fi
  if digest_file_ok; then
    echo "DIGEST: already complete, $DIGEST_FILE"
    return 0
  fi
  local attempt
  for attempt in 1 2; do
    echo "Running headless digest, attempt $attempt (timeout ${DIGEST_WATCHDOG_SEC}s) ..."
    printf '%s' "$DIGEST_PROMPT" | timeout "$DIGEST_WATCHDOG_SEC" "$CLAUDE" -p --dangerously-skip-permissions --output-format text \
      || echo "WARN: digest run exited non-zero (rc $?)."
    digest_file_ok && break
  done
  if digest_file_ok; then
    archive_old_digests
    notify-send -a news-digest "Bawaba digest ready" "$(basename "$DIGEST_FILE")" 2>/dev/null || true
    echo "DIGEST: success, $DIGEST_FILE"
    return 0
  fi
  [ "${DIGEST_QUIET_FAIL:-0}" = 1 ] \
    || notify-send -a news-digest "Bawaba digest FAILED" "No complete digest at $(basename "$DIGEST_FILE"). The coordinator retries at its next run. Log: $LOG" 2>/dev/null || true
  echo "DIGEST: FAILURE, no complete digest at $DIGEST_FILE"
  return 1
}

if [ "$MODE" = "digest" ]; then
  run_digest; RC=$?
  echo "════════ $(date '+%F %T') END mode=$MODE ════════"
  exit $RC
fi

if [ "$MODE" = "weekly" ]; then
  PROMPT="Use the Skill tool to load the skill named news-digest, then run it in WEEKLY mode — the Bawaba Weekly MAGAZINE (SKILL.md section 'Weekly Magazine'), topical departments in magazine prose, NOT a news recap. Pipeline: (1) run python3 ~/helm/03-rai/skills/news-digest/weekly_mine.py and confirm its console summary reports >0 week-unique records; (2) read the five department briefs + coverage.md it writes under .runs/weekly-<week>/, plus this week's daily digests from BOTH ~/helm/08-bawaba/daily/ AND ~/helm/13-archive/news/daily/ (prefer the daily/ copy when a date exists in both; skip missing days silently); (3) pick subjects per department — one Cover Story, the Model State inventory, ONE Lesson concept with real teaching depth, Workshop tools, 3-5 Reading Shelf long-reads — and pull full text from ~/helm/13-archive/news/dumps/<day>/ whenever a candidate needs depth; (4) enrich the Cover Story, The Lesson, and Model State subjects with WebSearch/WebFetch ONLY, max ~10 fetches — NEVER open a browser, never scrape sources; (5) write the issue (Editor's Letter, Cover Story, Model State, The Lesson, The Workshop, Reading Shelf, Closing — Wisdom, coverage footer; ~8,000-10,000 words) to ~/helm/08-bawaba/weekly/ named for the ISO week; (6) move any PRIOR week's file from 08-bawaba/weekly/ to 13-archive/news/weekly/ (move, never delete), then grep the new issue for CLAUDE_FILL and for instruction comments and confirm zero. Run fully autonomously; ask nothing. $HEADLESS_NOTE"
  OUT="$HELM/08-bawaba/weekly/$(date +%G)-W$(date +%V).md"
else
  PROMPT="Use the Skill tool to load the skill named news-digest, then run it to generate today's full DAILY digest. Run fully autonomously; ask nothing. $HEADLESS_NOTE SCHEDULED MODE: apply the scheduled-mode deadline contract in SKILL.md (config.yaml scheduled_mode) — collection must end by start+85min, never start a cooldown/retry that crosses that line, and ship the digest with explicitly-noted partial coverage rather than nothing. X COLLECTION (PRIMARY — do this FIRST, it is the dealbreaker source): X is gathered in THREE gentle passes per night to beat X's per-session timeline throttle — the 21:00 and 00:00 passes already ran (news-x-collect.timer) and ACCUMULATED into .runs/$(date +%Y-%m-%d)/x_foryou.json + x_following.json (merge-write, deduped by tweet id, tweets tagged source_tier). Do the FINAL pass now as a BLOCKING FOREGROUND call (NOT the Chrome MCP). Run: export PATH=\"\$HOME/.local/bin:\$PATH\"; uv run ~/helm/03-rai/skills/news-digest/_collect_x_headless.py --date $(date +%Y-%m-%d) --target 700 --following-target 50 --phase both — and WAIT for it to finish; it merge-appends this pass into the same pool. @johndoe is X Premium (~10k/day read cap), but each pass is intentionally gentle (~400-700 tweets) and the THREE passes accumulate — judge success on the MERGED pool, not this single pass: read the length of x_foryou.json / x_following.json after it finishes; success = >=700 For You + >=110 Following cumulative. A quick plateau on this final pass is EXPECTED when the pool is already full — do NOT grind reloads. If it exits 3 or writes .runs/<date>/x_LOGIN_FAILED.json the X login is dead — write a one-line marker to $FAIL_ROOT, then judge the MERGED pool. If the earlier passes left tweets in x_foryou.json or x_following.json, continue and ship with partial X noted. If the merged pool holds ZERO tweets, STOP: no X, no digest, in every run (John's rule, 2026-09-29). Add the reason to $FAIL_ROOT and do not write the digest. There is NO paired browser and NO claude-in-chrome MCP in scheduled runs — never call list_connected_browsers, select_browser, or any browser tool; if a headless collector fails, ship partial for that source. SUBSTACK + MEDIUM (headless, run AFTER the X pass): run as a BLOCKING FOREGROUND call: uv run ~/helm/03-rai/skills/news-digest/_collect_web_headless.py --date $(date +%Y-%m-%d) — it clones cookies, drives its own headless Chrome, and merge-writes substack.json + medium.json into .runs/$(date +%Y-%m-%d)/ (~1 min total; targets 200 Substack / 30 Medium). If it writes substack_LOGIN_FAILED.json or medium_LOGIN_FAILED.json, mark that source partial and CONTINUE — they are not dealbreakers. ENRICHMENT (MANDATORY, right after): uv run ~/helm/03-rai/skills/news-digest/_enrich_substack.py --date $(date +%Y-%m-%d) then uv run ~/helm/03-rai/skills/news-digest/_enrich_medium.py --date $(date +%Y-%m-%d) — both carry uv script headers; plain python3 fails on missing httpx. Collect all sources (Hacker News, Reddit, GitHub Trending via curl; X, Substack, Medium via the headless collectors) and save the digest to ~/helm/08-bawaba/daily/$(date +%Y-%m-%d).md. POST-FILL: you are not finished until every <CLAUDE_FILL_*> placeholder is replaced with real prose, every raw scaffolding line (those beginning with <!-- raw:) is stripped, AND every <!-- CLAUDE INSTRUCTIONS --> block is deleted (News Wire trim instructions, Gems hook rubric, Hot Topics); the News Wire instruction block requires you to DELETE non-tech candidate bullets before writing briefs. Before finishing, run grep -c on the output file for CLAUDE_FILL, for the raw scaffolding marker, and for the literal text <!-- CLAUDE, and confirm all three are 0. A digest shipped with placeholders or instruction blocks is a failed run."
  OUT="$HELM/08-bawaba/daily/$(date +%Y-%m-%d).md"
fi

# Budget-protecting retry prompt: reuse same-day .runs/ dumps instead of
# re-collecting. X is the hard constraint — its account-level read budget does
# not reset within the day, so a retry that re-scrapes X burns coverage for the
# NEXT attempt too. Prepended to the standard prompt; the override wording wins
# over the collection instructions inside it.
build_retry_prompt() {            # $1 = failure reason for attempt 1
  if [ "$MODE" = "weekly" ]; then
    printf '%s' "RETRY RUN — attempt 2 of today's weekly magazine: attempt 1 failed ($1). Mining the dumps and reading briefs/dailies is cheap and safe to redo, so regenerate the issue in full (weekly_mine.py is idempotent; the web-fetch cap applies fresh). $PROMPT"
  else
    printf '%s' "RETRY RUN — attempt 2 of today's scheduled digest: attempt 1 failed partway ($1). Collection artifacts from attempt 1 likely already exist in $RUNS_DIR/. BUDGET PROTECTION — this OVERRIDES the collection instructions that follow: as your first collection step, list $RUNS_DIR/; for every source whose dump file already exists there and is non-trivial, LOAD AND REUSE that dump instead of re-collecting the source — re-scrape only sources with no usable dump. X IS CRITICAL: the X account read budget is account-level and does NOT reset within the same day. If x_foryou.json or x_following.json exists there with more than 50 tweets, you MUST NOT re-scrape that timeline — merge the existing dump(s) and, if under target, note partial X coverage in the run note. Only if an X dump is missing or near-empty may you attempt ONE collection window; if it plateaus at ~10-15 tweets with an endless loading spinner, that is an account-level read rate-limit — do NOT run cooldown retries; record the finding and ship with partial X. A partial digest with an explicit run note beats no digest. ZERO X IS THE ONE STOP: if the merged X pool is still empty after that one window, write the reason to $FAIL_ROOT and do not write the digest. No X, no digest, in every run, a manual recovery included (John's rule, 2026-09-29). Everything below still applies. $PROMPT"
  fi
}

if [ "${RECOVERY:-0}" = "1" ] && [ "$MODE" != "weekly" ]; then
  PROMPT="$(build_retry_prompt "manual recovery run")"
  echo "RECOVERY MODE: using the built-in budget-protecting retry prompt (recovery-prompt.txt deleted)."
fi
echo "Expecting output: $OUT"

# 4. Run the digest HEADLESS (no WezTerm). `timeout` is the watchdog; completion
#    is this process returning. No --chrome since v5.9: every browser source is
#    a headless-CDP collector the agent runs via Bash.
run_headless() {                  # $1 = prompt
  printf '%s' "$1" | timeout "$WATCHDOG_SEC" "$CLAUDE" -p --dangerously-skip-permissions --output-format text >>"$LOG" 2>&1
}

digest_ok() {                     # complete digest on disk: exists, no placeholders/scaffolding/instruction blocks, non-trivial size
  local min_bytes=2000
  [ "$MODE" = "weekly" ] && min_bytes=20000   # a ~60-min magazine issue is never this small
  [ -f "$OUT" ] && ! grep -qE 'CLAUDE_FILL|<!-- raw:|<!-- CLAUDE' "$OUT" 2>/dev/null && [ "$(stat -c%s "$OUT" 2>/dev/null || echo 0)" -gt "$min_bytes" ]
}

failure_reason() {                # best-effort classification of attempt 1 for the retry prompt + notification
  if grep -q 'Usage Policy' "$LOG"; then
    echo "API Usage Policy block — likely a cyber-classifier false positive on security-news content"
  elif [ -f "$OUT" ]; then
    echo "incomplete digest — placeholders left or file too small"
  elif [ -f "$FAIL_ROOT" ]; then
    echo "no digest; X marker $(basename "$FAIL_ROOT") present: a dead X login or zero X"
  else
    echo "no digest file produced"
  fi
}

echo "Running headless digest (timeout ${WATCHDOG_SEC}s) ..."
run_headless "$PROMPT" || echo "WARN: headless run exited non-zero (rc $?)."

# 5. Auto-retry ONCE on failure (2026-06-10). Skipped for manual RECOVERY runs
#    (already a retry) and when NO_RETRY=1.
if ! digest_ok && [ "${RECOVERY:-0}" != "1" ] && [ "${NO_RETRY:-0}" != "1" ]; then
  REASON="$(failure_reason)"
  echo "ATTEMPT 1 FAILED: $REASON — auto-retrying once in ${RETRY_DELAY_SEC}s with the budget-protecting retry prompt."
  notify-send -a news-digest "News digest ($MODE) attempt 1 failed" "$REASON — auto-retry in $((RETRY_DELAY_SEC / 60)) min" 2>/dev/null || true
  sleep "$RETRY_DELAY_SEC"
  echo "Running retry attempt (timeout ${WATCHDOG_SEC}s) ..."
  run_headless "$(build_retry_prompt "$REASON")" || echo "WARN: retry exited non-zero (rc $?)."
fi

# 6. Archive the day's raw dumps regardless of outcome — present_v5.py copies
#    them on success, but a failed run's partial collection is information too
#    (helm = brain: nothing collected is thrown away). Idempotent rsync.
if [ "$MODE" != "weekly" ]; then
  RUNS_TODAY="$HELM/03-rai/skills/news-digest/.runs/$(date +%Y-%m-%d)"
  if [ -d "$RUNS_TODAY" ]; then
    mkdir -p "$HELM/13-archive/news/dumps/$(date +%Y-%m-%d)"
    rsync -a "$RUNS_TODAY/" "$HELM/13-archive/news/dumps/$(date +%Y-%m-%d)/" 2>/dev/null \
      && echo "Dumps archived to 13-archive/news/dumps/$(date +%Y-%m-%d)/"
  fi
fi

# 6a. Weekly mode: copy this week's run dir (the department briefs weekly_mine.py
#     writes) to 13-archive/news/weekly-runs/, since .runs lives in local state and
#     never reaches git. The week label mirrors weekly_mine.py: the ISO week of the
#     Saturday that ends this Sun..Sat week. rsync, then a checksum dry-run must come
#     back empty. Copy only: the state copy stays.
if [ "$MODE" = "weekly" ]; then
  WEEK_LABEL="$(date -d "$(date -d "$(( 6 - $(date +%w) )) days" +%F)" +%G-W%V)"
  WEEK_SRC="$HELM/03-rai/skills/news-digest/.runs/weekly-$WEEK_LABEL"
  WEEK_DST="$HELM/13-archive/news/weekly-runs/weekly-$WEEK_LABEL"
  if [ -d "$WEEK_SRC" ]; then
    mkdir -p "$WEEK_DST"
    rsync -a "$WEEK_SRC/" "$WEEK_DST/" 2>/dev/null
    if [ -z "$(rsync -rcn --out-format='%n' "$WEEK_SRC/" "$WEEK_DST/" 2>/dev/null | grep -v '/$' | head -1)" ]; then
      echo "Weekly run dir archived to 13-archive/news/weekly-runs/weekly-$WEEK_LABEL/ (checksum-verified)"
    else
      echo "WARN: .runs/weekly-$WEEK_LABEL differs from its archive copy after rsync"
    fi
  else
    echo "WARN: no .runs/weekly-$WEEK_LABEL to archive"
  fi
fi

# 6b. Prune archived day dirs older than 3 days from .runs, the working scratch.
#     .runs is a symlink to ~/.local/state/news-digest/runs, outside git; the
#     durable copy of each day lives in 13-archive/news/dumps/. A checksum rsync
#     dry-run must come back empty before the scratch copy goes; any difference
#     re-syncs and keeps the dir for the next pass. Same-day re-runs/retries are
#     never touched, and weekly-* dirs are never pruned (6a archives a copy).
if [ "$MODE" != "weekly" ]; then
  RUNS_DIR="$HELM/03-rai/skills/news-digest/.runs"
  PRUNE_CUTOFF="$(date -d '3 days ago' +%Y-%m-%d)"
  for d in "$RUNS_DIR"/????-??-??; do
    [ -d "$d" ] || continue
    day="$(basename "$d")"
    [[ "$day" < "$PRUNE_CUTOFF" ]] || continue
    dst="$HELM/13-archive/news/dumps/$day"
    mkdir -p "$dst"
    rsync -a "$d/" "$dst/" 2>/dev/null
    if [ -z "$(rsync -rcn --out-format='%n' "$d/" "$dst/" 2>/dev/null | grep -v '/$' | head -1)" ]; then
      rm -rf "$d" && echo "Pruned .runs/$day (archive copy checksum-verified)"
    else
      echo "WARN: .runs/$day differs from archive after rsync — kept for next pass"
    fi
  done
fi

# 7. Outcome notification (the local Chrome is left running — never killed here).
#    Exits non-zero on failure so systemd marks the unit failed (visible in
#    list-units / journal, and available to a future OnFailure= hook).
# The outcome also lands in a state file, so session-start can show a failed run as a banner
# that names workflow 10 at the next session, not only as a popup that may be missed.
write_news_state() {
  python3 - "$1" "$MODE" "$OUT" "$LOG" <<'PY' 2>/dev/null || true
import datetime, json, pathlib, sys
ok, mode, out, log = sys.argv[1:5]
p = pathlib.Path.home() / ".local/state/news-digest/last-run.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({
    "ok": ok == "1", "mode": mode, "out": out, "log": log,
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
}, indent=2) + "\n")
PY
}
if digest_ok; then
  notify-send -a news-digest "News digest ($MODE) ready" "$(basename "$OUT") — $(stat -c%s "$OUT") bytes" 2>/dev/null || true
  echo "RESULT: success — $OUT"
  write_news_state 1
  RC=0
else
  notify-send -a news-digest -u critical "News digest ($MODE) FAILED" "No complete digest at $(basename "$OUT"). Workflow 10 (~/helm/11-workflows/10-news-digest-recovery.md). Log: $LOG" 2>/dev/null || true
  echo "RESULT: FAILURE — no complete digest at $OUT"
  write_news_state 0
  RC=1
fi

# 8. The short digest, after a complete daily only. Its outcome never changes RC.
if [ "$MODE" = "daily" ] && [ "$RC" = 0 ]; then
  run_digest || true
fi

echo "════════ $(date '+%F %T') END mode=$MODE ════════"
exit $RC
