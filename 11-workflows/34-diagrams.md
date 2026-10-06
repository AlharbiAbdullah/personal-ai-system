# Diagrams

**Use when:** a system needs its picture drawn: the architecture and tech stack diagrams. They go in a README, a proof piece, a design doc or a decision paper. Also redrawing a pair after the system changed.
**Not for:** 30 architecture decision, for deciding the design itself: it hands the drawing here. A diagram inside a vault note or a workflow stays a D2 fence. An animated HTML explainer is `/visual → explain`. An illustration or a thumbnail is `/media → art`.
**Done when:** the pair of `.excalidraw.svg` files and their scene script sit in the repo's `docs/diagrams/`, the README shows both, and he approved the render.

Two diagrams, one layout. The architecture shows the solution as a whole. The tech stack is the same picture, with each tool placed where it lives on the system.

```d2
direction: right

read: "1. Read the system"
pair: "2. Two diagrams,\none layout"
style: "3. The style" {shape: diamond}
arch: "4. Draw the\narchitecture"
stack: "5. Place the tools"
arrows: "6. Label every arrow"
render: "7. Render and look"
iterate: "8. Iterate with him" {shape: hexagon}
land: "9. Land it"

read -> pair -> style -> arch -> stack -> arrows -> render -> iterate -> land
iterate -> render: "each change" {style.stroke-dash: 3}
```

---

## Steps

### 1. Read the system

- [ ] Read it from the repo, never from memory: the entrypoint and its commands, the config (`mise.toml`, `pyproject.toml`, the CI file) and the README's own words.
- [ ] List the stages in order, what moves between them, and what is only metadata, such as metric definitions.
- [ ] Mark what sits outside the project: an external API or a data provider.
- [ ] Note the environment that holds the project, such as mise and uv, and what CI/CD checks.

### 2. Two diagrams, one layout

- [ ] **Architecture:** the solution as a whole. Zones for the stages, and inside each zone, short part boxes that name the work: "contract check", "raw, staging, marts". No tools, no logos.
- [ ] **Tech stack:** the same zones, arrows and labels, with each tool placed in the zone where it lives. Logo and name only.
- [ ] Both diagrams share one zone grid, so the eye moves between them without relearning the picture.
- [ ] The level is a C4 container diagram: the parts of one system and what flows between them. Never the classes inside a part.

### 3. The style

- [ ] The house style is Seattle Standard. A white canvas, Nunito type and grey dashed zones with uppercase grey titles. Zones carry no fill.
- [ ] The environment box (mise and uv) is dotted. The external source sits outside it. CI/CD is a zone below it, with an arrow up into the project.
- [ ] Colour means kind and nothing else. Data arrows are solid ink, definition and metadata arrows are violet and dashed, and check arrows are grey and dashed.
- [ ] No title or subtitle inside the image that repeats the README: no project name, no "on every push".

> **Decision Point**: does he want a new style?
> - No: build in the house style.
> - Yes: run `/fusion → brainstorm` for design directions, build each one with `/media → diagram`, and publish them as one Artifact gallery he browses. He picks, and the pick becomes the house style here.

### 4. Draw the architecture

- [ ] Zone titles in capitals: SOURCE, INGEST, WAREHOUSE, PUBLISH, SEMANTIC, CONSUME, CI/CD, or the system's own stage names.
- [ ] Part boxes say what happens in two or three words, at 20 px.
- [ ] Leave about 120 px between zones, so each arrow label fits without crossing a box edge.

### 5. Place the tools

- [ ] Every tool is a 72 px logo with its name below at 20 px, the same size everywhere, CI/CD included.
- [ ] Only tools that define a stage. Drop glue libraries, and drop the language unless the language is the point.
- [ ] Every logo is real, fetched from its official source: simple-icons, the GitHub organisation, or the project's own site. Check the site before settling on a fallback.
- [ ] A tool with no logo is dropped, never drawn as a wordmark.
- [ ] A third-party data provider gets a generic mark, never its brand.

### 6. Label every arrow

- [ ] Each arrow carries its action: a verb and its object on two short lines, at 18 px. For example "load" over "into DuckDB".
- [ ] The labels match in both diagrams.

### 7. Render and look

- [ ] The scene script is `docs/diagrams/diagrams.py` in the repo, run through `/media → diagram`. It writes one `.excalidraw.svg` per diagram with the scene embedded.
- [ ] Rai reads the preview before he sees anything, and fixes overlaps, clipped labels and uneven sizes first.
- [ ] Check it at README width, about 880 px: the smallest text stays readable.

### 8. Iterate with him

- [ ] One round of his changes per turn: change the scene script, render, look, show.
- [ ] Changes go into the scene script, never by hand into the SVG. A hand edit in excalidraw.com is lost on the next render, unless he chooses to own the file there.
- [ ] His words decide the content: what to drop, what to rename. Never re-add a part or a tool he removed.

### 9. Land it

- [ ] The README embeds both files: the architecture near the top, the tech stack in its own section. The rest of the README follows [[35-readme]].
- [ ] SDD repo: the change merges at the G3 gate of [[21-project-init]] Phase C.
- [ ] Any other repo: [[02-task]] from its Review step. It commits on his word.

---

## Connections

- Skills: `/media → diagram` (the kit and its rules), `/fusion → brainstorm` (new style directions), `/git → commit`.
- Workflows: [[30-architecture-decision]] hands the drawing of a decided design here. The repo change runs through [[02-task]] or [[21-project-init]].
