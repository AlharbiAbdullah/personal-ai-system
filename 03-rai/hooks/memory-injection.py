#!/usr/bin/env python3
"""
memory-injection.py — UserPromptSubmit hook (Memory v3). Embeds the prompt, queries the
stores, and injects a CHEAP pointer to relevant memory for the model to expand on demand.

v3 tuning (Phase D):
- relevance floor  : matches below MIN_RELEVANCE are dropped (top-k-regardless injected noise)
- session dedup    : ids already injected this session are skipped — the practical Tier-0
                     for a hook (state: ~/.local/state/rai/runtime/injected/<session_id>.json,
                     cleaned by session-summary + the orphan sweep)
- hard 2s alarm    : the original v2 plan's timeout, now real

Registered (cutover 2026-06-28). Runs under py-chroma.sh (needs chromadb). Fails open
(never blocks a prompt). Every invocation logs to hook-perf.jsonl via hook_timer so
/sanity HOOK-4 can prove it is still firing.

Test:  py-chroma.sh memory-injection.py   (with a JSON prompt on stdin)
"""

import json
import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from lib.paths import get_runtime_dir  # noqa: E402

MIN_RELEVANCE = 0.35
INJECTED_DIR = get_runtime_dir() / "injected"

try:
    from lib.memory_retrieval import query_semantic, query_episodic
except Exception:
    sys.exit(0)


def _alarm(signum, frame):
    sys.exit(0)


signal.signal(signal.SIGALRM, _alarm)


def _load_seen(session_id: str) -> set:
    if not session_id:
        return set()
    p = INJECTED_DIR / f"{session_id}.json"
    try:
        if p.exists():
            return set(json.loads(p.read_text()))
    except Exception:
        pass
    return set()


def _save_seen(session_id: str, seen: set):
    if not session_id:
        return
    try:
        INJECTED_DIR.mkdir(parents=True, exist_ok=True)
        (INJECTED_DIR / f"{session_id}.json").write_text(json.dumps(sorted(seen)))
    except Exception:
        pass


def main():
    # Armed here (not at import) so the budget covers exactly the work: stdin, state,
    # queries. The first-query embedding-model load is covered too — session-start's
    # detached warmup (M3) keeps that path page-cached so 2s is a real budget, not a
    # cold-start death sentence.
    signal.alarm(2)
    try:
        data = json.loads(sys.stdin.read())
    except Exception:
        sys.exit(0)
    prompt = (data.get("prompt") or "").strip()
    if len(prompt) < 8:
        sys.exit(0)
    session_id = data.get("session_id", "")
    seen = _load_seen(session_id)

    try:
        facts = [f for f in query_semantic(prompt, top_k=3)
                 if f.get("relevance", 0) >= MIN_RELEVANCE and f.get("id") not in seen]
        eps = [e for e in query_episodic(prompt, top_k=2)
               if e.get("relevance", 0) >= MIN_RELEVANCE and e.get("session_id") not in seen]
    except Exception:
        sys.exit(0)
    if not facts and not eps:
        sys.exit(0)

    lines = []
    for f in facts:
        lines.append(f"  · {f['content'][:130]}")
        seen.add(f.get("id"))
    for e in eps:
        lines.append(f"  · past session {e.get('date')} {e.get('context', '')} — /recall to open")
        seen.add(e.get("session_id"))
    _save_seen(session_id, seen)
    print("[memory v3] possibly relevant — expand only if useful:\n" + "\n".join(lines))


if __name__ == "__main__":
    # Wrap in hook_timer so every fire is recorded in hook-perf.jsonl (observability: /sanity
    # HOOK-4 flags a hook that stops appearing). main()'s own sys.exit(0) early-outs still log via
    # the timer's finally. Fall back to a bare run only if the timer module can't load.
    try:
        from lib.hook_timer import hook_timer
    except Exception:
        hook_timer = None
    if hook_timer is not None:
        with hook_timer("memory-injection"):
            main()
    else:
        main()
