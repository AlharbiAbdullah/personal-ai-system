#!/usr/bin/env bash
# /fusion panel fan-out — send ONE prompt to the four OpenRouter panel models
# (sol, grok, glm, deepseek) in parallel at high reasoning effort, print four
# labeled outputs. Claude's voice is added separately by the running session
# (the coordinator), not here.
#
# Usage:
#   fusion.sh <prompt-file> [system-file]
#
# system-file defaults to the fusion panel prelude.
#
# Env:
#   OPENROUTER_API_KEY  required (consumed by call.sh)
#
# Output: four labeled sections on stdout.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: fusion.sh <prompt-file> [system-file]" >&2
  exit 2
fi

PROMPT_FILE="$1"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEM_FILE="${2:-$SCRIPT_DIR/../references/fusion-prelude.md}"

# Reuse ask-model's single-source call.sh (model aliases live there).
CALL="$HOME/helm/03-rai/skills/ask-model/scripts/call.sh"
[[ -x "$CALL" || -f "$CALL" ]] || { echo "error: call.sh not found at $CALL" >&2; exit 2; }
[[ -f "$PROMPT_FILE" ]] || { echo "error: prompt file not found: $PROMPT_FILE" >&2; exit 2; }

PANEL=(sol grok glm deepseek)
declare -A LABELS=([sol]="GPT-5.6 SOL" [grok]="GROK 4.5" [glm]="GLM 5.2" [deepseek]="DEEPSEEK V4 PRO")

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

pids=()
for alias in "${PANEL[@]}"; do
  ( REASONING_EFFORT=high "$CALL" "$alias" freeform "$PROMPT_FILE" "$SYSTEM_FILE" > "$TMP_DIR/$alias.txt" 2>"$TMP_DIR/$alias.err" ) &
  pids+=($!)
done

for pid in "${pids[@]}"; do
  wait "$pid" || true
done

for alias in "${PANEL[@]}"; do
  printf '\n========== %s ==========\n' "${LABELS[$alias]}"
  if [[ -s "$TMP_DIR/$alias.txt" ]]; then
    cat "$TMP_DIR/$alias.txt"
  else
    printf '[no response — model call failed]\n'
    [[ -s "$TMP_DIR/$alias.err" ]] && sed 's/^/  /' "$TMP_DIR/$alias.err"
  fi
done
printf '\n'
