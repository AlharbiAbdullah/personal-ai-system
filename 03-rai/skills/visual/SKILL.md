---
name: visual
description: >
  Visual explainer router. USE WHEN John wants something rendered as a single
  self-contained, animated, beautiful HTML file he opens in a browser: diagram-first,
  minimum words, with a light/dark toggle and auto-laid-out system diagrams narrated
  beat by beat. Routes between seven sub-skills: plan (render a planned change, such as
  an SDD change folder, for approval), explain (explain something that ALREADY exists), teach (teach a
  concept so he LEARNS it), compare (weigh options head-to-head), trace (walk a
  bug/incident/request path), data (explain a schema/dataset/pipeline), debug (replay a
  program in a step debugger: frames, locals, (return) rows, step over/into, recorded from
  a real run). All share ONE engine (references/engine.html). Triggers: "visual
  plan/explain/teach/compare/trace/data/debug", "explain this visually", "debug this
  visually".
---

# Visual

Turn an idea into a **single self-contained HTML file**: double-click to open, zero
build step, zero server. Diagram-first: auto-laid-out scenes narrated beat by beat,
minimum words, a light/dark toggle. Seven sub-skills, one shared engine.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Render a planned change (an SDD change folder or `.agent/plan.md`) for review before approval | plan | `plan.md` |
| Explain something that ALREADY exists (a system, codebase, concept, decision) | explain | `explain.md` |
| Teach a concept so the reader genuinely LEARNS it (predict / retrieve / build-up) | teach | `teach.md` |
| Weigh two-or-more options head-to-head; needs a scored matrix + a pick | compare | `compare.md` |
| Walk a bug / incident / request lifecycle; pulse to the failure point + timed beats | trace | `trace.md` |
| Explain a schema / dataset / data model / pipeline (ER, medallion layers, lineage) | data | `data.md` |
| Replay a program in a step debugger: current line, call stack, locals, `(return)` rows, terminal; Step Over/Into/Out/Continue from a REAL recorded run | debug | `debug.md` |

## How to use

1. Pick the sub-skill by intent (see the routing table + disambiguation below).
2. `Read` that file in this directory.
3. Build the HTML by cloning `references/engine.html` (see **The engine** below) and following the sub-skill's spec.

## When two could fit
- **plan vs explain:** plan argues a *future* state and gates code (no source edits until approved). explain describes a *present* state: no gate, usable anytime.
- **explain vs teach:** explain makes you *understand* (random-access reference). teach makes you *able to do it*: it forces you to predict and retrieve, in a forced build-up order. If there's a quiz, it's teach.
- **explain vs compare:** explain unpacks *one* thing; compare puts two or more side by side and ends on a recommendation.
- **explain vs trace:** explain shows steady-state behavior; trace follows *one specific* run/bug to where it went wrong (failure node + timed beats).
- **explain vs data:** data is explain specialized for schemas/datasets: entity cards, FK edges, medallion layers, lineage.
- **trace vs debug:** trace follows one request across a *system* (nodes, edges, failure node). debug follows one *program* at line altitude (frames, locals, returns, prints) inside a mimicked IDE debugger.
- **teach vs debug:** teach makes him predict and retrieve a concept; debug shows what the debugger *would show* for a real run, with look-notes. A teach artifact may embed one `debug()` block.

## Hard rules (all sub-skills)

1. **MINIMUM WORDS. This is a drawing tool, not an article tool.** Every section leads
   with a diagram; prose is ONE framing line (class `cap`) plus the beat captions. If you
   are writing a paragraph, draw another scene instead. Scenes are cheap. Aim for 2-4
   scenes per artifact: an overview map, then zoomed flows.
2. **It must be beautiful.** Warm paper + ink + terracotta accent in *both* themes
   (Anthropic-style oat light / warm graphite dark). Space Grotesk headings, Source Serif
   for the few body lines, Plex Mono labels. A plain or boxy result fails the brief.
3. **Never place coordinates.** Diagrams go through the engine's `scene()`: you declare
   nodes / edges / lanes / beats, the engine measures labels, ranks columns, and routes
   edges. Node kinds carry meaning (store cylinder, decision diamond, queue, actor, doc,
   dashed ext). Pick the right kind, not a generic box.
4. **Animation must aid understanding, not decorate.** Beats dim to a focused subgraph and
   pulse packets along real edges; the staged entry rises in rank order. No ambient motion.
5. **Ground it in reality.** Explaining/planning code → read the real files, schemas,
   symbols first; every node and edge maps to something real. Teaching a concept → get it
   correct; no diagram implying a structure that isn't true.
6. **Light/dark toggle + reduced-motion are non-negotiable.** Both are wired into the
   engine. The theme toggle is pure CSS variables (no redraw path to break), and every
   animation honors the global `REDUCED` guard.

## The engine: `references/engine.html`

ONE shared file is the source of truth for all seven sub-skills (deliberate: seven hand-synced
templates would drift). It is a crisp auto-layout engine. Zero CDN scripts: works offline except
webfonts.

