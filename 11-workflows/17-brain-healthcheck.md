# Brain Healthcheck

**Triggered by:** "is the brain healthy" / "brain healthcheck" / monthly / after a structural change
**Cadence:** Monthly (or after any structural change to skills/agents/memory)
**Done when:** `/rai → sanity` reports HEALTHY, pending sessions are drained on the coordinator, and the upgrade list has been reviewed.

Six `/rai` sub-skills that are never chained, and the **ordering is the whole value**.
This playbook never re-implements them — each working step delegates to its skill.

```
Sanity (STOP-gate) → Ingest (coordinator only) → Re-baseline (only post-PASS) → Upgrade list → Leave for coordinator
```

> **The order is dangerous — that's why it's a gate, not a checklist.** Draining
> sessions into a read-only / replica ChromaDB silently *loses* memory, and
> re-baselining over corruption *hides* the loss. ChromaDB has a **SINGLE WRITER:
> the Linux coordinator**. Never write memory from this Mac.
> Source: `03-rai/SYNC-ARCHITECTURE.md`.

---

## Steps

### 1. Sanity — the STOP-gate

- [ ] Run **`/rai → sanity`** — structural integrity scan of skills, agents, memory,
      and the semantic store.

> **STOP-GATE**: if sanity reports **BROKEN** → fix *that* first and do **nothing
> else** in this playbook. Do not ingest. Do not re-baseline. Draining or
> re-baselining on top of a broken brain converts a recoverable fault into silent,
> permanent memory loss. Only a clean/HEALTHY (or HEALTHY-with-warnings) report
> unlocks steps 2–4.

### 2. Ingest pending sessions (coordinator only)

- [ ] Check the pending queue (`03-rai/semantic-memory/pending/`). If **≥ ~10 sessions**
      are waiting, drain them.
- [ ] Run **`/rai → process-sessions`** — but **only on the Omarchy hub**.

> **WRITER GATE**: ChromaDB writes happen on the **Linux coordinator only**.
> This Mac is a passive replica — draining here writes into a stale/read-only store
> and the memory is lost. Reach the coordinator over keyless SSH and run
> it there. If you are on the Mac, leave the queue alone and let the next
> maintenance run (04/10/16/22:00 local time) drain it. Source: `03-rai/SYNC-ARCHITECTURE.md`.

### 3. Re-baseline (ONLY after sanity PASSES)

- [ ] Refresh structural baselines / maps only after step 1 returned HEALTHY.
- [ ] Run `sanity.py --baseline` to refresh the structural baseline (`.sanity-baseline.json`)
      that the next sanity run diffs against.
- [ ] Run **`/map-updater`** to refresh the vault index (`.helm-index/helm-index.md`).

> **Decision Point**: did step 1 actually PASS? Re-baselining over a corrupt brain
> overwrites the "known-good" snapshot with the corrupted state — it *hides* the
> loss instead of surfacing it. If sanity was anything but clean, skip this step
> until the fix lands and sanity re-runs green.

### 4. Upgrade list — review, don't auto-apply

- [ ] Run **`/rai → upgrade`** for a ranked list of improvement opportunities across
      skills, agents, and memory.
- [ ] **Review** the list. Triage into: fix now / queue / ignore. Do **not**
      auto-apply — the skill proposes, John disposes.

### 5. Sync (leave for the coordinator)

- [ ] Any vault edits (refreshed index, fix notes) stay **local**. The Linux
      coordinator commits + pushes at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Never `git push` from the Mac** — single-writer rule. Flag what changed;
      leave it local. Source: `03-rai/SYNC-ARCHITECTURE.md`.

---

## Gating facts (verified, sourced)

| Fact | Value | Source |
|------|-------|--------|
| ChromaDB writer | Linux coordinator only | `03-rai/SYNC-ARCHITECTURE.md` |
| Mac role | passive replica — never pushes | `03-rai/SYNC-ARCHITECTURE.md` |
| Coordinator maintenance | 04/10/16/22:00 local time | `03-rai/SYNC-ARCHITECTURE.md` |
| Pending queue | `03-rai/semantic-memory/pending/` | live |
| Ingest threshold | ~10 sessions waiting | convention |

---

## Connections

- Integrity scan: `/rai → sanity`
- Session ingest (coordinator): `/rai → process-sessions`
- Index refresh: `/map-updater` → `.helm-index/helm-index.md`
- Improvement opportunities: `/rai → upgrade`
- The other coordinator-gated, leave-it-local flow: [[09-monthly-money-close]]
- Single-writer sync architecture: `03-rai/SYNC-ARCHITECTURE.md`
