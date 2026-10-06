# Meeting Follow-through

**Use when:** a work meeting: preparing for it, and the debrief after it, until every follow-up has an owner and a date. That includes a meeting that will decide scope, ownership or architecture.
**Not for:** 30 architecture decision, for writing the decision paper itself. 32 work engagement, for the engagement the meetings belong to.
**Done when:** the meeting's file in `04-work/<engagement>/` holds the prep and the debrief. The debrief has the date, the attendees and the decisions. Every follow-up has an owner and a due date. Architecture decisions also sit in the engagement's decision log.

His way through a work meeting: prep, the meeting, then the debrief in the same file. No follow-up leaves without a name and a date. For a meeting that will decide something, he writes the framing down first instead of arguing in the room.

```
Prep → (decision paper first) → the meeting → Debrief in the prep file → Owner and date on every follow-up → Route → Sync
```

> **04-work house rules.** No AI or Claude mentions in anything that lands there. Formal tone by default. Check every name, amount and date with him, and never infer one. Never share, post or upload work content.

---

## Steps

### 1. Prep

- [ ] A meeting gets a file when it settles a decision or leaves work owed. A status chat with nothing owed gets none.
- [ ] List the engagements with `ls 04-work/`, never from a fixed list, and pick this meeting's one.
- [ ] Run `/work → meeting-prep`. It reads the engagement's files and writes the prep file, `04-work/<engagement>/meeting-<date>-<slug>.md`, with a blank Follow-ups section.
- [ ] Never invent attendees or context. Ask him.

> **Decision Point**: will the meeting decide scope, ownership or architecture?
> - Yes: the decision paper comes first. Frame it with [[30-architecture-decision]] steps 1 to 7 before the meeting. Its questions to raise go into the prep file, and the paper is the pre-read.
> - No: the prep file is enough.

### 2. The meeting

- [ ] Rai takes no action during the meeting. Resume at the debrief.

### 3. Debrief in the same file

- [ ] Append the debrief to the prep file. One file per meeting. A series that shares a file gets a new dated block.
- [ ] Write the date, the attendees and what was decided. Decisions only: what was settled, not what is still owed. Owed items are step 4.
- [ ] The meeting kept the wrong scope: record the unresolved questions and flag the dependency they leave.
- [ ] Split a thought by audience. The emotional half goes to his journal in `02-ana/`. The architectural half goes to the decision log in `04-work/<engagement>/`, recorded the way [[30-architecture-decision]] step 9 says.

> **Decision Point**: did a decision change scope, ownership or a live system?
> - Yes: flag it in the file. A decision that touches a live system is a production change: carry it into step 4 as an owned action, not only a note.
> - No: step 4.

### 4. Owner and date on every follow-up: the gate

- [ ] Every follow-up becomes one line in the file's Follow-ups section, with an owner and a due date. No exceptions.
- [ ] Stop: a bare "follow up on X" with no owner or no date is not done. Assign both before the debrief closes.
- [ ] An owner or a date only he can settle: put it to him as a question with 2 or 3 options, one of them Recommended. Never leave it dangling in the file.

### 5. Route

- [ ] Owed items stay in this file's Follow-ups section. The next `/work → meeting-prep` for the engagement reads the open ones first.
- [ ] A reusable lesson: `/knowledge → new-topic-note`. A raw spark worth growing: `/ideas → start-seed`. Ideas never die.

### 6. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Skills: `/work → meeting-prep`, `/knowledge → new-topic-note`, `/ideas → start-seed`.
- Workflows: [[30-architecture-decision]] frames the paper before a deciding meeting and holds the decision log's shape. [[32-work-engagement]] sends its meetings, demos and debriefs here.