Clone the whole file, then:
- Set `<body data-nav="…" data-skill="…">`: `data-nav` picks navigation (`scroll` linear
  build-up · `tabs` random access · `deck` slides), `data-skill` is
  `plan|explain|teach|compare|trace|data|debug` (drives the badge).
- Replace `{TITLE}` / `{SUBJECT}` / `{DATE}`, fill or DELETE sections, edit `buildScenes()`.

**Scene API** (each scene = one `<svg id="d-X">` + optional `#lg-X` legend, `#bt-X` beats
bar, `#cap-X` caption, all auto-built):

```js
scene("d-X", {
  lanes: [{id:"live", label:"Live session"}, …],          // optional horizontal bands
  nodes: [{id, label, sub?, kind?, lane?, rank?, role?}],  // NO coordinates, ever
  edges: [{from, to, label?, dashed?, role?}],
  beats: [{caption, focus?:[ids], pulse?:[[from,to],…], t?}], // beat 0 usually = overview (no focus)
  legend: [{role, label}]                                  // chips double as role filters
})
```

- `kind`: `svc` (default) · `store` cylinder · `queue` · `actor` · `job` · `decision`
  diamond · `doc` dog-ear · `ext` dashed external.
- `role` colors: `accent` · `blue` · `green` · `gold` · `plum` · `red` · `mute` (default).
- `rank`: explicit column when the longest-path default isn't right (use it to keep
  total columns ≤ 6 so the drawing stays big).
- Layout flows left→right. Same-rank cross-lane edges drop vertically; backward edges
  route through a corridor below (that's how a loop closes).
- A node with a matching `<div id="detail-ID" class="card note detail">` opens it on
  click: click-depth, never reading flow.

| Helper | What it does |
|--------|--------------|
| `scene(id, spec)` | Auto-layout + render + beats bar + legend + staged entry. The workhorse. |
| beats (in spec) | THE narration channel: each beat dims to `focus`, runs `pulse` packets along real edges, shows one caption. Prev/Next/ticks/Play come free. |
| `sceneDiff(id, spec)` | **plan signature:** nodes/edges carry `status:"add"|"remove"`; renders a Current/Planned toggle: kept nodes glide (FLIP), removed ghost, added arrive badged. Needs `<div class="ctrls" id="ab-X">`. |
| `debug(id, {file, code, steps, breakpoints, notes})` | **debug signature:** a step-debugger replay in `<div class="dbg" id="dbg-X">`: code pane + call stack + variables (`(return)` row) + terminal. Step Over/Into/Out/Continue are computed from real stack depth (F10/F11/⇧F11/F5). `steps` = JSON from `references/trace_recorder.py`, verbatim; `notes` = look-notes per stop with `hi` targets. |
| `slider(id, {label,min,max,value,unit,fmt,onInput})` | **Explorable:** a knob; `onInput` recomputes whatever you wire it to. |
| `tweak(sel, {min,max,step,value,unit,fmt,onInput})` | **Explorable:** a dashed inline number you drag left-right. |
| `.metric[data-count][data-unit]` + stat tiles | Numbers tick 0→N on section entry (`runMetrics` auto-runs). |
| `.chips[data-predict]` + `.reveal` | **teach:** predict-then-reveal; wrong shakes red, right opens the reveal. |
| `.selfx` markup | **teach:** commit a written reason, then reveal the canonical one. |
| `.calib` markup | **teach:** rate confidence, answer, surfaces "confident-but-wrong". |

`references/trace_recorder.py` records a Python program's real stops (`sys.settrace`, program frames
only, dunders dropped unless he wrote them, stdout attached one stop late as in the IDE):
`python3 trace_recorder.py program.py > steps.json`.

Shared chrome (free): sticky top rail (scroll-spy + jump), keyboard (`←/→` sections ·
`1-9` jump · `T` theme · `?` cheatsheet), theme persistence, self-check persistence,
reduced-motion handling.

Worked v2 sample: `~/helm/visual/memory-v3-pipeline.html` (3 scenes, 17 beats, minimum words).

## Where outputs live
A `visual/` folder at the **root of the project**, one HTML file per artifact, named
`<slug>.html`. Exception: `plan` writes `.agent/visual/<slug>.html` next to the spec it renders: scratch where `.agent/` is ignored, a record in a repo that tracks `.agent/` files, such as helm. Disposable: regenerate anytime; git log is the archive. For a topic not
tied to a repo, save to `~/helm/visual/`.

## Rendering notes
Opens in any browser by double-click. No CDN scripts. Google Fonts (Space Grotesk,
Source Serif 4, IBM Plex Mono) are the only network fetch. Offline, system fallbacks
keep everything working. To preview cleanly: `python3 -m http.server` in `visual/`.

## Cross-references
- Adapted from BuilderIO's `visual-plan`: the idea, not their hosted stack.
- `plan` and `explain` are sub-skills of this one router, not standalone skills.
- The engine is a crisp auto-layout system with beats, the Anthropic palette, and a
  diagram-first doctrine.
