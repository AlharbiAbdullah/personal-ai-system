#!/usr/bin/env bash
# /fusion panel runner. Harness-neutral: any coordinator with bash and tmux
# drives it, so /fusion works the same from Claude Code, pi or opencode.
#
#   panel.sh new <mode> [--cwd DIR] [--prelude NAME] [--coordinator VOICE|none]
#                                                     create a run, print its dir
#   panel.sh start <run> <round> [voice ...]          launch the round (default voices below)
#   panel.sh wait <run> <round> [seconds]             block until every voice exits
#                                                     (default FUSION_TIMEOUT + 300)
#   panel.sh status <run> <round>                     one line per voice
#   panel.sh show <run> <round> [voice ...]           the answers, labeled (all by default)
#   panel.sh cites <run> <round> [voice ...]          check every file:line exists
#   panel.sh digest <run>                             round-2 reply lines, by ledger item
#   panel.sh check <run>                              round 1 -> ledger -> synthesis gaps
#   panel.sh close <run>                              stop the run's voices and tmux sessions
#
# Before round 1 the coordinator writes <run>/ask.md: the ask and all its context.
# Between the rounds it may write <run>/ask-r2.md (round 2 gets it instead of
# ask.md) and <run>/ledger.md (every round-1 point, merged and numbered).
# Round 1: each voice answers alone. Round 2 skips the coordinator's own model
# (--coordinator, default opus): name it to run it anyway. Each voice gets its own
# brief, r2/brief-<voice>.md, with its own round-1 answer first. Then:
#   - with a ledger: where each of its points went, the ledger with its sources
#     stripped, and its assignment (r2/assign.txt): each open item goes to 2 voices
#     that did not raise it, an `open!` item to 3. A voice that failed round 1
#     still checks.
#   - without one: the others' answers under fixed labels (Voice A, B and on; key in
#     r2/key.txt), in an order rotated per voice.
# A round's briefs are built once; starting named voices again reuses them, so a
# failed voice can be re-run, even while the rest of its round is still running.
# A changed ask needs a new run.
# Each round is one detached tmux session, fusion-<run>-r<round>, one window per voice.
# Watch it live: tmux attach -t fusion-<run>-r<round>
#
# The ledger's line format, cites, digest and check live in ledger.sh.
#
# The voices read only --cwd (voice.sh jails every harness). Without it they get an
# empty folder. /, $HOME, any folder above it and any harness state folder are refused. Worst case per voice: FUSION_TIMEOUT
# (default 1800 s) of run, plus up to as long again waiting for an Ollama slot.
# agy retries any failure short of a timeout, so its worst case is two calls.
# Call wait again until it returns 0.
#
# The mode picks the brief's shaping; --prelude adds references/<NAME>.md
# (default: review-code for review, else references/<mode>.md when it exists).
# In a reference file, `INCLUDE-R1: <path>` expands in round 1 only: a style
# corpus a drafter needs and a judge does not. Voices: voices.conf.

set -euo pipefail
shopt -s inherit_errexit   # a failed INCLUDE inside $(...) stops the brief too

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REF="$(dirname "$HERE")/references"
STATE="${FUSION_STATE:-$HOME/.local/state/rai/fusion}"
MODES="review brainstorm plan debug decide ask write-english write-arabic"

die() { echo "panel.sh: $*" >&2; exit 2; }

# The ledger round 2 and the tools the coordinator runs after round 1.
source "$HERE/ledger.sh"

all_voices() { awk '!/^#/ && NF { print $1 }' "$HERE/voices.conf"; }

voice_label() { awk -v v="$1" '$1 == v { printf "%s (%s, %s)", $1, $2, $3 }' "$HERE/voices.conf"; }

# Round 1 keeps `INCLUDE-R1:` lines as includes; round 2 drops them.
round_includes() {
  if (( $2 == 1 )); then sed 's/^INCLUDE-R1: /INCLUDE: /' <<<"$1"; else sed '/^INCLUDE-R1: /d' <<<"$1"; fi
}

# Expand `INCLUDE: <path>` lines to a fixed point, so an included file may include more.
expand() {
  local text i round="${2:-1}"
  text="$(cat "$1")"
  for i in 1 2 3 4 5; do
    text="$(round_includes "$text" "$round")"
    grep -q '^INCLUDE: ' <<<"$text" || break
    text="$(printf '%s\n' "$text" | awk '
      /^INCLUDE: / {
        path = $0; sub(/^INCLUDE: /, "", path); gsub(/^~/, ENVIRON["HOME"], path)
        r = (getline line < path)
        if (r < 0) { printf "panel.sh: missing INCLUDE file %s\n", path > "/dev/stderr"; exit 1 }
        printf "\n=== INCLUDED FROM: %s ===\n", path
        while (r > 0) { print line; r = (getline line < path) }
        close(path)
        printf "=== END INCLUDE ===\n\n"
        next
      }
      { print }')"
  done
  printf '%s\n' "$text"
}

