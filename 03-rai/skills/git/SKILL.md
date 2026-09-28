---
name: git
description: >
  Git workflow router. USE WHEN the user wants to commit, write PR
  descriptions, generate changelogs, clean dead code after a session,
  or explore a codebase's history. Routes between commit, refactor-clean,
  pr-description, changelog, code-archaeology.
---

# Git

Git-centric workflow. Everything that lives at the commit / branch /
history layer.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Auto-split working tree into logical commits | commit | `commit.md` |
| Clean dead code + loose files after a coding session | refactor-clean | `refactor-clean.md` |
| Write a PR description from a diff or branch | pr-description | `pr-description.md` |
| Generate a changelog from commits between two tags/dates | changelog | `changelog.md` |
| Structured exploration of an unfamiliar or legacy codebase via git | code-archaeology | `code-archaeology.md` |

## How to use

1. Pick the sub-skill by task.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **commit vs refactor-clean:** commit stages and writes commits; refactor-clean finds garbage to delete before committing.
- **pr-description vs changelog:** pr-description covers ONE PR; changelog covers many PRs between two versions.
- **code-archaeology vs pr-description:** archaeology is reading history to build a mental model; pr-description is describing a single diff going out.

## Cross-references

- Language-specific code review → `/coding-standards/*` + `/testing/code-review`
- Pre-commit quality checks → `/testing/verify-completion`
