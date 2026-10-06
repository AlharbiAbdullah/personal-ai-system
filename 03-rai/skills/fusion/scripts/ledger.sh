# /fusion ledger and post-round tools, sourced by panel.sh (not run on its own).
# It uses panel.sh's helpers: die, answered, answered_r1, all_voices, build_common.
#
# Ledger line: L<n> | <voice>:<item> ... | <status> | <claim> | <evidence>
# A leading bullet, quote, table pipe or list number, and bold on the id, are allowed. Status: open, open! (high
# stakes), verified: <how>, dropped: <why>. Other lines (cluster headings, notes)
# pass through as they are.

# The awk prefix every ledger reader shares: an item line loses its leading
# bullet, quote or pipe, and is_item says whether the line is an item.
LEDGER_AWK='function item(  h, p) { l = $0; sub(/^[[:space:]>|*-]+/, "", l)
  sub(/^[0-9]+[.)][[:space:]]+/, "", l); p = index(l, "|")
  if (p) { h = substr(l, 1, p - 1); gsub(/\*/, "", h); l = h substr(l, p) }
  if (l !~ /^L[0-9]+[[:space:]]*\|/) return 0; $0 = l; return 1 }'

# Ledger items as id<TAB>sources<TAB>status. Other lines are skipped.
ledger_items() {
  awk -F'|' "$LEDGER_AWK"' item() {
    for (i = 1; i <= 3; i++) gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
    print $1 "\t" $2 "\t" $3 }' "$1"
}

# The ledger as the voices see it: the sources field removed, so no voice sees
# who raised an item or how many did.
ledger_strip() {
  awk -F'|' -v OFS='|' "$LEDGER_AWK"'
    item() { $2 = ""; sub(/\|\|/, "|"); print; next } { print }' "$1"
}

# Where each of a voice's round-1 points went: "your 3 -> L7 (open)".
ledger_own() {
  ledger_items "$1" | awk -F'\t' -v v="$2" '{
    n = split($2, t, /[[:space:],]+/); cur = ""
    for (i = 1; i <= n; i++) {
      if (t[i] ~ /:/) { split(t[i], q, ":"); cur = q[1]; num = q[2] }
      else if (t[i] ~ /^[0-9]+$/) num = t[i]
      else { cur = t[i]; num = "" }
      if (cur == v && t[i] != "") print "your " (num == "" ? "point" : num) " -> " $1 " (" $3 ")"
    }
  }'
}

# Each open item to 2 launching voices that did not raise it, an open! item to 3,
# round-robin so the load stays even. "-" when no voice qualifies, "SHORT" when
# fewer qualify than the item needs.
assign_items() {
  ledger_items "$1" | awk -F'\t' -v launch="$2" '
    BEGIN { nv = split(launch, vs, " "); p = 0 }
    $3 ~ /^open/ && nv {
      k = ($3 ~ /^open!/) ? 3 : 2; split("", src)
      m = split($2, t, /[[:space:],]+/)
      for (i = 1; i <= m; i++) { split(t[i], q, ":"); src[q[1]] = 1 }
      out = ""; got = 0
      for (j = 0; j < nv && got < k; j++) {
        c = vs[(p + j) % nv + 1]
        if (!(c in src)) { out = out " " c; got++; last = j }
      }
      if (got) p = (p + last + 1) % nv
      print $1 (got ? out : " -") (got && got < k ? " SHORT" : "")
    }'
}

