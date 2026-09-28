#!/bin/bash
# rai maintenance runner (UBUNTU) — SOLE COORDINATOR + SOLE WRITER since
# 2026-06-13. Full design in 03-rai/SYNC-ARCHITECTURE.md.
#
# This box is the ONLY machine that writes origin, so the old two-writer rebase
# war is gone — origin only ever moves when this runs. The Mac is the primary
# AUTHORING machine and holds two local-only timers of its own (2026-08-03): an
# hourly `mac-sync.sh commit` + push to the `mac-inbox` ref here, and a pull-only
# wake refresh. Neither touches origin, so the single-writer model is intact.
#
# Pipeline (headless `claude -p` for the two intelligent steps):
#   0. git fetch + merge --ff-only    (do_pull) defence + transition catch-up;
#                                      steady-state no-op since nobody else pushes origin.
#   1. capture_mac                     ssh mac → snapshot its churn into a commit,
#                                      `git fetch mac main`, merge it in. Mac asleep
#                                      → fall back to the `mac-inbox` ref it pushed
#                                      here on its own hourly timer. Conflict policy:
#                                      MAC wins content, this box wins its own state
#                                      (LINUX_WINS_GLOBS); the losing side is always
#                                      saved to ~/.local/state/rai-maintenance/merge-losers/.
#   2. merge-collisions  (claude)      fold any durably-backed-up collider files.
#   3. process-sessions  (claude)      drain BOTH machines' pending queue → ChromaDB
#                                      (this box is the sole ChromaDB writer).
#   3.5 sanity (harness)               certify the brain post-pipeline; write sanity-last.json
#                                      (committed + shipped to the Mac → session-start banner).
#   4. git-commit + push (claude)      group churn into logical commits → origin.
#   5. refresh_mac                     ssh mac → fast-forward the Mac to origin.
#
# Scheduled by systemd user timer rai-maintenance.timer (04/10/16/22:00). Logs +
# lock live in ~/.local/state/rai-maintenance/ — OUTSIDE the repo, so a run never
# commits or rebases its own log. The Mac is captured opportunistically — whatever
# it has whenever this box reaches it; if it is asleep the run still does the rest.
#
# Env:  NO_LOCK=1    skip the overlap lock (manual debugging)
#       SYNC_ONLY=1  do the git sync only (pull + capture_mac + refresh_mac),
#                    skip the three claude steps — fast plumbing check.

set -uo pipefail
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

CLAUDE="$HOME/.local/bin/claude"
HELM="$HOME/helm"
SCHED="$HELM/03-rai/skills/rai/scheduled"
STATE="$HOME/.local/state/rai-maintenance"                  # logs + lock OUTSIDE the repo
MAC_REMOTE="mac"                                            # git remote (mac:helm over ssh)
MAC_SSH="ssh -o BatchMode=yes -o ConnectTimeout=15 mac"     # Host mac in ~/.ssh/config
MAC_SYNC='bash ~/helm/03-rai/skills/rai/scheduled/mac-sync.sh'
MAC_INBOX="mac-inbox"                                       # local ref the Mac pushes to (travel path)
MERGE_LOSERS="$STATE/merge-losers"                           # discarded conflict sides, kept for recovery
mkdir -p "$STATE/logs"
LOG="$STATE/logs/$(date +%Y-%m-%d-%H%M)-maintenance.log"
exec >>"$LOG" 2>&1

echo "════════ $(date '+%F %T') START maintenance (ubuntu coordinator) ════════"

# Overlap lock — atomic mkdir; clear stale locks older than 60 min
LOCK="$STATE/.lock"
if [ "${NO_LOCK:-0}" != "1" ]; then
  if [ -d "$LOCK" ]; then
    AGE=$(( $(date +%s) - $(stat -c%Y "$LOCK" 2>/dev/null || echo 0) ))
    if [ "$AGE" -lt 3600 ]; then
      echo "Another run holds the lock (${AGE}s old) — skipping."; exit 0
    fi
    echo "Stale lock (${AGE}s old) — clearing."; rmdir "$LOCK" 2>/dev/null || true
  fi
  mkdir "$LOCK" 2>/dev/null || { echo "Lost lock race — skipping."; exit 0; }
  trap 'rmdir "$LOCK" 2>/dev/null' EXIT
fi

# News-run guard — same box runs the digest; never drain/commit mid-digest.
# Check the systemd units, not a process pattern: `pgrep -f "claude --chrome"`
# also matched Chrome's always-on `claude --chrome-native-host` (2026-08-26,
# every run skipped while Chrome was open). Oneshots report `activating` while running.
for unit in news-daily.service news-weekly.service; do
  if [ "$(systemctl --user show -p ActiveState --value "$unit" 2>/dev/null)" = activating ]; then
    echo "News run in progress ($unit activating) — skipping."; exit 0
  fi