session_name() { echo "fusion-$(basename "$1")-r$2"; }

answered() { [[ -f "$1.exit" && "$(cat "$1.exit")" == 0 && -s "$1.md" ]]; }

# The voices that answered round 1, in panel order.
answered_r1() {
  local x
  for x in $(all_voices); do if answered "$1/r1/$x"; then echo "$x"; fi; done
}

# Rewrite a round's voices file as the union of what it lists and $2, in panel order.
add_voice() {
  local have
  have=" $(cat "$1" 2>/dev/null || true) $2 "
  all_voices | while read -r x; do if [[ "$have" == *" $x "* ]]; then echo "$x"; fi; done | xargs > "$1"
}

cmd_new() {
  local mode="${1:-}" cwd="" prelude="" coord=opus run
  [[ -n "$mode" ]] || die "usage: new <mode> [--cwd DIR] [--prelude NAME] [--coordinator VOICE|none]"
  [[ " $MODES " == *" $mode "* ]] || die "unknown mode '$mode' (modes: $MODES)"
  shift
  while (( $# )); do
    case "$1" in
      --cwd) (( $# >= 2 )) || die "--cwd needs a directory"; cwd="$2"; shift 2 ;;
      --prelude) (( $# >= 2 )) || die "--prelude needs a name"; prelude="$2"; shift 2 ;;
      --coordinator) (( $# >= 2 )) || die "--coordinator needs a voice"; coord="$2"; shift 2 ;;
      *) die "unknown option $1" ;;
    esac
  done
  if [[ -n "$cwd" ]]; then
    [[ -d "$cwd" ]] || die "no such directory: $cwd"
    cwd="$(cd "$cwd" && pwd -P)"   # the real path: a symlink to $HOME is $HOME
    [[ "$cwd" != / && "$HOME/" != "$cwd/"* ]] || die "never run the panel in $cwd: name the folder the ask is about"
    # A harness's own state folder, or a folder holding one, would undo the jail's masks.
    local s
    for s in "$HOME/.claude" "$HOME/.pi" "$HOME/.gemini" "$HOME/.cache/opencode" "$STATE"; do
      [[ "$s/" == "$cwd/"* || "$cwd/" == "$s/"* ]] && die "never run the panel in $cwd: it holds harness state"
    done
  fi
  if [[ -z "$prelude" ]]; then
    case "$mode" in review) prelude=review-code ;; *) [[ -f "$REF/$mode.md" ]] && prelude="$mode" ;; esac
  fi
  [[ -z "$prelude" || -f "$REF/$prelude.md" ]] || die "no prelude references/$prelude.md"
  [[ "$coord" == none ]] && coord=""
  [[ -z "$coord" ]] || all_voices | grep -qxF -- "$coord" || die "unknown coordinator voice: $coord"
  mkdir -p "$STATE/runs"
  run="$(mktemp -d "$STATE/runs/$(date +%Y%m%d-%H%M%S)-$mode-XXXX")"
  echo "$mode" > "$run/mode"
  [[ -n "$cwd" ]] || { mkdir "$run/empty"; cwd="$run/empty"; }
  echo "$cwd" > "$run/cwd"
  echo "$prelude" > "$run/prelude"
  echo "$coord" > "$run/coordinator"
  echo "$run"
}

# The part of a round's brief every voice shares: the role, the mode rules and the ask.
build_common() {
  local run="$1" round="$2" mode prelude ask="$1/ask.md"
  mode="$(cat "$run/mode")"; prelude="$(cat "$run/prelude")"
  if (( round == 1 )); then
    expand "$REF/panel.md" 1
  else
    expand "$REF/round2.md" 2
    [[ -s "$run/ask-r2.md" ]] && ask="$run/ask-r2.md"
  fi
  [[ -n "$prelude" ]] && { echo; expand "$REF/$prelude.md" "$round"; }
  printf '\n# MODE: %s\n\n# THE ASK\n\n' "$mode"
  cat "$ask"
}

# Round 2 without a ledger: one brief per voice that answered round 1. Labels are
# shuffled once per run and fixed, so "Voice D" is the same answer in every reply.
# Each voice sees its own answer first and the others rotated, so each answer takes
# every position once.
build_r2_essays() {
  local run="$1" d="$1/r2" common n total i j k v
  local letters=(A B C D E F G H I J K L) voices=()
  mapfile -t voices < <(answered_r1 "$run" | shuf)
  n=${#voices[@]}
  (( n > 0 )) || die "no voice answered round 1"
  total=$(all_voices | wc -l)
  common="$(build_common "$run" 2)"
  : > "$d/key.txt.new"
  for (( i = 0; i < n; i++ )); do echo "Voice ${letters[$i]} = ${voices[$i]}" >> "$d/key.txt.new"; done
  for (( i = 0; i < n; i++ )); do
    v="${voices[$i]}"
    {
      printf '%s\n\n%s of %s voices answered round 1.\n' "$common" "$n" "$total"
      printf '\n# YOUR ROUND-1 ANSWER\n\n'
      cat "$run/r1/$v.md"
      printf '\n\n# THE OTHER ROUND-1 ANSWERS\n'
      for (( k = 1; k < n; k++ )); do
        j=$(( (i + k) % n ))
        printf '\n## Voice %s\n\n' "${letters[$j]}"
        cat "$run/r1/${voices[$j]}.md"
      done
    } > "$d/brief-$v.md.new"
  done
  for v in "${voices[@]}"; do mv "$d/brief-$v.md.new" "$d/brief-$v.md"; done
  mv "$d/key.txt.new" "$d/key.txt"
}

# The ledger layout serves the modes that check claims; the write modes and ask
# always show the drafts and answers themselves.
ledger_mode() {
  case "$(cat "$1/mode")" in write-*|ask) return 1 ;; esac
  [[ -s "$1/ledger.md" ]]
}

build_r2() { if ledger_mode "$1"; then build_r2_ledger "$1" "$2"; else build_r2_essays "$1"; fi; }

# The voices of round 2, in panel order: those its key lists.
r2_voices() { local x; for x in $(all_voices); do if grep -q "= $x\$" "$1/r2/key.txt"; then echo "$x"; fi; done; }

# Round 2's default voices, minus the coordinator's model: those that answered
# round 1, or with a ledger every voice round 1 launched, a failed one included.
r2_default() {
  local coord x
  coord="$(cat "$1/coordinator" 2>/dev/null || true)"
  { if ledger_mode "$1"; then xargs -n1 < "$1/r1/voices"
    elif [[ -f "$1/r2/key.txt" ]]; then r2_voices "$1"
    else answered_r1 "$1"; fi; } | while read -r x; do if [[ "$x" != "$coord" ]]; then echo "$x"; fi; done
}

# Build a round's briefs once, so a re-run of some voices keeps the same briefs
# and key. Prints the voices to launch: those named, else the round's defaults.
prepare_round() {
  local run="$1" round="$2" voices="$3" d="$1/r$2" v
  mkdir -p "$d"
  if (( round == 1 )); then
    if [[ ! -f "$d/brief.md" ]]; then
      build_common "$run" 1 > "$d/brief.md.new"
      mv "$d/brief.md.new" "$d/brief.md"
    fi
    echo "${voices:-$(all_voices | xargs)}"
    return
  fi
  [[ -n "$voices" ]] || voices="$(r2_default "$run" | xargs)"
  [[ -n "$voices" ]] || die "no voice left for round 2: name one"
  [[ -f "$d/key.txt" ]] || build_r2 "$run" "$voices"
  for v in $voices; do
    [[ -f "$d/brief-$v.md" ]] || die "round 2 was built without $v: start a new run to include it"
  done
  echo "$voices"
}

cmd_start() {
  local run="${1:-}" round="${2:-}" voices="" sess v first=1 d
  [[ -f "$run/mode" ]] || die "not a run dir: $run"
  [[ "$round" == 1 || "$round" == 2 ]] || die "round must be 1 or 2"
  [[ -s "$run/ask.md" ]] || die "write $run/ask.md first"
  shift 2
  for v in "$@"; do
    awk -v v="$v" '$1 == v { found = 1 } END { exit !found }' "$HERE/voices.conf" || die "unknown voice: $v"
    [[ " $voices " == *" $v "* ]] || voices="$voices $v"
  done
  d="$run/r$round"
  voices="$(prepare_round "$run" "$round" "$voices")"
  sess="$(session_name "$run" "$round")"
  if tmux has-session -t "=$sess" 2>/dev/null; then
    # The round is open: re-run only named voices that have finished.
    (( $# )) || die "round $round is still open: name the voices to re-run, or close the run first"
    for v in $voices; do
      [[ -f "$d/$v.exit" ]] || ! grep -qw "$v" "$d/voices" 2>/dev/null || die "$v is still running"
    done
    for v in $voices; do tmux kill-window -t "=$sess:=$v" 2>/dev/null || true; done
    first=0
    tmux has-session -t "=$sess" 2>/dev/null || first=1   # the last window took the session
  fi
  # tmux runs windows in its server's environment: carry ours across.
  local envs=(-e "PATH=$PATH" -e "HOME=$HOME" -e "FUSION_STATE=$STATE")
  local var
  for var in FUSION_TIMEOUT FUSION_EFFORT; do
    [[ -n "${!var:-}" ]] && envs+=(-e "$var=${!var}")
  done
  for v in $voices; do
    rm -f "$d/$v".{md,err,exit,secs,queue,jsonl}
    # remain-on-exit keeps each finished pane on screen until close.
    if (( first )); then
      tmux new-session -d -s "$sess" -n "$v" -c "$(cat "$run/cwd")" "${envs[@]}" \
        "bash '$HERE/voice.sh' '$run' '$round' '$v'" \; set-option -w remain-on-exit on >/dev/null
      first=0
    else
      tmux new-window -t "$sess:" -n "$v" -c "$(cat "$run/cwd")" "${envs[@]}" \
        "bash '$HERE/voice.sh' '$run' '$round' '$v'" \; set-option -w remain-on-exit on >/dev/null
    fi
    add_voice "$d/voices" "$v"   # recorded only once its window exists
  done
  echo "round $round started: $(wc -w <<<"$voices") voices in tmux session $sess"
  echo "watch: tmux attach -t $sess"
}

cmd_status() {
  local run="$1" round="$2" v f q
  [[ -f "$run/r$round/voices" ]] || die "round $round was not started"
  for v in $(cat "$run/r$round/voices"); do
    f="$run/r$round/$v"
    q="$(cat "$f.queue" 2>/dev/null || echo 0)"
    q=$([[ "$q" =~ ^[0-9]+$ ]] && (( q > 0 )) && echo "  queued ${q}s" || true)
    if [[ ! -f "$f.exit" ]]; then
      printf '%-12s running%s\n' "$v" "$q"
    elif answered "$f"; then
      printf '%-12s done    %5ss  %6s words%s\n' "$v" "$(cat "$f.secs")" "$(wc -w < "$f.md")" "$q"
    else
      printf '%-12s FAILED  exit %s: %s\n' "$v" "$(cat "$f.exit")" "$(tail -c 300 "$f.err" 2>/dev/null | tr '\n' ' ')"
    fi
  done
}

cmd_wait() {
  local run="$1" round="$2" limit="${3:-$(( ${FUSION_TIMEOUT:-1800} + 300 ))}" end v left
  [[ -f "$run/r$round/voices" ]] || die "round $round was not started"
  end=$(( $(date +%s) + limit ))
  while :; do
    left=0
    for v in $(cat "$run/r$round/voices"); do [[ -f "$run/r$round/$v.exit" ]] || left=$((left + 1)); done
    (( left == 0 )) && { cmd_status "$run" "$round"; return 0; }
    (( $(date +%s) >= end )) && { cmd_status "$run" "$round"; echo "still running: $left"; return 3; }
    sleep 5
  done
}

cmd_show() {
  local run="$1" round="$2" v f list
  [[ -f "$run/r$round/voices" ]] || die "round $round was not started"
  shift 2
  list="${*:-$(cat "$run/r$round/voices")}"
  for v in $list; do
    f="$run/r$round/$v"
    printf '\n========== %s ==========\n' "$(voice_label "$v")"
    if answered "$f"; then
      cat "$f.md"
    else
      printf '[no answer: exit %s]\n' "$(cat "$f.exit" 2>/dev/null || echo running)"
      tail -c 600 "$f.err" 2>/dev/null | sed 's/^/  /'
    fi
  done
  [[ ! -f "$run/r$round/key.txt" ]] || { printf '\n========== round 2 key ==========\n'; cat "$run/r$round/key.txt"; }
  return 0
}

cmd_close() {
  local run="$1" r sess pid
  for r in 1 2; do
    sess="$(session_name "$run" "$r")"
    tmux has-session -t "=$sess" 2>/dev/null || continue
    # timeout puts each call in its own process group, so killing the tmux
    # session alone leaves calls running. Each pane is its own session id:
    # stop every process in it, then the tmux session.
    for pid in $(tmux list-panes -s -t "=$sess" -F '#{pane_pid}'); do
      pkill -TERM -s "$pid" 2>/dev/null || true
    done
    tmux kill-session -t "=$sess" 2>/dev/null || true
  done
  echo "closed: $run"
  [[ -s "$run/synthesis.md" ]] || echo "panel.sh: warning: no synthesis.md in $run: save the answer you gave" >&2
}

sub="${1:-}"; shift || true
case "$sub" in
  new) cmd_new "$@" ;;
  start) cmd_start "$@" ;;
  wait) cmd_wait "$@" ;;
  status) cmd_status "$@" ;;
  show) cmd_show "$@" ;;
  cites) cmd_cites "$@" ;;
  digest) cmd_digest "$@" ;;
  check) cmd_check "$@" ;;
  close) cmd_close "$@" ;;
  *) sed -n '2,15p' "$0"; exit 2 ;;
esac