# Round 2 with a ledger: a brief for every voice, so any can be run. Each sees its
# own round-1 answer, where its points went, the stripped ledger and its
# assignment. $2 is the voices that launch first; only they get assignments.
build_r2_ledger() {
  local run="$1" d="$1/r2" n total common v own
  n=$(answered_r1 "$run" | wc -l); total=$(all_voices | wc -l)
  common="$(build_common "$run" 2)"
  assign_items "$run/ledger.md" "$2" > "$d/assign.txt.new"
  : > "$d/key.txt.new"
  for v in $(all_voices); do
    echo "Checker = $v" >> "$d/key.txt.new"
    {
      printf '%s\n\n%s of %s voices answered round 1.\n' "$common" "$n" "$total"
      printf '\n# YOUR ROUND-1 ANSWER\n\n'
      if answered "$run/r1/$v"; then cat "$run/r1/$v.md"; else echo "You gave none: you check only."; fi
      printf '\n\n# YOUR ITEMS IN THE LEDGER\n\n'
      own="$(ledger_own "$run/ledger.md" "$v")"
      echo "${own:-You raised no item in the ledger.}"
      printf '\n# THE LEDGER\n\n'
      ledger_strip "$run/ledger.md"
      printf '\n# YOUR ASSIGNMENT\n\n'
      own="$(awk -v v="$v" '{ for (i = 2; i <= NF; i++) if ($i == v) { printf "%s%s", s, $1; s = ", " } }' "$d/assign.txt.new")"
      if [[ -n "$own" ]]; then echo "Check these items first: $own"
      else echo "No item is assigned to you: check what you judge most consequential."; fi
    } > "$d/brief-$v.md.new"
  done
  for v in $(all_voices); do mv "$d/brief-$v.md.new" "$d/brief-$v.md"; done
  mv "$d/assign.txt.new" "$d/assign.txt"
  mv "$d/key.txt.new" "$d/key.txt"
}

