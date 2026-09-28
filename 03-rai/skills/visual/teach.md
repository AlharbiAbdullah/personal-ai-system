---
name: teach
description: >
  Teach a concept so John genuinely LEARNS it — not just understands it once. A single
  self-contained animated HTML file that forces prediction, retrieval, and forced build-up:
  diagram-first scenes revealed beat by beat, predict-then-reveal (wrong guess flashes red),
  confidence calibration. Light/dark toggle. Invoked via /visual router. Use when John
  says "visual teach" / "teach me X visually".
---

# /visual · teach

Teach a concept in a **single self-contained HTML file** so the reader can *do* something
afterward — not just nod along. The difference from `explain`: teach makes the learner
**generate, predict, and retrieve** rather than passively receive. The interaction *is* the
learning; the beats *are* the explanation of a process unfolding.

Built on evidence-based mechanisms — generation effect, prediction-error, retrieval practice,
worked-example→completion fading, desirable difficulty, misconception confrontation.

## How John uses it
1. He wants to actually learn something — a concept, an algorithm, a system's mental model.
2. He says **"visual teach"** (or "teach me X visually").
3. You **create the HTML** that walks him from zero, making him predict and retrieve along the way.
4. He works through it top to bottom (the order is the lesson).

## Build it (from `references/engine.html` — see the router's Engine API)
1. **Get it correct first.** A teaching artifact that teaches a wrong model is worse than none.
   Ground in the real thing; verify the mental model before drawing it. Build the beats from
   the actual mechanism. An analogy in the hook is a way in, not a substitute for showing it.
2. **Clone the engine**, set `<body data-nav="scroll" data-skill="teach">`. **Scroll = forced
   build-up** — no skipping ahead; each scene stages in as it enters view.
3. **Draw the ramp, minimum words** (one framing line per section):
   - **Hook + misconception** — one line: "You probably think…", then a scene set up to break it.
   - **Build-up** — the model as beats: each beat adds one relationship with a one-line
     caption (focus grows beat by beat over the same scene).
   - **Worked example → completion → solo** — the same scene revisited with decreasing
     scaffolding (later beats show less, ask more).
   - **Retrieval checkpoints** — `.chips[data-predict]` questions *between* scenes, not piled at the end.
   - **Self-explain prompts** — `.selfx`: commit a reason before the canonical one reveals.
   - **Calibration** — `.calib` at the close: rate confidence, answer, see confident-but-wrong.
4. **Signature interaction — predict-then-reveal.** Before each key reveal, the learner
   commits a guess via `.chip[data-correct]`; only then advance the beat that shows the
   truth. For misconceptions, pulse the WRONG edge first (role `red`), then the correct
   path — the **prediction-error contrast is the teaching moment**.
5. **Pacing & escape hatch.** Keep gating *light* — predict-then-reveal already supplies the
   desirable difficulty; don't lock whole sections. The beats bar lets a re-reader skip
   ahead freely, so re-reads aren't punished. Teach-specific interaction logic lives in the
   teach HTML, not the shared engine, so the other sub-skills stay lean.

## When NOT to use
- He just needs to *understand* it once, as reference → use `explain`.
- Planning a feature → use `plan`.
- The concept is trivial — prediction/retrieval would be busywork.
