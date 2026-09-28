---
name: retain
description: >
  Random rehearsal of knowledge John already finished learning, so it does
  not decay. One small session: a random subject, he does some work, Rai states
  findings, write-back, done. USE WHEN the user says "test me", "retain",
  "rehearse", "am I forgetting", "quiz me on something old", or types /retain.
  Not for new lessons (use /learning) and not for the 3-question weak-spot pull
  (use /learning quiz).
---

# Retain

Rehearsal of finished material. `/learning quiz` re-tests logged weak spots in 3 quick questions; `/retain` picks a whole lesson at random from a finished curriculum and makes John produce it again (build, teach-back, reconstruct, transfer). Light by design so he triggers it often.

## Routing table

| Source | Sub-skill | File to Read |
|--------|-----------|--------------|
| Finished curricula in `13-archive/learning/` | learning | `learning.md` |

Rehearsing topic notes (`10-knowledge/`) or finished books (`07-reading/`) is
not built yet. See `03-rai/skills/GAPS.md`.

## How to use

1. Default (no source named) routes to `learning`.
2. `Read` the sub-skill file and follow it.
3. One session = one pick. "More" is John's call, never Rai's suggestion.

## Examples

- "/retain" → random archived lesson, mode chosen by material
- "/retain python" → random python-fundamentals lesson
- "/retain Lesson 018" → that lesson
- "/retain --mode teach-back" → random lesson, forced mode