done

# ── git self-healing (unattended — every recoverable state recovers HERE) ──────
# Unchanged from the two-writer era except the integration SOURCE: step 1 now
# merges the Mac over SSH instead of both boxes racing origin. The three heal
# layers + durable collision backups are kept verbatim — they still protect the
# origin pull and the Mac merge. Backups go to a DURABLE dir (not /tmp) and are
# folded back by the merge-collisions claude step, then deleted.
COLLISION_ROOT="$HOME/.local/state/helm-pull-collisions"
COLLISION_BACKUP="$COLLISION_ROOT/$(date +%Y%m%d-%H%M%S)"

backup_path() {  # backup_path REPO_RELATIVE_PATH
  mkdir -p "$COLLISION_BACKUP/$(dirname "$1")"
  cp "$HELM/$1" "$COLLISION_BACKUP/$1"
}

self_heal_git_state() {
  if [ -d "$HELM/.git/rebase-merge" ] || [ -d "$HELM/.git/rebase-apply" ]; then
    echo "self-heal: aborting dead rebase"; git -C "$HELM" rebase --abort || true
  fi
  if [ -f "$HELM/.git/MERGE_HEAD" ]; then
    echo "self-heal: aborting dead merge"; git -C "$HELM" merge --abort || true
  fi
  if [ -f "$HELM/.git/CHERRY_PICK_HEAD" ]; then
    echo "self-heal: aborting dead cherry-pick"; git -C "$HELM" cherry-pick --abort || true
  fi
  local p
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    if [ -e "$HELM/$p" ]; then
      backup_path "$p"
      echo "self-heal: backed up conflicted $p -> $COLLISION_BACKUP/$p"
    fi
    git -C "$HELM" restore --staged --worktree --source=HEAD -- "$p" 2>/dev/null \
      || { git -C "$HELM" rm --cached -q -- "$p" 2>/dev/null || true; rm -f "$HELM/$p"; }
  done < <(git -C "$HELM" diff --name-only --diff-filter=U)
}

resolve_untracked_collisions() {  # incoming tracked path exists locally as untracked
  local ref="${1:-origin/main}"
  git -C "$HELM" fetch origin main || return 1
  local p
  while IFS= read -r p; do
    [ -e "$HELM/$p" ] || continue
    git -C "$HELM" ls-files --error-unmatch "$p" >/dev/null 2>&1 && continue   # tracked → autostash handles it
    if git -C "$HELM" show "$ref:$p" 2>/dev/null | cmp -s - "$HELM/$p"; then
      rm -f "$HELM/$p"
      echo "collision (identical): dropped local untracked $p"
    else
      backup_path "$p" && rm -f "$HELM/$p"
      echo "collision (divergent): backed up local untracked $p -> $COLLISION_BACKUP/$p"
    fi
  done < <(git -C "$HELM" diff --name-only HEAD "$ref")
}

heal_autostash_conflicts() {
  local tries=0 p
  while git -C "$HELM" diff --name-only --diff-filter=U | grep -q .; do
    tries=$((tries+1))
    if [ "$tries" -gt 3 ]; then
      echo "ERROR: unmerged paths survived 3 heal passes"; return 1
    fi
    echo "self-heal: conflicted autostash pop — resolving (pass $tries, disk side wins)"
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      git -C "$HELM" checkout --theirs -- "$p" 2>/dev/null || true  # delete/modify: keep disk copy
      git -C "$HELM" add -A -- "$p" 2>/dev/null || true             # index.lock race → next pass
    done < <(git -C "$HELM" diff --name-only --diff-filter=U)
    sleep 2
  done
  if [ "$tries" -gt 0 ] && git -C "$HELM" stash list | head -1 | grep -q ': autostash$'; then
    echo "self-heal: dropping conflicted autostash entry (content resolved into tree)"
    git -C "$HELM" stash drop 'stash@{0}' || true
  fi
  return 0
}

# Linux is the SOLE writer to origin, so origin/main is always an ancestor of
# local main — there is never local work to replay onto it. Use fetch + ff-only,
# not `pull --rebase`. The rebase form was the chronic jam: any run that died
# before its push (step 4) left an unpushed merge; the next run's rebase then
# tried to REPLAY the wip(mac) churn commits onto origin and choked on
# `Cannot merge binary files` in ChromaDB, leaving a half-done rebase that
# poisoned every following run (detached HEAD + UU conflicts). ff-only can never
# do that — it is a no-op in steady state and, on the anomalous diverged-origin
# case, fails cleanly (no half-rebase) and lets the retry/abort path call a human.
do_pull() {
  git -C "$HELM" fetch origin main || return 1
  git -C "$HELM" merge --ff-only FETCH_HEAD
}

