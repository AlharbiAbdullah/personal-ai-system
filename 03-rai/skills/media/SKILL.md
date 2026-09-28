---
name: media
description: >
  Media creation router. USE WHEN the user wants to generate images, animated
  videos, or write fiction. Routes between Art (image generation), Remotion
  (programmatic video via React), and WriteStory (layered fiction writing).
---

# Media

Three media-creation skills. Pick by the output medium.

## Routing table

| Output | Sub-skill | File to Read |
|--------|-----------|--------------|
| Single image (illustration, diagram, thumbnail, comic, icon) | Art | `art.md` |
| Animated video from React components | Remotion | `remotion.md` |
| Animated explainer / data viz video | Remotion | `remotion.md` |
| Fiction (story, chapter, character development) | WriteStory | `write-story.md` |
| Story bible, world-building, narrative interview | WriteStory | `write-story.md` |

## How to use

1. Pick the medium the user wants to produce.
2. `Read` the appropriate file in this directory.
3. Follow that file's instructions.

Static image (explanation, diagram, thumbnail, comic) → Art. Animation or motion (sequence, tutorial, slideshow, animated explainer) → Remotion. GIFs are usually Remotion.
