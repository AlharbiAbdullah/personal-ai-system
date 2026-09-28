# 11-workflows/: Repeatable Playbooks

## Purpose

Step-by-step playbooks for recurring work. A **playbook** is the ordering, decision
gates, and stop-conditions across 2 or more skills that no single skill owns. It
**delegates** to skills (`/router → sub-skill`). It never re-implements them.

## How a playbook gets invoked

1. **Via the router (preferred):** the `/workflow` skill (`03-rai/skills/workflow/SKILL.md`)
   maps a natural-language trigger → the right file here, then reads it. This is the
   discovery surface.
2. **By name:** "do a weekly review", "close the month", "ship this".
3. Every playbook starts with a `**Triggered by:**` line so a plain grep also matches a
   complaint straight to a file.

## Playbooks

### Coding & shipping
| # | Name | When |
|---|------|------|
| 01 | project | Vault side of a new project: idea, kitchen, init, retrospective |
| 02 | task | One unit of work; routes SDD repos to 21 |
| 03 | kitchen | Draft `specs/` in `05-projects/kitchen/` before a repo exists |
| 04 | debugging | Diagnosing a bug or system issue |
| 05 | code-review | Self-review gate before merge |
| 06 | shipping | Releasing / deploying |
| 07 | learning-tech | Evaluating + adopting a new technology |
| 21 | project-init | `/project-init` a repo, then the feature loop, replan, release |

### Life & money
| # | Name | When |
|---|------|------|
| 09 | monthly-money-close | Payday: bills, savings lock, surplus, Visa tripwire |
| 14 | quarterly-financial-review | 90-day statement review + drift propagation |
| 19 | bot-go-live-readiness | Real-money gate for a trading bot; dormant, no live engine exists (rare) |

### Work
| # | Name | When |
|---|------|------|
| 11 | meeting-to-followthrough | Prep → debrief → owned, dated actions |

### Knowledge & vault
| # | Name | When |
|---|------|------|
| 08 | weekly-review | Saturday processing + reflection |
| 12 | harvest-curriculum | Bridge a finished book/course into `10-knowledge/` |
| 13 | capture-sweep | Empty `00-landing/` + `01-inbox/` |
| 18 | deep-research-to-home | Verified research report → permanent vault home |
| 20 | arabic-piece-pipeline | Arabic prose for the site (trio-synth, locked voice) |

### Operations (machines & the brain)
| # | Name | When |
|---|------|------|
| 10 | news-digest-recovery | The scheduled digest failed or shipped placeholders |
| 15 | theme-rollout | Roll a theme out, verify each adapter |
| 16 | cross-machine-parity | Mirror a tool/config across OS adapters (Mac ↔ Ubuntu) |
| 17 | brain-healthcheck | `/rai` sanity → ingest → upgrade, in the safe order |

## Rules

- **Playbooks are stable.** Update only when the workflow itself changes, not for one-off
  variations.
- **Each playbook is self-contained.** No cross-references that force the reader to chase
  another playbook to understand this one. The exception is a hand-off between the project
  playbooks, so each procedure is written once. 01, 02 and 03 keep their triggers and pass
  everything from `/project-init` on to 21. 21 passes the kitchen to 03 and a repo with no
  `specs/` to 02. 04, 05 and 06 pass the fix, the merge and the release of a repo with
  `.project.toml` to 21.
- **Numbered prefix is fixed.** When adding a new playbook, give it the next number.
- **Reference skills as `/router → sub-skill`** (e.g. `/git → commit`, `/architecture →
  solution-architect`), never the bare or under_scored token. This is the convention that
  stops references from rotting.
- **Vault playbooks leave changes for the coordinator.** Anything that edits `~/helm` ends
  with a Sync step: changes stay local, and the hub (the Linux coordinator) commits +
  pushes. Every other machine is a passive replica and never pushes
  (`03-rai/SYNC-ARCHITECTURE.md`). Only code-project playbooks (`~/projects/`) call
  `/git → commit`.
- **Ideas never die; delete over archive.** No "archive the idea" steps. Sessions are the
  only thing archived.

## What Claude should do

When the user invokes a workflow by name or trigger:
1. Read the relevant playbook (the router will route you, or match the `Triggered by:` line).
2. Follow it step by step; run the skills it delegates to.
3. If a step needs adapting to the current context, **propose** the adaptation rather than
   silently skipping.

When the user is mid-work and the situation matches a playbook, suggest it by name. Do not
auto-invoke without confirmation.

If a playbook drifts (a step references a deleted skill or moved path), flag it and propose
an update. `/rai → sanity` checks folder structure and template frontmatter, not playbook
reference integrity. That is caught by reading, not by an automated check.