# write_abort_status: an early abort (step 0/1) never reaches the sanity step, so the
# committed sanity-last.json keeps saying whatever it said LAST. In Sep 2026 that was
# HEALTHY for 2.5 days while nothing was pulling, draining or backing up — the alarm
# died in the same instant as the thing it watched. Write a BROKEN verdict in the
# harness's own shape so the session-start banner on this box says so at the next
# prompt, and a reader elsewhere sees a fresh FAIL instead of a stale PASS. Only this
# box writes the file and do_pull is ff-only, so a dirty copy never blocks a run.
write_abort_status() {
  python3 - "$1" "$LOG" "$HELM" <<'PY' 2>/dev/null || true
import datetime, json, pathlib, sys
reason, log, helm = sys.argv[1:4]
p = pathlib.Path(helm) / "03-rai/memory/learning/system/sanity-last.json"
p.parent.mkdir(parents=True, exist_ok=True)
p.write_text(json.dumps({
    "verdict": "BROKEN", "role": "producer",
    "ts": datetime.datetime.now().isoformat(timespec="seconds"),
    "counts": {"PASS": 0, "WARN": 0, "FAIL": 1, "SKIP": 0},
    "fails": [{"id": "COORD-0", "subsystem": "Coordinator",
               "evidence": f"run aborted before the pipeline: {reason}. Log: {log}"}],
    "warns": [],
}, indent=2) + "\n")
PY
}

# drop_stale_autostashes: an aborted rebase orphans its --autostash entry, which
# then lingers in `git stash list` forever. These are git temp-state, not records
# (their content was already applied to the tree), so drop any `autostash` entry
# older than 1h — a current run's own autostash is younger, so it is never touched.
# NAMED/manual stashes are always kept.
drop_stale_autostashes() {
  local cutoff=$(( $(date +%s) - 3600 )) sel n=0
  for _ in $(seq 1 100); do
    sel=$(git -C "$HELM" stash list --format='%gd %ct %gs' | awk -v c="$cutoff" '$3=="autostash" && $2<c {print $1; exit}')
    [ -z "$sel" ] && break
    git -C "$HELM" stash drop "$sel" >/dev/null 2>&1 && n=$((n+1)) || break
  done
  [ "$n" -gt 0 ] && echo "tidy: dropped $n orphaned autostash entries (named stashes kept)"
}

# ── Merge conflict policy (2026-08-03) ────────────────────────────────────────
# The Mac is the PRIMARY AUTHORING machine; this box runs the automation. So on a
# content conflict the MAC wins. This box wins only on the runtime state it alone
# writes (indexes, rendered blocks, learning logs) — where the Mac's copy is by
# definition a stale read-replica.
#
# Replaces the old blanket `-X ours`, which silently discarded the Mac's side of
# every conflicting file. Whichever side loses is copied to $MERGE_LOSERS first:
# no resolution here is allowed to destroy content in either direction.
# Linux also wins paths it stopped tracking: they leave the index, the working file stays.
LINUX_WINS_GLOBS=(
  "03-rai/memory/state/*"
  "03-rai/memory/learning/*"
  "03-rai/semantic-memory/index/*"
  "03-rai/semantic-memory/processed-sessions.jsonl"
  ".obsidian/workspace.json"
  ".obsidian/themes/Omarchy/*"
  "03-rai/skills/synced/*/.last-complete-round"
  "03-rai/semantic-memory/backfill-done/*"
  "03-rai/skills/news-digest/.runs/*"
)

linux_wins() {  # linux_wins REPO_RELATIVE_PATH → 0 if THIS box's side should win
  local p="$1" g
  for g in "${LINUX_WINS_GLOBS[@]}"; do
    # shellcheck disable=SC2254
    case "$p" in $g) return 0;; esac
  done
  return 1
}

