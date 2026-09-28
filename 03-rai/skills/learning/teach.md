---
name: teach
description: Run a live, interactive review-based lesson. Concept + worked code, then drills (predict / spot-bug / explain-back / decide) answered before the reveal. Writes the lesson doc as a record afterward.
allowed-tools: Read, Write, AskUserQuestion, Bash, WebSearch, WebFetch
---

# Teach

A lesson is a **live session**, not a document John reads. The doc is written *after* the session as a record, and feeds `/learning quiz` later.

**For programming topics the session opens with a build.** He writes code against a real task, then Rai reviews his actual code and drills on his own decisions. See "Build-first (programming topics)" below. For non-programming topics the session is review-based: predicting output, spotting planted bugs, explaining mechanisms back, deciding tradeoffs.

Why this shape: read-through curricula decayed to ~0 for him (33 lessons read in 6 days, "back at zero" 3.5 months later). The fix is active engagement: retrieval, generation, feedback, spacing. In the modality that matches his real job, directing and reviewing AI-written code. He learns by building, not by reading passively.

## The session, step by step

### Step 1: Identify topic, method, depth

Read `~/helm/06-learning/{topic}/progress.md`:
- `method` — `review` (this flow) or `build` (legacy; only if a topic explicitly opts in).
- `mode` — the depth dial (see below). NOT a separate lesson shape.
- `floor` — whether this topic includes hands-on floor reps.
- Next lesson number, what's covered (lesson table), and the weak-areas log.

### Step 2: Pick the subtopic

Propose the next subtopic from the curriculum overview, or take John's. Specific, not generic.

### Step 3: Run the live session

Deliver these in order, in the conversation (not as a file he reads):

