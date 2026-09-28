---
name: trace
description: >
  Walk a bug, incident, or request lifecycle through a system as a single self-contained
  animated HTML file — a packet pulses along the real path to the failure point, time-stamped
  beats replay what happened when, and a hypothesis list shows what was ruled in and out.
  Light/dark toggle. Invoked via /visual router. Use when John says "visual trace" /
  "visualize this bug/incident/request".
---

# /visual · trace

Make a bug or an incident *legible* by animating its path through the system — in a **single
self-contained HTML file**. A pulse rides the real edges to the **point of failure**,
time-stamped beats replay what happened when, and a hypothesis list shows what was ruled in
and out. A debugging/postmortem companion to the `debugger` agent.

## How John uses it
1. Something broke, or a request's lifecycle is hard to hold in the head.
2. He says **"visual trace"** (or "visualize this bug / incident / request path").
3. You build the HTML: the path, the failure, the timeline beats, the hypotheses, the fix.
4. He steps the beats, follows the pulse, sees where it went wrong.

## Build it (from `references/engine.html` — see the router's Engine API)
1. **Reconstruct the real path first.** Read the code, the logs, the trace. Every node, edge,
   and timestamp must be real — a trace that invents the path teaches the wrong lesson.
2. **Clone the engine**, set `<body data-nav="scroll" data-skill="trace">`. Scroll suits a
   narrative ("here's what happened, in order").
3. **Draw the incident, minimum words** (one framing line per section):
   - **What broke** — the symptom in ONE line + the blast radius.
   - **The path** — a `scene()` of the request/data route; the failure node gets
     `role:"red"`. This is the centerpiece.
   - **Timeline = beats with `t` labels.** Give each beat a timestamp (`t:"09:14"` or
     `t:"40ms"`) so the ticks read as a timeline; each beat's caption is one event, its
     focus + pulse move the packet one hop closer to the failure.
   - **Hypotheses** — a card list of what was suspected, ruled in (green) or out (red)
     using `.diff-add` / `.diff-rem` glyphs (not color alone).
   - **Root cause & fix** — one line each: the cause, the fix, the guardrail against recurrence.
4. **Signature animation — the pulse to failure.** The final beats pulse along the real
   edges into the red failure node, then stop — the reader watches the request die exactly
   where it died. No pulse past the failure point.

## When NOT to use
- A one-line root cause is enough — just say it.
- Explaining healthy steady-state behavior → use `explain`. Planning a fix's build → use `plan`.