# Resolve every unmerged path by the policy above. Stage 2 = ours (linux),
# stage 3 = theirs (mac). Returns 1 if anything survived unresolved.
resolve_merge_by_policy() {
  local paths p dest ts winner side nm=0 nl=0
  paths=$(git -C "$HELM" diff --name-only --diff-filter=U)
  [ -z "$paths" ] && return 0
  ts=$(date +%Y%m%d-%H%M%S)
  while IFS= read -r p; do
    [ -z "$p" ] && continue
    if linux_wins "$p"; then side="--ours";   winner=linux; nl=$((nl+1))
    else                     side="--theirs"; winner=mac;   nm=$((nm+1)); fi
    dest="$MERGE_LOSERS/$ts/$p"
    mkdir -p "$(dirname "$dest")"
    if [ "$winner" = linux ]; then git -C "$HELM" show ":3:$p" > "$dest" 2>/dev/null || true
    else                           git -C "$HELM" show ":2:$p" > "$dest" 2>/dev/null || true; fi
    [ -s "$dest" ] || rm -f "$dest"            # delete/modify: no losing blob to keep
    if [ "$winner" = linux ] && ! git -C "$HELM" ls-files -u -- "$p" | awk '$3 == 2 {f=1} END {exit !f}'; then
      # No stage 2: Linux deleted or untracked it. Keep it out of the index (checkout
      # --ours would fail and add -A would re-add the Mac's copy); the working file stays.
      git -C "$HELM" rm --cached -q -- "$p" 2>/dev/null || true
    else
      git -C "$HELM" checkout "$side" -- "$p" 2>/dev/null || true
      git -C "$HELM" add -A -- "$p" 2>/dev/null || true
    fi
    echo "  conflict: $p → $winner wins (other side → $dest)"
  done <<< "$paths"
  echo "capture_mac: resolved $((nm+nl)) conflict(s) — mac won $nm, linux won $nl"
  notify-send -a rai-maintenance -u normal "Rai maintenance" \
    "Mac merge: $((nm+nl)) conflict(s) resolved (mac $nm / linux $nl). Losing sides in $MERGE_LOSERS/$ts" 2>/dev/null || true
  git -C "$HELM" diff --name-only --diff-filter=U | grep -q . && return 1
  return 0
}

# untrack_ignored_paths: .gitignore holds only secrets, machine droppings and derived
# state, so an ignored path must never be tracked. mac-sync's autostash heal can re-add a
# path Linux untracked (the Mac had it dirty); the Mac snapshot commits it and it merges
# back here as a clean add, so the merge policy never sees it. Untrack what the merge
# brought back (the working file stays) and commit only that removal: the commit is built
# from HEAD in a scratch index, so nothing else that is staged rides along.
untrack_ignored_paths() {
  local p head tree commit idx="$HELM/.git/index.untrack-ignored"
  local msg="chore: keep gitignored paths untracked after the Mac merge"
  local -a gone=()
  while IFS= read -r -d '' p; do
    if git -C "$HELM" rm --cached -q -- "$p" 2>/dev/null; then
      gone+=("$p"); echo "capture_mac: untracked gitignored path the Mac merge brought back: $p"
    else
      echo "WARN: capture_mac: could not untrack gitignored path $p"
    fi
  done < <(git -C "$HELM" ls-files -z -ci --exclude-standard)
  [ "${#gone[@]}" -eq 0 ] && return 0
  head=$(git -C "$HELM" rev-parse HEAD) || return 1
  rm -f "$idx"
  if GIT_INDEX_FILE="$idx" git -C "$HELM" read-tree HEAD \
    && GIT_INDEX_FILE="$idx" git -C "$HELM" rm --cached -q --ignore-unmatch -- "${gone[@]}" \
    && tree=$(GIT_INDEX_FILE="$idx" git -C "$HELM" write-tree); then
    if [ "$tree" = "$(git -C "$HELM" rev-parse "HEAD^{tree}")" ]; then
      echo "capture_mac: the untracked path(s) were not in HEAD, nothing to commit"
    elif commit=$(git -C "$HELM" commit-tree "$tree" -p "$head" -m "$msg") \
      && git -C "$HELM" update-ref -m "commit: $msg" HEAD "$commit" "$head"; then
      echo "capture_mac: committed the untrack of ${#gone[@]} gitignored path(s) as ${commit:0:9}"
    else
      echo "WARN: capture_mac: commit of the untrack failed; the index still holds it for step 4"
    fi
  else
    echo "WARN: capture_mac: scratch index for the untrack commit failed; the index still holds it for step 4"
  fi
  rm -f "$idx"
  return 0
}

