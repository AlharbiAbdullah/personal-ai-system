---
name: blog
description: >
  Long-form blog essays for johndoe.dev. USE WHEN the user wants to
  publish an engineering writeup, project retrospective, or mental-model
  essay on his personal site. Target: ~500-2500 words. Audience: builders,
  engineers, local tech peers. Tone: candid, lived-experience first.
---

# Blog

Long-form essays for johndoe.dev. The personal-site blog. Not Substack (different shape, different skill).

## Voice mandate

Read `references/voice.md` first. Long-form is where AI tells become unbearable: every paragraph is a chance to fail. Re-read the gate at the bottom of voice.md before shipping.

## What this site publishes

Three shapes, in order of frequency:

1. **Engineering writeup**: a real project, what broke, what fixed it, what's next. Code or config snippets. ASCII diagrams. The kind of post you'd send to someone debugging the same problem.
2. **Project retrospective**: post-mortem of a shipped (or failed) project. Honest about what went wrong. Names ownership. Doesn't dramatize.
3. **Mental model**: observation about how something works (organizations, AI, infra, local tech market). Anchored in lived experience, not abstract theorizing.

If a post doesn't fit one of these three, ask before drafting. The site has a shape.

Every post follows the Public posts rule in the router `SKILL.md`: client work stays out without his go.

## Post anatomy

| Section | Length | What it does |
|---------|--------|--------------|
| **Title** | 6-12 words | Specific, opinionated. Not "How to X" listicle bait. |
| **Lede** (1-2 paragraphs) | 50-150 words | The verdict, up front. The reason a stranger should keep reading. |
| **Context** | 100-300 words | What the situation was, what was at stake, who was involved. Concrete. |
| **The body** | 300-1500 words | The actual work: what happened, what broke, what fixed it. Tables, ASCII, code blocks where they help. |
| **The takeaway** | 50-200 words | What this means going forward. One specific lesson, not five. |
| **Next** (optional) | 1-2 sentences | What you're working on next, or what question this opened. |

## Process

1. **State the verdict in one sentence.** Not the topic, the verdict. "Air-gap projects fail when nobody tests in the real environment." If you can't, the post isn't ready.
2. **Pick shape**: writeup, retrospective, or mental model. Different scaffolds.
3. **List the 3-5 concrete moments** that anchor the post. No moments = no post.
4. **Draft fast**: single sitting if possible. Don't polish mid-draft.
5. **Cut**: first pass typically 30% too long. Hardest cuts are usually the throat-clearing intros.
6. **Self-check**: banned words, em-dashes, lead-with-answer, active voice on hard parts.
7. **Add concrete artifacts**: code, ASCII diagram, screenshot reference, table. Pure prose for 1500 words is suspicious.
8. **Review the title** last. It usually changes after the post is done.

## Anti-patterns

- **Listicle structure** ("5 things I learned from X"): these read AI-shaped. Use only if the list is the actual content (e.g., 5 different bugs).
- **The "humble brag retrospective"**: pretending failure was learning when really it was fine. Be honest.
- **Abstract takeaways**: "always communicate clearly" type. Specific or cut.
- **Throat-clearing openers**: "I've been thinking about...", "It's interesting that..."
- **The five-paragraph essay structure** drilled into us at school. Loosen up. Vary paragraph length.
- **Conclusion paragraphs that summarize what you just said.** Reader was there. Skip the summary, end on the next move.
- **Evergreen-shaped posts that say nothing dated**: your blog is dated by nature; lean into the year, the project, the version.

## Output spec

Markdown file. Frontmatter (title, date, slug, tags) matching johndoe.dev's convention (TBD: confirm with the site repo when first post drafts).

```markdown
---
title: <opinionated specific title>
date: <YYYY-MM-DD>
slug: <kebab-case-from-title>
tags: [engineering | retrospective | mental-model | <topic>]
---

<lede>

<body>

<takeaway>
```

Draft folder location is not yet decided (no `05-content/` or equivalent
exists in the vault). Until John picks one, save the draft as
`<YYYY-MM-DD>-<slug>.md` wherever he asks in the moment, and flag that this is
still an open decision.

## Voice anchors

- **Long-form structure**: `~/helm/04-work/acme/meeting-prep-q1-planning.md`: not a blog post, but the long-form rhythm is right. Tables, ASCII, no flourish.
- **Honest retrospective tone**: `~/helm/05-projects/completed/pomodoro-cli/retrospective.md`: the retrospective shape. Story, role, work, architecture, outcome. No drama.
- **Voice cadence**: `~/helm/02-ana/journal/` (recent entries). The candid micro-rhythm.
- **Existing live blog**: read 2-3 posts at https://johndoe.dev/ (WebFetch) before drafting if it's been a while since the last post. Match what's already there.

## Cross-skill links

- Raw notes → structured draft: see `/content-analysis/fabric` (`extract_wisdom`, `summarize` patterns).
- Source material is a long doc you want to mine: see `/research/extract-wisdom`.
- After publishing: write a Substack note + tweet to promote it → `/writing/social-media`.

## Examples

- "Write a blog post on quarantining bad rows instead of dropping them"
- "Engineering writeup: how I made the offline installer 4x faster"
- "Mental model post: why air-gap projects need real-environment testing"
- "Retrospective on a finished side project: what worked, what didn't"
