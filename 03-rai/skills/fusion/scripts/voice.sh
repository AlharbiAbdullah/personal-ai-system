#!/usr/bin/env bash
# /fusion: run ONE panel voice for one round, read-only, in the run's working
# directory. panel.sh launches this in its own tmux window; it is not called by hand.
#
#   voice.sh <run-dir> <round> <voice>
#
# Reads  <run>/r<round>/brief-<voice>.md when it exists (round 2), else brief.md
# Writes <run>/r<round>/<voice>.md (the answer), .err, .secs, .queue, and .exit last
#
# Every voice is cut off from John's own setup: no Rai identity, AGENTS.md,
# memory, skills, extensions, plugins, hooks or MCP tools reach the model, no
# transcript reaches Rai's capture, and no voice can edit a file or run a command.
# Every harness runs inside bwrap: the filesystem is read-only; his home folder,
# /tmp, his runtime folder (cached secrets, sockets) and /var/log are empty; the
# environment is cleared to a short allow list. Only the working directory, the
# harness install and the harness's own login and state come back.
# One exception: agy always loads the working folder's own AGENTS.md and
# GEMINI.md files (it has no switch for them), so in ~/helm its voice sees the
# vault's AGENTS.md. Masking them would blank those files for a voice reviewing them.
#
# Env:
#   FUSION_TIMEOUT  seconds one call may run once it starts (default 1800)
#   FUSION_EFFORT   overrides every voice's effort (for cheap plumbing tests)
#   FUSION_STATE    state root (default ~/.local/state/rai/fusion)

set -uo pipefail

# The Rai harness contract, set for every voice and every harness: RAI_OFF=1
# tells a Rai harness adapter to do nothing, and RAI_HEADLESS=1 tells the Rai
# hooks to capture nothing. The structural guards below hold without them.
export RAI_OFF=1 RAI_HEADLESS=1

RUN="$1"; ROUND="$2"; VOICE="$3"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE="${FUSION_STATE:-$HOME/.local/state/rai/fusion}"
D="$RUN/r$ROUND"
BRIEF="$D/brief-$VOICE.md"
[[ -f "$BRIEF" ]] || BRIEF="$D/brief.md"
OUT="$D/$VOICE.md"
ERR="$D/$VOICE.err"
LIMIT="${FUSION_TIMEOUT:-1800}"
START=$(date +%s)
: > "$ERR"
echo 0 > "$D/$VOICE.queue"

finish() {
  local rc="$1"
  [[ -s "$OUT" ]] || (( rc != 0 )) || rc=1   # an empty answer is a failure
  if (( rc == 124 || rc == 137 )); then echo "timed out after ${LIMIT}s" >> "$ERR"; fi
  echo "$(( $(date +%s) - START ))" > "$D/$VOICE.secs"
  # .exit is written last, in one rename: panel.sh reads it as "done".
  echo "$rc" > "$D/$VOICE.exit.tmp" && mv "$D/$VOICE.exit.tmp" "$D/$VOICE.exit"
  printf '\n[fusion] %s finished: exit %s after %ss\n' "$VOICE" "$rc" "$(cat "$D/$VOICE.secs")"
  exit 0
}

read -r HARNESS MODEL EFFORT < <(awk -v v="$VOICE" '$1 == v { print $2, $3, $4 }' "$HERE/voices.conf")
[[ -n "${HARNESS:-}" ]] || { echo "unknown voice: $VOICE" >> "$ERR"; finish 2; }
[[ -f "$BRIEF" ]] || { echo "missing brief: $BRIEF" >> "$ERR"; finish 2; }
EFFORT="${FUSION_EFFORT:-$EFFORT}"
cd "$(cat "$RUN/cwd")" || { echo "missing working directory" >> "$ERR"; finish 2; }
command -v bwrap >/dev/null || { echo "bwrap is missing: every voice needs it to run read-only" >> "$ERR"; finish 2; }

# The harness binary by its real path, so the jail needs no PATH lookups and
# no mise shim (a shim would read mise config from the hidden home folder).
resolve() {
  local p
  p="$(command -v "$1")" || return 1
  p="$(readlink -f "$p")"
  if [[ "$(basename "$p")" == mise ]]; then p="$(mise which "$1")" || return 1; fi
  echo "$p"
}
BIN="$(resolve "$HARNESS")" || { echo "$HARNESS is not installed" >> "$ERR"; finish 2; }