# ── Mac over SSH ──────────────────────────────────────────────────────────────
# capture_mac: commit the Mac's churn (so there is something to fetch), fetch it,
# merge it into this tree. Two sources, in order of preference:
#   1. SSH — the Mac is reachable: snapshot its churn live, then fetch `mac/main`.
#   2. $MAC_INBOX — the Mac is asleep/away but pushed to this box on its own hourly
#      timer. Merging that ref still captures its work. (Travel path, 2026-08-03.)
# Returns 1 only when neither source has anything.
capture_mac() {
  local ref=""
  if $MAC_SSH 'true' 2>/dev/null; then
    echo "capture_mac: Mac reachable — snapshotting its churn over SSH"
    # Memory v3 batch scanner: scan the Mac's native ~/.claude transcripts into its vault
    # pending/ BEFORE the commit snapshot, so the churn we fetch includes them.
    $MAC_SSH 'python3 ~/helm/03-rai/hooks/scripts/sync_claude_sessions.py' 2>&1 \
      || echo "WARN: mac sync-claude-sessions returned nonzero"
    $MAC_SSH "$MAC_SYNC commit" 2>&1 || echo "WARN: mac-sync commit returned nonzero"
    if git -C "$HELM" fetch "$MAC_REMOTE" main 2>&1; then
      ref="$MAC_REMOTE/main"
    else
      echo "WARN: git fetch $MAC_REMOTE failed — falling back to $MAC_INBOX."
    fi
  else
    echo "capture_mac: Mac unreachable (asleep/away) — trying its pushed $MAC_INBOX ref."
  fi

  # Fall back to whatever the Mac pushed here itself.
  if [ -z "$ref" ] && git -C "$HELM" rev-parse --verify -q "$MAC_INBOX" >/dev/null; then
    ref="$MAC_INBOX"
  fi
  if [ -z "$ref" ]; then
    echo "capture_mac: no Mac source this run — proceeding without its churn."; return 1
  fi
  if git -C "$HELM" merge-base --is-ancestor "$ref" HEAD 2>/dev/null; then
    echo "capture_mac: $ref already merged — nothing to capture."; return 0
  fi

  # Untracked local files that $ref adds as tracked make `git merge` refuse the checkout
  # outright ("untracked working tree files would be overwritten") — autostash cannot move
  # untracked files, and the refusal returned rc=0 here, so the Mac silently went uncaptured
  # (4 of 186 runs; both machines opening the same day's daily log between cycles is the
  # usual trigger). Commit just those paths first: the collision becomes an ordinary add/add
  # merge, `merge=union` folds the daily logs, and resolve_merge_by_policy settles the rest
  # with the losing side kept.
  local ncoll=0 p
  while IFS= read -r p; do
    [ -e "$HELM/$p" ] || continue
    git -C "$HELM" ls-files --error-unmatch "$p" >/dev/null 2>&1 && continue
    git -C "$HELM" add -- "$p" && ncoll=$((ncoll+1))
  done < <(git -C "$HELM" diff --name-only HEAD "$ref")
  if [ "$ncoll" -gt 0 ]; then
    git -C "$HELM" commit -q -m "wip(linux): snapshot $ncoll untracked path(s) colliding with the Mac merge" \
      && echo "capture_mac: pre-committed $ncoll untracked path(s) that $ref adds as tracked"
  fi

  echo "capture_mac: merging $ref (mac wins content conflicts; linux wins its own state)"
  git -C "$HELM" merge --autostash --no-edit "$ref" 2>&1 || true
  if [ -f "$HELM/.git/MERGE_HEAD" ]; then
    if ! resolve_merge_by_policy; then
      echo "ERROR: unresolved paths survived the merge policy — aborting the Mac merge."
      git -C "$HELM" merge --abort 2>/dev/null || true
      notify-send -a rai-maintenance -u critical "Rai maintenance" "Mac merge aborted — see $LOG" 2>/dev/null || true
      return 1
    fi
    git -C "$HELM" commit --no-edit -q 2>&1 || true
  fi
  if ! heal_autostash_conflicts; then
    echo "ERROR: Mac merge left unmerged paths after 3 heal passes."
    notify-send -a rai-maintenance -u critical "Rai maintenance" "Mac merge conflict unresolved — see $LOG" 2>/dev/null || true
    return 1
  fi
  untrack_ignored_paths   # the merge (SSH or $MAC_INBOX) is done; runs before any commit step
  return 0
}

