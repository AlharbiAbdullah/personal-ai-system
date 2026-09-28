---
name: systematic-debug
description: >
  4-phase root cause methodology for debugging: Observe, Hypothesize,
  Isolate, Fix. USE WHEN a bug is non-trivial, intermittent, or keeps
  coming back. Counters the "random shot-in-the-dark" failure mode.
---

# Systematic Debug

Observe → Hypothesize → Isolate → Fix. In that order. No skipping.

## When to use

- Bug is intermittent or hard to reproduce
- Previous fix attempts didn't work
- Root cause is unclear
- Stakes are high (production, customer-facing, data integrity)

## When NOT to use

- Obvious typo or trivial bug — just fix it
- Syntax errors + lints — the compiler already told you

## Phase 1: Observe

Gather evidence before theorizing.

1. **Reproduce** — what are the exact steps? Can you trigger it on demand?
2. **Record** — logs, screenshots, network traces, error messages, stack traces
3. **Characterize** — when does it happen? When does it NOT? What's different?
4. **Scope** — who's affected? How often? Which environments?

Output of Phase 1: a crisp problem statement.
```
"When user A submits form B in environment C, the response returns 500
  with 'null reference' in auth.py:42. Happens ~30% of the time. Does
  not happen for other users or forms. Started ~2026-04-20."
```

## Phase 2: Hypothesize

Generate 3–5 explanations that would explain the evidence.

1. **Top 3** most likely causes based on the evidence
2. For each, predict: if TRUE, what else would we observe?
3. Rank by likelihood + ease of testing

Example:
- H1: Race condition in session refresh (would see inconsistent behavior; matches "30% of the time")
- H2: Null user field from DB migration (would affect all users equally; eliminated)
- H3: New dependency introduced 2026-04-20 (timeline matches; would affect multiple endpoints)
- H4: User A has corrupted profile data (would be 100% for user A; partially matches)

## Phase 3: Isolate

Test hypotheses with the minimum experiment each.

1. **Binary search** — bisect the problem space (commits, env vars, inputs, code paths)
2. **Minimal repro** — strip away until only the bug-triggering code remains
3. **One variable at a time** — change, test, revert; change the next, test, revert
4. **Read the evidence** — does the experiment confirm or refute the hypothesis?

Tools:
- `git bisect` — find the commit that introduced the bug
- Debugger breakpoints at the boundary between suspect + non-suspect code
- `strace / dtruss / ktrace` — system call level for opaque failures
- Network tap (tcpdump, Wireshark) — for network layer issues
- Print statements with unique markers — lowest-tech, highest-ROI

End of Phase 3: you have the root cause. Verify it by predicting: "If I change X, the bug goes away" and confirm.

## Phase 4: Fix

Now (and only now) write the fix.

1. **Address the root cause**, not the symptom. Patching symptoms creates layered bugs.
2. **Write a regression test** that fails without the fix, passes with it
3. **Consider blast radius** — what else could this fix break?
4. **Document** — commit message explains what + why + how verified
5. **Verify** in the original scenario: does the bug still reproduce?

Example (continuing):
- Root cause: H3 confirmed — new `auth-lib` v2.3 had breaking change to `get_user()` returning None on cache miss instead of re-fetching
- Symptom fix (WRONG): add null check, return 401
- Root fix (RIGHT): downgrade auth-lib OR update call site to handle new semantics with a retry
- Regression test: request sequence that hits the cache-miss path
- Commit: "fix(auth): handle None return from auth-lib v2.3 on cache miss"

## Discipline checklist

- [ ] Did I reproduce before theorizing?
- [ ] Did I write down my hypotheses?
- [ ] Did I test hypotheses individually, not all at once?
- [ ] Did I find the root cause, not just a symptom?
- [ ] Does my fix have a regression test?
- [ ] Did I verify the original bug is gone?

## Common failure modes

- **Jumping to fix without observing** — "I bet it's X, let me change X" → 3 hours later, still broken
- **Changing multiple things at once** — can't attribute success to any single change
- **Fixing symptoms** — bug reappears in a different form
- **Not reproducing** — can't tell if the "fix" actually worked
- **No regression test** — bug returns in 6 months
- **Premature fix** — fixes the wrong thing; real bug still there

## Working with AI

AI coding assistants often skip Observe + Hypothesize. They pattern-match
to similar bugs and suggest fixes. For simple bugs this works. For non-trivial
bugs, force the methodology:
- "Before proposing a fix, what do you OBSERVE? Restate the problem."
- "What are your top 3 hypotheses?"
- "Which would you test first, and how?"
- "Confirm root cause before fixing."

## Anti-patterns

- "It works on my machine" — that's a hypothesis, not a conclusion
- Reading code + pattern-matching without running it
- "I'll just try X" without thinking about what X would prove
- Blaming dependencies / users / the universe without evidence
- Shipping the fix without writing a test
- Not documenting what the root cause actually was — future-you + teammates lose the lesson

## Examples

- "Debug why Helios chat returns 500 intermittently"
- "Systematic debug: Taskflow ingestion pipeline loses 0.1% of events"
- "Why does the OpenKit scanner hang on large repos?"
- "This test fails in CI but passes locally — walk through systematically"
