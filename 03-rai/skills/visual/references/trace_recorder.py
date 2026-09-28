#!/usr/bin/env python3
"""Record a Python program's execution as debugger stops, for /visual debug.

Usage:
    python3 trace_recorder.py program.py [--max 400] > steps.json

Emits a JSON array. One entry per debugger stop (call / line / return / exception),
only for frames in program.py (stdlib frames are skipped), in the exact order a step
debugger would visit them:

    {"n": 12, "event": "line", "line": 37,
     "stack": [{"fn": "<module>", "line": 37}, {"fn": "Stage.__enter__", "line": 9}],
     "locals": {"self": "<Stage bronze>", "name": "'bronze'"},
     "ret": "<Stage bronze>",          # only on return events: the (return) row
     "exc": "ValueError('x')",         # only on exception events
     "out": "opened bronze\\n"}         # stdout produced since the previous stop

Locals show the TOP frame only, plain names only. Dunder names are dropped except
dunder functions/classes defined in the program itself (a `__enter__` he wrote is
worth seeing; `__builtins__` is not). Values are repr(), truncated to 60 chars.
Paste the array as `steps` into debug(id, {...}) in the HTML.
"""

from __future__ import annotations

import io
import json
import runpy
import sys
from pathlib import Path

MAX_STEPS = 400
TRUNC = 60


def _short(v: object) -> str:
    try:
        s = repr(v)
    except Exception:  # noqa: BLE001 - repr of a half-built object may raise
        s = f"<{type(v).__name__}>"
    return s if len(s) <= TRUNC else s[: TRUNC - 1] + "…"


def _own(v: object, target: str) -> bool:
    """A dunder defined in the traced program (his own __enter__), not a builtin."""
    mod = getattr(v, "__module__", None)
    return (
        mod == "__main__"
        or getattr(getattr(v, "__code__", None), "co_filename", "") == target
    )


def _locals(frame, target: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in frame.f_locals.items():
        if k.startswith("__") and not _own(v, target):
            continue
        out[k] = _short(v)
    return out


def _stack(frame, target: str) -> list[dict[str, object]]:
    frames = []
    f = frame
    while f is not None:
        if f.f_code.co_filename == target:
            name = getattr(f.f_code, "co_qualname", f.f_code.co_name)
            frames.append({"fn": name, "line": f.f_lineno})
        f = f.f_back
    frames.reverse()  # bottom (<module>) first, top frame last
    return frames


def record(path: str, max_steps: int) -> list[dict[str, object]]:
    target = str(Path(path).resolve())
    steps: list[dict[str, object]] = []
    real_stdout = sys.stdout
    buf = io.StringIO()

    def drain() -> str:
        """Text printed since the previous stop. Attached to the stop that comes AFTER the
        print line ran: exactly when it appears in the IDE terminal while stepping."""
        text = buf.getvalue()
        buf.seek(0)
        buf.truncate()
        return text

    def tracer(frame, event, arg):
        if frame.f_code.co_filename != target:
            return None  # do not descend into stdlib frames
        if len(steps) >= max_steps:
            sys.settrace(None)
            return None
        if event == "call" and frame.f_code.co_name == "<module>":
            return tracer  # a debugger never stops on the module "call"; first stop is line 1
        step: dict[str, object] = {
            "n": len(steps) + 1,
            "event": event,
            "line": frame.f_lineno,
            "stack": _stack(frame, target),
            "locals": _locals(frame, target),
        }
        printed = drain()
        if printed:
            step["out"] = printed
        if event == "return":
            step["ret"] = _short(arg)
        elif event == "exception":
            step["exc"] = _short(arg[1])
        steps.append(step)
        return tracer

    sys.stdout = buf
    sys.settrace(tracer)
    try:
        runpy.run_path(target, run_name="__main__")
    except SystemExit:
        pass
    except Exception as e:  # noqa: BLE001 - the crash IS the thing to show
        if steps:
            steps[-1]["exc"] = _short(e)
    finally:
        sys.settrace(None)
        sys.stdout = real_stdout
    tail = drain()
    if tail and steps:
        steps[-1]["out"] = str(steps[-1].get("out", "")) + tail
    return steps


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    max_steps = MAX_STEPS
    if "--max" in args:
        i = args.index("--max")
        max_steps = int(args[i + 1])
        del args[i : i + 2]
    steps = record(args[0], max_steps)
    json.dump(steps, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
