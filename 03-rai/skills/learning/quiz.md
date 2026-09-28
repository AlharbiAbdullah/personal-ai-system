---
name: quiz
description: Spaced retrieval from the whole learning history. Default is a random weighted pull across ALL topics, active and archived. Scoped per-topic quiz only on explicit request.
allowed-tools: Read, Bash, Edit, AskUserQuestion
---

# Quiz

Random spaced retrieval. "Quiz me" means: pick from everything John has ever learned, weighted toward what he missed and what he has not been tested on in the longest time. He must not be able to predict the topic. A python question 4 months after the topic closed is worth more than ten questions the same week (John's call, 2026-08-15; replaces the one-shot batch-drain model).

## Modes

- **Default ("quiz me", no scope):** random pool, cross-topic. This is the normal mode.
- **Scoped ("quiz me on python", "quiz me on L011"):** restrict the pool to that topic or lesson, same steps otherwise.

## Steps

### 1. Build the pool

Sources, all of them:
- `~/helm/06-learning/**/progress.md` — active topics, including nested sub-tracks (e.g. `python-programming/fundamentals/`). The weak-areas log is the primary bank; the cleared-at-delay list is the low-weight spacing pool.
- `~/helm/13-archive/learning/*/progress.md` — retired topics (systems-thinking etc.). Retired does not mean exempt; these are the long-delay questions that matter most.
- Lesson docs and distilled notes (`10-knowledge/`) as costume material, not as separate question sources.

### 2. Weight, then pick at random

Weight each candidate item:
- HIGH / priority-flagged spots: 3x
- Missed or first-contact, never re-tested: 2x
- Ordinary open spots: 1x
- Cleared-at-delay (spacing maintenance): 0.5x
- Multiply up for staleness: the longer since the item was last tested, the heavier.

Then pick with real randomness, not model whim: number the weighted candidate list and select via Bash (`$RANDOM`). Default **3 questions** per session; honor an explicit count ("one quick question" = 1). Max 2 from the same topic per session.

### 3. Pose, one at a time

- **Always in costume.** Never re-ask the logged wording; same mechanism, new surface. A spot logged as SQL injection in an f-string can resurface as an ORM `.raw()` call. A ternary-position spot can resurface inside a dict comprehension.
- Same modalities as live lessons: predict the output, spot the bug, explain back, decide, write-from-memory where the log demands it.
- Python code questions ship as runnable files in `~/playground/python-playground/` when he wants to verify (standing rule); short ones can stay inline.
- Wait for his answer. Never reveal first. Multi-part questions: chase skipped parts, it is a logged habit.

### 4. Grade

- Correct: one line, move on.
- Partial: name exactly what is missing.
- Wrong: right answer plus mechanism. No "good try".
- Vague answers do not pass. Push for the mechanism, not the verdict.

### 5. Write back (this is what makes spacing work)

Update the item in its topic's `progress.md` weak-areas log, with date:
- Clean retrieval at real delay: move toward cleared. Convention: two clean retrievals at increasing delays = cleared (keep in the cleared list for occasional 0.5x spacing).
- Partial or wrong: stays open, note what failed this time, bump priority.
- If a NEW gap surfaces mid-answer, log it as a new item.

### 6. Report

Score, what cleared, what stays open, in a few lines. No study plans, no schedules, no "next quiz on Tuesday": he pulls when he pulls, never a hard daily target.

## Rules

- Never propose per-lesson quiz gates. Retrieval rides on random pulls at natural delays.
- Never re-read as remedy. A missed item gets another drill later, not a lesson re-read.
- Never ask "does this make sense?". Ask a real question.
- The weak-areas logs are the single source of truth. If a quiz result is not written back, the quiz did not happen.
