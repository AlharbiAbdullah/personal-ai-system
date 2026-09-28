#!/usr/bin/env bash
# Personal AI System — one-shot wiring into Claude Code.
#
# Links the brain in 03-rai/ into ~/.claude (CLAUDE.md, hooks, skills, agents,
# settings), backing up anything it would replace.
# Safe to re-run: already-correct links are left alone; only real files/dirs or
# wrong links get moved to a timestamped backup first.
#
#   ./setup.sh            # wire it up
#   ./setup.sh --check    # verify an existing setup without changing anything
#
set -euo pipefail

# ── Resolve the vault root = the directory this script lives in ────────────────
# (works even if the repo was cloned somewhere other than ~/helm)
SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do
  DIR="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"
  SOURCE="$(readlink "$SOURCE")"
  [ "${SOURCE#/}" = "$SOURCE" ] && SOURCE="$DIR/$SOURCE"
done
VAULT="$(cd -P "$(dirname "$SOURCE")" >/dev/null 2>&1 && pwd)"

CLAUDE_DIR="$HOME/.claude"
CHECK_ONLY="${1:-}"

green() { printf '  \033[32m✓\033[0m %s\n' "$1"; }
yellow(){ printf '  \033[33m!\033[0m %s\n' "$1"; }
red()   { printf '  \033[31m✗\033[0m %s\n' "$1"; }

# source-under-03-rai  →  name-under-~/.claude
LINKS=(
  "03-rai/AGENTS.md|CLAUDE.md"
  "03-rai/hooks|hooks"
  "03-rai/skills|skills"
  "03-rai/agents|agents"
  "03-rai/config/settings.json|settings.json"
)

echo "Personal AI System — setup"
echo "  vault : $VAULT"
echo "  target: $CLAUDE_DIR"
echo

# ── Sanity: is this actually the vault? ────────────────────────────────────────
if [ ! -d "$VAULT/03-rai" ]; then
  red "no 03-rai/ next to this script — is setup.sh in the repo root?"
  exit 1
fi

# settings.json hardcodes \$HOME/helm in its hook commands; warn if we're elsewhere.
if [ "$VAULT" != "$HOME/helm" ]; then
  yellow "vault is not ~/helm. The .claude links below will point here correctly,"
  yellow "but hook commands inside 03-rai/config/settings.json use \$HOME/helm —"
  yellow "either clone to ~/helm, or edit those paths by hand. See SETUP.md §1."
  echo
fi

# ── --check mode: report link state, change nothing ───────────────────────────
if [ "$CHECK_ONLY" = "--check" ]; then
  echo "Checking links (read-only):"
  ok=1
  for pair in "${LINKS[@]}"; do
    src="$VAULT/${pair%%|*}"; tgt="$CLAUDE_DIR/${pair##*|}"
    if [ -L "$tgt" ] && [ "$(readlink "$tgt")" = "$src" ]; then
      green "${pair##*|} → $src"
    else
      red "${pair##*|} not linked to $src"; ok=0
    fi
  done
  [ "$ok" = 1 ] && { echo; green "all links correct"; } || { echo; yellow "run ./setup.sh to fix"; exit 1; }
  exit 0
fi

# ── Wire it up ────────────────────────────────────────────────────────────────
mkdir -p "$CLAUDE_DIR"
BACKUP="$CLAUDE_DIR/.pai-backup-$(date +%Y%m%d-%H%M%S)"
backed_up=0

for pair in "${LINKS[@]}"; do
  src="$VAULT/${pair%%|*}"; name="${pair##*|}"; tgt="$CLAUDE_DIR/$name"

  if [ ! -e "$src" ]; then
    red "missing source: $src (skipped)"; continue
  fi
  # Already correct? leave it.
  if [ -L "$tgt" ] && [ "$(readlink "$tgt")" = "$src" ]; then
    green "$name (already linked)"; continue
  fi
  # Something else is there — back it up before replacing.
  if [ -e "$tgt" ] || [ -L "$tgt" ]; then
    mkdir -p "$BACKUP"; mv "$tgt" "$BACKUP/$name"; backed_up=1
    yellow "$name existed → backed up"
  fi
  ln -sfn "$src" "$tgt"
  green "$name → $src"
done

[ "$backed_up" = 1 ] && { echo; yellow "previous entries saved in $BACKUP"; }

# ── Verify ────────────────────────────────────────────────────────────────────
echo
echo "Verifying:"
if python3 "$VAULT/03-rai/hooks/session-start.py" >/dev/null 2>&1; then
  green "hooks run (session-start.py OK)"
else
  red "session-start.py errored — run it directly to see why:"
  red "    python3 $VAULT/03-rai/hooks/session-start.py"
fi

if command -v uv >/dev/null 2>&1; then
  if uv run --python 3.12 --with chromadb python3 -c "import chromadb" >/dev/null 2>&1; then
    green "chromadb reachable via uv (vector memory ready)"
  else
    yellow "uv present but chromadb check failed — vector recall will be skipped"
  fi
else
  yellow "uv not installed — vector memory is optional; see SETUP.md prerequisites"
fi

echo
green "Done. Next: fill in the templates in 02-ana/identity/, then run 'claude' from $VAULT."
echo "       Optional feature deps: pip install -r requirements.txt"
