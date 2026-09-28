#!/bin/sh
# Build the M3 fixture repo: tipcalc as it was before project-init (branch master, one commit),
# renamed to main, with a tracked uv.lock, pytest as a dev dependency and project-init's spec
# plugin (templates/tests/conftest.py) in one commit on top.
#
# usage: make_tipcalc.sh [<dest> [<tipcalc repo>]]
#   <dest>          a path that does not exist yet; default: <new temp dir>/tipcalc
#   <tipcalc repo>  default: $TIPCALC_SOURCE, else ~/projects/tipcalc
#
# The source repo is only read: `git clone --no-local` copies its objects, and origin is removed
# right after, so nothing the fixture does can reach it. The commit uses the caller's
# GIT_AUTHOR_* / GIT_COMMITTER_* when set, else a fixture identity.
set -eu

here=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
skill=$(dirname -- "$(dirname -- "$here")")
conftest="$skill/templates/tests/conftest.py"
dest=${1:-$(mktemp -d)/tipcalc}
source=${2:-${TIPCALC_SOURCE:-$HOME/projects/tipcalc}}

if [ -e "$dest" ]; then
  echo "make_tipcalc: $dest already exists" >&2
  exit 1
fi
[ -f "$conftest" ] || { echo "make_tipcalc: missing $conftest" >&2; exit 1; }

git clone -q --no-local --branch master "$source" "$dest"
cd "$dest"
git remote remove origin
git branch -m master main

uv lock -q
uv add -q --dev pytest
mkdir -p tests
cp "$conftest" tests/conftest.py
cat >>pyproject.toml <<'EOF'

[tool.pytest.ini_options]
addopts = "-q --strict-markers -p no:cacheprovider"
markers = ["spec(*ids): scenario ids this test proves"]
EOF
printf '\n# project-init scratch\n.cache/\n.agent/\n' >>.gitignore

git add -A
git -c user.name="tipcalc fixture" -c user.email="fixture@example.invalid" \
  commit -q -m "build: track uv.lock, add pytest and the spec plugin"
echo "make_tipcalc: $dest on main ($(git rev-parse --short HEAD))"
