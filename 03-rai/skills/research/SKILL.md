---
name: research
description: >
  Research router. A group of research specializations. USE WHEN the user
  wants to research a topic, investigate something, compare options,
  extract wisdom from existing content, survey academic literature, size a
  market, teardown a competitor, or drive a browser for a single-page task.
  Routes between WebResearch, ExtractWisdom, Academic, Literature, Market,
  Competitor, and Browser.
---

# Research

Seven complementary skills live here. Pick by where the information needs to
come from and how formal the output must be.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Multi-source web research with verification | WebResearch | `web-research.md` |
| Compare options across the web | WebResearch | `web-research.md` |
| Investigate a topic from scratch | WebResearch | `web-research.md` |
| Extract insights from a transcript / article / video | ExtractWisdom | `extract-wisdom.md` |
| Mine takeaways from a podcast or book chapter | ExtractWisdom | `extract-wisdom.md` |
| Pull ideas, quotes, references from existing content | ExtractWisdom | `extract-wisdom.md` |
| Formal paper, thesis, or report needing academic rigor and citations | Academic | `academic.md` |
| Systematic literature review, citation graph, methodology comparison | Literature | `literature.md` |
| Market sizing, segmentation, TAM/SAM/SOM, growth rates | Market | `market.md` |
| Head-to-head competitor teardown: positioning, pricing, weaknesses | Competitor | `competitor.md` |
| Single-page browser automation: form fills, clicks, screenshots, JS console | Browser | `browser.md` |

## How to use

1. Identify whether the work needs **outside info** (WebResearch), **mining existing content**
   (ExtractWisdom), or one of the specialized shapes above.
2. `Read` the appropriate file in this directory.
3. Follow that file's instructions.

If the source is a specific piece of content already provided, use ExtractWisdom. If the work
requires gathering from multiple sources, use WebResearch. For large-scale data extraction
across a whole site or platform (not a single interactive session), use `/scraping` instead of Browser.

`web-research` is the generalist; the other five sub-skills are specialized shapes for a
particular kind of research task.
