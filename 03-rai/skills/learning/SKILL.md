---
name: learning
description: >
  Learning router for courses, tutorials, and skill acquisition. USE WHEN the
  user wants to start a learning topic, generate a lesson, take a quiz, or
  check a topic's coverage (never a closing gate). Sub-skills operate on
  `~/helm/06-learning/`.
---

# Learning

Learning work for courses, tutorials, skills — anything that's NOT a book (for books, use `/reading`).

## Method

Default is **review**: a lesson is a live, interactive session, not a doc you read. Concept + worked code, then drills (predict the output / spot the planted bug / explain back / decide) answered BEFORE the reveal. Lesson docs are records of the session; `/quiz` re-tests weak spots on a delay. This replaces read-through curricula, which decayed to ~0 for John. Legacy `build` method (write-the-code-yourself) stays available per topic. See `teach.md`.

**Real tools, never banned (2026-09-18).** Every topic uses the libraries, packages, macros and built-in features practitioners use (dbt_utils, dbt_expectations, dbt semantic layer, ...). Tasks never forbid them; the check is knowing what the tool does underneath. Details in `teach.md`.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Create a new topic folder + progress.md + curriculum overview | start-topic | `start-topic.md` |
| Run a live review-based lesson (concept + code, then drills) | teach | `teach.md` |
| Retrieval practice, spaced + weak-area-weighted | quiz | `quiz.md` |
| Check a topic's coverage when he asks (never a closing gate) | audit-coverage | `audit-coverage.md` |

## How to use

1. Pick the sub-skill by what you want to do.
2. `Read` the file in this directory.
3. Follow that file's instructions.
