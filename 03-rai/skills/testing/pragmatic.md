---
name: pragmatic
description: >
  Pragmatic testing — the anti-TDD companion. USE WHEN TDD is overkill:
  rapid prototyping, spike solutions, exploratory code, legacy migration.
  Tests still exist; they just don't lead.
---

# Pragmatic Testing

TDD is excellent for production code in well-understood domains. It's overkill
for prototyping, spikes, and exploratory work. This skill is the escape hatch.

## When to use (TDD is wrong tool)

- **Spike / exploration** — you don't know the design yet; TDD assumes you do
- **Prototype** — will be thrown away or substantially rewritten
- **Legacy migration** — the goal is to not break behavior, not to redesign
- **Research code** — correctness of the approach matters more than test coverage
- **Ops scripts / glue code** — one-shot, low-blast-radius

## When NOT to use (go back to TDD)

- Production code entering the main branch
- Code that other teams depend on
- Anything billing/security/safety-critical
- Business logic that will evolve over time

## Workflow

### 1. Code first, tests targeted
- Write the code to prove the idea
- Once it works, pick 2–5 key tests for the parts that matter:
  - **Happy path** — main success case
  - **Known edge case** — the one that bit you during development
  - **Public API boundary** — what callers depend on

### 2. Test ONLY what's fragile
- Don't test getters/setters, trivial glue
- Don't test framework-provided behavior
- DO test: business logic, integration points, non-obvious branches

### 3. Characterization tests for legacy
When migrating legacy code, write tests that document CURRENT behavior (warts and all) before refactoring:
```
def test_current_behavior_with_null_input():
    # This is weird but it's what the old code does.
    # Test exists to catch regressions, not endorse the behavior.
    assert legacy_func(None) == "fallback_string"
```

### 4. Know when to stop
Test coverage ≠ test quality. Stop when:
- The critical paths are covered
- You can make changes confidently
- Future-you will thank present-you

Goal coverage: 40–70% for pragmatic code vs 80–95% for TDD code.

## Signals you should upgrade to TDD

- The code is getting merged to main
- Someone else is now building on it
- Production is depending on it
- You keep fixing the same bug twice

Upgrade by adding tests first for NEW features from that point forward.

## Anti-patterns

- "No tests at all" justified as pragmatic — that's not pragmatic, that's sloppy
- Pragmatic phase extending indefinitely — the prototype becomes prod
- Refactoring legacy without characterization tests — you have no baseline
- Copying TDD ceremony into pragmatic work — defeats the purpose
- Testing implementation details in either mode — tests brittle to refactor

## Comparison with TDD

| Dimension | TDD | Pragmatic |
|---|---|---|
| Order | Test → Code | Code → Test |
| Coverage | 80–95% | 40–70% |
| Design driver | Tests shape API | Code shapes API |
| Best for | Production, well-known domain | Exploration, legacy, prototypes |
| Refactor safety | Very high | Medium |
| Speed (initial) | Slower | Faster |
| Speed (over life) | Faster | Slower |

## Examples

- "Test the new Helios entity extractor spike"
- "What tests should I add to this prototype?"
- "I'm migrating legacy code — where do I start with tests?"
- "Quick and dirty script — what's minimum viable testing?"
