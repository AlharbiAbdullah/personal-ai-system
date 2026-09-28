# Weekly Review Workflow

**Triggered by:** "weekly review" / "Saturday processing" / "process the week"
**Cadence:** Weekly (Saturday)
**Done when:** sessions processed, inbox empty, projects + ideas reviewed, next week's ONE priority chosen, changes left for the coordinator.

Saturday processing ritual. Process the week, maintain the vault, plan the next week.

```
Sessions → Inbox → This Week's News → Projects → Ideas → Vault → Plan → Sync
```

---

## Steps

### 1. Process Sessions

- [ ] Run `/rai → process-sessions` — drain pending transcripts from `03-rai/semantic-memory/pending/`
- [ ] Review summaries saved to ChromaDB
- [ ] Flag any sessions that produced knowledge worth capturing as notes

### 2. Process Inbox

- [ ] Run the [[13-capture-sweep]] playbook (process-landing → process-inbox → route).
- [ ] Inbox is empty when done.

> **Decision Point**: Item doesn't fit anywhere?
> - If interesting → `09-ideas/` as a Seed (`/ideas → start-seed`)
> - If not → delete it. Not everything deserves a note. (Git log is the archive.)

### 3. Review This Week's News

- [ ] Skim this week's daily digests in `08-bawaba/daily/` (and the Saturday `weekly/` issue if it landed)
- [ ] For anything that stuck: deep-read the content, discuss relevance
- [ ] Decide per item:
  - **Done** — interesting but no action needed (the news skill archives digests to `13-archive/news/`)
  - **Promote** — create a Seed in `09-ideas/` or a capture in `01-inbox/`
- [ ] Worth a full write-up? → [[18-deep-research-to-home]]

### 4. Review Active Projects

- [ ] Open `05-projects/projects-moc.md` — the project inventory
- [ ] For each active project:
  - [ ] Is it still active? If it stalled for more than 2 weeks, consider pausing it. A repo with `.project.toml` records the pause in its `specs/roadmap.md` through a replan (`/grill "replan the roadmap"` in the repo), never in the vault.
  - [ ] Where it stands: `mise run status` in a repo with `.project.toml` (the open change, the next roadmap item). `active/{name}/` keeps research and meeting notes, never a status copy.
  - [ ] Check priorities: still correct? If not, the repo is due a replan.
- [ ] Any blocked projects? Identify the blocker.

### 5. Review Ideas Pipeline

- [ ] Scan `09-ideas/` — any seeds ready to become plants? plants → trees? trees → graduate?
- [ ] Advance the ready ones with `/ideas → promote` / `graduate`.
- [ ] **No pruning.** Ideas never die (`09-ideas/AGENTS.md`); low-energy ones stay and seed future ideas via lineage.

> **Decision Point**: Promote an idea?
> - Yes → `/ideas → promote` (or `graduate` if it's a ripe Tree)
> - Not ready → leave it, check next week

### 6. Update Vault

- [ ] Create any new knowledge notes from the week's learnings (`/knowledge → new-topic-note`)
- [ ] Update existing notes with new insights
- [ ] Check for emergent connections (`/knowledge → find-connections`) — create an [[Insight Note]] if found
- [ ] Run `/map-updater` to refresh `.helm-index/helm-index.md`

### 7. Plan Next Week

- [ ] Choose ONE priority for the week (not three, one)
- [ ] Block time for deep work on that priority
- [ ] Identify dependencies or blockers ahead of time
- [ ] Write the priority in the journal: `/routine → tomorrow-prep` or `02-ana/journal/[date].md`

### 8. Sync

- [ ] Verify nothing was accidentally deleted or overwritten.
- [ ] Vault edits stay **local** — the Linux coordinator commits + pushes at its next maintenance run. **Do not `git push` from the Mac** (single-writer — `03-rai/SYNC-ARCHITECTURE.md`).

---

## Cadence

| Frequency | Action |
|-----------|--------|
| Weekly (Saturday) | Full workflow above |
| Daily (optional) | Quick inbox scan, journal entry (`/routine`) |
| Monthly | Money close ([[09-monthly-money-close]]), review MOCs, brain healthcheck ([[17-brain-healthcheck]]) |

---

## Connections

- Session processing: `/rai → process-sessions`
- Capture triage: [[13-capture-sweep]]
- Idea lifecycle: `/ideas` skill group
- Project tracking: `05-projects/projects-moc.md`
- Journal: `/routine → journal`
