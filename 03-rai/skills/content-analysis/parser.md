# Parser

Parse unstructured content into clean, typed JSON. Auto-detects content type
and extracts entities, metadata, and relationships.

## Supported formats

| Format | Detection Signal | Key Extractions |
|--------|-----------------|-----------------|
| Newsletter | Email headers, digest layout | Items, links, topics |
| Twitter/X | @handles, tweet structure | Author, thread, entities |
| Article | Byline, paragraphs, headings | Title, author, claims, sources |
| YouTube | Transcript markers, timestamps | Segments, speakers, key points |
| PDF | Document structure, pages | Sections, tables, references |

## Process

1. **Detect:** identify content type from structure and signals.
2. **Extract:** pull entities (people, orgs, tools, concepts).
3. **Structure:** map to typed JSON schema for that content type.
4. **Deduplicate:** collision detection against known entities.
5. **Validate:** check required fields, flag ambiguities.
6. **Output:** return clean JSON with confidence scores.

User can override auto-detection: 'Parse this as [article/newsletter/PDF/transcript]'.

## Entity extraction

Each entity gets:
- `name`: canonical form
- `type`: one of [person, org, location, tool, concept, event, date]
- `mentions`: count and locations
- `confidence`: extraction confidence (0-1)
- `collisions`: potential duplicates in existing data

## Collision detection

When an extracted entity matches an existing one:
- Exact match: merge and note.
- Fuzzy match uses Levenshtein distance normalized to 0–1; >0.8 indicates likely duplicates: flag for review.
- Partial match: list as potential duplicate.

## Examples

- "Parse this newsletter into JSON"
- "Extract entities from this article"
- "Structure this YouTube transcript"
- "Parse this tweet thread into structured data"
