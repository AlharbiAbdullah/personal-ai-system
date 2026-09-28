---
name: workflow
description: >
  Playbook router. USE WHEN the user is about to run a recurring multi-step
  process that has a playbook: "ship this", "the news didn't fire", "close the
  month", "do it on ubuntu too", "review the portfolio", "I finished this book",
  "prep the {x} meeting", "let's debug this", "is the bot ready for real money",
  "init this project", "add a feature to {repo}", "replan {repo}".
  Maps the trigger to the right numbered playbook in `~/helm/11-workflows/` and
  reads it. This is the sequencing layer OVER skills: it never replaces a skill,
  it orders them.
---

# Workflow

The discovery surface for `~/helm/11-workflows/`. A **playbook** is the ordering,
decision gates, and stop-conditions that no single skill owns. It sequences
skills, it does not re-implement them. When the user is about to start a recurring
process, match the trigger below, then `Read` the playbook file and follow it.

The playbooks live in `~/helm/11-workflows/`, **not** in this skill folder. This
router only maps intent → file.

## Routing table

Match on the user's phrasing or the situation. Then `Read` `~/helm/11-workflows/{file}`.

### Coding & shipping
| Trigger | Playbook | File |
|---------|----------|------|
| "new project", "build {idea} from scratch", "start the {idea} project" (an idea in `09-ideas/`, no folder yet) | project | `01-project.md` |
| "do this task", "implement {feature}", "fix {bug}", single unit of work | task | `02-task.md` |
| "plan {project}", "write the PRD/SPEC for {project}", "graduate this idea", "draft the specs for {project}" | kitchen | `03-kitchen.md` |
| "let's debug this", "{X} is broken", "why is {behaviour} happening" | debugging | `04-debugging.md` |
| "review this diff", "self-review before merge" | code-review | `05-code-review.md` |
| "ship this", "deploy {project}", "cut a release" | shipping | `06-shipping.md` |
| "should I adopt {tool}", "evaluate {tech}", "learn {framework}" | learning-tech | `07-learning-tech.md` |
| "init this project", "set up a new project", "adopt {repo}", "upgrade {repo} to v3", "audit {repo}", "add a feature to {repo}", "replan {repo}" | project-init | `21-project-init.md` |

### Life & money
| Trigger | Playbook | File |
|---------|----------|------|
| "close the month", "payday", "salary landed", "monthly money run" | monthly-money-close | `09-monthly-money-close.md` |
| "quarterly review", "run the Q review", "90-day statement review" | quarterly-financial-review | `14-quarterly-financial-review.md` |
| "is the bot ready for real money", "go live with the bot" | bot-go-live-readiness | `19-bot-go-live-readiness.md` |

### Work
| Trigger | Playbook | File |
|---------|----------|------|
| "prep the {engagement} meeting", "debrief the meeting", "action items from {meeting}" | meeting-to-followthrough | `11-meeting-to-followthrough.md` |

### Knowledge & vault
| Trigger | Playbook | File |
|---------|----------|------|
| "weekly review", "Saturday processing", "process the week" | weekly-review | `08-weekly-review.md` |
| "I finished {book/course}", "harvest {topic}" | harvest-curriculum | `12-harvest-curriculum.md` |
| "clear the inbox", "run a capture sweep", "empty landing + inbox" | capture-sweep | `13-capture-sweep.md` |
| "research {X} properly and write it up", "deep research on {X}" | deep-research-to-home | `18-deep-research-to-home.md` |
| "write an Arabic post", "اكتب مقال", "Arabic piece for the site" | arabic-piece-pipeline | `20-arabic-piece-pipeline.md` |

### Operations (machines & the brain)
| Trigger | Playbook | File |
|---------|----------|------|
| "news didn't fire", "digest is placeholders", "no news today" | news-digest-recovery | `10-news-digest-recovery.md` |
| "add this theme", "{X} didn't adapt/repaint", "roll out {theme}" | theme-rollout | `15-theme-rollout.md` |
| "do it on ubuntu too", "mirror to the other machine", "set up on both boxes" | cross-machine-parity | `16-cross-machine-parity.md` |
| "is the brain healthy", "brain healthcheck" | brain-healthcheck | `17-brain-healthcheck.md` |

## How to use

1. Match the request to a row. If two could fit, see the playbook's own header.
   - project (01) or project-init (21): an idea still only in `09-ideas/` goes to 01; a
     folder or repo in hand goes to 21. 01 hands off to 21 at init, so either start is safe.
   - "cut a release" goes to 06. In a repo with `.project.toml`, 06 sends the version,
     changelog and tag to Phase E of 21.
   - A PRD for work or a client is not a playbook: `/writing → prds`. 03 drafts the
     `specs/` of a product John builds himself.
2. `Read` `~/helm/11-workflows/{file}`: the whole file.
3. Follow it step by step. Where a step says `/router → sub-skill`, invoke that skill
   for the machine work; the playbook owns only the sequence and the gates.
4. If a step needs adapting to the current context, **propose** the adaptation rather
   than silently skipping it (per `11-workflows/AGENTS.md`).
5. Do **not** auto-invoke a playbook the user didn't ask for. Suggest by name when the
   situation matches.

## Workflow vs skill: the boundary

- A **skill** is one capability invocation (`/testing → tdd`).
- A **playbook** is the *ordering + decision gates + stop-conditions* across 2 or more
  skills that no single skill owns.
- If a candidate is really one skill, it belongs in `03-rai/skills/`, not here.
- A playbook **delegates** to skills (`run /X`); it must never paste a skill's content.

## Single-writer note

Playbooks that edit the `~/helm` vault leave the push to the coordinator. The hub is the
sole writer of `origin`; every other machine is a **passive replica** and never runs
`git push` on the vault. Vault playbooks end by leaving changes for the hub's next
maintenance run. Only code-project playbooks (in `~/projects/`) call `/git → commit`.
See `03-rai/SYNC-ARCHITECTURE.md`.

## Cross-references

- The playbooks themselves → `~/helm/11-workflows/`
- Folder rules + index → `~/helm/11-workflows/AGENTS.md`
- Reference-integrity audits run inside → `/rai → sanity`
