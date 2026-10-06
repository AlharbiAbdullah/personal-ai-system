#!/usr/bin/env bash
# /fusion protocol tests. No model is called: the four harnesses are mocks in a
# throwaway HOME, run through the real panel.sh, voice.sh, tmux and bwrap.
#
#   bash test_panel.sh        exit 0 when every case passes
#
# Covers the read-only jail, per-voice round-2 briefs, the coordinator skip,
# round 2 with a ledger (stripped sources, own-item map, assignment), digest,
# check, cites, the close warning, round-1-only includes, ask-r2.md, a live
# re-run, the fast-failure retry, a broken opencode stream, the queue file,
# status words and show by voice.

set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VAULT="$(cd "$HERE/../../../.." && pwd)"
REAL_HOME="$HOME"
# The fake HOME lives under the real one, never /tmp: the jail empties /tmp on
# its own, which would hide a missing home mask.
mkdir -p "$HOME/.cache"
FH="$(mktemp -d "$HOME/.cache/fusion-test.XXXXXX")"
export HOME="$FH" FUSION_STATE="$FH/.local/state/rai/fusion" FUSION_TIMEOUT=60
export PATH="$FH/.local/bin:$PATH"
P="$HERE/panel.sh"
FAILS=0

ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; FAILS=$((FAILS + 1)); }
check() { if eval "$2"; then ok "$1"; else bad "$1"; fi; }

# --- the throwaway HOME -------------------------------------------------------
ln -s "$VAULT" "$FH/helm"                       # INCLUDE paths resolve into this tree
mkdir -p "$FH/.local/bin" "$FH/.pi/agent/rai-transcripts" "$FH/.claude/projects" \
  "$FH/.gemini/antigravity-cli/conversations" "$FH/.gemini/config" "$FH/.cache/opencode" \
  "$FH/.local/share/opencode"
echo secret > "$FH/secret.txt"
echo transcript > "$FH/.pi/agent/rai-transcripts/t.jsonl"
echo session > "$FH/.claude/projects/s.jsonl"
echo creds > "$FH/.claude/.credentials.json"
echo '{}' > "$FH/.claude.json"
echo '{}' > "$FH/.gemini/antigravity-cli/settings.json"
echo conv > "$FH/.gemini/antigravity-cli/conversation_summaries.db"
echo pi-login > "$FH/.pi/agent/auth.json"
RUNDIR="/run/user/$(id -u)"; RT_SECRET="$RUNDIR/fusion-test-secret.$$"
[[ -w "$RUNDIR" ]] && echo key > "$RT_SECRET"

# One mock for every harness: it answers by its model name, reports what it can
# see, and obeys MOCK_ markers in its brief.
cat > "$FH/.local/bin/mock" <<'EOF'
#!/usr/bin/env bash
name="$(basename "$0")"; model=""; brief=""
while (( $# )); do
  case "$1" in
    --model|-m) model="$2"; shift ;;
    -p=*) brief="${1#-p=}" ;;
  esac
  shift
