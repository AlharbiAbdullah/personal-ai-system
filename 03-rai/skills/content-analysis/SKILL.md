---
name: content-analysis
description: >
  Content analysis router. USE WHEN the user wants to apply Fabric prompt
  patterns (240+ named patterns), parse raw content into structured JSON, or
  process a document file (DOCX/PDF/PPTX/XLSX). Routes between Fabric (named
  pattern execution), Parser (entity-extracting JSON parser), and Documents
  (format-level document processing).
---

# ContentAnalysis

Three skills for working with content at scale. Pick by what kind of output
the user wants.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| User names a Fabric pattern (`extract_ideas`, `summarize_paper`, etc.) | Fabric | `fabric.md` |
| User asks for a structured analysis matching a pattern template | Fabric | `fabric.md` |
| Need to summarize, extract, analyze, or create using a defined pattern | Fabric | `fabric.md` |
| Need raw content turned into typed JSON | Parser | `parser.md` |
| Entity extraction from articles, tweets, newsletters | Parser | `parser.md` |
| YouTube transcript → structured segments | Parser | `parser.md` |
| Create, extract from, edit, or fill a DOCX/PDF/PPTX/XLSX file | Documents | `documents.md` |
| Convert between document formats | Documents | `documents.md` |

## How to use

1. Identify whether the user wants a **pattern-driven transformation** (Fabric), **structured data extraction** (Parser), or **format-level document work** (Documents).
2. `Read` the appropriate file in this directory.
3. Follow that file's instructions.

If the user mentions a Fabric pattern by name, always use Fabric. If they want JSON output, use Parser. If they hand you a DOCX/PDF/PPTX/XLSX file to create, edit, or convert, use Documents.

## Neighboring skills

- `/research/extract-wisdom` — semantic mining of one piece of content (insights, quotes, themes). Prose output, not JSON or Fabric template.
