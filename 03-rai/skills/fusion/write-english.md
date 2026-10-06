---
name: write-english
description: >
  Multi-model English draft. Each voice drafts under the English writing
  rules, then scores the others' drafts against the same rules; the
  coordinator synthesizes ONE final draft that passes the voice gate. USE
  WHEN /fusion write-english, or a high-stakes English piece should get
  six drafts before one ships.
---

# /fusion write-english

Rules: `references/write-english.md` (it includes `/writing`'s `voice.md`).

## The ask (`$RUN/ask.md`)

- **Target:** the piece, the section, the file.
- **Audience** and the register they expect.
- **Purpose:** what the reader should think, feel or do after.
- **Current state:** the existing text, pasted, if any.
- **Constraints:** length, format, markup to keep, phrasings he locked in.
- **Document type:** for a blog post, proposal, PRD or social post, paste the
  matching `/writing` file (`blog.md`, `proposals.md`, `prds.md`,
  `social-media.md`) under a `# DOCUMENT RULES` heading.

## Rounds

- **Round 1:** each voice writes a full draft.
- **Round 2:** each voice scores every draft 1 to 10, quotes the strongest
  opening, middle and close, and lists each draft's rule breaks.

## Synthesis

1. Take the strongest opening, middle and close the scores point to. Lock in
   phrasings 2 or more drafts share. Fix every rule break a voice showed with
   the quoted line: one demonstrated break is enough.
2. Rewrite lightly where no draft is best. Do not stitch: the final reads as
   one voice.
3. Run the gate in `/writing`'s `voice.md`. For a file in the vault,
   `vale --filter='.Name matches "^Rai"' <file>` prints nothing.
4. Give him the final only, plus one line on what came from where if he asks.
   Save it in `$RUN/synthesis.md`.
   A public piece then goes on at [[33-career]] step 6, His go, then publish or send.

## Examples

- `/fusion write-english the about page intro for johndoe.dev`
- `/fusion write-english a LinkedIn post on the medallion layout, skip opus`