# refresh_mac: fast-forward the Mac to origin AFTER this box has pushed, so the
# Mac picks up the drained ChromaDB + merged memory. Best-effort.
refresh_mac() {
  if ! $MAC_SSH 'true' 2>/dev/null; then
    echo "refresh_mac: Mac unreachable — it self-refreshes on the next run it is awake for."
    return 0
  fi
  echo "refresh_mac: fast-forwarding the Mac to origin/main over SSH"
  local rrc=0
  $MAC_SSH "$MAC_SYNC refresh" 2>&1 || rrc=$?

  # ChromaDB is gitignored since 2026-06-15, so it no longer rides along in git.
  # Linux is its SOLE writer; mirror it to the Mac out-of-band so the Mac's
  # read-replica recall stays current. Safe here: refresh_mac runs after
  # process-sessions (step 3), so Linux's store is quiescent. Best-effort.
  local CDB="03-rai/semantic-memory/chromadb"
  if [ -d "$HELM/$CDB" ]; then
    if rsync -a --delete -e "ssh -o BatchMode=yes -o ConnectTimeout=15" \
         "$HELM/$CDB/" "mac:helm/$CDB/" 2>&1; then
      echo "refresh_mac: ChromaDB mirrored to Mac via rsync"
    else
      echo "refresh_mac: WARN — ChromaDB rsync to Mac failed (Mac keeps prior copy)"
    fi
  fi

  # The Mac can't fetch GitHub (keychain), so its origin/main ref would freeze and
  # `git status` on the Mac would show a bogus, ever-growing "ahead of origin".
  # Propagate THIS box's real origin SHA so the Mac's view of GitHub stays honest.
  local osha; osha=$(git -C "$HELM" rev-parse origin/main 2>/dev/null)
  [ -n "$osha" ] && $MAC_SSH "git -C ~/helm update-ref refs/remotes/origin/main $osha" 2>/dev/null || true

  # VERIFY the refresh actually LANDED — don't trust the exit code alone. The Mac
  # pulls THIS box's main over SSH, so a landed refresh leaves Mac HEAD == this
  # box's HEAD. Comparing against local HEAD (not origin/main) is the right
  # invariant in SYNC_ONLY too, where origin hasn't been pushed yet. A silent miss
  # (the untracked-collision abort, 2026-06-14) left the Mac stale for days while
  # every run logged rc=0; surface it loudly so it can never be invisible again.
  local lhead mhead
  lhead=$(git -C "$HELM" rev-parse HEAD 2>/dev/null)
  mhead=$($MAC_SSH "git -C ~/helm rev-parse HEAD" 2>/dev/null)
  if [ -n "$lhead" ] && [ "$mhead" = "$lhead" ]; then
    echo "refresh_mac: Mac is current @ ${mhead:0:10}"
    return 0
  fi
  echo "refresh_mac: WARN — Mac did NOT reach this box's HEAD (Mac=${mhead:0:10}, linux=${lhead:0:10}, mac-sync rc=$rrc). Mac is STALE; self-heals on wake/next run."
  notify-send -a rai-maintenance -u normal "Rai sync: Mac STALE" "refresh_mac did not land (rc=$rrc) — Mac ${mhead:0:10} != linux ${lhead:0:10} — see $LOG" 2>/dev/null || true
  return 1
}

# Ensure the Mac git remote exists (idempotent; first install or fresh clone).
git -C "$HELM" remote get-url "$MAC_REMOTE" >/dev/null 2>&1 || {
  echo "setup: adding git remote $MAC_REMOTE -> mac:helm"
  git -C "$HELM" remote add "$MAC_REMOTE" mac:helm
}

# ── Step 0 — origin defence/transition pull ────────────────────────────────────
self_heal_git_state
resolve_untracked_collisions || echo "WARN: fetch failed — attempting pull anyway."
if ! do_pull; then
  echo "pull failed — re-running self-heal + collision pass, then one retry."
  self_heal_git_state
  resolve_untracked_collisions || true
  if ! do_pull; then
    echo "ERROR: origin ff-only pull failed twice, needs a human. Aborting run."
    write_abort_status "origin pull failed twice (auth, network or a diverged origin)"
    notify-send -a rai-maintenance -u critical "Rai maintenance FAILED" "origin ff-only pull failed twice, see $LOG" 2>/dev/null || true
    exit 1
  fi
fi
if ! heal_autostash_conflicts; then
  echo "ERROR: unmerged files remain — refusing to run steps on a conflicted tree."
  write_abort_status "unmerged files remain after autostash healing"
  notify-send -a rai-maintenance -u critical "Rai maintenance FAILED" "autostash conflicts unresolved — see $LOG" 2>/dev/null || true
  exit 1
fi

drop_stale_autostashes   # tidy orphaned rebase autostashes (git clutter, not records)

# ── Step 1 — capture the Mac's churn over SSH ──────────────────────────────────
capture_mac || true

# SYNC_ONLY — fast plumbing check: refresh the Mac (to current origin) and stop
# before the expensive claude steps. Leaves any merged churn uncommitted for the
# next real run.
if [ "${SYNC_ONLY:-0}" = "1" ]; then
  refresh_mac; RC5=$?
  echo "════════ $(date '+%F %T') END (SYNC_ONLY) rc5=$RC5 ════════"
  exit "$RC5"
