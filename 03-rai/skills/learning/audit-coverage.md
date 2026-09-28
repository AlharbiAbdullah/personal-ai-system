---
name: audit-coverage
description: Verify a learning topic has full coverage before declaring done. Flags gaps.
allowed-tools: Read, Bash, AskUserQuestion
---

# Audit Coverage

Before John marks a topic as complete, verify it. Identify gaps, missing mechanisms, unanswered questions.

## Instructions

### Step 1: Identify topic

Ask John which topic is up for audit. Confirm from `~/helm/06-learning/{topic}/progress.md`.

### Step 2: Enumerate lessons

List every lesson file in the topic. Read each one.

### Step 3: Audit per method

Read `method` from `progress.md`. For `review` topics (the default), use the Review checklist. For legacy `build` topics, use the depth-shape checklists below.

#### Review audit (method: review)
For each lesson doc (it is a RECORD of a live session, not a textbook):
- [ ] Has "Concept" + "Worked code"?
- [ ] Has "Drills" — a mix of predict-output / spot-the-bug / explain-back / decide?
- [ ] Each drill recorded with John's answer + the reveal, not just the question?
- [ ] Has "Weak spots" logged, and mirrored to the weak-areas log in progress.md?
- [ ] No read-through walls: reads as a record, not a textbook to re-absorb?
- [ ] Planted bugs are realistic (the kind he'd meet reviewing AI code)?

#### Beginner audit (legacy build)
For each lesson:
- [ ] Has "The Problem" — a concrete situation, not "what is X"?
- [ ] Has "How It Works" — step-by-step mechanism, no forward references?
- [ ] Has "Minimal Example" + "Less Minimal Example"?
- [ ] Has "Common Traps" — specific, not generic?
- [ ] Has "Do This Now" — one exercise, not optional?
- [ ] Defines all jargon on first use?

#### Mid audit (legacy build)
For each lesson:
- [ ] Has "Claim" — specific enough to be wrong?
- [ ] Has "Evidence" — measurable?
- [ ] Has "Counter-claim" — what alternative was rejected?
- [ ] Has "Tradeoff" — real cost, not "nothing"?
- [ ] Has "Application" — specific to John's stack?
- [ ] Has "Prediction" — what the author would do next?

#### Expert audit (legacy build)
For each lesson:
- [ ] Has "Delta" — novel vs prior knowledge?
- [ ] Has "Mechanism" — code or spec level with citations?
- [ ] Has "Failure Mode" — where does this break?
- [ ] Has "Steal-List" — concrete transplants, not ideas?
- [ ] Has "Open Questions"?

### Step 4: Check coverage gaps

Cross-check: are there subtopics the topic name implies but no lesson covers?

For example, `master-data-path` implies coverage of: warehouses, pipelines, SQL, dimensional modeling, streaming, governance. If any is absent, flag.

### Step 5: Report

Output a pass/fail per lesson + an overall verdict:

```markdown
# Audit: {topic}

## Per-lesson results
- Lesson 001: ✅ all required sections present.
- Lesson 002: ⚠️ missing "Counter-claim" (Mid mode requires it).
- Lesson 003: ❌ "Application" is generic — no John-specific stack reference.

## Coverage gaps
- No lesson covers {subtopic X}. Suggest: add Lesson NNN.

## Overall
{pass | needs N fixes | fail}
```

### Step 6: Offer to fix

For each failed lesson, offer to regenerate it via `/learning teach`. Don't auto-fix without confirmation.

## Rules

- Apply the exact method criteria (review by default). Don't lower the bar.
- Flag anti-patterns (see `teach.md` anti-patterns list) — meta-sections, checkbox goals, empty scaffolding.
- Honest verdict. Don't rubber-stamp.
