# Capture Sweep

**Triggered by:** "clear the inbox" / "run a capture sweep" / "empty landing + inbox"
**Cadence:** Weekly — also the front half of the weekly review
**Done when:** both `00-landing/` and `01-inbox/` hold nothing except items already assigned
to an active `master-plan.md` stage — those are consumed inside their stage, not by this
sweep (rule 5).

The capture spine. Two skills exist but nothing sequences them with the delete-gate, so
the manual sweep never self-fires. This playbook is the ordering + the gate: landing decides
promote-or-delete, inbox researches + rates + routes, and the delete-gate keeps the vault
from filling with notes nothing will reread.

```
Landing → Inbox → Delete-gate → Route → Confirm empty → Leave for coordinator
```

> **Parking-lot rule:** `00-landing/` has no middle ground — a landing item either earns a
> place in the inbox or it dies. The inbox has no middle ground either — an item becomes a
> destination note or it's deleted. Git log is the archive; not everything deserves a note.

---

## Steps

### 1. Drain landing (promote or delete)

- [ ] Run **`/triage → process-landing`** — walk every item in `00-landing/`.
- [ ] Each item: **promote to `01-inbox/`** (worth researching) **OR delete** (noise,
      stale, already-known). No "leave it for later" — an item a master-plan stage already
      names stays put for that stage, everything else gets a decision now.

> **Decision Point**: is this still a live question for you *this week*?
> - Yes → promote to inbox.
> - No / can't remember why you captured it → delete. The capture already did its job.

### 2. Research the inbox

- [ ] Run **`/triage → process-inbox`** — for every item: enrich it, then rate **A/B/C/D**.
- [ ] The rating *is* the routing signal: A/B survive to step 4, C/D feed the delete-gate.

### 3. Delete-gate (the whole point)

- [ ] Before routing, run the gate on each researched item. **Not everything deserves a
      note.**
- [ ] **D = delete now.** **C = delete unless it cross-links to something already live.**
      A/B proceed.

> **Decision Point**: will I actually reread this, or link to it from real work?
> - Yes → route it (step 4).
> - No → delete it. The git log preserves that it ever existed; the vault stays a
>   working set, not a graveyard.

### 4. Route the survivors

- [ ] Send each A/B item to its destination. Use the scaffolding skill, never hand-build a
      note shape (templates: `12-system/templates/`).

| Item is… | Destination | How |
|----------|-------------|-----|
| an incubating idea | `09-ideas/` (Seed) | `/ideas → start-seed` |
| work / engagement | `04-work/` | file under the engagement |
| a learning topic | `06-learning/{topic}/` | `/learning → start-topic` |
| a knowledge insight | `10-knowledge/{domain}/` | `/knowledge → new-topic-note` |
| a book to read | `07-reading/{book}/` | `/reading → start-book` |
| a project seed | `09-ideas/` (Seed) | `/ideas → start-seed`; its kitchen comes later from `/ideas → graduate` |
| personal / life | `02-ana/` | file under the right Life OS folder |

> Ideas never die — a Seed in `09-ideas/` is not pruned or archived later, status just
> lives in frontmatter (`seed|plant|tree|graduated`).

### 5. Confirm both folders empty

- [ ] `00-landing/` is empty (ignore its `AGENTS.md`).
- [ ] `01-inbox/` holds nothing except items a `master-plan.md` stage already claims
      (ignore its `AGENTS.md`).
- [ ] If either still holds an unclaimed item, it failed a gate — go back and force the
      promote / delete / route decision. **"Done" means empty of everything this sweep
      owns, not "mostly processed."**

### 6. Sync (leave for the coordinator)

- [ ] All edits (new notes, deletions, idea seeds) stay **local**. The Linux coordinator
      commits + pushes at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Connections

- Landing triage: `/triage → process-landing`
- Inbox research + rating: `/triage → process-inbox`
- Idea capture: `/ideas → start-seed`, `/ideas → promote`
- Knowledge / learning / reading scaffolds: `/knowledge → new-topic-note`, `/learning → start-topic`, `/reading → start-book`
- This is the front half of: [[08-weekly-review]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
