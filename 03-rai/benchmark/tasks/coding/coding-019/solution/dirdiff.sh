#!/usr/bin/env bash
# Compare two directory trees by file content (sha256).
# Usage: dirdiff.sh [-q] [-x PATTERN]... OLD NEW
set -euo pipefail
export LC_ALL=C

usage() {
    echo "usage: dirdiff.sh [-q] [-x PATTERN]... OLD NEW" >&2
    exit 2
}

quiet=0
excludes=()
while getopts ":qx:" opt; do
    case $opt in
        q) quiet=1 ;;
        x) excludes+=("$OPTARG") ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))
[[ $# -eq 2 ]] || usage
old=$1
new=$2
[[ -d $old && -d $new ]] || usage

is_excluded() {
    local pattern
    for pattern in "${excludes[@]}"; do
        # shellcheck disable=SC2053  # unquoted on purpose: glob match, * also matches /
        [[ $1 == $pattern ]] && return 0
    done
    return 1
}

# scan DIR NAME: fill the associative array NAME with relative path -> sha256
scan() {
    local dir=$1 rel sum
    local -n hashes=$2
    while IFS= read -r -d '' rel; do
        rel=${rel#./}
        is_excluded "$rel" && continue
        sum=$(sha256sum <"$dir/$rel")
        hashes["$rel"]=${sum%% *}
    done < <(cd -- "$dir" && find . -type f -print0)
}

declare -A old_hashes=() new_hashes=()
scan "$old" old_hashes
scan "$new" new_hashes

differences=$(
    for rel in "${!old_hashes[@]}"; do
        if [[ -z ${new_hashes["$rel"]+set} ]]; then
            printf 'D %s\n' "$rel"
        elif [[ ${new_hashes["$rel"]} != "${old_hashes["$rel"]}" ]]; then
            printf 'M %s\n' "$rel"
        fi
    done
    for rel in "${!new_hashes[@]}"; do
        [[ -n ${old_hashes["$rel"]+set} ]] || printf 'A %s\n' "$rel"
    done
)

if [[ -z $differences ]]; then
    exit 0
fi
((quiet)) || printf '%s\n' "$differences" | sort -t ' ' -k 2
exit 1
