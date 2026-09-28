---
name: sanity
description: End-to-end integrity CERTIFIER for the Rai brain and the helm jobs around it. Runs the sanity.py harness, role-aware checks that assert every subsystem PRODUCES fresh output, not merely that files exist. A PASS certifies the whole system works as intended. Use when the user says "/sanity", "check the brain", "run a healthcheck", or suspects something is broken.
allowed-tools: Bash, Read
---

# /rai sanity: brain integrity certifier

The brain was sick for three months once while the old healthcheck stayed green. It tested
structure (a file exists, a hook is registered), never function (the thing produced fresh
output). It also drifted onto a dead collection and passed on the corpse. This harness is built
so that class of failure cannot hide:

- Every productive component asserts an output and freshness contract.
- Coverage gates FAIL or WARN on any live component no check asserts.
- Every check has a fault test that proves it fires on the fault it exists for.

The logic lives in `skills/rai/scripts/`: `sanity.py` runs and reports, and `sanity_checks/`
holds the checks, one module per subsystem. This skill runs the harness and relays the report.
Do not re-implement checks inline. Add or change them in the harness, with a test.

## Run it

```bash
~/helm/03-rai/semantic-memory/scripts/py-chroma.sh ~/helm/03-rai/skills/rai/scripts/sanity.py
```

The `py-chroma.sh` wrapper provides chromadb. Plain `python3` fails: the system python has no
chromadb. A full run takes a few seconds.

Present the report as-is: it is grouped by subsystem, with a fix line under every FAIL and WARN.
Lead with the VERDICT line, surface FAIL and WARN rows first, and offer to investigate. Do not
auto-fix.

## Flags

| Flag | Effect |
|------|--------|
| (none) | Full certification |
| `--quick` | Skip the slow checks (subprocess smoke runs, the full-tree symlink scan) |
| `--json` | Machine-readable output. Exit code is the verdict: 0 HEALTHY, 1 DEGRADED, 2 BROKEN |
| `--list` | Print the check catalog (ID, subsystem, role, what it asserts) from the code |
| `--baseline` | Reset `.sanity-baseline.json` to today's counts, after a known-good cycle or a deliberate large cleanup |
| `--write-status` | Write `memory/learning/system/sanity-last.json`, and refresh the baseline when it is a week old and this run saw no drop. The coordinator passes this every cycle |

## Coverage by subsystem

`--list` prints every check. By subsystem:

| Subsystem | Asserts | FAIL means BROKEN |
|-----------|---------|:-:|
| Data safety | origin reachable and pushes landing, coordinator heartbeat, no count drop, union merge rules, restic backup fresh, no tracked file near GitHub's limits, no unattended `git pull --rebase` | yes |
| Environment | chromadb imports, the wrapper runs | yes |
| Stores | the four collections populated, fresh, writable, queryable, in parity with the committed index | yes |
| Pipeline | queue draining, scripts parse on both interpreters, coordinator wired and firing, its steps succeeding, scanner capturing both transcript roots | yes |
| Live capture | daily logs fresh and parseable, rai-daily tracking them, working memory under its cap | |
| Self-evolve | candidates accruing, promotion gate working, the ACTIVE render present and capped | yes |
| Retrieval | the frozen memory block fresh, semantic, episodic and daily queries returning rows | yes |
| Hooks | every registered hook present, parsing, importing, firing, error-free, and touching its artifact | yes |
| Identity, Eval | identity loads as session-start runs it, stays in the budget session-start warns on; the golden set parses | |
| Config, Harness | the Claude Code, pi and OpenCode edges resolve into the vault, pi runs the same hooks, the dev-env bootstrap can recreate every edge | |
| Vault, Code | the folder skeleton, templates and root files exist; every other `.py` and `.sh` in the vault parses | |
| Auto-memory | helm's Claude Code memory slot is mounted from `03-rai/auto-memory`, the index is under the loader's 200-line cut | |
| Skills, Agents | names match folders, critical skills reachable, no dead collection refs, agents match their MANIFEST | |
| Jobs | news, portfolio, gold-skim and the Obsidian Sync watcher timers fire clean and leave output; every helm timer is asserted | |
| Drift | MANIFEST rows, types and counts, doc paths, helm-index and curated wikilinks, router tables, Obsidian folders, cited check IDs, tracked-but-ignored files | |
| External | the claude-hud status line resolves | |
| Self-test | every live collection is asserted, the hook registry is readable, every check has a fault test | yes |

