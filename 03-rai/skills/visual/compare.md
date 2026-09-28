---
name: compare
description: >
  Compare two-or-more options (tools, libraries, architectures, approaches) head-to-head as a
  single self-contained animated HTML file — each option drawn in the same visual language,
  a scored trade-off matrix, and a clear recommendation. Light/dark toggle. Invoked via
  /visual router. Use when John says "visual compare X vs Y" or is weighing options and
  wants them laid out visually.
---

# /visual · compare

Lay N options side by side so the choice is obvious — in a **single self-contained HTML file**.
Where `explain`'s diff toggle compares two states of *one* thing, `compare` is built for a
**decision**: each option gets its own scene, the criteria become a scored matrix, and the
artifact ends on a recommendation with its reasoning.

## How John uses it
1. He's weighing options — tools, libraries, architectures, vendors, approaches.
2. He says **"visual compare X vs Y"** (or "lay these out").
3. You build the HTML: each option drawn, scored against shared criteria, with a clear pick.
4. He scans the matrix, flips light/dark, drills into any option.

## Build it (from `references/engine.html` — see the router's Engine API)
1. **Get the facts straight first.** Each option's real shape, trade-offs, and constraints —
   no strawman of the one you're not picking. A dishonest comparison is worse than none.
2. **Clone the engine**, set `<body data-nav="tabs" data-skill="compare">`. Tabs let the reader
   jump straight to the option (or the matrix) they care about.
3. **Draw the decision, minimum words** (one framing line per section):
   - **The decision** — one line: what's being chosen and the criteria that matter.
   - **Option A / Option B / …** — one tab each: a `scene()` of that option with beats
     narrating how it handles the core flow. Internals go in click-open `detail-<id>` cards.
   - **Scorecard** — a styled table: criteria × options; use `.diff-add` / `.diff-rem`
     glyphs and color (never color alone) so wins/losses read at a glance. Animate totals
     with `.metric[data-count]` tiles.
   - **The pick** — the recommendation, *why* in one or two lines, and the conditions under
     which you'd choose differently.
4. **Signature feel — the side-by-side.** The payoff is seeing the options drawn in the
   same visual language: same lanes, same kinds, same roles, structurally parallel so
   differences pop. When two options share most structure, one `sceneDiff()` (Current =
   option A, Planned = option B) shows exactly what changes between them.

## When NOT to use
- One option clearly dominates — just say so. A comparison would be theater.
- Explaining how one existing thing works → use `explain`. Planning to build one → use `plan`.