fi

# run_step NAME CAP_MINUTES PROMPT [allowedTools...]
run_step() {
  local name="$1" cap_min="$2" prompt="$3"; shift 3
  echo "──── STEP $name start $(date '+%T') (cap ${cap_min}m) ────"
  ( cd "$HELM" && timeout --kill-after=30 "${cap_min}m" "$CLAUDE" -p "$prompt" --allowedTools "$@" )
  local rc=$?
  [ "$rc" -eq 124 ] && echo "STEP $name TIMED OUT after ${cap_min}m."
  echo "──── STEP $name end $(date '+%T') rc=$rc ────"
  return $rc
}

# ── Step 2 — fold collision backups back into the vault ────────────────────────
RC0=0
if [ -n "$(find "$COLLISION_ROOT" -type f 2>/dev/null | head -c1)" ]; then
  P0="Collision backups live under $COLLISION_ROOT/<timestamp>/<repo-relative-path> — files the vault sync set aside instead of clobbering. For each backed-up file: read it and the corresponding live file at ~/helm/<repo-relative-path>. If the backup contains content the live file lacks, merge it in — append-only logs (memory .md / .jsonl) get the union of entries in time order; state/config files keep the more complete or newer version. Strip any git conflict markers (<<<<<<< / ======= / >>>>>>>) — keep both sides' content, never the markers. If the live file already covers the backup, change nothing. Then delete the processed backup file and remove empty directories under $COLLISION_ROOT. Fully unattended — never ask for confirmation."
  run_step "merge-collisions" 15 "$P0" \
    "Read" "Write" "Edit" "Glob" "Grep" \
    "Bash(ls *)" "Bash(find *)" "Bash(diff *)" "Bash(cmp *)" "Bash(rm *)" "Bash(rmdir *)"
  RC0=$?
  [ "$RC0" -ne 0 ] && echo "WARN: merge-collisions rc=$RC0 — backups left in place for next run."
fi

# ── Step 2.7 — scan native Claude transcripts into pending (the batch scanner) ──
# Deterministic, no AI. The scanner is the only capture path: every session reaches
# pending/ through this step (4 runs a day) or through capture_mac on the Mac.
echo "──── STEP sync-claude-sessions start $(date '+%T') ────"
timeout --kill-after=30 10m python3 "$HELM/03-rai/hooks/scripts/sync_claude_sessions.py" 2>&1
RCS2=$?
echo "──── STEP sync-claude-sessions end $(date '+%T') rc=$RCS2 ────"

# ── Step 3 — drain pending sessions (this box is the sole ChromaDB writer) ─────
P1="Read ~/helm/03-rai/skills/rai/process-sessions.md and execute it exactly as written, fully unattended — never ask for confirmation. If there are no pending sessions, say so and stop. CRITICAL (headless claude -p): you MUST run the drain IN-TURN and wait for it to finish — never launch it with run_in_background or shell '&'. When your turn ends this process is reaped and every background child dies with it (this exact bug silently killed the drain for weeks). If it is long, poll in-turn until DONE."
run_step "process-sessions" 30 "$P1" \
  "Bash(~/helm/03-rai/semantic-memory/scripts/py-chroma.sh *)" \
  "Bash(python3 *)" "Bash(ls *)" "Bash(mv *)" "Bash(grep *)" "Bash(wc *)" \
  "Read" "Write" "Edit" "Glob" "Grep"
RC1=$?
[ "$RC1" -ne 0 ] && echo "WARN: process-sessions rc=$RC1 — continuing to commit step anyway."

# ── Step 3.2 — weekly self-evolve curation ("dreaming", Sundays) ───────────────
# Deterministic merge/decay/promote over learned-candidates.jsonl + re-renders
# learned.md and identity/learned.md. See MEMORY-ARCHITECTURE.md (self-evolve).
# Once per ISO week: the first Sunday cycle that exits 0 writes the week to the stamp,
# and the later Sunday cycles skip.
CURATE_STAMP="$STATE/curate-week"
CURATE_WEEK=$(date +%G-W%V)
if [ "$(date +%u)" = "7" ]; then
  if [ "$(cat "$CURATE_STAMP" 2>/dev/null)" = "$CURATE_WEEK" ]; then
    echo "curate-candidates: already ran for $CURATE_WEEK, skipping."
  else
    echo "──── STEP curate-candidates start $(date '+%T') ────"
    timeout --kill-after=30 10m bash "$HELM/03-rai/semantic-memory/scripts/py-chroma.sh" \
      "$HELM/03-rai/hooks/scripts/curate_candidates.py" 2>&1
    RCC=$?
    echo "──── STEP curate-candidates end $(date '+%T') rc=$RCC ────"
    [ "$RCC" -eq 0 ] && echo "$CURATE_WEEK" > "$CURATE_STAMP"
  fi
