#!/usr/bin/env bash
# /ask-model trio compare — call gemini, gpt, AND claude for the same task
# in parallel, print three labeled outputs side-by-side.
#
# Usage:
#   compare.sh <task> <prompt-file> [system-file]

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: compare.sh <task> <prompt-file> [system-file]" >&2
  exit 2
fi

TASK="$1"
PROMPT_FILE="$2"
SYSTEM_FILE="${3:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CALL="$SCRIPT_DIR/call.sh"

TMP_DIR=$(mktemp -d)
trap 'rm -rf "$TMP_DIR"' EXIT

GEMINI_OUT="$TMP_DIR/gemini.txt"
GPT_OUT="$TMP_DIR/gpt.txt"
CLAUDE_OUT="$TMP_DIR/claude.txt"

# Run all three in parallel.
( "$CALL" gemini "$TASK" "$PROMPT_FILE" "$SYSTEM_FILE" > "$GEMINI_OUT" ) &
GEMINI_PID=$!
( "$CALL" gpt    "$TASK" "$PROMPT_FILE" "$SYSTEM_FILE" > "$GPT_OUT" ) &
GPT_PID=$!
( "$CALL" claude "$TASK" "$PROMPT_FILE" "$SYSTEM_FILE" > "$CLAUDE_OUT" ) &
CLAUDE_PID=$!

wait $GEMINI_PID || true
wait $GPT_PID    || true
wait $CLAUDE_PID || true

printf '\n========== GEMINI 3.1 PRO PREVIEW ==========\n'
cat "$GEMINI_OUT"
printf '\n\n========== GPT-5.5 ==========\n'
cat "$GPT_OUT"
printf '\n\n========== CLAUDE OPUS 4.7 ==========\n'
cat "$CLAUDE_OUT"
printf '\n'
