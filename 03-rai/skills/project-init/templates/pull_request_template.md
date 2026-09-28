## What

At most 3 lines: what changes for the person who uses it.

## Review depth

`mise run status -- --merge` prints it: trunk READ, each trunk file with its why; leaf SKIM, the other files, against the proof.

## Rollback

The change's Rollback line: `revert: <why>`, `flag: <ENV_NAME>` or `one-way: <what>`.

## Proof

The confidence line of each group, a `low` one first. Then the capture of each `## Proof` row of `validation.md`: an image or GIF inline, run output in a details block. The full index: `proof/<date>-<slug>/README.md`.

## Scenarios

The scenario IDs this change adds or changes (its `Spec:` trailers), or "none" and why.

## Checklist

- [ ] `mise run verify` is green.
- [ ] Each behaviour change edits its scenario in `specs/capabilities/`, in the same commit as its test and code.
- [ ] The `## Trunk` section of `specs/tech-stack.md` is current, and a `flag:` change has its `[flag-off]` guard.
- [ ] The `## Proof` rows are captured and current (`mise run proof -- show`), and each group has its confidence line.
- [ ] A surprise is in `project_memory/lessons.md`. A choice later changes must respect has its file in `project_memory/decisions/`.
- [ ] No secret values: `op://` pointers only.
