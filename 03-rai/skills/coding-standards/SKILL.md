---
name: coding-standards
description: >
  Language-specific coding standards router. USE WHEN the user wants code
  reviewed or written against idiomatic conventions for a specific language.
  Routes between python, typescript, go, rust.
---

# Coding Standards

Per-language style, structure, and review standards. Pick by target language.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Review or write Python code (imports, type hints, naming, ruff) | python | `python.md` |
| Review or write TypeScript/JavaScript code (types, modules, naming) | typescript | `typescript.md` |
| Review or write Go code (error handling, packages, idioms) | go | `go.md` |
| Review or write Rust code (ownership, traits, error handling) | rust | `rust.md` |

## How to use

1. Pick the sub-skill matching the language.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## Cross-references

- Test-write patterns are language-agnostic → `/testing/tdd`, `/testing/unit-test`
- Code review as an activity (language-agnostic) → `/testing/code-review`
- Dependency audit → `/testing/dependency-audit`