# JAIL: the bwrap prefix. RW: paths bound back writable (the harness's login and
# state). MASK: paths inside RW hidden again (his history, sessions, transcripts).
# RO: extra paths bound back read-only. BIND: raw bwrap bind arguments. ENV: the
# NAME=value pairs the harness gets, on top of the allow list in jail().
# The cwd is bound first, so no RW path or MASK it contains can be undone by it.
RW=(); MASK=(); RO=(); BIND=(); ENV=()
EMPTY="$STATE/empty"   # an empty file, bound over a masked file
[[ -f "$EMPTY" && ! -s "$EMPTY" ]] || { mkdir -p "$STATE" && : > "$EMPTY"; }
jail() {
  local p kv run_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
  JAIL=(bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --tmpfs "$HOME"
        --tmpfs "$run_dir" --tmpfs /var/log
        --ro-bind "$PWD" "$PWD" --chdir "$PWD"
        --ro-bind "$BIN" "$BIN"
        --ro-bind-try "$HOME/.local/share/mise/installs" "$HOME/.local/share/mise/installs")
  for p in "${RW[@]}"; do JAIL+=(--bind-try "$p" "$p"); done
  for p in "${MASK[@]}"; do
    if [[ -d "$p" ]]; then JAIL+=(--tmpfs "$p"); elif [[ -e "$p" ]]; then JAIL+=(--ro-bind "$EMPTY" "$p"); fi
  done
  for p in "${RO[@]}"; do JAIL+=(--ro-bind-try "$p" "$p"); done
  JAIL+=("${BIND[@]}" --clearenv)
  for p in HOME PATH LANG LC_ALL TERM USER RAI_OFF RAI_HEADLESS; do
    [[ -n "${!p:-}" ]] && JAIL+=(--setenv "$p" "${!p}")
  done
  for kv in "${ENV[@]}"; do JAIL+=(--setenv "${kv%%=*}" "${kv#*=}"); done
  JAIL+=(--)
}

# Ollama Pro runs 3 requests at once. Hold one of 3 slots so a queued call
# never burns its own timeout while it waits. The lock frees when this exits.
# The wait is recorded in .queue; .secs counts the run after the slot.
take_ollama_slot() {
  local i q0 deadline
  q0=$(date +%s); deadline=$(( q0 + LIMIT ))
  mkdir -p "$STATE/locks"
  echo "[fusion] $VOICE waiting for an Ollama slot"
  while (( $(date +%s) < deadline )); do
    for i in 1 2 3; do
      exec 9>"$STATE/locks/ollama-$i.lock"
      if flock -n 9; then
        echo "$(( $(date +%s) - q0 ))" > "$D/$VOICE.queue"
        echo "[fusion] $VOICE took slot $i"
        return 0
      fi
      exec 9>&-
    done
    sleep 3
  done
  echo "no Ollama slot came free within ${LIMIT}s" >> "$ERR"
  finish 3
}

call_agy() {
  # Plan mode does not stop agy's file writing tool, and its user-wide allow
  # list would let some shell commands through. So the jail makes the whole
  # filesystem read-only, and an empty allow list is mounted over his agy
  # settings for this call only. Headless agy aborts with no answer when the
  # model tries a blocked command, so the prompt steers it to its file view tool.
  local tier settings locked conf f note prompt extra=()
  case "$EFFORT" in max|xhigh|high) tier=high ;; *) tier=low ;; esac
  settings="$HOME/.gemini/antigravity-cli/settings.json"
  locked="$RUN/agy-settings.json"   # per run: a parallel run never rewrites it mid-call
  if [[ -f "$settings" ]]; then
    jq '.permissions.allow = [] | .allowNonWorkspaceAccess = false' "$settings" > "$locked.$$"
  else
    echo '{"permissions":{"allow":[]},"allowNonWorkspaceAccess":false}' > "$locked.$$"
  fi
  mv "$locked.$$" "$locked"
  # His global agy customizations live in ~/.gemini: the Rai plugin, hooks,
  # skills and MCP servers in config/, the global rules in GEMINI.md. The voice
  # sees a ~/.gemini holding only agy's own state (antigravity-cli/) and a
  # private copy of config/ with the allow-listed state files, rebuilt each
  # call. Its transcripts and his agy history are hidden behind empty folders.
  conf="$RUN/agy-config"
  rm -rf "$conf" && mkdir -p "$conf"
  for f in .migrated projects; do
    [[ -e "$HOME/.gemini/config/$f" ]] && cp -a "$HOME/.gemini/config/$f" "$conf/"
  done
  # Of agy's own state only the login, its install and its updater state come
  # back. His conversations, their summaries, history and logs stay out. The
  # rest of the folder exists only inside the jail, so what this call writes
  # there is gone after it.
  local cli="$HOME/.gemini/antigravity-cli"
  RW=("$cli/antigravity-oauth-token" "$cli/last_check.timestamp" "$cli/jetski_state.pbtxt")
  MASK=(); RO=("$cli/bin" "$cli/builtin" "$cli/updater" "$cli/installation_id"); ENV=()
  BIND=(--bind "$conf" "$HOME/.gemini/config")
  [[ -f "$settings" ]] && BIND+=(--ro-bind "$locked" "$settings")
  note="Tool note: do not run terminal commands in this session; a blocked command aborts your whole answer. Read files by their path with your file view tool. If the tool returns a file in parts, keep reading until its end."
  if (( $(wc -c < "$BRIEF") <= 100000 )); then
    prompt="$note"$'\n\n'"$(cat "$BRIEF")"
  else
    # agy takes the prompt as a flag value, so a long brief goes by path, in
    # a folder of its own: the round folder holds the round-2 key.
    mkdir -p "$RUN/agy-r$ROUND" && cp "$BRIEF" "$RUN/agy-r$ROUND/brief.md"
    prompt="$note"$'\n\n'"Your full brief is the file $RUN/agy-r$ROUND/brief.md. Read all of it, every part, then answer it exactly as it asks."
    extra=(--add-dir "$RUN/agy-r$ROUND")
    RO+=("$RUN/agy-r$ROUND")
  fi
  jail
  timeout --kill-after=30 "$LIMIT" "${JAIL[@]}" "$BIN" --model "$MODEL-$tier" \
    --mode plan --sandbox "${extra[@]}" "-p=$prompt" 2>> "$ERR" | tee "$OUT"
  RC=${PIPESTATUS[0]}
}

