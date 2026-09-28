# Harvest Curriculum

**Triggered by:** "I finished {book/course}" / "harvest {topic}" / a `progress.md` reading all-✅
**Cadence:** Per course/book (~monthly)
**Done when:** ≥1 topic note exists in `10-knowledge/` wired into a MOC, and the curriculum is marked harvested in its `progress.md`.

The missing bridge. Today `06-learning/` and `07-reading/` both dead-end at
`audit-coverage` — coverage gets verified, then nothing crosses into `10-knowledge/`.
This playbook is that bridge: it turns a finished curriculum into durable, wired knowledge.
The actual work is the `/knowledge` skills — this is the ordering + the gates.

```
Coverage gate → Distill → Topic note → Wire into MOC → Forward-seed → Mark harvested → Leave for coordinator
```

> **Harvest only what's complete.** A curriculum with gaps is not ready to harvest —
> partial knowledge wired into a MOC reads as settled when it isn't. The coverage
> gate (step 1) is a hard stop, not a formality.

---

## Steps

### 1. Coverage gate (hard stop)

- [ ] Course → run **`/learning → audit-coverage`**. Book → run **`/reading → audit-coverage`**.
- [ ] Source of truth is the curriculum's `progress.md` (`06-learning/{topic}/` or
      `07-reading/{book}/`).

> **Decision Point**: did audit-coverage PASS (all modules/chapters ✅)?
> - **PASS** → proceed to step 2.
> - **FAIL** → STOP. Finish the open modules first (`/learning → teach` or
>   `/reading → teach`). Do not harvest an incomplete curriculum.

### 2. Distill the durable concepts

- [ ] Identify the **1–5 DURABLE ideas** worth keeping forever. Most of a curriculum is
      scaffolding (exercises, worked examples, repetition) — keep only the load-bearing ideas.
- [ ] If you can't name at least one durable concept, the curriculum wasn't worth a topic
      note — mark it harvested (step 6) and stop. Not every course earns a knowledge note.

> **Decision Point**: more than 5 candidate concepts?
> - You're keeping scaffolding. Cut to the few ideas that change how you think,
>   not the facts you can re-look-up.

### 3. Write the topic note(s)

- [ ] For each durable concept, run **`/knowledge → new-topic-note`** — one note per concept.
- [ ] **Simplicity Theorem first**: the note opens with the idea in its simplest form
      before any depth. Scaffold from `12-system/templates/` (`Topic Note.md`).
- [ ] A topic note is your understanding, not the course's outline. Don't transcribe lessons.

### 4. Wire into a MOC

- [ ] Run **`/knowledge → audit-moc`** to place each note under the right MOC in
      `10-knowledge/_mocs/` (6 MOCs exist).
- [ ] Run **`/knowledge → find-connections`** to link the new note(s) to existing notes.

> **Decision Point**: does the note fit cleanly under an existing MOC?
> - **Yes** → wire it in. An unwired note is invisible — wiring is what makes step's
>   "Done when" true.
> - **No clean home** → the note may be too narrow, or a MOC gap. Flag it; don't force-fit.

### 5. Forward-seed open threads

- [ ] Any questions the curriculum opened but didn't close, or "I want to build X with
      this" threads → run **`/ideas → start-seed`** to capture each as a Seed in `09-ideas/`.
- [ ] Ideas never die — capture freely; the pipeline (Seed→Plant→Tree) sorts them later.

### 6. Mark the curriculum harvested

- [ ] Edit the curriculum's `progress.md` (`06-learning/{topic}/` or `07-reading/{book}/`):
      mark it **harvested**, with links to the topic note(s) it produced.
- [ ] The source folder can later retire: a `06-learning/` curriculum moves to
      `13-archive/learning/` (a sanctioned standing exception); a `07-reading/` curriculum has
      no matching archive exception, so it gets deleted (git log keeps it). Either way, that
      is a separate housekeeping pass, not part of this harvest.

### 7. Refresh the map, then Sync (leave for the coordinator)

- [ ] Run **`/map-updater`** to refresh the vault index (`.helm-index/helm-index.md`) so
      the new topic note is discoverable.
- [ ] Vault edits (topic notes, MOC links, seeds, progress.md) stay **local**. The Linux
      coordinator commits + pushes at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Connections

- Coverage gate: `/learning → audit-coverage` · `/reading → audit-coverage`
- Knowledge authoring: `/knowledge → new-topic-note`, `audit-moc`, `find-connections`
- Forward-seeding: `/ideas → start-seed`
- Upstream curricula: [[07-learning-tech]] (course/book intake → this harvests the output)
- Map refresh: `/map-updater` → `.helm-index/helm-index.md`
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