fi

# ── Step 3.5 — certify the brain (producer self-check) ─────────────────────────
# Runs the full /sanity harness right after the pipeline, in PRODUCER role, and writes
# sanity-last.json INTO the repo so the next commit (step 4) ships it to origin and refresh_mac
# (step 5) lands it on the Mac — where session-start surfaces a banner on any non-HEALTHY verdict.
# This is the cure for "the brain was sick for 3 months and nobody knew": every cycle self-certifies
# and the alarm reaches the Mac you actually look at. Exit code 0=HEALTHY 1=DEGRADED 2=BROKEN.
echo "──── STEP sanity start $(date '+%T') ────"
SANITY_LOG="$STATE/logs/$(date +%Y-%m-%d-%H%M)-sanity.txt"
timeout --kill-after=30 5m bash "$HELM/03-rai/semantic-memory/scripts/py-chroma.sh" \
  "$HELM/03-rai/skills/rai/scripts/sanity.py" --write-status >"$SANITY_LOG" 2>&1
RCS=$?
echo "──── STEP sanity end $(date '+%T') verdict-rc=$RCS (0=HEALTHY 1=DEGRADED 2=BROKEN; 124=timeout) ────"
if [ "$RCS" -ge 1 ]; then
  VERD=$([ "$RCS" -eq 2 ] && echo BROKEN || { [ "$RCS" -eq 124 ] && echo "TIMED-OUT" || echo DEGRADED; })
  echo "════════ ⚠️ BRAIN SANITY $VERD (rc=$RCS) — see $SANITY_LOG + sanity-last.json ════════"
  # Urgency matches severity. `critical` never auto-expires in the notification daemon, so a
  # DEGRADED popup every cycle stacks on the desktop until dismissed by hand and trains you to
  # ignore the one that matters. BROKEN / TIMED-OUT stay sticky; DEGRADED expires on its own.
  URG=critical; [ "$RCS" -eq 1 ] && URG=normal
  notify-send -a rai-maintenance -u "$URG" "Rai brain sanity: $VERD" "Post-maintenance sanity rc=$RCS — see $SANITY_LOG" 2>/dev/null || true
fi

# ── Step 4 — commit + push (sole writer to origin) ─────────────────────────────
P2="Read ~/helm/03-rai/skills/git/commit.md and execute it on ~/helm exactly as written: group the working-tree changes into logical commits, stage files explicitly, commit, then run git fetch origin; if the branch is not behind origin, push directly (never pull --rebase at behind=0); only if it is behind, follow commit.md step 4. Fully unattended — never ask for confirmation. If the tree is clean but the branch is ahead of origin, still push, same rule. If the tree is clean and nothing is ahead, say so and stop. SELF-EVOLVE VISIBILITY: first run 'git diff -- 03-rai/semantic-memory/promotions.log'; if it shows added lines, quote each added PROMOTED line verbatim in the body of the commit that includes that file — John reads promotions from commit messages."
run_step "git-commit" 30 "$P2" \
  "Bash(git *)" "Read" "Glob" "Grep"
RC2=$?

# ── Step 5 — fast-forward the Mac to the freshly-pushed origin ─────────────────
refresh_mac; RC5=$?

echo "════════ $(date '+%F %T') END rc0=$RC0 rc1=$RC1 rc2=$RC2 rc5=$RC5 ════════"
[ "$RC5" -ne 0 ] && echo "════════ NOTE: Mac is STALE (refresh_mac rc=$RC5) — see WARN above ════════"

# Honest exit status for systemd (fixed 2026-08-03). The bare `[ ] && echo` above
# used to be the script's last command, so every HEALTHY run (RC5=0 → test false)
# exited 1 and `systemctl --user status rai-maintenance` read `failed` forever —
# which meant a real failure was indistinguishable from success.
# Fail the unit only on the merge-collisions fold (RC0) and the commit+push (RC2).
# A failed origin pull already exited 1 at step 0. process-sessions (RC1) and a
# stale Mac (RC5) are logged above and do not fail the unit; the sanity verdict
# has its own notification.
if [ "$RC0" -ne 0 ] || [ "$RC2" -ne 0 ]; then
  echo "════════ EXIT 1 — pipeline failure (rc0=$RC0 rc2=$RC2) ════════"
  exit 1
fi
exit 0
