#!/usr/bin/env bash
# /ask-model — single-shot OpenRouter call.
#
# Usage:
#   call.sh <model-alias> <task> <prompt-file> [system-file]
#
# model-alias: gemini | gpt | sol | grok | claude | glm | deepseek
# task:        write | translate | judge | critique | summarize | freeform
# prompt-file: path to a file containing the user prompt (the actual content/task)
# system-file: optional path to a file containing the system prompt
#
# Env:
#   OPENROUTER_API_KEY  required
#   REASONING_EFFORT    optional: low | medium | high (models that support it)
#   ASK_MODEL_TIMEOUT   optional: seconds before the call gives up (default 540, under the
#                       10-minute limit of one agent Bash call); a hung model exits 5
#
# Output: prints the model's response to stdout.

set -euo pipefail

if [[ $# -lt 3 ]]; then
  echo "usage: call.sh <gemini|gpt> <task> <prompt-file> [system-file]" >&2
  exit 2
fi

ALIAS="$1"
TASK="$2"
PROMPT_FILE="$3"
SYSTEM_FILE="${4:-}"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "error: OPENROUTER_API_KEY env var not set" >&2
  echo "       export it in ~/.zshrc or pass via env, then retry" >&2
  exit 3
fi

case "$ALIAS" in
  gemini) MODEL="google/gemini-3.1-pro-preview" ;;
  gpt)    MODEL="openai/gpt-5.5" ;;
  sol)    MODEL="openai/gpt-5.6-sol" ;;
  grok)   MODEL="x-ai/grok-4.5" ;;
  claude) MODEL="anthropic/claude-opus-4.7" ;;
  glm)      MODEL="z-ai/glm-5.2" ;;
  deepseek) MODEL="deepseek/deepseek-v4-pro" ;;
  *)
    echo "error: unknown model alias '$ALIAS'. expected: gemini | gpt | sol | grok | claude | glm | deepseek" >&2
    exit 2
    ;;
esac

[[ -f "$PROMPT_FILE" ]] || { echo "error: prompt file not found: $PROMPT_FILE" >&2; exit 2; }
PROMPT=$(cat "$PROMPT_FILE")

SYSTEM=""
if [[ -n "$SYSTEM_FILE" && -f "$SYSTEM_FILE" ]]; then
  # Preprocess INCLUDE: directives. Any line `INCLUDE: <path>` (tilde-expanded)
  # is replaced with the file's contents, wrapped in a section header.
  # Loops to a fixed point so an included file can itself contain INCLUDEs
  # (e.g. a CORPUS.md that includes a glob of sample files).
  SYSTEM=$(cat "$SYSTEM_FILE")
  for _ in 1 2 3 4 5; do
    grep -q '^INCLUDE: ' <<<"$SYSTEM" || break
    SYSTEM=$(printf '%s\n' "$SYSTEM" | awk '
      /^INCLUDE: / {
        path = $0
        sub(/^INCLUDE: /, "", path)
        gsub(/^~/, ENVIRON["HOME"], path)
        printf "\n=== INCLUDED FROM: %s ===\n", path
        while ((getline line < path) > 0) print line
        close(path)
        printf "=== END INCLUDE ===\n\n"
        next
      }
      { print }
    ')
  done
fi

# Build messages JSON via jq (avoids quoting hell).
if [[ -n "$SYSTEM" ]]; then
  MESSAGES=$(jq -n --arg sys "$SYSTEM" --arg user "$PROMPT" \
    '[{role:"system",content:$sys},{role:"user",content:$user}]')
else
  MESSAGES=$(jq -n --arg user "$PROMPT" \
    '[{role:"user",content:$user}]')
fi

PAYLOAD=$(jq -n --arg model "$MODEL" --argjson messages "$MESSAGES" \
  '{model:$model, messages:$messages, max_tokens:32000, usage:{include:true}}')

if [[ -n "${REASONING_EFFORT:-}" ]]; then
  PAYLOAD=$(jq --arg effort "$REASONING_EFFORT" '. + {reasoning:{effort:$effort}}' <<<"$PAYLOAD")
fi

STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

LIMIT="${ASK_MODEL_TIMEOUT:-540}"
if ! RESPONSE=$(curl -sS --connect-timeout 30 --max-time "$LIMIT" \
  https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -H "Content-Type: application/json" \
  -H "HTTP-Referer: https://johndoe.dev" \
  -H "X-Title: Rai / ask-model" \
  -d "$PAYLOAD"); then
  echo "error: $ALIAS ($MODEL) gave no answer within ${LIMIT}s, or the request failed" >&2
  exit 5
fi

ERR=$(jq -r '.error.message // empty' <<<"$RESPONSE")
if [[ -n "$ERR" ]]; then
  echo "error from OpenRouter: $ERR" >&2
  exit 4
fi

CONTENT=$(jq -r '.choices[0].message.content // ""' <<<"$RESPONSE")

printf '%s\n' "$CONTENT"
