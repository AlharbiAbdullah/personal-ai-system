"""Hook error logger. Makes swallowed exceptions visible."""

import json
import traceback

from .paths import get_learning_dir
from .time_utils import get_iso_timestamp

ERROR_LOG = get_learning_dir() / "system" / "hook-errors.jsonl"


def log_error(hook: str, err: Exception, context: str = "") -> None:
    try:
        ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "hook": hook,
            "error": type(err).__name__,
            "message": str(err)[:500],
            "context": context[:200],
            "traceback": traceback.format_exc()[:2000],
            "ts": get_iso_timestamp(),
        }
        with ERROR_LOG.open("a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass
