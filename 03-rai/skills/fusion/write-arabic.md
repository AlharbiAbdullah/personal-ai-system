---
name: write-arabic
description: >
  Multi-model Arabic draft. Each voice drafts under the Arabic writing rules
  (the /writing arabic skill, the dictionary and the Lumen corpus), then
  scores the others' drafts; the coordinator synthesizes ONE final. USE WHEN
  /fusion write-arabic, or serious Arabic prose should get six drafts
  before one ships. The steps around it live in workflow 20.
---

# /fusion write-arabic

The whole piece follows [[20-arabic-piece-pipeline]]. This is its drafting step.
Rules: `references/write-arabic.md` (it includes `/writing`'s `arabic.md`,
`voice.md`, the dictionary and the Lumen corpus).

## The ask (`$RUN/ask.md`)

- **Target:** the piece, the section, the file.
- **Audience** and the register they expect.
- **Purpose:** what the reader should think, feel or do after.
- **Current state:** the existing Arabic, pasted, if any.
- **English source,** when there is one: it is the semantic truth. Nothing in
  it may be cut, softened or added to unless he said so.
- **Constraints:** length, markup to keep (`<strong>`, `<highlight>`),
  phrasings he locked in.

## Rounds

- **Round 1:** each voice writes a full Arabic draft.
- **Round 2:** each voice scores every draft 1 to 10 against the Arabic rules
  and quotes the strongest opening, middle and close. It lists each draft's
  rule breaks: register drift, missing الـ, an unwrapped English token, a
  forbidden translation.

## Synthesis

1. Strongest opening, middle and close, by the scores. Lock phrasings 2 or
   more drafts share. Fix every break a voice showed with the quoted line: one
   demonstrated break is enough.
2. Where drafts disagree, pick the more Lumen-like reading.
3. Against an English source: check no section, severity, caveat or marker
   was dropped. A rewrite that hides what the source says is a failed draft.
4. Save the final in `$RUN/synthesis.md`. Hand it back to
   [[20-arabic-piece-pipeline]] step 5, the voice
   check. He reads it only after that gate passes.

## Examples

- `/fusion write-arabic the about-page opener, English source attached`
- `/fusion write-arabic an Arabic LinkedIn post on data contracts, gemini and the pi voices`
