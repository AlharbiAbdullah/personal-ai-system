"""Tab state setter: writes the terminal title (OSC) and persists the per-session state
that question-answered and the pi bridge read back."""

import json
import sys

from .paths import get_runtime_dir
from .tab_constants import TAB_STATES

TAB_TITLES_DIR = get_runtime_dir() / "tab-titles"


def set_tab_title(title: str):
    """Set the terminal tab title with an OSC escape sequence."""
    try:
        # OSC 1 ; title ST (set tab/icon name) — synchronous, goes over tty
        sys.stderr.write(f"\033]1;{title}\007")
        sys.stderr.flush()
    except Exception:
        pass


def set_tab_state(state: str, session_id: str = "", detail: str = ""):
    """
    Set tab to a named state.
    States: thinking, working, question, completed, error, idle.
    """
    base = TAB_STATES.get(state, state)
    title = f"{base}: {detail}" if detail else base
    set_tab_title(title)
    _persist_state(session_id, state, title)


def read_tab_state(session_id: str) -> dict:
    """Read persisted tab state."""
    path = TAB_TITLES_DIR / f"{session_id}.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _persist_state(session_id: str, state: str, title: str):
    """Persist tab state to disk for cross-hook coordination."""
    if not session_id:
        return
    try:
        TAB_TITLES_DIR.mkdir(parents=True, exist_ok=True)
        path = TAB_TITLES_DIR / f"{session_id}.json"
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text())
            except Exception:
                pass
        # capture the OLD title before overwriting — the previous order set
        # previous_title AFTER title, so it always equaled the new title and
        # question-answered's "restore previous" never actually restored.
        data["previous_title"] = data.get("title", "")
        data["state"] = state
        data["title"] = title
        path.write_text(json.dumps(data))
    except Exception:
        pass
