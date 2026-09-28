---
name: reading
description: >
  Book curriculum router. USE WHEN the user wants to start a book curriculum,
  generate a lesson from a book, or audit coverage of a completed book.
  Parallel to /learning but for books specifically — complete coverage, not
  summaries. Sub-skills operate on `~/helm/07-reading/`.
---

# Reading

Books through Claude Code. Complete coverage. "I don't have time to read books. So I read them through you."

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Scaffold a book curriculum + progress.md + tier plan | start-book | `start-book.md` |
| Generate a lesson (Chapter / Law / Practice / Synthesis) | teach | `teach.md` |
| Verify full book coverage before declaring done | audit-coverage | `audit-coverage.md` |

## How to use

1. Pick the sub-skill by what you want to do.
2. `Read` the file in this directory.
3. Follow that file's instructions.
