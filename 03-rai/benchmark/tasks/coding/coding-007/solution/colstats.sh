#!/usr/bin/env bash
# Statistics for one numeric column of a delimited text file with a header row.
# Usage: colstats.sh [-d DELIM] FILE COLUMN
set -euo pipefail

usage() {
    echo "usage: colstats.sh [-d DELIM] FILE COLUMN" >&2
    exit 2
}

delim=","
while getopts ":d:" opt; do
    case $opt in
        d) delim=$OPTARG ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))

[[ $# -eq 2 ]] || usage
file=$1
column=$2
[[ ${#delim} -eq 1 ]] || usage
[[ -f $file && -r $file && -s $file ]] || usage

DELIM=$delim COLUMN=$column awk '
function trim(s) {
    sub(/^ +/, "", s)
    sub(/ +$/, "", s)
    return s
}
BEGIN {
    FS = ENVIRON["DELIM"]
    col = ENVIRON["COLUMN"]
}
{ sub(/\r$/, "") }
NR == 1 {
    for (i = 1; i <= NF; i++) {
        if (trim($i) == col) { idx = i; break }
    }
    if (!idx) {
        print "column not found: " col > "/dev/stderr"
        missing = 1
        exit
    }
    next
}
$0 == "" { next }
{
    v = trim($idx)
    if (v ~ /^[+-]?[0-9]+(\.[0-9]+)?$/) {
        v += 0
        if (n == 0 || v < lo) lo = v
        if (n == 0 || v > hi) hi = v
        sum += v
        n++
    } else {
        skipped++
    }
}
END {
    if (missing) exit 3
    print "count=" n + 0
    if (n > 0) printf "sum=%.2f\nmin=%.2f\nmax=%.2f\nmean=%.2f\n", sum, lo, hi, sum / n
    print "skipped=" skipped + 0
}
' "$file"
