# Learning Stage

**Use when:** running a learning topic in `06-learning/`: opening it, building its curriculum, running its lessons, closing it. A track inside a topic (Python 2.1 to 2.4) runs the same way. So does a topic's lab project.
**Not for:** `07 evaluate a technology` (whether to adopt a tool; an adopted tool's curriculum opens here). `13 capture sweep` (landing and inbox items). `18 research to home` (one question that deserves a written answer). `04 debugging` (a bug outside a lesson build).
**Done when:** he has closed the stage. The topic sits in `13-archive/learning/` and in the `/retain` pool. Its videos are unliked and its captures consumed. Its durable ideas are topic notes.

A stage is one learning topic in `06-learning/`. He opens it and closes it on his word, with no gate. His own tracker (`north-star.md`, `master-plan.md`) is not part of this workflow: Rai neither reads it nor writes it.

```d2
direction: right

open: "1-3 Open\non his word\nmaterial + curriculum"
tools: "4 Tools\none at a time"
lesson: "5-6 Lesson loop\ntask, build,\nfindings, record"
close: "7-9 Close on his word\narchive, unlike,\nconsume, distill"

open -> tools -> lesson
lesson -> lesson: "next lesson"
lesson -> close: "he says done"
```

---

## Steps

### 1. Open the stage

- [ ] He names the topic and opens it. Rai never opens one on its own.
- [ ] Gather the material up front from what he hands over: curriculum, books, liked videos, vault captures. Record it in the curriculum overview. A topic is covered once, from one pile.
- [ ] The resources he hands over are the spine of the curriculum. Use all of them.

### 2. Build the curriculum first

- [ ] No curriculum folder yet: build it before any lesson with `/learning → start-topic`. It asks the method, the depth dial, the floor and the shape.
- [ ] Decide the depth dial and the books now, when the stage opens, never in advance.
- [ ] Method is `review`: live drills, answer before the reveal, never a read-through. A programming topic opens every lesson with a build.
- [ ] A new domain gets a hands-on floor: a few real reps at its base. He may switch the floor off.
- [ ] Anchor the examples in his work: data pipelines, ETL, his own systems.
- [ ] A drill earns its place: real-world use, a concept he must own, or a logged weak spot. Material he can look up (regex syntax, for one) is never drilled.
- [ ] A book inside the topic is its material: taught with `/reading → teach`, and closed with the topic on his word.

### 3. Project stages

- [ ] Offer the project domains as numbered options, one (Recommended). He picks.
- [ ] He sets the product direction before any build. Write it into the curriculum overview and the repo README.
- [ ] Code lives in `~/projects/<topic>-lab/`, outside the vault. Task files sit in its `tasks/` folder; lesson records stay in `06-learning/`.
- [ ] Libraries fold into the build. There is no separate libraries path.
- [ ] Real tools are never banned: the libraries, packages and features practitioners use. The check is whether he knows what the tool does underneath.

### 4. Tools, one at a time

- [ ] Pitch a tool only when a lesson needs it: two lines on what and why, 2 or 3 numbered options, one (Recommended). Never a forward tool roadmap.
- [ ] Rank the options by what practitioners use, and prefer the official tool. He overrules when he has a reason.
- [ ] Libraries go per project with `uv add`.

### 5. Run a lesson

- [ ] When the lesson has one, queue a watch-first video. For Python they came from Corey Schafer and Indently only. He may skip it for a lesson.
- [ ] Write the task file before the build. The concept comes first: the problem with its evidence, what we want, what he will understand, before and after, the guardrails.
- [ ] Then the easy, mid and hard tiers over one scenario: the exact target output, an exact spec (names, columns, counts), and the withheld mechanisms. Reference data comes last.
- [ ] Each task carries one reading question that he answers in words, in the chat.
- [ ] No skeleton. Withhold the decisions that are the lesson, and say which ones are withheld.
- [ ] The easy tier is the mandatory entry: one function, one withheld decision, about 10 lines. Mid builds on it without a rewrite. Hard is optional.
- [ ] Sample data uses Latin script only: no Arabic strings in fixtures, drills or expected output.
- [ ] A concept starts from the mechanism: what the thing is and does, at a level he can check. A label or an analogy comes after, if at all.
- [ ] He does the work. Rai writes the task and reviews. Rai builds only when he asks for a step-by-step build that he follows.

### 6. Review and record

- [ ] Mid-build: one issue per turn, one next action, only what he needs. Never preview a later tier. Hints and stripped experiments, never the solution.
- [ ] His own bugs are his to find: point at the traceback. A bug inside a lesson build follows this rule, not [[04-debugging]].
- [ ] At "check" or a tier's end, review against the task lines only. State 2 to 4 findings, one line each: what is load-bearing, what leaks, what he did well. No questions to close a tier.
- [ ] Working output proves nothing on its own. The reading question and his design defense carry the grade.
- [ ] He decides when to climb and when to stop. Stopping after any tier is a complete lesson, marked done. No daily targets and no caps.
- [ ] At the lesson's close, on his word: `/git → commit` the lab code and push. Write the lesson record, then update `progress.md`: the lesson row, the current line, the weak-areas log.

### 7. Close the stage

- [ ] The stage closes on his word. When all lessons are done, offer the archive. Never propose a quiz pull or a closing gate.
- [ ] He may close before the last lesson. The close line names what was left undone: unrun lessons, an unused question bank.
- [ ] Move the topic folder whole to `13-archive/learning/`, and add its dated line to the `learning/` list in `13-archive/AGENTS.md`.
- [ ] The weak-areas log stays in the archived `progress.md`: it is the `/retain` question bank. Write the close line into its current section.
- [ ] Add the topic to the `/retain` pool: the `POOL` list in `03-rai/skills/retain/scripts/pick.py` and the pool list in `03-rai/skills/retain/learning.md`. A retired tool's course stays out.

### 8. Drain the stage's pile

- [ ] Unlike the stage's liked videos, from the material in its curriculum overview. Never open Chrome unasked: ask first, or hand him the list.
- [ ] After the unlike, the likes count must drop: check it, or ask him when he did it himself.
- [ ] Show him the stage's landing and inbox notes as one list. Each is consumed and deleted on his yes, or stays on the read list by his decision.

### 9. Distill

- [ ] Name the durable ideas the stage left: the ideas worth keeping, not the exercises and worked examples. None: the stage is done.
- [ ] Each durable idea gets one topic note: `/knowledge → new-topic-note`. The Simplicity Theorem comes first, and the note is his understanding, not the course outline. The skill adds it to its MOC.
- [ ] Link the new notes to the existing ones: `/knowledge → find-connections`.
- [ ] Run `/map-updater` so the new notes reach the helm index.
- [ ] Rehearsal happens later, through `/retain` only.

### 10. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Curriculum and lessons: `/learning → start-topic`, `/learning → teach`.
- Books: `/reading → start-book`, `/reading → teach` (Q12.2).
- Lab code: `/git → commit`, on his word.
- Rehearsal after the close: `/retain → learning`.
- Distill: `/knowledge → new-topic-note`, `/knowledge → find-connections`, `/map-updater`.
- Upstream: a tool adopted at [[07-learning-tech]] step 4 opens its curriculum here. [[08-weekly-review]] checks where the open topic stands. [[13-capture-sweep]] leaves the items he keeps for later.
- No agent step: he does the work, and Rai reviews it.
