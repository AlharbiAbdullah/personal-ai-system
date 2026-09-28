---
name: debug
description: >
  Replay a program inside a step debugger as a single self-contained animated HTML file:
  code pane with the current line, call stack, variables with the (return) row, terminal,
  and Step Over / Into / Out / Continue that behave exactly like the IDE's. Every stop is
  recorded from a REAL run (references/trace_recorder.py), never imagined, and look-notes
  point at the one thing to see at each stop that matters. Light/dark toggle. Invoked via
  /visual router. Use when John says "visual debug" / "debug this visually" / "show me
  what the debugger would show".
---

# /visual · debug

Mimic the step debugger in a **single self-contained HTML file**: the Cursor panels (code,
Call Stack, Variables, Terminal) replayed stop by stop, with a **look-note** at each stop
that matters saying what to see and outlining the row or panel that shows it. The
difference from `trace`: trace follows one request across a *system* (nodes and edges);
debug follows one program at *line* altitude (frames, locals, returns, prints).

## How John uses it
1. He has a program, usually a learning exercise in the playground or `06-learning/`, and
   wants to see how it *actually* executes: which frame appears when, what a `(return)`
   row holds, when a local changes, what prints when.
2. He says **"visual debug"** plus a file path or the code inline.
3. You record a real run, build the HTML, write the look-notes.
4. He steps it with F10 / F11 / F5 exactly as in Cursor. The notes tell him where to look.

## Build it (from `references/engine.html`; see the router's Engine API)
1. **Record, never imagine.**
   ```
   python3 ~/helm/03-rai/skills/visual/references/trace_recorder.py program.py > steps.json
   ```
   Every stop, frame, local, return value and printed line in the HTML comes from that
   run. Pin inputs and randomness first. Keep it small: under ~150 stops (`--max` caps it);
   shrink a 1000-iteration loop to 2-3 iterations before recording. Non-Python: the recorder
   is Python-only; transcribe stops by hand from a real debugger session into the same JSON
   shape and say so in the artifact.
2. **Clone the engine**, set `<body data-nav="scroll" data-skill="debug">`. Delete the
   sample sections you do not use.
3. **Draw the program, minimum words** (one framing line per section):
   - **The shape** (only if more than one function): a `scene()` with functions as nodes
     and calls as edges, one beat per call. Skip it for a single function.
   - **Step it**, the centerpiece: `debug("dbg-run", {file, code, steps, breakpoints, notes})`.
     `code` = the exact source the recorder ran (line numbers must match), `steps` = the
     JSON pasted verbatim, `breakpoints` = where he would set them (Continue jumps between
     them; he can toggle more in the gutter).
   - **Look-notes**: `notes` keyed by stop number (`"18"`), or by `"<line>:<event>"` when
     the number may shift (`"8:return"`). Four to eight per program, at the stops that
     teach: the first call into a frame (stack grows), a `(return)` row (who reads this
     value?), a local that changed, the terminal filling one stop late, an exception row.
     Each note is ONE sentence saying what to see, plus `hi` targets so the panel or row is
     outlined: `"stack"`, `"stack:Stage.__enter__"`, `"vars"`, `"vars:self"`,
     `"vars:(return)"`, `"vars:(exception)"`, `"term"`, `"code"`. A note that needs a
     paragraph is two notes on two stops.
   - **Predict checkpoint** (optional, at most two): `.chips[data-predict]` above the
     debugger: "what will the `(return)` row show at stop 18?" Borrowed from teach.
   - **Recap**: one line, the one thing the run proved.
4. **Signature interaction: Step Over vs Step Into.** The buttons are computed from real
   stack depth, so they behave exactly like the IDE's: Step Over from a call line jumps
   past every stop inside the callee; Step Into lands on the `def` line with the new frame
   on the stack; Step Out returns to the caller; Continue runs to the next breakpoint or
   exception. Keyboard: F10 / F11 / Shift+F11 / F5. Play auto-steps into everything.

## What the panels show (the IDE, minus the noise)
- **Call stack**: top frame first. A class body is its own frame, as the IDE shows it.
- **Variables**: top frame only, plain names only. Dunder names are dropped except the
  ones he wrote himself (his `__enter__` is a real artifact; `__builtins__` is noise). This
  is the standing rule from his debugger sessions. A green `(return) fn` row on return
  stops, a red `(exception)` row on exception stops, changed values in accent.
- **Terminal**: cumulative stdout, newest chunk in accent. It fills one stop AFTER the
  print line, as in the IDE. Write a look-note on that the first time it happens.

## When NOT to use
- The question is a path across services, not a program's frames → `trace`.
- He wants to learn the *concept* the program illustrates, with prediction and retrieval
  → `teach` (which may embed one `debug()` block).
- The program is trivial: three stops teach nothing. Just run it.
