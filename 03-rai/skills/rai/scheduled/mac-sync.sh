#!/bin/bash
# mac-sync.sh — Mac side of the Rai vault sync, DRIVEN BY LINUX over SSH
# SSH. The Mac runs NO scheduler of its own since 2026-06-13 (no launchd job, no
# sleepwatcher, no ~/.wakeup) — it is a passive source + replica. Full design in
# 03-rai/SYNC-ARCHITECTURE.md.
#
# Linux (the sole coordinator and sole writer to origin) invokes this over SSH:
#
#   mac-sync.sh commit    Snapshot the Mac's working-tree churn into ONE local
#                         commit so Linux can `git fetch mac main` it. No push,
#                         no network — pure local snapshot.
#   mac-sync.sh snapshot  commit + push that commit to the coordinator's `mac-inbox`
#                         ref. Driven by the MAC's OWN hourly launchd timer
#                         (com.john.rai.mac-snapshot), added 2026-08-03 when the
#                         Mac became the primary authoring machine: work no longer
#                         waits for the 6-hourly coordinator run to reach a laptop
#                         that may be asleep or away. Still never touches origin —
#                         CI/CD and the origin push stay Linux's job.
#   mac-sync.sh refresh   Bring the Mac up to date AFTER Linux has pushed (drained
#                         ChromaDB + merged memory) by pulling LINUX directly over
#                         keyless SSH (the `linux` remote) — NOT GitHub.
#                         The Mac's GitHub creds live in the macOS Keychain, which
#                         a non-interactive SSH session cannot unlock (err -25308),
#                         so the Mac never touches origin. Live churn is autostashed.
#
# Single-writer model: Linux absorbs the Mac's commit into origin's ancestry, so
# the Mac never truly diverges — refresh is effectively always a fast-forward.
# Conflicts are rare; when an autostash pop hits one, the live disk copy wins
# (hooks rewrite state files constantly, so disk is the freshest truth).

set -uo pipefail
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"   # launchd gives a bare PATH
HELM="$HOME/helm"
REFRESH_REMOTE="linux"   # git remote → linux:helm over keyless SSH (NOT origin/GitHub)
INBOX_REF="mac-inbox"    # side branch on the coordinator; never `main` (checked out there)
cd "$HELM" || { echo "mac-sync: no $HELM"; exit 1; }

# Durable backups for divergent collision casualties (NOT /tmp). In practice
# these are stale hook-written state files; kept so a human can recover if needed.
COLLISION_ROOT="$HOME/.local/state/mac-sync/collisions"
COLLISION_BACKUP="$COLLISION_ROOT/$(date +%Y%m%d-%H%M%S)"
backup_path() {  # backup_path REPO_RELATIVE_PATH
  mkdir -p "$COLLISION_BACKUP/$(dirname "$1")"
  cp "$HELM/$1" "$COLLISION_BACKUP/$1"
}

# Clear a half-finished rebase/merge/cherry-pick left by a killed run, so we
# never snapshot or refresh on top of a conflicted index.
clear_git_state() {
  if [ -d .git/rebase-merge ] || [ -d .git/rebase-apply ]; then
    echo "mac-sync: aborting dead rebase"; git rebase --abort 2>/dev/null || true
  fi
  [ -f .git/MERGE_HEAD ]       && { echo "mac-sync: aborting dead merge";       git merge --abort 2>/dev/null || true; }
  [ -f .git/CHERRY_PICK_HEAD ] && { echo "mac-sync: aborting dead cherry-pick"; git cherry-pick --abort 2>/dev/null || true; }
  return 0
}

# An autostash pop can leave unmerged paths even when the rebase/FF itself
# succeeded. The stashed side IS the live local state, so it wins; delete/modify
# conflicts keep whatever is on disk. Mirrors the proven heal in the coordinator.
heal_autostash_conflicts() {
  local tries=0 p
  while git diff --name-only --diff-filter=U | grep -q .; do
    tries=$((tries+1))
    if [ "$tries" -gt 3 ]; then echo "mac-sync ERROR: unmerged paths survived 3 heal passes"; return 1; fi
    echo "mac-sync: conflicted autostash pop — resolving (pass $tries, disk side wins)"
    while IFS= read -r p; do
      [ -z "$p" ] && continue
      git checkout --theirs -- "$p" 2>/dev/null || true   # delete/modify: keep disk copy
      git add -A -- "$p" 2>/dev/null || true              # index.lock race → next pass
    done < <(git diff --name-only --diff-filter=U)
    sleep 2
  done
  if [ "$tries" -gt 0 ] && git stash list | head -1 | grep -q ': autostash$'; then
    echo "mac-sync: dropping conflicted autostash entry (content resolved into tree)"
    git stash drop 'stash@{0}' 2>/dev/null || true
  fi
  return 0
}

# Drop orphaned autostash entries (>1h) left by aborted pulls — git temp-state,
# not records (content already applied). Named/manual stashes are always kept.
drop_stale_autostashes() {
  local cutoff=$(( $(date +%s) - 3600 )) sel n=0
  for _ in $(seq 1 100); do
    sel=$(git stash list --format='%gd %ct %gs' | awk -v c="$cutoff" '$3=="autostash" && $2<c {print $1; exit}')
    [ -z "$sel" ] && break
    git stash drop "$sel" >/dev/null 2>&1 && n=$((n+1)) || break
  done
  [ "$n" -gt 0 ] && echo "mac-sync: dropped $n orphaned autostash entries"
}

