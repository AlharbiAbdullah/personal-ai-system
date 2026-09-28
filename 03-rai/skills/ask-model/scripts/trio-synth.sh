#!/usr/bin/env bash
# /ask-model trio-synth — three-model collaborative writing.
#
# Stage 1: Gemini + GPT each draft independently (parallel).
# Stage 2: Claude synthesizes ONE final version from both drafts.
# Output: a single final version, plus the two intermediate drafts for audit.
#
# Usage:
#   trio-synth.sh <task> <prompt-file> [system-file]
#
# task:        write | translate | freeform (anything supported by call.sh)
# prompt-file: path to the user-prompt file. Should include:
#                - CONTEXT block (audience, purpose, current state)
#                - TASK block (what to draft, constraints)
# system-file: optional prelude file (with INCLUDE: directives if needed)
#
# Output to stdout:
#   - DRAFT A (Gemini)
#   - DRAFT B (GPT)
#   - FINAL (Claude synthesis)
#
# Synthesis prompt is built inline by this script.

set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "usage: trio-synth.sh <task> <prompt-file> [system-file]" >&2
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
SYNTH_PROMPT="$TMP_DIR/synth-prompt.txt"
CLAUDE_OUT="$TMP_DIR/claude.txt"

# ============================================================
# Stage 1: parallel drafts
# ============================================================
echo "[trio-synth] stage 1: drafting in parallel (gemini + gpt)..." >&2

( "$CALL" gemini "$TASK" "$PROMPT_FILE" "$SYSTEM_FILE" > "$GEMINI_OUT" ) &
GEMINI_PID=$!
( "$CALL" gpt    "$TASK" "$PROMPT_FILE" "$SYSTEM_FILE" > "$GPT_OUT" ) &
GPT_PID=$!

wait $GEMINI_PID || { echo "[trio-synth] gemini failed" >&2; exit 4; }
wait $GPT_PID    || { echo "[trio-synth] gpt failed"    >&2; exit 4; }

# ============================================================
# Stage 2: build synthesis prompt, then Claude synthesizes
# ============================================================
echo "[trio-synth] stage 2: synthesizing via claude..." >&2

ORIGINAL_PROMPT=$(cat "$PROMPT_FILE")
GEMINI_DRAFT=$(cat "$GEMINI_OUT")
GPT_DRAFT=$(cat "$GPT_OUT")

cat > "$SYNTH_PROMPT" <<EOF
You are the synthesizer. Two other models drafted Arabic prose for the SAME task using the SAME context and rules. Your job: read both drafts, pick the strongest moves from each, and produce ONE final version that beats either draft on its own.

# ORIGINAL TASK (what was asked of both drafters)

$ORIGINAL_PROMPT

# DRAFT A — Gemini 3.1 Pro Preview

$GEMINI_DRAFT

# DRAFT B — GPT-5.5

$GPT_DRAFT

# SYNTHESIS GUIDELINES

1. **Strongest opening wins.** Whichever draft opens with the cleanest, most Lumen-style first sentence — use that opening (or adapt it lightly).
2. **Strongest middle wins.** Whichever draft has the most concrete, rhythmic, dictionary-compliant body — use that argument.
3. **Strongest close wins.** Whichever draft lands the close best — keep that close.
4. **Where they agree, lock it in.** If both drafts use a phrase, that phrase is settled.
5. **Where they disagree, pick the more Lumen-like.** Refer to the corpus anchors in your system prompt — match cadence, sentence length, register, density of concrete language.
6. **Fix issues that exist in BOTH.** If both drafts share the same voice problem (e.g., stiff opening, missing الـ, wrong dictionary call), your synthesis fixes it.
7. **Don't be a copy-machine.** If the strongest version of a line requires a small rewrite that neither model produced, do it.
8. **Preserve formatting markup.** \`<strong>\`, \`<highlight>\`, \`«word»\`, and \`الـ\` rules from the system prompt — apply rigorously.

# OUTPUT

Output ONE final version only. Arabic prose ready to ship. No meta-commentary, no headers like "FINAL VERSION:", no notes about which draft you borrowed from. Just the prose.

If the original task asked for JSON output, output JSON. If it asked for plain prose, output plain prose. Match the format the original task specified.
EOF

"$CALL" claude "${TASK}-synth" "$SYNTH_PROMPT" "$SYSTEM_FILE" > "$CLAUDE_OUT" || {
  echo "[trio-synth] claude synthesis failed" >&2
  exit 4
}

# ============================================================
# Output
# ============================================================
printf '\n========== DRAFT A — GEMINI 3.1 PRO PREVIEW ==========\n'
cat "$GEMINI_OUT"
printf '\n\n========== DRAFT B — GPT-5.5 ==========\n'
cat "$GPT_OUT"
printf '\n\n========== FINAL — CLAUDE OPUS 4.7 SYNTHESIS ==========\n'
cat "$CLAUDE_OUT"
printf '\n'
