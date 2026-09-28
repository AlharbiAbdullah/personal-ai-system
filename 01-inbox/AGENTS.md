# 01-inbox/ — Research Queue

## Purpose
Items John has promoted from `00-landing/` because they deserve effort.
Rai researches each item on request: what it is, why care, why it matters, and
rates it on relevance to John. When the destination is obvious, the
enriched file (research included) moves there.

## Lifecycle
1. John manually moves a file from `00-landing/` to `01-inbox/`.
2. John invokes the inbox-processing skill (`/triage process-inbox`).
3. Rai applies the research template to each file, in place.
4. The enriched file moves to its destination folder — whole.

## Research template (Rai applies)
- What is it: 1-2 sentences.
- Why I should care: tied to John's goals/identity (reads `02-ana/identity/goals.md` + `02-ana/identity/who-i-am.md`).
- Why it matters: urgency / leverage / uniqueness.
- Rating: A / B / C / D — relevance to John, not generic importance.
- Suggested destination: see Routing below.

## Routing table
- Reading material (book, article, paper) → `07-reading/`
- Curriculum / course → `06-learning/`
- Tool / library / concept → `10-knowledge/`
- Idea seed → `09-ideas/` (start as Seed)
- Project → `09-ideas/` as a Seed (only `/ideas → graduate` opens a kitchen). Research for a project → `05-projects/kitchen/{name}/research/` while it has a kitchen, `05-projects/active/{name}/research/` after its repo's G1 merge. A feature idea for a repo with `.project.toml` → that repo's backlog (`mise run backlog -- <topic>`, run in the repo), never `09-ideas/`.
- Work item → `04-work/{engagement}/`

## Rules
- Writers: John (file moves from landing), Claude (research, via the skill only).
- No autonomous enrichment. Claude writes only when the skill is invoked.
- Strict flat. No subfolders.
- One concept per file. Filename is the topic.

## What Claude does
- When `/triage process-inbox` runs: apply the template, propose destination, move on confirmation.
- When John references a specific inbox file without invoking the skill: answer from its contents — do not enrich, rate, or move.
