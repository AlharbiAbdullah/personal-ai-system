# Meeting → Follow-through

**Triggered by:** "prep the {engagement} meeting" / "debrief the meeting" / "action items from {meeting}"
**Cadence:** Per meeting (~weekly)
**Done when:** a meeting file exists under `04-work/{engagement}/` capturing decisions + dated, OWNED action items, and the follow-ups are tracked — not lost.

The loop that doesn't close today. `/work → meeting-prep` emits a brief with a BLANK
Follow-ups section, and ZERO meeting files exist — so prep happens and the debrief never
does. This playbook is the ordering + the one gate that matters: every follow-up leaves
the room with a name and a date on it.

```
Prep → [meeting] → Capture decisions → Convert follow-ups to owned+dated actions → Route → Leave for coordinator
```

> **The gate (step 4):** a bare "follow up on X" is how things rot. A live engagement
> — a dropped action here is a real deliverable dropped. No item leaves the debrief
> without an owner AND a due date.

---

## Steps

### 1. Pre-brief

- [ ] Run **`/work → meeting-prep`** for the engagement — emits agenda, talking points,
      and open threads pulled from `04-work/{engagement}/` and the current ISO-week plan
      under `04-work/work-plans/`.
- [ ] Engagements live under `04-work/{engagement}/`, e.g. `04-work/acme/`. Pick the right one.
- [ ] The brief's Follow-ups section will be blank — that's expected. Steps 3–4 fill it.

### 2. [The meeting happens]

- [ ] No Rai action during the meeting. Resume at the debrief.

### 3. Capture decisions

- [ ] Write (or append to) a meeting file under **`04-work/{engagement}/`** — date in the
      filename, plus **date · attendees · decisions** in the body. One file per meeting,
      append a new dated block if a series shares a file.
- [ ] Decisions only here — what was settled, not what's still owed. Owed items are step 4.

> **Decision Point**: did a decision change scope, ownership, or a live system?
> - If the engagement is in production, a decision touching it is a prod change. Flag it
>   explicitly in the file and carry it into step 4 as an action, not just a note.

### 4. Convert follow-ups to owned + dated actions — THE GATE

- [ ] Every follow-up becomes a line item with **an owner and a due date**. No exceptions.
- [ ] **STOP condition:** any bare "follow up on X" with no owner or no date → it is NOT
      done. Assign both before the debrief closes, or surface it as an open question for
      John to resolve. Never leave it dangling in the file.

### 5. Route deliverables & lessons

- [ ] Deliverables (things owed by a date) → land them in the ISO-week plan under
      **`04-work/work-plans/`** so they show up in the next `/work → weekly-planner` run.
- [ ] A reusable lesson worth keeping → **`/knowledge → new-topic-note`** (topic note with
      the Simplicity Theorem). A raw spark worth incubating → **`/ideas → start-seed`**
      (seed in `09-ideas/`, status in frontmatter). Ideas never die — no pruning.

### 6. Sync (leave for the coordinator)

- [ ] Vault edits (the meeting file, week-plan additions, any topic note / seed) stay
      **local**. The Linux coordinator commits + pushes at its next maintenance run
      (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Connections

- Pre-brief + week planning: `/work → meeting-prep`, `/work → weekly-planner`
- Lesson capture: `/knowledge → new-topic-note`, `/ideas → start-seed`
- Engagements: `04-work/acme/` and any others under `04-work/{engagement}/`; week plans: `04-work/work-plans/`
- Weekly processing that sweeps open actions: [[08-weekly-review]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
