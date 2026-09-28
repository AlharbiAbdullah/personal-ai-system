---
name: quote
description: >
  Capture + browse meaningful quotes and personal aphorisms organized by
  theme. USE WHEN the user wants to save a quote, find quotes by theme,
  search for wisdom on a topic, or browse themed collections (work ethic,
  resilience, learning, stoicism, etc.). Invoked via /life router.
allowed-tools: Write, Read, Glob
argument-hint: "Quote text" - Author Name  OR  theme keyword for browse
---

# Quote

Three workflows on one storage: `~/helm/02-ana/quotes/`. CAPTURE a new
quote, FIND quotes by theme, SEARCH across the full collection.

## Storage

Quotes live in `~/helm/02-ana/quotes/`, one file per quote. Each file's
`tags:` frontmatter is the theme index — there are no separate theme
folders. Themes emerge from tags.

## Themes

Common tag clusters:
- **work-ethic** — discipline, craft, persistence, mastery
- **resilience** — adversity, grit, recovery, anti-fragility
- **learning** — curiosity, growth, mistakes, knowledge
- **stoicism** — control, acceptance, virtue, present-moment
- **leadership** — vision, service, decision-making
- **creativity** — originality, risk, process

Tags are not a fixed taxonomy — add new ones as they appear.

## Workflows

### CAPTURE
Save a new quote. Fast path, one-shot.

1. **Parse input**: Extract quote text and author (after `-` or `—`)
2. **Fix spelling**: Correct any typos in the quote silently
3. **Ask for source** (optional): Book, conversation, article
4. **Classify tags**: Pick 1–3 topic tags from the Themes list (or propose a new one)
5. **Dedup check**: Hash quote text (lowercase, whitespace-normalized) against existing files. If match exists, point to existing file instead of creating a new one.
6. **Generate filename**: Key phrase from quote (lowercase, dashes, max 6 words)
7. **Read template**: `~/helm/12-system/templates/Quote.md`
8. **Write note**: Save to `~/helm/02-ana/quotes/[phrase].md` substituting frontmatter

### FIND
Retrieve quotes matching a theme or mood.

1. Glob `~/helm/02-ana/quotes/*.md`
2. Filter by `tags:` frontmatter matching the requested theme or keyword
3. Rank by tag-match count, then by recency (`captured:` field)
4. Return top 3–5 with author and source

### SEARCH
Full-text search across text + author + tags.

1. Glob `~/helm/02-ana/quotes/*.md` and read each
2. Match search terms against the body and frontmatter
3. Return results sorted by relevance, capped at 10 items

## Output Formats

### After CAPTURE

```markdown
---
author: [Author Name]
source: [Source if provided]
captured: YYYY-MM-DD
tags: [topic tags only]
---

> "[Quote text]"
> — Author
```

### After FIND or SEARCH

```
"[Quote text]"
  -- [Author], [Source]
  Themes: [tag1], [tag2]
  File:   ~/helm/02-ana/quotes/[slug].md
```

## Rules

- Fix spelling mistakes silently
- Keep tags topic-based (`discipline`, `craft`, `stoicism`). No mood tags (`inspiring`, `motivating`). 1–3 tags per quote.
- Filename: short phrase from quote (3–6 words, lowercase, dashes)
- No reflection section — the quote speaks for itself
- If no author: use `Unknown`. If no source: leave `source:` empty.

## Examples

- `/life quote "The only way out is through" - Robert Frost` → CAPTURE
- "Find me a quote about persistence" → FIND
- "Search quotes about dealing with failure" → SEARCH
- "Give me 3 stoic quotes for a tough day" → FIND with theme=stoicism, limit=3
- "Add this aphorism: 'We are what we repeatedly do' — Aristotle" → CAPTURE

## One library, two modes

Capture vs. browse are natural modes on one library, not two skills: this
skill handles both.