call_opencode() {
  # A config and data dir of the voice's own. His global opencode config
  # pulls in the Rai identity files and his agents; this one holds only the
  # voice's provider, model and effort, and a read-only agent.
  # A private data dir also keeps parallel voices off one SQLite database
  # ("database is locked") and out of his opencode history.
  local oc_home="$STATE/opencode/$VOICE" provider variant=() oc_effort oc_auth
  mkdir -p "$oc_home/config/opencode" "$oc_home/data/opencode"
  RW=("$oc_home" "$HOME/.cache/opencode"); MASK=(); RO=(); BIND=()
  ENV=("XDG_CONFIG_HOME=$oc_home/config" "XDG_DATA_HOME=$oc_home/data"
       OPENCODE_DISABLE_CLAUDE_CODE=1 OPENCODE_DISABLE_EXTERNAL_SKILLS=1
       OPENCODE_DISABLE_PROJECT_CONFIG=1 OPENCODE_DISABLE_AUTOUPDATE=1 OPENCODE_DISABLE_SHARE=1)
  if [[ "$MODEL" == ollama/* ]]; then
    case "$EFFORT" in max|xhigh|high) oc_effort=high ;; medium) oc_effort=medium ;; *) oc_effort=low ;; esac
    provider=$(jq -n --arg model "${MODEL#ollama/}" --arg effort "$oc_effort" '{ ollama: {
      npm: "@ai-sdk/openai-compatible", name: "Ollama",
      options: { baseURL: "http://localhost:11434/v1" },
      models: { ($model): { name: $model, reasoning: true, options: { reasoningEffort: $effort } } } } }')
  else
    # A built-in provider on his subscription (OpenAI through Sign in with
    # ChatGPT): the voice uses his login through a link, so a token refresh
    # lands in his own file, and asks for its effort as a model variant.
    oc_auth="${XDG_DATA_HOME:-$HOME/.local/share}/opencode/auth.json"
    [[ -f "$oc_auth" ]] || { echo "opencode is not signed in: run opencode auth login" >> "$ERR"; RC=2; return; }
    ln -sfn "$oc_auth" "$oc_home/data/opencode/auth.json"
    RW+=("$oc_auth")
    provider='{}'
    variant=(--variant "$EFFORT")
  fi
  jq -n --argjson provider "$provider" '{
    "$schema": "https://opencode.ai/config.json",
    provider: $provider,
    agent: { "fusion-panel": {
      mode: "primary", description: "read-only /fusion panel voice",
      permission: { edit: "deny", bash: "deny", webfetch: "deny", websearch: "deny",
                    codesearch: "deny", task: "deny", skill: "deny", external_directory: "deny" } } }
  }' > "$oc_home/config/opencode/opencode.json"
  jail
  timeout --kill-after=30 "$LIMIT" "${JAIL[@]}" "$BIN" run --pure --agent fusion-panel \
    --format json -m "$MODEL" "${variant[@]}" < "$BRIEF" 2>> "$ERR" > "$D/$VOICE.jsonl"
  RC=$?
  # A stream that does not parse is a failed answer, never a partial one.
  if ! jq -r 'select(.type == "text") | .part.text' "$D/$VOICE.jsonl" > "$OUT" 2>> "$ERR"; then
    (( RC == 0 )) && RC=1
  fi
  jq -r 'select(.type == "error") | tostring' "$D/$VOICE.jsonl" >> "$ERR" 2>/dev/null
  cat "$OUT"
}

call_pi() {
  local a="$HOME/.pi/agent" pa="$RUN/pi-$VOICE" f
  RO=(); BIND=()
  if [[ "$MODEL" == ollama/* ]]; then
    # An Ollama voice needs no login, so it gets an agent dir of its own, like
    # opencode's: copies of his pi settings and model list, per run.
    rm -rf "$pa" && mkdir -p "$pa"
    for f in settings.json models.json models-store.json; do
      [[ -e "$a/$f" ]] && cp -L "$a/$f" "$pa/$f"
    done
    RW=("$pa"); MASK=(); ENV=("PI_CODING_AGENT_DIR=$pa")
  else
    # A voice on his login (ChatGPT through Sign in with ChatGPT) runs on his real
    # agent dir, so a token refresh takes the same lock as his own pi. His
    # transcripts, sessions and other logins stay hidden.
    [[ -f "$a/auth.json" ]] || { echo "pi is not signed in: run pi and /login" >> "$ERR"; RC=2; return; }
    RW=("$a"); ENV=()
    MASK=("$a/rai-transcripts" "$a/sessions" "$a/rai-bridge.log" "$a/antigravity-accounts.json")
    # models.json links into dev-env, which the jail hides: bring its target back.
    [[ -L "$a/models.json" ]] && RO+=("$(readlink -f "$a/models.json")")
  fi
  jail
  timeout --kill-after=30 "$LIMIT" "${JAIL[@]}" "$BIN" -p --no-session --no-extensions \
    --no-skills --no-context-files --no-prompt-templates --no-themes \
    --tools read,grep,find,ls --model "$MODEL" --thinking "$EFFORT" \
    < "$BRIEF" 2>> "$ERR" | tee "$OUT"
  RC=${PIPESTATUS[0]}
}

call_claude() {
  # Project settings only: no user hooks, so no Rai identity injection. No
  # CLAUDE.md or AGENTS.md files and no auto-memory (its instructions name
  # his memory folder, and in ~/helm they load his memory index). No MCP
  # servers or connectors. Read tools only. The brief comes on stdin.
  # ~/.claude comes back for the login; his sessions, history and the
  # machine settings stay hidden.
  local c="$HOME/.claude" p
  RW=("$c" "$HOME/.claude.json"); MASK=(); RO=(); BIND=()
  ENV=(CLAUDE_CODE_DISABLE_CLAUDE_MDS=1 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1)
  for p in projects file-history plans sessions session-env shell-snapshots paste-cache \
           backups feedback todos history.jsonl settings.local.json; do MASK+=("$c/$p"); done
  jail
  timeout --kill-after=30 "$LIMIT" "${JAIL[@]}" "$BIN" -p --model "$MODEL" --effort "$EFFORT" \
    --setting-sources project --strict-mcp-config --tools Read,Grep,Glob \
    --no-session-persistence < "$BRIEF" 2>> "$ERR" | tee "$OUT"
  RC=${PIPESTATUS[0]}
}

echo "[fusion] $VOICE: $HARNESS $MODEL effort=$EFFORT round $ROUND"
case "$HARNESS" in agy|opencode|pi|claude) ;; *) echo "unknown harness: $HARNESS" >> "$ERR"; finish 2 ;; esac
[[ "$MODEL" == ollama/* ]] && take_ollama_slot
START=$(date +%s)
# One retry for a call that failed without timing out: a headless agy abort,
# or a harness that died early. A timeout is final. Outside agy, only a fast
# failure (under 2 minutes) is retried, so a long call never runs twice. agy
# retries any failure short of a timeout, so its worst case is two calls.
RC=1
for TRY in 1 2; do
  T0=$(date +%s)
  "call_$HARNESS"
  [[ "$RC" == 0 && -s "$OUT" ]] && break
  (( RC == 124 || RC == 137 )) && break
  [[ "$HARNESS" != agy ]] && (( $(date +%s) - T0 >= 120 )) && break
  (( TRY == 1 )) && echo "[fusion] $VOICE failed (exit $RC, try $TRY): $(tail -c 200 "$ERR")"
done
finish "$RC"
