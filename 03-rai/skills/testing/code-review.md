---
name: code-review
description: >
  Structured code review: pre-review self-checklist for your own PRs +
  review of someone else's PR. USE WHEN producing or consuming a code
  review. Separate from /security/security-review (which is attack-surface).
---

# Code Review

Two uses: review your own code before opening the PR, and review someone else's PR.

## When to use

- About to open a PR — self-review first
- Assigned to review a teammate's PR
- Onboarding a new codebase (reviewing historical PRs teaches fast)

## When NOT to use

- Security-focused review → `/security/security-review`
- Whole-system architectural feedback → `/architecture/system-design`
- Review of your own PR when you're a solo dev — at least sleep on it first

## Pre-review self-checklist (YOUR PR)

Run through this before requesting reviewers:

**Scope**
- [ ] PR does ONE thing. (Multiple things → split.)
- [ ] PR title describes the change imperatively ("Add foo" not "Added foo")
- [ ] Description explains WHY (not just what — the diff shows what)
- [ ] Screenshots / examples for user-visible changes

**Correctness**
- [ ] Code compiles / type-checks cleanly
- [ ] Tests pass locally
- [ ] New tests for new logic (or reasoned skip with TDD escape — see `/testing/pragmatic`)
- [ ] Manually tested the happy path
- [ ] Considered one edge case and either tested it or documented why not

**Quality**
- [ ] No commented-out code
- [ ] No `TODO` without a ticket or date
- [ ] No `console.log` / debug prints
- [ ] Variable names tell the reader what they mean
- [ ] Functions do one thing; extract if not

**Safety**
- [ ] No secrets / keys in code
- [ ] No new external deps without justification
- [ ] No breaking API changes without version bump
- [ ] Migration is reversible (or rollback is documented)

**Docs**
- [ ] CHANGELOG / release notes if user-facing
- [ ] README / docs updated if behavior changed
- [ ] ADR written if architectural choice

Fix everything on this list, then request review.

## Reviewing someone else's PR

### Step 1: Understand intent
- Read the PR description first
- Read the linked ticket / issue
- If intent is unclear, ask BEFORE line-by-line review

### Step 2: Scan the diff
- What files changed — does the surface area match the intent?
- Are there unexpected files (dependency updates, formatting drift, unrelated changes)?
- Is the PR too big? (>500 lines is a smell. Ask to split.)

### Step 3: Line-by-line
- Logic: does it do what the description says?
- Edge cases: nil checks, empty collections, overflow, concurrency
- Error handling: propagated with context, or swallowed?
- Naming: clear, consistent with codebase
- Tests: do they cover the change? Happy path + edge cases?

### Step 4: Holistic
- Is there a simpler way? (Often yes. Don't impose; suggest.)
- Does this fit existing patterns in the codebase?
- Will this age well, or is it debt in disguise?

### Step 5: Feedback
- **Blocking** comments (clearly marked): correctness bugs, safety issues, must-fix
- **Suggestion** comments: style, improvement, not blocking
- **Nit** comments: tiny nits, don't block approval
- **Question** comments: "Why this way? Just curious" — shows engagement, not authority

## Feedback style rules

- Attack the code, not the person ("This function" not "You")
- Ask why before asserting how ("What's the reason for X?" before "You should do Y")
- Offer reasoning, not just opinion ("Because Z" — so the author can push back)
- Praise what's good — reviews are mostly "change this"; tell them what works
- Don't nitpick whitespace / style — that's the linter's job

## Review smells (your review is off if...)

- Every PR gets "LGTM" without substantive comments — you're not really reviewing
- Every PR gets 50+ comments — you're reviewing style, not substance
- Reviews take 3+ days — blocks the author; prioritize same-day response
- You can't explain why you didn't approve — you're gatekeeping, not helping

## Anti-patterns (author side)

- PRs with >500 lines of diff
- PRs that touch unrelated things
- PRs without description
- Responding to feedback defensively — reviewers are trying to help
- Ignoring feedback you disagree with — push back explicitly, don't silent-ignore

## Examples

- "Self-review this branch before I push"
- "Review PR #1234"
- "Is this code ready for production?"
- "What should I comment on in this diff?"