## Roles

The hub (Omarchy) is the producer and the coordinator. The Mac is a read replica. Producer checks such as "is it distilling" or "do the timers fire" would false-FAIL on the
replica, where not doing them is correct. So the harness detects its role and SKIPs checks that
do not apply: `darwin` is the consumer, anything else the producer. `RAI_ROLE=producer|consumer`
overrides it. A SKIP never counts toward the verdict.

## Verdict tiers

- **HEALTHY:** no FAIL, at most two WARN.
- **DEGRADED:** a FAIL outside the load-bearing set, or three or more WARN. A feature is off. Data is safe.
- **BROKEN:** a FAIL in a subsystem marked yes above. Stop and fix it before other brain work.

A check that raises, hangs past 90 seconds, or returns a malformed result reports FAIL with the
reason. A broken check is a finding, never a silent pass.

## On a fresh kit

Before `./setup.sh` and your first few sessions, expect BROKEN: the `~/.claude` links, the four
collections and the self-evolve files do not exist yet. After setup and a first
`/rai process-sessions`, what stays red is honest. A few checks cover optional parts you may
never set up: the pi bridge (HARN), the vault auto-memory store (MEM-1) and the offsite backup
(DATA-5) SKIP until you do. The Jobs checks assume the news and maintenance timers from
`SYNC-ARCHITECTURE.md`; drop the ones you do not run from `JOBS` in `sanity_checks/jobs.py`.

## The alarm path

Every coordinator cycle (04, 10, 16 and 22 local) runs `sanity.py --write-status` as step 3.5,
right after the pipeline. The committed `sanity-last.json` reaches every machine, and
session-start opens the next session with a BRAIN SANITY banner when the verdict is not
HEALTHY. A verdict older than 30 hours shows as STALE: the coordinator has stopped. A run that
aborts before step 3.5 writes a BROKEN `COORD-0` verdict itself. The hub also raises a desktop
notification: critical for BROKEN, normal for DEGRADED.

## Tests

```bash
cd ~/helm && uv run --offline --python 3.12 --with chromadb --with pytest \
  python3 -m pytest 03-rai/skills/rai/scripts/tests -q -p no:cacheprovider
```

Each test builds a throwaway home tree, points the harness at it, injects one fault and asserts
the verdict. They run in a few seconds and touch nothing live. META-3 WARNs on any check
without a `test_<id>_fault*` test.

## Extending it

- **New check:** an `@check("ID", "Subsystem", role=...)` function in the right module, plus a
  `test_<id>_fault*` test. Keep its evidence line specific enough to act on.
- **New collection:** add it to `ASSERTED_COLLECTIONS` with a check, or to
  `TOMBSTONED_COLLECTIONS`. META-1 FAILs on a live collection in neither.
- **New hook:** HOOK-1 to HOOK-4 read the registry, so it is covered for presence, parsing and
  firing. Add a HOOK-6 effect row if it writes an artifact, and wire it into the pi bridge
  (HARN-2 WARNs otherwise).
- **New timer:** add it to `JOBS` in `sanity_checks/jobs.py` and give it an output check. JOB-3
  WARNs on any helm timer missing there.
- **New harness edge:** assert it in `harness.py` and create it in the dev-env bootstrap.
  HARN-3 WARNs when the bootstrap cannot recreate an edge sanity asserts.
- **New subsystem:** add it to `SUBSYSTEM_ORDER` in `sanity_checks/core.py`, and to
  `BROKEN_SUBSYSTEMS` if a failure there means the brain is not working.

## Notes

- Read-only by default. Only `--baseline` and `--write-status` write, and only to the baseline
  and the status file.
- STORE-3 writes and deletes one row in the permanent `sanity-probe` collection. It never drops
  the collection, because each drop leaves an orphan segment directory on disk.
