---
name: pr-description
description: >
  Draft a clear, complete PR description from a diff or branch. USE WHEN
  the user opens a PR and wants reviewers to actually understand the
  change in under 30 seconds.
---

# PR Description

Reviewers decide in 30 seconds whether your PR is worth reading carefully.
The PR description has to earn that time.

## When to use

- Opening a PR on GitHub / GitLab / Bitbucket
- Drafting release notes that derive from a set of PRs
- Documenting a change for future git archaeology

## When NOT to use

- Commit message — `/git/commit` handles that
- Full release changelog across many PRs — `/git/changelog`
- Internal PRD: `/writing → prds`. The spec of one change in an SDD repo: `/grill`, which writes its change folder under `specs/changes/`

## Structure — 5 parts

### 1. Title (~70 chars)
- Imperative mood: "Add feature X" not "Adds" or "Added"
- Scope prefix per convention (Conventional Commits): `feat(auth): ...`, `fix(ingest): ...`
- Specific: "Fix user login" beats "Bug fix"
- Under 70 chars — fits in listings

### 2. Summary (1–3 bullets)
What changed, at the most abstract useful level.

```
## Summary
- Swap bcrypt for argon2id in password hashing
- Add migration path (rehash on next login)
- Bump password policy minimum length to 12
```

### 3. Why (motivation)
Why is this change happening?
- Link to ticket / issue / customer request
- Technical reason if not obvious from ticket
- Constraint that forced this shape

```
## Why
Argon2id is the OWASP-recommended default for new systems as of 2025.
Bcrypt remains acceptable for existing hashes. We migrate on login to
avoid a bulk-rehash downtime.
```

### 4. Test plan (checklist)
How the author verified + how the reviewer should verify.

```
## Test plan
- [x] Unit tests for new argon2id wrapper
- [x] Migration test: old bcrypt hash → new argon2id on login
- [x] Manual: logged in with old account, confirmed hash upgraded
- [ ] Reviewer: hit /login with a pre-migration test user
```

### 5. Screenshots / examples (if visual or output-changing)
Before + after screenshots for UI changes. Code snippets for API changes.

## Optional sections

### Breaking changes
If the change breaks existing contracts, call it out explicitly + mention mitigation.

### Rollout plan
If the change needs feature flags, staged rollout, or comms, describe it.

### Post-merge tasks
Things that happen AFTER this merges (monitor metrics, run migration script, update docs).

## Tone + style

- Imperative + concrete, not marketing-speak
- Third person ("this PR") or implicit author — avoid "I did..."
- Short paragraphs; reviewers scan
- Markdown headers + bullets for skimmability
- Link liberally — tickets, docs, prior PRs, specs

## Using git to generate

```bash
# Summary of changes for drafting
git log main..HEAD --oneline

# Full diff (pipe to less)
git diff main..HEAD

# Files touched by area
git diff main..HEAD --stat
```

## Anti-patterns

- Title: "WIP" / "fix stuff" / "updates" — reviewer can't prioritize
- No Why — reviewer has to guess the motivation
- No test plan — reviewer has to re-derive how to verify
- "See ticket" as the only content — reviewer shouldn't need to context-switch
- Wall of prose — structure beats paragraphs for PR descriptions
- Marketing tone — "revolutionary", "best-in-class" — reviewers roll eyes
- Mentioning Claude / AI in the description — breaks John's git hygiene rule

## Size + reviewability

- < 100 lines changed: easy
- 100–500 lines: reasonable
- 500+ lines: split the PR or provide a review map ("review in order: file A, then B, then C")

If a PR is big because it can't be split, the description should explain why and guide the review order.

## Examples

- "Draft a PR description from the diff on this branch"
- "Write release notes from the last 10 PRs"
- "Rewrite this PR description — it's too long"
- "Generate PR description for the Helios auth migration"
