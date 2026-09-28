---
name: academic
description: >
  Formal academic-style research with proper methodology, citations, and
  argument structure. USE WHEN the user is writing a paper, thesis,
  chapter, or formal research report that must stand academic scrutiny.
---

# Academic Research

Academic rigor: hypothesis, method, evidence, proper citations.

## When to use

- Writing a paper, thesis, dissertation chapter
- Producing research for a journal, conference, or academic audience
- Formal research report for a funding body or review committee
- Internal research where academic standards are required (defense, healthcare)

## When NOT to use

- Practical question with a quick answer → `/research/web-research`
- Business market sizing → `/research/market`
- Single-paper deep extraction → `/content-analysis/fabric` with `extract_wisdom` or similar
- Literature survey without full paper-writing → `/research/literature`

## Process

1. **Formulate the research question** — single, specific, falsifiable
2. **Literature review** — use `/research/literature` for the depth pass first
3. **Methodology** — pick + justify:
   - Quantitative (experiment, observational, modeling)
   - Qualitative (interview, ethnography, case study)
   - Mixed methods
   - Theoretical / computational
4. **Design** — variables, participants/data, procedure, validity threats
5. **Data collection** — execute per protocol; document deviations
6. **Analysis** — statistical tests (with assumptions checked) or qualitative coding
7. **Write-up** — IMRaD structure (Introduction, Methods, Results, Discussion)
8. **Cite everything** — no uncited claim

## IMRaD outline

- **Introduction** (1–3 pages) — problem, gap, research question, contribution
- **Methods** (2–5 pages) — replicable detail; reviewer must be able to redo your work
- **Results** (2–6 pages) — facts without interpretation; tables + figures
- **Discussion** (2–4 pages) — what it means; limitations; future work
- **References** — full bibliography in the target format (APA, MLA, Chicago, IEEE)

## Citation formats

- **APA** — social sciences, psychology, education
- **MLA** — humanities, literature
- **Chicago** — history, some humanities
- **IEEE** — engineering, CS
- **Vancouver** — medicine

Pick one + be consistent. Tools: Zotero, Mendeley, BibTeX.

## Anti-patterns

- Scope too broad ("AI in society") — narrow to something defensible
- Uncited claims ("it is well-known that...") — cite or cut
- Results section that interprets — that's Discussion
- Discussion that introduces new data — that's Results
- Ignoring null / negative results — publishable and honest
- P-hacking or selective reporting
- No discussion of limitations — every study has them

## Tools

- **Zotero** — reference management
- **LaTeX + Overleaf** — formatting (especially STEM)
- **R / Python** — reproducible analysis
- **Jupyter / R Markdown** — literate computation
- **Pandoc** — format conversion

## Output artifact

The paper in the target format. Sections complete, citations formatted, figures labeled, tables numbered.

## Examples

- "Write a research paper on medallion architecture performance in air-gapped environments"
- "Academic chapter on prompt injection defense taxonomies"
- "Thesis proposal: compliance automation for local regulatory frameworks"
- "Conference paper draft — RAG for domain-specific legal text"
