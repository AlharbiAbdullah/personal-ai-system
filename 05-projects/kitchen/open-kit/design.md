---
title: "open-kit — design"
status: DRAFT
created: "2026-01-01"
updated: "2026-01-01"
type: design
---

# open-kit — Design

> Example design note. The third kitchen doc: how the tool *feels* to use. CLI ergonomics,
> output, error messages. Pairs with [[05-projects/kitchen/open-kit/PRD|PRD]] and
> [[05-projects/kitchen/open-kit/architecture|architecture]].

## Design principle

A good CLI is **predictable, quiet on success, and loud-but-kind on failure.** open-kit should
feel like a sharp tool a senior engineer would reach for — not a wizard that asks ten questions.

## The one command that matters

```
$ open-kit new go-cli weather
  ✓ created weather/ from template "go-cli"
  ✓ wrote 9 files, initialized git, added MIT license
  → next:  cd weather && make run
```

- One line per real action, a leading `✓`.
- Ends with a concrete **next step**, never just "done".
- `--dry-run` prints the same tree without writing.

## Ergonomics

| Choice | Decision |
|--------|----------|
| Naming | `open-kit <noun> <verb>`? No — `<verb> <thing>`: `new`, `add`, `list`. Verbs lead. |
| Flags | Long flags documented; short flags only for the obvious (`-n` dry-run). |
| Defaults | Sensible enough that a bare `open-kit new go-cli x` just works. |
| Color | On for TTY, off when piped. Never required to read output. |

## Error voice

Bad:
```
Error: ENOENT
```
Good:
```
✗ can't write to weather/ — the folder already exists and isn't empty.
  try:  open-kit new go-cli weather --into weather-v2
```
Every error names what failed, why, and a way forward. This is the same bar as
[[05-projects/kitchen/open-kit/PRD|PRD]] criterion "a stranger succeeds unaided".

## Open questions
- Interactive mode at all? Leaning no for v1 — flags + good defaults beat a prompt maze.
- A `--json` output for scripting? Defer until someone asks.

## Related
- [[05-projects/kitchen/open-kit/PRD|PRD]] · [[05-projects/kitchen/open-kit/architecture|architecture]]