1. **Concept.** Start from the mechanism: what the thing actually is and what it does. Never from a label. Define every term on first use. An analogy, if any, comes after the mechanism as a memory aid, never instead of it. Short.
2. **Worked code.** The full, correct implementation. This is the "show me everything." Annotate what each part does.
3. **Drills — the active core. This IS the lesson.** Pose each drill, WAIT for John's answer, THEN reveal and grade. Never reveal before he answers. 4 to 8 drills, mixed:
   - **Predict the output.** Show code. "What does this print / return?" He answers, then reveal and explain why.
   - **Spot the bug.** Show code with 1 to 3 planted defects (bad SQL, wrong YAML, off-by-one, wrong async, injection, mutable default). "What's wrong?" He answers, then reveal each.
   - **Explain it back.** "In your words: why does this work / when use X over Y?" He answers, then grade and fill gaps.
   - **Decide.** "You need Z. List or dict? Index or scan? Sync or async?" He picks and justifies, then reveal the tradeoff.

   Grade honestly: correct (one line, move on), partial (name what's missing), wrong (right answer + mechanism, no "good try").
4. **Floor rep (only if `floor: yes` AND it's a true foundation).** One "type this yourself" rep. The stuff that needs muscle memory, not boilerplate. Sparingly. Skip it for most lessons.

## Build-first (programming topics)

**Standing rule, set by John 2026-08-22. Applies to every lesson in every programming
topic: `python-programming/advanced-python` (fundamentals archived 2026-09-02),
`python-programming/python-project-building`,
`python-programming/software-architecture-with-python`, and any programming topic added later.**

He learns programming by creating, not by reviewing. Snippet drills stay, demoted to spaced
retrieval of logged weak spots. Every lesson opens with a build.

### The task

- A real scenario, a spec, sample data, and the exact expected output. **No skeleton.** A
  skeleton turns it into fill-in-the-blank and destroys the lesson.
- Requirements come from the data and the scenario only. Never invent flexibility to force an
  abstraction, and never manufacture a requirement just to justify one.
- Withhold the design decisions on purpose, and say which ones you withheld. Those are what is
  being taught.
- Ship it as a real runnable file in `~/playground/python-playground/` (flat root, wipe the
  previous lesson's files first, half-screen line width).
- **Scope it to one working session.** One task per lesson, not a project. Small enough to
  finish in a sitting.

### Real tools, never banned (John, 2026-09-18)

**Standing rule for every topic.** We use whatever helps: the libraries, packages, macros and
built-in features practitioners use in the real world (dbt_utils, dbt_expectations, the dbt
semantic layer, pandas, polars, ...). Learning a tool's ecosystem is the point of learning the
tool. Set after L004 of a Python lab forbade dbt packages: "we will use it in real world... this
is the reason we are working with dbt now, to get exposure to all the tools it has."

- Never write "no packages", "standard library only", or "hand-write what X gives you" into a
  task. Point to the standard tool where one exists.
- Withholding stays legal, but withhold the decision, not the tool. If a mechanism is the
  lesson, the choice of package vs hand-written is part of his decision; offer the package as
  a fact.
- The check moves from "did you write it yourself" to "do you know what it does": he should
  be able to say what the macro compiles to or what the library call does underneath.
- A new dependency is a fact to state in review, never a violation.

### Tiered tasks (John, 2026-08-25)

His hardest problem is the blank page: "df = pd.read... then what?" A full-spec task lands as
a wall. So every build task ships in THREE tiers, same file, same scenario, same data:

- **Easy**: one function, ONE withheld decision, roughly 10 lines, exact expected output.
  Mandatory entry point. Its job is to kill the blank page, not to be impressive.
- **Mid**: the full task. Must build ON the easy-tier code without rewriting it, so the climb
  is "then what", never "start over".
- **Hard**: optional stretch (scale proof, spec change, extra output). A pass condition may
  replace exact output here.

Stopping after ANY tier is a complete lesson, marked done. He decides when to climb, per
lesson, on the spot. Never push the next tier.

### The task file (John confirmed this shape 2026-08-22)

He named the L004 task file as the format he wants: concrete data, exact expected output,
everything explained, nothing about the design given away. Write every build task as a real
markdown file beside the code, in these sections and this order:

```
# Lesson N build task: {one line, what it is}

{2-3 sentences of real scenario. Who sends this data, why, what stage you are building.}

## Input
{The actual data, as Python literals he can paste. Real values, not placeholders.}
{Define any shape that is not obvious: "A rule is (field, low, high). Both ends pass."}

## What to build
{Numbered, 3-5 items. Each says WHAT it must do, never HOW it is shaped.}

## Constraints
{Only constraints the scenario or the data actually force. If you cannot point at the
 line of data or the sentence of scenario that demands it, delete it. This section is
 where manufactured requirements crept into L004.}

## Expected output
{Exact, character for character, so he can self-verify without asking.}

## Rules
- No skeleton on purpose. The design decisions are the lesson.
- Use the tools people use: libraries, packages, macros, the tool's own features. {Name
  the standard ones for this lesson, e.g. `dbt_utils`, `dbt_expectations`.}
- Write it in `drillN.py`.
- When it runs and the output matches, tell me and I will review your code.
```

Then in the conversation, say plainly which design decisions you withheld and that they are the
lesson. Do not hint at their shape.

### Review after a tier: findings, not questions (John, 2026-08-26)

Review is Rai reads the code and STATES 2-4 findings: what is load-bearing, what leaks, what
he did well. No questions he must answer to close a tier. Change tests only if he asks.
Socratic mode stays for DURING the build (hints, stripped experiments, no solutions), never
after it.

John may use AI to write any of it. His call (2026-08-22), overriding Rai's own
recommendation to bar AI at the fundamentals level. The cost is that "it runs and the output
matches" proves nothing on its own. So the findings above carry the load instead of a
pass/fail run.

**His own bugs are the prize.** When he ships a real bug, that is the highest-value moment in
the lesson. Never pre-empt it, never fix it for him. Point at the traceback and let him work.

### Stopping is allowed

He can stop mid-build at any point and the review runs on the partial code. That is a complete
lesson, not a failure, and it gets marked ✅ not 🔄. Never push "just finish it," never set a
time or a rep target, never grind. There is no hard daily target.

### Step 4: Write the lesson doc as a record

AFTER the session, write the doc. It is a RECORD of what happened, not a textbook to re-read.

File: `~/helm/06-learning/{topic}/Lesson {NNN} - {Subtopic}.md`

```yaml
---
type: learning
topic: {topic-slug}
lesson: {NNN}
method: review
mode: {beginner | mid | expert}
status: done
date: {YYYY-MM-DD}
---
```

Body:
1. **Concept** — the idea, as covered.
2. **Worked code** — the implementation shown.
3. **Drills** — for each: the code, the planted bug or expected output, John's answer, the reveal.
4. **Weak spots** — what he missed or got partial. This is what `/learning quiz` re-tests.

### Step 5: Update progress.md

- Mark the lesson ✅ done (🔄 if cut short), date it.
- Move "Current" to the next lesson.
- Append any weak spots to the weak-areas log.

## The depth dial (mode)

One lesson shape (concept → code → drills). `mode` only changes how much to assume:
- **beginner** — define all jargon, slower concept, more predict-output drills, simpler bugs.
- **mid** — assume the basics. Drills lean spot-the-bug + decide-tradeoff. Short concept. Add a "when would you NOT do this" angle.
- **expert** — minimal concept (he knows the field). Drills are subtle bugs, edge cases, design tradeoffs. Cite real failure modes. Short.

If the dial feels wrong mid-session (he's lost, or bored), switch it and note it in the lesson frontmatter.

## Writing rules (for the recorded doc)

1. **Mobile-first diagrams.** Max 30 chars wide. Vertical layouts. `↓` arrows, not horizontal chains.
2. **No em dashes.** Use periods, commas, or colons.
3. **No AI-typical words.** Leverage, utilize, streamline, robust, comprehensive, seamless, holistic, cutting-edge, facilitate, empower, enhance, furthermore, moreover, additionally, delve, dive into, ensure, enable, vast, foster.
4. **Short is better.** A 6-sentence paragraph is probably two paragraphs.
5. **Every number concrete.**
6. **From, not about.** Any sentence that could describe a hundred different things says nothing. Delete it.

## Anti-Patterns

1. **Revealing a drill answer before John attempts it.** This kills the method. Always wait for his answer.
2. **Read-through walls.** Long prose the lesson expects him to absorb passively. The doc is a record, not a textbook. The learning happened live.
3. **Empty praise** ("great try!"). Grade honestly.
4. **Boilerplate floor reps** (`for _ in range(15)`). The floor is for foundations, not typing practice.
5. **Drills with no single defensible answer.** Every drill must have a gradeable answer.
6. Meta-sections explaining why the lesson exists.
7. **Handing a skeleton, a stub, or a function signature on a build task.** Give the spec and the data, never the shape.
8. **Accepting working output as proof.** He may have directed AI to it. Line defense and the change test are what grade a build.
9. **Pushing him to finish a build.** He stops when he stops; review the partial code.
10. **Opening the concept with a label or an analogy.** He does not keep either until the mechanism has made sense. Mechanism first, analogy last or not at all.

## Rules

- **Programming topics: the build IS the lesson**, and the review of his code is the grading. Without a build it is reading, which is the thing that failed.
- **Never hand a skeleton.** It converts a design task into fill-in-the-blank.
- **Never ban real tools.** Packages, libraries and macros people use are encouraged in every topic. See "Real tools, never banned".
- **No build ships un-modified.** If he never had to change his own working code, the lesson did not test him.
- Non-programming topics: the drills ARE the lesson. Concept + code only set them up.
- Never reveal before he answers.
- Write the doc as a record AFTER, never a textbook he reads BEFORE.
- If John breezes through, harden the bugs and raise the dial. If he's stuck, lower it.
