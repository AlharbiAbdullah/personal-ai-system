#!/usr/bin/env bash
# One fleet-state snapshot for the orchestrator's monitor loop.
# Usage: orch-poll.sh <run-dir> <repo-basename>
# Prints one line per task: TASK STATUS AGE DONE INBOX PANE
#   STATUS  from the hook-written status file (- if none yet)
#   AGE     seconds since the status file was last touched
#   DONE    yes if done/<task>.DONE exists
#   INBOX   yes if inbox/<task>.json exists
#   PANE    fallback read, ONLY when the status file is missing or stale
#           (>360s): spinner|prompt|gone after ANSI stripping. Spinner
#           overrides an apparently idle prompt by construction: it is
#           checked first.
set -u
RUN_DIR=${1:?run dir}
REPO_BASE=${2:?repo basename}
NOW=$(date +%s)

shopt -s nullglob
BRIEFS=("$RUN_DIR"/briefs/*.md)
if [ ${#BRIEFS[@]} -eq 0 ]; then
  echo "no briefs in $RUN_DIR/briefs" >&2
  exit 1
fi

printf '%-14s %-9s %6s %-5s %-6s %s\n' TASK STATUS AGE DONE INBOX PANE
for brief in "${BRIEFS[@]}"; do
  task=$(basename "$brief" .md)
  status=- age=- done=no inbox=no pane=-

  sf="$RUN_DIR/status/$task.json"
  if [ -f "$sf" ]; then
    status=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('status','?'))" "$sf" 2>/dev/null || echo '?')
    mtime=$(stat -c %Y "$sf" 2>/dev/null || stat -f %m "$sf")
    age=$((NOW - mtime))
  fi
  [ -f "$RUN_DIR/done/$task.DONE" ] && done=yes
  [ -f "$RUN_DIR/inbox/$task.json" ] && inbox=yes

  if [ "$status" = "-" ] || { [ "$age" != "-" ] && [ "$age" -gt 360 ]; }; then
    sess="wk-$REPO_BASE-$task"
    # "=" asks for this exact name: a bare wk-app-g1 prefix-matches wk-app-g10.
    if tmux has-session -t "=$sess" 2>/dev/null; then
      text=$(tmux capture-pane -t "=$sess:" -p 2>/dev/null | sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g')
      if echo "$text" | grep -qE '✻|✽|✳|✶|esc to interrupt|tokens'; then
        pane=spinner
      elif echo "$text" | grep -q '❯'; then
        pane=prompt
      else
        pane=unknown
      fi
    else
      pane=gone
    fi
  fi
  printf '%-14s %-9s %6s %-5s %-6s %s\n' "$task" "$status" "$age" "$done" "$inbox" "$pane"
done
