---
name: diagram
description: >
  Excalidraw diagrams as code. USE WHEN a repo, README or doc needs an architecture
  diagram or a tech stack diagram drawn as an image: a scene script places zones, parts,
  logos and labelled arrows, and the kit renders one .excalidraw.svg per diagram that
  GitHub shows and excalidraw.com opens. The method is 34 diagrams.
---

# Diagram

The kit behind [[34-diagrams]]. A Python scene script describes each diagram. The kit
renders it with Excalidraw itself, in headless Chromium, to an SVG with the scene
embedded. Vault notes keep D2 fences: this is for images in repos and public docs.

## Files

- `scripts/diagram/lib.py`: the `Scene` helpers, the house style constants, logo fetching.
- `scripts/diagram/render.mjs`: the renderer. `lib.render()` calls it.
- Cache: `~/.cache/rai-diagram/` holds logos, the renderer's `puppeteer-core`, and one
  `scenes/<run>/` folder per run with its scenes and previews. It rebuilds itself when
  wiped. Never build diagrams under `/tmp`.

Needs: `node`, `uv`, Chromium (`/usr/bin/chromium`, or `CHROME=`), `magick` and
`rsvg-convert` for logos, and the network on first fetch and on every render
(Excalidraw loads from esm.sh).

## The scene script

It lives in the repo beside its output: `docs/diagrams/diagrams.py`, a PEP 723 script.

```python
KIT = Path(os.environ.get("RAI_DIAGRAM_KIT", Path.home() / "helm/03-rai/skills/media/scripts/diagram"))
sys.path.insert(0, str(KIT))
from lib import MUTED, VIOLET, Scene, render

s = Scene()
s.zone(0, 150, 190, 300, "SOURCE")                 # dashed grey zone, title top-left
s.zone(280, 0, 1600, 790, None, dotted=True)        # the environment box
s.part(20, 230, 150, 52, "orders API")             # architecture: a component box
s.tool(95, 240, "si:json", "REST API")             # tech stack: logo with its name below
s.arrow([(192, 300), (328, 300)], label="fetch\nraw JSON", at=(190, 240, 88))
s.save("architecture")
render(HERE, "architecture")                        # writes HERE/architecture.excalidraw.svg
```

Run it with `./docs/diagrams/diagrams.py`. Each repo keeps its own scene script there.

## Logo keys

Each key fetches once into the cache.

| Key | Source | Example |
|---|---|---|
| `si:<slug>` | simple-icons, brand colour | `si:duckdb` |
| `si:<slug>#RRGGBB` | simple-icons, a set colour, when the brand colour 404s | `si:dbt#FF694B` |
| `si:<slug>+#RRGGBB` | the icon on a rounded tile, for a mark that vanishes on white | `si:ruff+#261230` |
| `gh:<owner>` | the GitHub avatar, rounded | `gh:rilldata` |
| `url:<https URL>` | any SVG or PNG, trimmed and squared | the project site's own mark |

Check the project's own site for its mark before settling on a fallback: Apache Ossie's
is a kangaroo on ossie.apache.org.

## Rules the kit encodes

- **Text sits in invisible boxes.** Excalidraw measures label text in the browser, so a
  centred label lands centred. Never position bare text by guesswork.
- **One logo size.** `tool()` draws every logo at `LOGO` (72 px) with a 20 px name.
- **Arrow labels** are 18 px, two short lines, in the arrow's colour.
- **Colour means kind:** ink solid for data, `VIOLET` dashed for definitions and metadata,
  `MUTED` dashed for checks. Zones stay grey with no fill.
- **Preview before showing.** Each render prints the path of its preview PNG. Rai
  reads it, fixes what it sees, and only then shows him.
- **Readability.** A README shows about 880 px. Keep the canvas under about 1,900 px wide
  and the smallest text at 18 px.

## Next

The work carries on in [[34-diagrams]] step 7.
