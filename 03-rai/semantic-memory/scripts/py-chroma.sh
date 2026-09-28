#!/usr/bin/env bash
# py-chroma.sh - Run a python script or inline python with chromadb available.
#
# System python3 (Arch, 3.14.x) has no chromadb module. This wrapper uses
# uv to run an ephemeral python 3.12 env with chromadb installed, cached
# in ~/.cache/uv so repeat invocations are fast.
#
# Usage:
#   py-chroma.sh /path/to/script.py [args...]
#   py-chroma.sh -c "import chromadb; ..."
#
# Why Python 3.12: chromadb wheels are published for 3.12, not yet 3.14.
#
# Why the offline probe: a plain `uv run --with chromadb` re-resolves against
# pypi.org on every call, so a DNS blip took the whole env down with it. The
# probe answers "is the cache warm?" without running the caller's script, so
# the script still executes exactly once and its exit code is the one we
# return. Only a cold cache reaches for the network.
set -euo pipefail

if uv run --quiet --offline --python 3.12 --with chromadb python3 -c '' 2>/dev/null; then
	exec uv run --quiet --offline --python 3.12 --with chromadb python3 "$@"
fi

exec uv run --quiet --python 3.12 --with chromadb python3 "$@"
