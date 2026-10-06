# Brain Healthcheck

**Use when:** the BRAIN SANITY banner opens a session, a "Rai brain sanity" desktop alert fires, or he asks whether the brain is healthy. Also the aftercare after a structural change to Rai: a skill, hook, agent, memory path or scheduled job.
**Not for:** `24 changing Rai` (making the change; 17 is its aftercare). `25 incident` (anything else broken on a machine: a job, a timer, sync, the disk, an app). `10 news recovery` (the news digest failed).
**Done when:** `sanity-last.json` is under 30 hours old and not BROKEN, and every FAIL and WARN row has been named to him. After a structural change, the upgrade list is in front of him.

The coordinator runs the brain's routine four times a day. It drains the sessions and certifies the brain with sanity, and it refreshes the baseline once a week. Rai's part is to read the verdict when an alarm fires, stop everything on BROKEN, and run the aftercare after a structural change.

```d2
direction: right

cycle: "Coordinator 04/10/16/22\ndrain, then sanity\n(weekly baseline)"
status: "sanity-last.json\nbanner + desktop alert"
read: "1. Read the verdict\nfile time + service"
broken: "2. BROKEN stops everything\nsre or debugger, fix, confirm"
change: "24 changing Rai"
after: "3. Aftercare\nsanity, eval if asked,\nmap-updater, upgrade list"

cycle -> status -> read
read -> broken: "BROKEN or STALE"
change -> after
```

---

## Steps

### 1. Read the verdict

- [ ] On a banner or an alert, read `03-rai/memory/learning/system/sanity-last.json`: the verdict, its time, the FAIL and WARN rows.
- [ ] A stale green verdict proves nothing. Check the file's time and the service (`systemctl --user status rai-maintenance.service`) before trusting it.
- [ ] Older than 30 hours means STALE: the coordinator has stopped.
- [ ] The cycle logs live outside the repo, in `~/.local/state/rai-maintenance/logs/`: one maintenance log and one sanity log per run.
- [ ] Judge the brain from the hub. Sanity run on the Mac over SSH reports a false `DATA-1 remote=NO`.
- [ ] The service exiting 1 while every step returned 0 is the verdict speaking (DEGRADED), not a crash.
- [ ] Daily-log bullets missing under a HEALTHY verdict: check the turn's length and content first. Short or trivial turns are skipped by design.

> **Decision Point**: what the verdict says.
> - HEALTHY and fresh: nothing to do.
> - DEGRADED: name every FAIL and WARN row to him with its fix line, and offer to investigate. Never auto-fix.
> - BROKEN, STALE, or a `COORD-0` row: step 2.

### 2. BROKEN stops everything

- [ ] Fix it before any other brain work: no manual drain and no eval.
- [ ] Never reset the baseline over a FAIL: it hides the loss. The one exception is a count drop from a cleanup he made on purpose (step 3).
- [ ] The coordinator skips the drain on any cycle that follows a harness BROKEN verdict, so a broken store takes no new writes. The runner's own early-abort verdict (`COORD-0`) is about the coordinator, not the stores, and never holds the drain.
- [ ] STALE, a `COORD-0` row or a failed coordinator goes to the `sre` agent. Inputs: the cycle logs, the service's status and journal, `sanity-last.json`. It returns the failing step and its cause with evidence, and changes nothing live.
- [ ] A FAIL row that names a script or a check goes to the `debugger` agent. Inputs: the FAIL row, the sanity log, the script. It returns the proven cause and a proposed fix, and writes nothing live.
- [ ] Rai re-checks every load-bearing claim the agent returns.
- [ ] A fix to a Rai script, hook or job follows the build rules in [[24-changing-rai]] step 5, then its proof in step 7. A machine cause (the disk, a credential, the network) goes to [[25-incident]] step 6. Both prove the fix in scratch first and fix forward.
- [ ] Never restrict Claude's permissions as a fix.
- [ ] A manual drain (`/rai → process-sessions`) runs on the hub only, the sole ChromaDB writer, and only once sanity is out of BROKEN.
- [ ] Confirm with `/rai → sanity` by hand. The next cycle writes the fresh verdict, and the drain resumes on the cycle after it.

### 3. Aftercare after a structural change

Called from [[24-changing-rai]] step 11.

- [ ] Run `/rai → sanity` in full. The change must add no new FAIL.
- [ ] A deliberate large cleanup: once the rest of the run is clean, reset the baseline with `sanity.py --baseline`. The count-drop check then stops firing on the planned drop.
- [ ] `/rai → eval` runs only when he asks. When memory quality is in doubt, say so and let him decide. Never schedule it.
- [ ] Run `/map-updater`. Nothing else refreshes the helm index.
- [ ] Run `/rai → upgrade` for its ranked list. First drop anything on the declined record: the closed audits in `13-archive/audits/` and the never-re-pitch rulings in Rai's memory.
- [ ] He triages the rest: fix now, queue, or drop. Nothing applies itself.

### 4. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## What runs by itself

| Piece | When | Where |
|---|---|---|
| Drain, `/rai → process-sessions` | every cycle (step 3), skipped for a cycle after a harness BROKEN verdict | the hub only, the sole ChromaDB writer |
| Sanity, `sanity.py --write-status` | every cycle (step 3.5), right after the drain | writes `03-rai/memory/learning/system/sanity-last.json` |
| Baseline refresh | inside `--write-status`, once the baseline is a week old and the run saw no drop | `03-rai/.sanity-baseline.json` |
| Early abort | an abort before step 3.5 writes a BROKEN `COORD-0` verdict | the runner |
| Banner | session start, when the verdict is not HEALTHY or is over 30 hours old | `03-rai/hooks/session-start.py` |
| Desktop alert | the hub: critical for BROKEN, normal for DEGRADED | the runner |

The runner is `03-rai/skills/rai/scheduled/run-maintenance-ubuntu.sh`, on `rai-maintenance.timer` at 04, 10, 16 and 22.

---

## Connections

- Skills: `/rai → sanity`, `/rai → eval`, `/rai → upgrade`, `/rai → process-sessions`, `/map-updater`.
- Agents: the `sre` agent and the `debugger` agent at step 2.
- Workflows: [[24-changing-rai]] calls step 3 and owns every fix. [[25-incident]] takes other machine breakage, and [[10-news-digest-recovery]] a failed news run.
- Docs: `03-rai/SYNC-ARCHITECTURE.md` (the coordinator), `03-rai/MEMORY-ARCHITECTURE.md` (what a cycle does inside the memory pipeline).