done
[[ "$name" == agy ]] || brief="$(cat)"
[[ "$brief" == *"$model-SLEEP"* ]] && sleep 15
# The sol voice (pi on ChatGPT) is the one with a writable file to mark a crash in.
if [[ "$brief" == *MOCK_FAILONCE* && "$model" == openai/* ]] && ! grep -q crashed "$HOME/.pi/agent/auth.json"; then
  echo crashed >> "$HOME/.pi/agent/auth.json"; echo "mock pi crash" >&2; exit 1
fi
if [[ "$brief" == *MOCK_BADJSON* && "$name" == opencode ]]; then echo 'not json {'; exit 0; fi
seen() { if cat "$1" >/dev/null 2>&1; then echo "$2_VISIBLE"; else echo "$2_HIDDEN"; fi; }
body="ANSWER-$model
$(seen "$HOME/secret.txt" SECRET)
$(seen "$HOME/.pi/agent/rai-transcripts/t.jsonl" PITRANSCRIPT)
$(seen "$HOME/.claude/projects/s.jsonl" CLAUDEPROJECT)
$(seen ./target.txt CWDFILE)
$(seen "$HOME/.pi/agent/auth.json" PILOGIN)
$(seen "$HOME/.gemini/antigravity-cli/conversation_summaries.db" AGYHISTORY)
$(ls /run/user/$(id -u)/fusion-test-secret.* >/dev/null 2>&1 && echo RUNTIME_VISIBLE || echo RUNTIME_HIDDEN)
$([[ -n "${FUSION_STATE:-}" ]] && echo ENV_LEAKED || echo ENV_CLEARED)
$( (echo x > ./written.txt) 2>/dev/null && echo CWD_WRITABLE || echo CWD_READONLY )"
if [[ "$name" == opencode ]]; then
  jq -cn --arg t "$body" '{type: "text", part: {text: $t}}'
else
  printf '%s\n' "$body"
fi
EOF
chmod +x "$FH/.local/bin/mock"
for h in agy opencode pi claude; do cp "$FH/.local/bin/mock" "$FH/.local/bin/$h"; done

TARGET="$(mktemp -d "$REAL_HOME/.cache/fusion-target.XXXXXX")"; echo target > "$TARGET/target.txt"
trap 'tmux ls -F "#S" 2>/dev/null | grep "^fusion-" | grep -- "-t-" | xargs -r -n1 tmux kill-session -t; rm -rf "$FH" "$TARGET" "$RT_SECRET"' EXIT

new_run() {   # mode, ask text
  local run
  run="$("$P" new "$1" --cwd "$TARGET")"
  mv "$run" "${run%-*}-t-${run##*-}"; run="${run%-*}-t-${run##*-}"
  printf '%s\n' "$2" > "$run/ask.md"
  echo "$run"
}
VOICES="gemini minimax glm deepseek sol opus"

# --- round 1, the jail ---------------------------------------------------------
RUN="$(new_run decide 'Pick A or B. MOCK_ASK_ONE')"
"$P" start "$RUN" 1 >/dev/null && "$P" wait "$RUN" 1 120 >/dev/null
for v in $VOICES; do
  f="$RUN/r1/$v.md"
  check "r1 $v answered"            "grep -q '^ANSWER-' '$f'"
  check "r1 $v cannot read home"    "grep -q SECRET_HIDDEN '$f'"
  check "r1 $v reads the cwd"       "grep -q CWDFILE_VISIBLE '$f'"
  check "r1 $v cwd is read-only"    "grep -q CWD_READONLY '$f'"
  check "r1 $v pi transcripts hidden"  "grep -q PITRANSCRIPT_HIDDEN '$f'"
  check "r1 $v claude projects hidden" "grep -q CLAUDEPROJECT_HIDDEN '$f'"
  check "r1 $v agy history hidden"     "grep -q AGYHISTORY_HIDDEN '$f'"
  check "r1 $v runtime folder hidden"  "grep -q RUNTIME_HIDDEN '$f'"
  check "r1 $v environment cleared"    "grep -q ENV_CLEARED '$f'"
  if [[ $v == sol ]]; then
    check "r1 sol (pi on ChatGPT) reaches its login" "grep -q PILOGIN_VISIBLE '$f'"
  else
    check "r1 $v cannot read the pi login" "grep -q PILOGIN_HIDDEN '$f'"
  fi
done
check "no file written to the cwd" "[[ ! -e '$TARGET/written.txt' ]]"
check "queue file for Ollama voices" "[[ -f '$RUN/r1/minimax.queue' && -f '$RUN/r1/deepseek.queue' ]]"
check "status counts words" "[[ \$('$P' status '$RUN' 1 | grep -c words) == 6 ]]"

# --- round 2, per-voice briefs ---------------------------------------------------
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 120 >/dev/null
check "r2 key lists 6 voices" "[[ \$(wc -l < '$RUN/r2/key.txt') == 6 ]]"
check "r2 skips the coordinator (opus) by default" "[[ ! -e '$RUN/r2/opus.md' && \$(wc -w < '$RUN/r2/voices') == 5 ]]"
"$P" start "$RUN" 2 opus >/dev/null && "$P" wait "$RUN" 2 120 >/dev/null
firsts=""
for v in $VOICES; do
  b="$RUN/r2/brief-$v.md"
  model="$(awk -v v="$v" '$1 == v { print $3 }' "$HERE/voices.conf")"
  own="$(awk '/^# YOUR ROUND-1 ANSWER/{f=1; next} /^# THE OTHER ROUND-1 ANSWERS/{f=0} f' "$b")"
  others="$(awk '/^# THE OTHER ROUND-1 ANSWERS/{f=1} f' "$b")"
  check "r2 $v brief shows its own answer first" "grep -qF 'ANSWER-$model' <<<\"\$own\""
  check "r2 $v own answer not among the others"  "! grep -qF 'ANSWER-$model' <<<\"\$others\""
  check "r2 $v sees the 5 others"                "[[ \$(grep -c '^## Voice ' <<<\"\$others\") == 5 ]]"
  check "r2 $v told 6 of 6 answered"             "grep -q '6 of 6 voices answered' '$b'"
  # Each label must point at the answer the key gives it.
  while read -r _ letter _ lv; do
    [[ "$lv" == "$v" ]] && continue
    lm="$(awk -v v="$lv" '$1 == v { print $3 }' "$HERE/voices.conf")"
    sec="$(awk -v L="## Voice $letter" '$0 == L {f=1; next} /^## Voice /{f=0} f' <<<"$others")"
    grep -qF "ANSWER-$lm" <<<"$sec" || bad "r2 $v label $letter does not match the key"
  done < "$RUN/r2/key.txt"
  firsts="$firsts $(grep -m1 '^## Voice ' <<<"$others" | awk '{print $3}')"
  check "r2 $v answered" "grep -q '^ANSWER-' '$RUN/r2/$v.md'"
done
check "r2 order rotates per voice" "[[ \$(tr ' ' '\n' <<<'$firsts' | grep . | sort -u | wc -l) == 6 ]]"
check "show by voice prints one voice and the key" "[[ \$('$P' show '$RUN' 2 sol | grep -c '^==========') == 2 ]]"
"$P" close "$RUN" >/dev/null 2>&1

# --- the coordinator option ----------------------------------------------------------
check "refuses an unknown coordinator" "! '$P' new decide --cwd '$TARGET' --coordinator nobody 2>/dev/null"
check "refuses a regex as coordinator" "! '$P' new decide --cwd '$TARGET' --coordinator 'o.us' 2>/dev/null"
RUN="$(new_run decide 'x')"; rm "$RUN/coordinator"          # a run from before the option
"$P" start "$RUN" 1 gemini opus >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "an old run's round 2 keeps every voice" "[[ \$(cat '$RUN/r2/voices') == 'gemini opus' ]]"
"$P" close "$RUN" >/dev/null 2>&1
RUN="$(new_run decide 'x')"; echo sol > "$RUN/coordinator"
"$P" start "$RUN" 1 gemini sol >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "--coordinator sol: round 2 skips sol" "[[ \$(cat '$RUN/r2/voices') == gemini ]]"
"$P" close "$RUN" >/dev/null 2>&1
RUN="$(new_run review 'x')"
"$P" start "$RUN" 1 gemini opus >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
echo 'L1 | opus:1 | open | a claim |' > "$RUN/ledger.md"
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null; "$P" close "$RUN" >/dev/null 2>&1
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "ledger r2 keeps a round-1 subset, even after close" "[[ \$(cat '$RUN/r2/voices') == gemini ]]"
"$P" close "$RUN" >/dev/null 2>&1
R3="$("$P" new decide --cwd "$TARGET" --coordinator none)"
check "--coordinator none records no voice" "[[ -z \$(cat '$R3/coordinator') ]]"
rm -rf "$R3"

# --- round-1-only includes, round-2 preludes ---------------------------------------
RUN="$(new_run write-arabic 'Write one line.')"
"$P" start "$RUN" 1 gemini >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
check "write-arabic r1 brief carries the corpus" "grep -q 'Lumen («لومن») voice corpus' '$RUN/r1/brief.md'"
echo 'L1 | gemini:1 | open | a stray ledger |' > "$RUN/ledger.md"   # the write modes ignore it
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "write-arabic r2 brief drops the corpus" "! grep -q 'Lumen («لومن») voice corpus' '$RUN/r2/brief-gemini.md'"
check "write-arabic r2 ignores a ledger: drafts, not items" "! grep -q '^# THE LEDGER' '$RUN/r2/brief-gemini.md'"
check "write-arabic r2 brief keeps the dictionary" "grep -q 'Definite article' '$RUN/r2/brief-gemini.md'"
check "write-arabic r2 brief has no draft-only order" "! grep -qi 'output the draft' '$RUN/r2/brief-gemini.md'"
"$P" close "$RUN" >/dev/null 2>&1

RUN="$(new_run review 'x')"; echo review-prose > "$RUN/prelude"
"$P" start "$RUN" 1 gemini >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
check "English prose review loads no Arabic rules" "! grep -q 'Definite article' '$RUN/r1/brief.md'"
"$P" close "$RUN" >/dev/null 2>&1

# --- ask-r2.md --------------------------------------------------------------------
RUN="$(new_run plan 'FULL_ASK_MARKER')"
echo 'SHORT_ASK_MARKER' > "$RUN/ask-r2.md"
"$P" start "$RUN" 1 gemini sol >/dev/null && "$P" wait "$RUN" 1 60 >/dev/null
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "r2 uses ask-r2.md" "grep -q SHORT_ASK_MARKER '$RUN/r2/brief-sol.md' && ! grep -q FULL_ASK_MARKER '$RUN/r2/brief-sol.md'"
check "r2 counts 2 of 6 answered" "grep -q '2 of 6 voices answered' '$RUN/r2/brief-sol.md'"
"$P" close "$RUN" >/dev/null 2>&1

# --- round 2 with a ledger --------------------------------------------------------------
# The opencode voices (minimax, glm) fail round 1 on a broken stream.
RUN="$(new_run review 'Review it. MOCK_BADJSON')"
echo 'Review it, round 2.' > "$RUN/ask-r2.md"
"$P" start "$RUN" 1 gemini minimax glm sol opus >/dev/null && "$P" wait "$RUN" 1 120 >/dev/null
cat > "$RUN/ledger.md" <<'L'
## Cluster one
L1 | gemini:1 sol:2 | open | claim one LEDGERCLAIM1 | target.txt:1
L2 | opus:4 | open! | claim two |
L3 | glm:1 | verified: test ran | claim three |
L4 | minimax:2,3 | dropped: duplicate of L1 | claim four |
L5 | gemini:2 minimax:1 glm:2 deepseek:1 sol:1 | open | everyone raised it |
- L6 | gemini:3, 4 | open | a claim with a | pipe in it |
L7 | gemini:5 minimax:5 glm:5 | open! | three raised it |
L8 | gemini:10, 11 | verified: read it | items past nine |
**L9** | gemini:6 | open | a bold id |
1. L10 | gemini:7 | open | a numbered line |
L
"$P" start "$RUN" 2 >/dev/null && "$P" wait "$RUN" 2 120 >/dev/null
B="$RUN/r2/brief-gemini.md"
led="$(awk '/^# THE LEDGER/{f=1; next} /^# YOUR ASSIGNMENT/{f=0} f' "$B")"
check "ledger r2: no peer essays"           "! grep -q '^# THE OTHER ROUND-1 ANSWERS' '$B'"
check "ledger r2: sources stripped"         "! grep -qE 'gemini:|sol:2|minimax:2' <<<\"\$led\""
check "ledger r2: items and headings kept"  "grep -qF 'L1 | open | claim one' <<<\"\$led\" && grep -q 'Cluster one' <<<\"\$led\""
check "ledger r2: own items mapped"         "grep -qF 'your 1 -> L1 (open)' '$B' && grep -qF 'your 2 -> L5 (open)' '$B'"
check "ledger r2: a dropped item shows why" "grep -qF 'your 3 -> L4 (dropped: duplicate of L1)' '$RUN/r2/brief-minimax.md'"
check "ledger r2: a failed r1 voice still checks" "grep -q 'You gave none' '$RUN/r2/brief-minimax.md' && grep -q '^ANSWER-' '$RUN/r2/minimax.md'"
check "ledger r2: a voice round 1 never launched stays out" "[[ ! -e '$RUN/r2/deepseek.md' ]]"
check "ledger r2: a bulleted item is stripped and assigned" "! grep -q 'gemini:3' <<<\"\$led\" && grep -q '^L6 ' '$RUN/r2/assign.txt'"
check "ledger r2: a comma-space source maps" "grep -qF 'your 4 -> L6 (open)' '$B'"
check "ledger r2: bold and numbered items are stripped and assigned" "! grep -qE 'gemini:(6|7)' <<<\"\$led\" && grep -qE '^L9 ' '$RUN/r2/assign.txt' && grep -qE '^L10 ' '$RUN/r2/assign.txt'"
check "ledger r2: an open! item short of checkers is marked" "grep -qE '^L7 .* SHORT\$' '$RUN/r2/assign.txt'"
check "ledger r2: coordinator brief built, not launched" "[[ -f '$RUN/r2/brief-opus.md' && ! -e '$RUN/r2/opus.md' ]]"
A="$RUN/r2/assign.txt"
check "ledger r2: open item to 2 non-raisers" "[[ \$(awk '\$1==\"L1\"{print NF-1}' '$A') == 2 ]] && ! grep -qE '^L1 .*\b(gemini|sol)\b' '$A'"
check "ledger r2: open! item to 3, never its raiser" "[[ \$(awk '\$1==\"L2\"{print NF-1}' '$A') == 3 ]] && ! grep -qE '^L2 .*\bopus\b' '$A'"
check "ledger r2: verified and dropped items unassigned" "! grep -qE '^L(3|4) ' '$A'"
check "ledger r2: item nobody can check is marked" "grep -qx 'L5 -' '$A'"
first="$(awk '$1=="L1"{print $2}' "$A")"
check "ledger r2: assignment in the brief" "grep -q 'Check these items first: .*L1' '$RUN/r2/brief-$first.md'"
sum_before="$(md5sum < "$A")"
"$P" start "$RUN" 2 "$first" >/dev/null && "$P" wait "$RUN" 2 60 >/dev/null
check "ledger r2: a re-run keeps the assignment" "[[ \$(md5sum < '$A') == '$sum_before' ]]"

# digest: hand-written replies stand in for the voices.
printf '**L1 DISPUTED:** wrong, target.txt:1 says target\n- L2 UNVERIFIED: needs a test\nNEW: something else target.txt:1\nCHECKED: L1, L2\n' > "$RUN/r2/$first.md"
others="$(awk '$1=="L1"{print $3}' "$A")"
echo 'Plain prose with no reply line.' > "$RUN/r2/$others.md"
DG="$("$P" digest "$RUN")"
check "digest groups verdicts by item"  "grep -q 'L1 DISPUTED' <<<\"\$DG\" && grep -q 'L2 UNVERIFIED' <<<\"\$DG\""
check "digest lists free lines"         "grep -q 'NEW: something else' <<<\"\$DG\""
check "digest flags an unparsed answer" "grep -qE 'UNPARSED +$others' <<<\"\$DG\""
printf 'NEW: serve it as HTML1 with a LEVEL1 cache\nCHECKED: L2\n' > "$RUN/r2/$others.md"
DG2="$("$P" digest "$RUN")"
check "digest flags a missed assignment" "grep -qE 'MISSING +$others never named L1' <<<\"\$DG2\""
check "digest flags a short assignment" "grep -qE 'SHORT +L7' <<<\"\$DG\""
check "digest flags an unassigned item" "grep -q 'UNASSIGNED L5' <<<\"\$DG\""
printf 'Voice B 3 DISPUTED: no, target.txt:1\n' > "$RUN/r2/$others.md"
DG="$("$P" digest "$RUN")"
check "digest reads essay-layout lines" "grep -q 'Voice B 3 DISPUTED' <<<\"\$DG\""
printf 'NONE\nCHECKED: L1\n' > "$RUN/r2/$others.md"
DG="$("$P" digest "$RUN")"
check "digest takes a NONE reply as parsed" "! grep -qE 'UNPARSED +$others' <<<\"\$DG\""
printf 'A full review in prose.\nCHECKED: L1\n' > "$RUN/r2/$others.md"
printf 'NONE\nCHECKED: L2\n' > "$RUN/r2/$first.md"
DG="$("$P" digest "$RUN")"
check "digest ignores CHECKED from an unparsed answer" "grep -qE 'UNPARSED +$others' <<<\"\$DG\" && grep -qE 'UNCHECKED +L1' <<<\"\$DG\""
echo 1 > "$RUN/r2/$first.exit"; echo 1 > "$RUN/r2/$others.exit"
DG="$("$P" digest "$RUN")"
check "digest flags an item whose checkers all failed" "grep -qE 'UNCHECKED +L1' <<<\"\$DG\""

# check: round 1 -> ledger -> synthesis.
seq 1 12 | sed 's/$/. item/' > "$RUN/r1/gemini.md"
CK="$("$P" check "$RUN" || true)"
check "check fails with no synthesis" "grep -q 'NO SYNTHESIS' <<<\"\$CK\""
printf 'L1 L2 L3 L4 L6 L7 L8 L9 L10\n' > "$RUN/synthesis.md"
CK="$("$P" check "$RUN" || true)"
check "check names unmapped items past 9, in order" "grep -q 'NOT IN LEDGER  gemini items: 8 9 12' <<<\"\$CK\""
check "check names an item missing from the synthesis" "grep -q 'NOT IN SYNTHESIS  L5' <<<\"\$CK\""
printf '%s. item\n' 1 2 3 4 5 6 7 10 11 > "$RUN/r1/gemini.md"; echo 'L5' >> "$RUN/synthesis.md"
CK="$("$P" check "$RUN")"
check "check passes on a complete chain" "grep -q 'chain complete' <<<\"\$CK\""

# cites: every file:line against cwd.
mkdir -p "$TARGET/sub" "$TARGET/locked"; printf 'a\nb\nc\n' > "$TARGET/sub/deep.txt"; chmod 000 "$TARGET/locked"
printf 'See target.txt:1, `target.txt`:99, nofile.py:3, deep.txt:2, deep.txt:02 and 127.0.0.1:8000.\n' > "$RUN/r1/sol.md"
CT="$("$P" cites "$RUN" 1 sol 2>&1)"; chmod 755 "$TARGET/locked"
check "cites counts refs and failures"    "grep -qE '^sol +5 refs +2 not found' <<<\"\$CT\""
check "cites finds a bare name in a subfolder past an unreadable one" "! grep -q 'deep.txt' <<<\"\$CT\""
check "cites flags a missing line"        "grep -q 'NO LINE  target.txt:99' <<<\"\$CT\""
check "cites flags a missing file"        "grep -q 'NO FILE  nofile.py:3' <<<\"\$CT\""
check "cites skips a host:port"           "! grep -q '127.0.0' <<<\"\$CT\""
rm "$RUN/synthesis.md"
CW="$("$P" close "$RUN" 2>&1 >/dev/null)"
check "close warns with no synthesis" "grep -q 'no synthesis.md' <<<\"\$CW\""

# --- live re-run, retry, broken stream ---------------------------------------------------
RUN="$(new_run debug 'claude-opus-5-5-SLEEP MOCK_FAILONCE MOCK_BADJSON')"
"$P" start "$RUN" 1 >/dev/null
sleep 4
check "re-run of a running voice is refused" "! '$P' start '$RUN' 1 opus 2>/dev/null"
"$P" wait "$RUN" 1 10 >/dev/null; sleep 1
check "re-run of a finished voice while the round is open" "'$P' start '$RUN' 1 gemini >/dev/null"
"$P" wait "$RUN" 1 120 >/dev/null
check "gemini answered after the live re-run" "grep -q '^ANSWER-' '$RUN/r1/gemini.md'"
check "pi voice retried a fast crash and answered" "grep -q '^ANSWER-' '$RUN/r1/sol.md' && grep -q crashed '$FH/.pi/agent/auth.json'"
check "broken opencode stream is a failure" "[[ \$(cat '$RUN/r1/minimax.exit') != 0 ]]"
"$P" close "$RUN" >/dev/null 2>&1

# --- refused working folders -------------------------------------------------------------
check "refuses the home folder"        "! '$P' new ask --cwd '$FH' 2>/dev/null"
check "refuses the root folder"        "! '$P' new ask --cwd / 2>/dev/null"
ln -s "$FH" "$TARGET/home-link"
check "refuses a symlink to home"      "! '$P' new ask --cwd '$TARGET/home-link' 2>/dev/null"
check "refuses a folder above home"    "! '$P' new ask --cwd '$(dirname "$FH")' 2>/dev/null"
check "refuses a harness state folder" "! '$P' new ask --cwd '$FH/.claude/projects' 2>/dev/null"
check "refuses a folder holding state" "! '$P' new ask --cwd '$FH/.local' 2>/dev/null"

# --- wait default ---------------------------------------------------------------------
check "wait default covers the call limit" "grep -q 'FUSION_TIMEOUT:-1800} + 300' '$P'"

echo
if (( FAILS )); then echo "$FAILS case(s) failed"; exit 1; fi
echo "all cases passed"