# One file:line reference: FOUND, NO FILE or NO LINE. A bare name is looked up
# anywhere under cwd.
cite_ref() {
  local cwd="$1" ref="$2" path line f
  path="${ref%:*}"; line="${ref##*:}"
  f="$cwd/$path"
  [[ -f "$f" ]] || f="$(find "$cwd" -path '*/.git' -prune -o -type f -path "*/$path" -print -quit 2>/dev/null || true)"
  if [[ -z "$f" || ! -f "$f" ]]; then echo "NO FILE  $ref"
  elif (( 10#$line > $(wc -l < "$f") + 1 )); then echo "NO LINE  $ref (file has $(wc -l < "$f"))"
  fi
}

# Every file:line in an answer must exist under cwd, at that line. Prints the
# failures. Quotes are not checked: a quote of the source and the fix text a
# voice proposes look the same.
cmd_cites() {
  local run="$1" round="$2" cwd v f ref fails refs
  [[ -f "$run/r$round/voices" ]] || die "round $round was not started"
  shift 2
  cwd="$(cat "$run/cwd")"
  for v in ${*:-$(cat "$run/r$round/voices")}; do
    f="$run/r$round/$v"; answered "$f" || continue
    fails=""; refs=0
    while read -r ref; do
      [[ -n "$ref" ]] || continue
      refs=$((refs + 1)); fails+="$(cite_ref "$cwd" "$ref")"$'\n'
    done < <(tr -d '`*' < "$f.md" | grep -oE '\.?[A-Za-z0-9_][A-Za-z0-9_./-]*\.[A-Za-z0-9]+:[0-9]+' \
               | grep -E '^[^:]*[A-Za-z]' | sort -u)
    fails="$(grep . <<<"$fails" || true)"
    printf '%-10s %3s refs  %3s not found\n' "$v" "$refs" "$(grep -c . <<<"$fails" || true)"
    [[ -z "$fails" ]] || sed 's/^/    /' <<<"$fails"
  done
}

# Round-2 reply lines, grouped by item (L7, or Voice B 3 without a ledger), then the
# free lines, then coverage:
# assigned items a voice never named, answers with no reply line, unassigned items.
cmd_digest() {
  local run="$1" d="$1/r2" v
  [[ -f "$d/voices" ]] || die "round 2 was not started"
  for v in $(cat "$d/voices"); do
    answered "$d/$v" || { echo "FAILED   $v"; continue; }
    awk -v v="$v" '{ line = $0; gsub(/[*`]/, "", line); sub(/^[[:space:]>|-]+/, "", line) }
      match(line, /^(L[0-9]+|Voice [A-L][[:space:]]+[0-9]+)[[:space:]:|]+(DISPUTED|UNVERIFIED|EVIDENCE|CONFIRMED)/) {
        n = split(line, a, /[^A-Za-z0-9]+/)
        key = (a[1] == "Voice") ? sprintf("V%s%08d", a[2], a[3]) : sprintf("L%08d", substr(a[1], 2))
        printf "I\t%s\t%s\t%s\n", key, v, substr(line, 1, 400); next }
      match(line, /^(NEW|CHANGED|MINE|UNDERRATED|TOP|PICK)[[:space:]0-9]*:/) {
        printf "F\t%s\t%s\n", v, substr(line, 1, 400); next }
      match(line, /^NONE([^A-Za-z]|$)/) { printf "F\t%s\t%s\n", v, line; next }
      match(line, /^CHECKED:/) { printf "C\t%s\t%s\n", v, line }' "$d/$v.md"
  done > "$d/digest.tsv"
  echo "== by item"
  awk -F'\t' '$1 == "I"' "$d/digest.tsv" | sort -t$'\t' -k2,2 -k3,3 | cut -f3- | sed 's/\t/  /'
  echo "== new, changed, mine, picks"
  awk -F'\t' '$1 == "F" { print $2 "  " $3 }' "$d/digest.tsv"
  echo "== coverage"
  digest_coverage "$d"
}

# Answers with no verdict or NONE line, then per assigned item: a parsed checker
# that never named it, an item no parsed checker named, a short or empty assignment.
digest_coverage() {
  local d="$1" v ok=""
  for v in $(cat "$d/voices"); do
    answered "$d/$v" || continue
    # A CHECKED line alone is not a reply: its claims count only with a verdict or NONE.
    if awk -F'\t' -v v="$v" '($1 == "I" && $3 == v) || ($1 == "F" && $2 == v) { f = 1 } END { exit !f }' \
         "$d/digest.tsv"; then ok+=" $v"
    else echo "UNPARSED   $v: no reply line, read it with show; its CHECKED claims are ignored"; fi
  done
  [[ -f "$d/assign.txt" ]] || return 0
  awk -v ok="$ok " '
    FNR == NR { split($0, f, "\t"); v = ($1 == "I") ? f[3] : f[2]; t = " " $0
      while (match(t, /[^A-Za-z0-9]L[0-9]+/)) {
        named[v SUBSEP substr(t, RSTART + 1, RLENGTH - 1)]; t = substr(t, RSTART + RLENGTH) }
      next }
    $2 == "-" { print "UNASSIGNED " $1 ": verify it yourself"; next }
    { any = 0
      for (i = 2; i <= NF; i++) {
        if ($i == "SHORT") { print "SHORT      " $1 ": fewer checkers than it needs"; continue }
        if (index(ok, " " $i " ") == 0) continue
        if (($i SUBSEP $1) in named) any = 1; else print "MISSING    " $i " never named " $1
      }
      if (!any) print "UNCHECKED  " $1 ": no checker that answered named it" }' "$d/digest.tsv" "$d/assign.txt"
}

# The chain from round 1 to the answer: every numbered round-1 item maps to a
# ledger source, and every ledger item appears in synthesis.md. Exit 1 on a gap.
cmd_check() {
  local run="$1" v nums mapped miss gaps=0
  [[ -s "$run/ledger.md" ]] || die "no ledger.md in $run"
  for v in $(answered_r1 "$run"); do
    nums="$(grep -oE '^(#+ )?\*{0,2}[0-9]{1,2}[.)]' "$run/r1/$v.md" | grep -oE '[0-9]+' | sort -u || true)"
    mapped="$(ledger_items "$run/ledger.md" | cut -f2 | tr -s ' ,' '\n' | awk -F: -v v="$v" '
      $1 == v { cur = 1; if ($2 != "") print $2; next } /^[0-9]+$/ && cur { print; next } { cur = 0 }' | sort -u)"
    miss="$(comm -23 <(echo "$nums") <(echo "$mapped") | grep . | sort -n | xargs || true)"
    [[ -z "$miss" ]] || { echo "NOT IN LEDGER  $v items: $miss"; gaps=1; }
  done
  if [[ -s "$run/synthesis.md" ]]; then
    miss="$(ledger_items "$run/ledger.md" | cut -f1 | while read -r id; do
      grep -qw "$id" "$run/synthesis.md" || echo "$id"; done | xargs)"
    [[ -z "$miss" ]] || { echo "NOT IN SYNTHESIS  $miss"; gaps=1; }
  else
    echo "NO SYNTHESIS  write $run/synthesis.md"; gaps=1
  fi
  (( gaps )) || echo "chain complete: round 1 -> ledger -> synthesis"
  return "$gaps"
}

