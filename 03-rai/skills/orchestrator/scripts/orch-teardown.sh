#!/usr/bin/env bash
# Guarded teardown of one finished task: tmux session, worktree, branch.
# Usage: orch-teardown.sh <repo> <worktree> <branch> <tmux-session>
# Refuses (exit 1, reason on stdout) when:
#   - the worktree has uncommitted or untracked files
#   - the branch is not fully merged into the repo's current HEAD
#   - the branch has commits not on any remote AND not on HEAD (unpushed work)
#   - the tmux session to kill is the caller's own session
# A refusal is surfaced to John; never work around it.
set -u
REPO=${1:?repo}
WT=${2:?worktree}
BRANCH=${3:?branch}
SESS=${4:?tmux session}

fail() { echo "REFUSED: $1"; exit 1; }

# 1. Self-kill guard (claude-code#29787).
if [ -n "${TMUX:-}" ]; then
  own=$(tmux display-message -p '#S' 2>/dev/null || true)
  [ -n "$own" ] && [ "$own" = "$SESS" ] && fail "target session '$SESS' is our own session"
fi

# 2. Work-preserving guards.
if [ -d "$WT" ]; then
  dirty=$(git -C "$WT" status --porcelain 2>/dev/null)
  [ -n "$dirty" ] && fail "worktree $WT has uncommitted/untracked work:
$dirty"
fi
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  if ! git -C "$REPO" merge-base --is-ancestor "$BRANCH" HEAD; then
    fail "branch $BRANCH is not merged into HEAD"
  fi
fi

# 3. Teardown, most-reversible last.
# "=" asks for this exact name: a bare wk-app-g1 prefix-matches wk-app-g10.
tmux kill-session -t "=$SESS" 2>/dev/null && echo "killed session $SESS" || echo "session $SESS already gone"
if [ -d "$WT" ]; then
  git -C "$REPO" worktree remove "$WT" && echo "removed worktree $WT"
else
  echo "worktree $WT already gone"
fi
git -C "$REPO" worktree prune
if git -C "$REPO" show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git -C "$REPO" branch -d "$BRANCH" && echo "deleted branch $BRANCH"
fi
echo "teardown complete: $SESS / $WT / $BRANCH"
