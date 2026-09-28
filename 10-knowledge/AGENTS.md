# 10-knowledge/ — Topic Notes + MOCs

## Purpose

The compounding knowledge base. Where understanding lives long-term. Built around topic notes (deep dives) and MOCs (Maps of Content — navigation hubs). Quality over quantity.

## Subfolders

| Folder | Contents |
|--------|----------|
| `_mocs/` | Maps of Content — topic hubs, navigation |
| `_insights/` | Insight Notes — emergent connections between two existing notes |
| `ai/` | LLMs, RAG, embeddings, ML tools (the domain this kit ships an example for) |
| `tools/` | Tool-specific notes that don't fit a broader domain note yet |

Add your own domain folders (`data-engineering/`, `devops/`, `system-design/`, …) as your
notes accumulate. `ai/` is shipped populated so you can see the shape; the rest start empty.

## Note Types Here

### Topic Notes (primary)

Comprehensive notes covering an entire topic area. Each topic note consolidates what used to be multiple atomic notes into sections. Tools are folded into a `## Toolbox` section, not spun out as separate notes. Use the Topic Note template in `12-system/templates/`.

**Required structure:**

1. Simplicity Theorem (one-sentence "aha")
2. Simplicity Diagram (3-5 line ASCII)
3. Why It Matters
4. Sections (1-8 depending on topic breadth)
5. Toolbox (tools folded in, not separate notes)
6. Connections (links to other notes)
7. Trade-offs

**Naming:** descriptive topic names, e.g. "SQL Fundamentals", "Data Modeling", "Containers & Docker".

**Sections:** each `## Section` covers what used to be a separate atomic note. Flexible count (1-8) depending on topic breadth.

### MOCs

Topic hubs in `_mocs/`. Navigation + Agent Breadcrumbs section for future-session pointers. See § Agent Breadcrumbs below for the breadcrumb format.

### Insight Notes

Emergent connections between two existing notes. Created when notes interact interestingly. Use `type: insight` frontmatter with `emerged_from` pointers. See § Emergent Insights below for when to create one.

---

## Simplicity Theory

Based on Jean-Louis Dessalles' cognitive science research: humans are drawn to things that are "unexpectedly simple." Complex ideas become memorable when reduced to their essence.

### Every Note Starts With

**1. Simplicity Theorem** (first section after title)

```markdown
## Simplicity Theorem

> [One sentence - the "aha moment" that captures the entire concept]

[2-3 sentences max. Strip away ALL complexity. What would you tell someone in 30 seconds?]
```

**2. Simplicity Diagram** (immediately after theorem)

```markdown
## Simplicity Diagram

```
[Minimal ASCII art - 3-5 lines capturing the essence in one visual]
```

---
```

### Guidelines

| Element | Rule |
|---------|------|
| Theorem quote | One sentence, simple words, captures the "why it exists" |
| Theorem body | 2-3 sentences max, no jargon, a 12-year-old could understand |
| Diagram | Minimal — if you can remove something, remove it |
| Separator | `---` after diagram to visually separate from deep content |

### Examples

**Good Simplicity Theorem:**
> Give the LLM a cheat sheet before it answers.

**Bad (too complex):**
> RAG augments LLM generation by retrieving relevant documents from a vector store using semantic similarity search.

**Good Simplicity Diagram:**
```
Question ──▶ Search Docs ──▶ Paste + Ask ──▶ LLM ──▶ Answer
```

**Bad (too detailed):**
```
User Query → Embedding Model → Vector DB → Top-K Retrieval →
Reranking → Context Assembly → Prompt Template → LLM →
Output Parser → Response
```

---

## Agent Breadcrumbs

When you discover a useful navigation pattern or a user preference while working in a topic, record it in the relevant MOC under an `## Agent Breadcrumbs` section. Future sessions read these first.

**Format:**

```markdown
## Agent Breadcrumbs
<!-- Claude leaves notes here for future sessions -->

### YYYY-MM-DD
[Discovery or preference noted for future sessions]
```

**Examples:**
- "When user asks about X, start with [[Note A]] then [[Note B]]"
- "User prefers approach A over B for this scenario"
- "These two concepts connect because..."

---

## Emergent Insights

When two notes interact in an interesting way during a session, propose creating a new Insight Note. Do not create one without proposing first.

**Procedure:**
1. Notice the connection.
2. Create the note with `type: insight` frontmatter.
3. Document the `emerged_from` notes.
4. Capture the insight that neither note alone contains.

---

## Rules

- **Wiki-links woven into prose,** not footnoted: "Because [[Containers & Docker|containers are ephemeral]], we need volumes" — NOT "See [[Docker basics]]."
- **Wiki-links = semantic connections in prose, not footnotes.** Ask: "Would a reader of note A benefit from note B?"
- **Tags = categorization metadata.** Different purpose from wiki-links; both apply.
- **Every note must stand on its own.** A note is broken if linking forces the reader to chase three other notes first. If linking requires that, split the topic up.
- **Use templates from `12-system/templates/`.** Never invent note structures.
- **MOC drift is the failure mode.** If a topic gains a fifth note, update the MOC.

## Skills

The `/knowledge` skill group (`03-rai/skills/knowledge/`) helps build and maintain this knowledge base:
- `new-topic-note` — scaffold a compliant note (Simplicity Theorem + Diagram + sections)
- `insight` — propose an Insight Note from two existing notes (proposes before creating)
- `audit-moc` — check a MOC for drift (missing notes, broken links)
- `find-connections` — scan notes for emergent-insight opportunities

## What Claude Should Do

When the user asks about a topic, start by checking the relevant MOC. Follow links to build the picture. Leave Agent Breadcrumbs in MOCs when you discover useful navigation patterns or user preferences.

When two existing notes interact in an interesting way during a session, propose an Insight Note. Do not create one without proposing first.

Never write here without a template. If unsure which template fits, ask.