# An incoming tracked path can exist locally as an UNTRACKED file — a hook rewrites
# state files (e.g. 03-rai/memory/state/current-work.json) without git's knowledge.
# git refuses to clobber it on merge ("untracked working tree files would be
# overwritten") and --autostash only stashes TRACKED changes, so the refresh
# aborts and the Mac silently falls 10+ commits behind (2026-06-14 jam). Drop
# identical colliders; back up + drop divergent ones — disk is stale local churn,
# Linux's tracked copy is authoritative. Ports the coordinator's healer.
resolve_untracked_collisions() {
  local ref="${1:-$REFRESH_REMOTE/main}" p
  git fetch "$REFRESH_REMOTE" main || return 1
  while IFS= read -r p; do
    [ -e "$HELM/$p" ] || continue
    git ls-files --error-unmatch "$p" >/dev/null 2>&1 && continue   # tracked → autostash handles it
    if git show "$ref:$p" 2>/dev/null | cmp -s - "$HELM/$p"; then
      rm -f "$HELM/$p"
      echo "mac-sync: collision (identical) — dropped local untracked $p"
    else
      backup_path "$p" && rm -f "$HELM/$p"
      echo "mac-sync: collision (divergent) — backed up local untracked $p -> $COLLISION_BACKUP/$p"
    fi
  done < <(git diff --name-only HEAD "$ref")
}

# Push HEAD to the coordinator's side ref so the Mac's work is off this laptop even
# when it is asleep or away at 04/10/16/22. `main` is checked out on the coordinator,
# so pushing there is refused — hence a dedicated ref it merges from. Only the Mac
# ever writes this ref, so a --force retry (needed after a history rewrite) is safe.
push_inbox() {
  if git push -q "$REFRESH_REMOTE" "HEAD:refs/heads/$INBOX_REF" 2>/dev/null; then
    echo "mac-sync: pushed $(git rev-parse --short HEAD) → $REFRESH_REMOTE/$INBOX_REF"
  elif git push -q --force "$REFRESH_REMOTE" "HEAD:refs/heads/$INBOX_REF" 2>/dev/null; then
    echo "mac-sync: force-pushed $(git rev-parse --short HEAD) → $REFRESH_REMOTE/$INBOX_REF (ref had diverged)"
  else
    echo "mac-sync: WARN — push to $REFRESH_REMOTE/$INBOX_REF failed (coordinator offline?); next run retries"
    return 1
  fi
}

case "${1:-}" in
  snapshot)
    # The Mac's own hourly timer: local snapshot, then hand it to the coordinator.
    "$0" commit || true
    push_inbox
    ;;

  commit)
    clear_git_state
    git add -A
    # ChromaDB is gitignored (2026-06-15) — authored only on Linux (sole writer),
    # so the Mac's read-induced binary drift never enters git. Nothing to unstage.
    if git diff --cached --quiet; then
      echo "mac-sync: nothing to commit (tree clean) @ $(git rev-parse --short HEAD)"
    else
      git commit -q -m "wip(mac): churn snapshot $(date '+%F %T %z')" \
        && echo "mac-sync: committed churn snapshot @ $(git rev-parse --short HEAD)"
    fi
    ;;

  refresh)
    clear_git_state
    # ChromaDB is gitignored (2026-06-15): no longer pulled via git. The coordinator
    # mirrors Linux's authoritative store to the Mac via rsync in refresh_mac.
    # Drop/back-up untracked files that collide with incoming tracked paths
    # BEFORE the pull — autostash cannot move them out of the way (see above).
    resolve_untracked_collisions
    # Pull LINUX (the coordinator) over SSH, not GitHub. ff-only, NOT
    # --rebase: Linux is the sole writer so the Mac is always a clean ancestor and
    # refresh is always a fast-forward. The rebase form replayed wip(mac) commits
    # and jammed on binary ChromaDB (the chronic 2026-06-14 jam the coordinator
    # already dropped in abc1234); ff-only is a no-op in steady state and fails
    # cleanly on the anomalous diverged case instead of half-rebasing. --autostash
    # because the tree's tracked files are essentially always dirty.
    if ! git pull --ff-only --autostash "$REFRESH_REMOTE" main; then
      echo "mac-sync: ff-only pull from $REFRESH_REMOTE failed — healing and retrying once"
      clear_git_state
      resolve_untracked_collisions
      git pull --ff-only --autostash "$REFRESH_REMOTE" main || true
    fi
    heal_autostash_conflicts || { echo "mac-sync: refresh left unmerged paths — next run retries"; exit 1; }
    drop_stale_autostashes
    # Honest exit contract: succeed (rc 0) ONLY if we actually reached linux/main,
    # so the coordinator's refresh_mac can trust that a nonzero rc means "Mac is
    # stale" instead of logging a false rc=0 over a silently-aborted refresh.
    if [ "$(git rev-parse HEAD)" != "$(git rev-parse "$REFRESH_REMOTE/main")" ]; then
      echo "mac-sync ERROR: refresh did NOT reach $REFRESH_REMOTE/main (HEAD=$(git rev-parse --short HEAD), want $(git rev-parse --short "$REFRESH_REMOTE/main"))"
      exit 1
    fi
    echo "mac-sync: refreshed to $(git rev-parse --short HEAD)"
    ;;

  *)
    echo "usage: mac-sync.sh {snapshot|commit|refresh}"; exit 2;;
esac
