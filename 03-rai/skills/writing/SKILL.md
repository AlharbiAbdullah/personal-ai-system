---
name: writing
description: >
  Writing craft router. USE WHEN the user needs to draft prose that should
  read as written by a real person, not an AI. Routes between Arabic prose,
  proposals, PRDs, social-media posts, and long-form blog essays. Every
  sub-skill enforces the shared anti-AI voice rules in references/voice.md.
---

# Writing

The craft of producing prose. Document-type and language are routed; voice and anti-AI rules are shared.

## Routing table

| Task | Sub-skill | File |
|------|-----------|------|
| Arabic prose: regional business correspondence, Arabic LinkedIn, internal Arabic docs | Arabic | `arabic.md` |
| Client proposals, RFP responses, grant proposals, scoped pitches | Proposals | `proposals.md` |
| Requirements document for someone else (work, a client): features, scope, success metrics. John's own products use /grill and the SDD templates | PRDs | `prds.md` |
| Short-form posts: X threads, LinkedIn, Substack notes | Social media | `social-media.md` |
| Long-form essays for johndoe.dev (engineering writeups, project retros) | Blog | `blog.md` |

## How to use

1. Pick the sub-skill that matches the document shape.
2. **Read `references/voice.md` first.** Non-negotiable. The voice file enforces the anti-AI-persona rules every output must pass.
3. `Read` the chosen sub-skill file.
4. Follow that file's process.
5. Self-check output against the gate at the bottom of `voice.md` before delivering.

## When NOT to use this router

- **Sales narratives, pitch decks, battlecards** → `/business/sales`
- **Pitch decks for talks/conferences/presentations** → `/business/presentations`
- **Pricing pages, packaging copy** → `/business/pricing`
- **Fiction, story-craft** → `/media/write-story`
- **Pattern-driven content transformation (summarize, extract)** → `/content-analysis/fabric`
- **Research synthesis from multiple sources** → `/research/extract-wisdom`
- **Commit messages, PR descriptions, changelogs** → `/git/commit`, `/git/pr-description`

## Why a separate router

`/business` owns go-to-market work where prose is one ingredient (sales, presentations, pricing). `/writing` owns the prose craft itself: language, document type, voice. Proposals and PRDs live here because they're document compositions before they're business artifacts.

`/media/write-story` is fiction. `/writing` is non-fiction. Different muscles.

## Voice mandate

Every sub-skill output goes through the gate in `references/voice.md`:

1. Banned words check (20 words from `voice.md`, checked by hand)
2. No em dashes
3. Sentence length distribution
4. Lead with the answer
5. Active voice on the hard parts
6. Concrete numbers, not "many"

When the draft is a file inside the vault, run the mechanical half first: `vale --filter='.Name matches "^Rai"' <draft.md>` must print nothing (config `~/helm/.vale.ini`, styles in `03-rai/config/vale/`, README there). The full `vale <draft.md>` report (ai-tells rules) is advisory: read it, fix what rings true.

If output fails the gate, rewrite. Don't ship.

## Public posts

Any post on X, LinkedIn, Substack or johndoe.dev, in English or Arabic:

- Never names client work without his explicit go. Confidentiality comes first (`04-work/AGENTS.md`).
- Takes its hook from his interest areas: data engineering, DevOps, AI, system design. Not from project names, which go stale fast.
- Names a side project only when it is active and the link is real.

## Examples

- "Draft an Arabic email to a partner company's engineering team about open-kit" → arabic
- "Write a proposal for a 3-month Helios pilot for an Acme entity" → proposals
- "PRD for the bulk import flow" → prds
- "Turn these 5 bullet points into an X thread" → social-media
- "Write a blog post on why a deploy recreates containers instead of restarting them" → blog

## Files in this folder

```
writing/
├── SKILL.md              # this file
├── arabic.md
├── proposals.md
├── prds.md
├── social-media.md
├── blog.md
└── references/
    └── voice.md          # shared ruleset
```
