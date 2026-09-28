---
name: explain
description: >
  Explain something that ALREADY exists — a system, codebase, concept, process, or
  decision — as a single self-contained animated HTML file with a light/dark toggle.
  Diagram-first, minimum words: auto-laid-out scenes narrated beat by beat, packets
  pulsing along the real runtime path. A communication artifact, NOT a gate. Invoked
  via /visual router. Use when John says "visual explain" / "explain this visually".
---

# /visual · explain

Explain something in a **single self-contained HTML file**, not chat prose. Drawings do
the explaining: an overview map plus zoomed flow scenes, each narrated beat by beat, with
packets that trace the real runtime path.

The point is *understanding*, not approval and not testing. It's a reference the reader
steps through or jumps around in — onboarding to a subsystem, unpacking a tricky flow,
walking a decision. No gate; usable anytime, including after code ships.

## How John uses it
1. You're discussing something — a system, a piece of code, a concept, a choice.
2. He says **"visual explain"** (or "explain this visually").
3. You **create the HTML** and live-update it as the explanation sharpens.
4. He opens it in a browser, steps the beats, toggles light/dark.

## Build it (from `references/engine.html` — see the router's Engine API)
1. **Understand first** — read the real files/symbols, or pin the concept down precisely.
   You can't draw a clean picture of something you only half-know. The diagram must show the
   real mechanism, not a stand-in analogy. That is what makes it click for him.
2. **Clone the engine**, set `<body data-nav="scroll" data-skill="explain">` (`tabs` if
   it's truly random-access reference).
3. **Draw 2-4 scenes, minimum words** (one framing line each; delete unused sections):
   - **The map** — one `scene()` of the whole system: lanes for the major bands, kinds
     for meaning (stores as cylinders, decisions as diamonds), a legend keyed by role.
   - **Zoomed flows** — one scene per tricky path: the request route, the failure branch,
     the routing decision. More scenes beat more paragraphs.
   - **Numbers** — stat tiles (`data-count`) if real numbers carry the story.
   - **Recap** — ONE sentence, optional calibration question.
4. **Signature: the narrated trace.** Beats are the explanation. Beat 0 = the overview
   (often with a pulse chain across the main path); each later beat dims to one subgraph
   and pulses the edges it narrates. The path must mirror the real runtime path — never
   decorate. Put node internals in click-to-open `detail-<id>` cards, not in the flow.
5. **Update live** — re-edit the same file; tell him to refresh.

## When NOT to use
- A one-sentence answer would do — just say it.
- Planning a feature for approval → use `plan`. Teaching so he can *do* it → use `teach`.
- The thing is genuinely simple — a picture would add ceremony, not clarity.
