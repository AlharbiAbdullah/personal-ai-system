#!/usr/bin/env bash
# Rotate every non-empty *.log file directly inside DIR, keeping KEEP old generations.
# Usage: rotate_logs.sh DIR KEEP
set -euo pipefail
export LC_ALL=C

usage() {
    echo "usage: rotate_logs.sh DIR KEEP   (DIR: existing directory, KEEP: integer >= 1)" >&2
    exit 2
}

[[ $# -eq 2 ]] || usage
dir=$1
keep=$2
[[ -d $dir ]] || usage
[[ $keep =~ ^[0-9]+$ ]] || usage
keep=$((10#$keep))
((keep >= 1)) || usage

rotate() {
    local log=$1 old n i
    # 1. drop generations that would fall off the end (N >= KEEP)
    for old in "$log".*; do
        [[ -e $old || -L $old ]] || continue
        n=${old#"$log".}
        [[ $n =~ ^[0-9]+$ ]] || continue
        if ((10#$n >= keep)); then
            rm -f -- "$old"
        fi
    done
    # 2. shift the remaining generations up by one, oldest first
    for ((i = keep - 1; i >= 1; i--)); do
        if [[ -e $log.$i ]]; then
            mv -f -- "$log.$i" "$log.$((i + 1))"
        fi
    done
    # 3. current log becomes generation 1; start a fresh empty log
    mv -f -- "$log" "$log.1"
    : >"$log"
}

shopt -s nullglob
for log in "$dir"/*.log; do
    [[ -f $log && ! -L $log && -s $log ]] || continue
    rotate "$log"
    echo "rotated ${log##*/}"
done
