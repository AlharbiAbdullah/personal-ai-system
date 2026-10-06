# 11-workflows/: John's workflows

## What a workflow is

**A workflow is John's way of doing one kind of work:** the steps, their order, the gates and the checklists. A skill is a capability Rai calls along the way. An agent is a specialist Rai hands one step to.

- **Not a list of skills.** Never slim a workflow to its skill order, and never cut its steps as "general advice".
- **His way belongs here.** A way of working that lives only in memory rulings, or in one repo's docs, is a missing workflow.
- **Need follows who he is.** His profession and interests decide which kinds of work get a workflow, never recent usage. Stale means factually wrong today, not unused.

Judge a workflow by two questions. Does it say how John does this kind of work? Does Rai work that way when the work comes up?

## What Rai does

- In interactive work, when the work matches a workflow, Rai reads it before starting, follows it, and names it: "Following 04 debugging."
- Rai asks only when two workflows fit. Rai skips one only when John says so.
- A step that does not fit the moment gets a proposed adaptation, never a silent skip.
- In a learning build (a lesson repo or a `06-learning/` folder), the Socratic rule in `/learning` wins over 04.
- Headless and scheduled runs follow their own prompts.
- A step that drifted (a moved path, a retired skill) gets flagged with a proposed fix.

## Two kinds of workflow

- **Delivery workflows** move a change from idea to shipped: 01, 02, 05, 06, 21.
- **Method workflows** say how one kind of problem gets solved: 04, 07, 27 to 31, 34, 35.

A method workflow runs inside a delivery workflow. In a repo with `.project.toml` it fills 21's slots: the talk questions, the plan groups, the proof rows, the rollback line and the launch. In any other repo it runs through 02.

## File shape

1. `# Title`, the kind of work in his words.
2. The header lines:
   - `**Use when:**` the kinds of work and situations, in plain words, not trigger phrases.
   - `**Not for:**` the neighbour workflows, as `NN name`, and what goes to each.
   - `**Done when:**` an observable end state.
   - `**Cadence:**` only when the work recurs on a rhythm.
3. One or two sentences on what it is, then the flow as a D2 fence or a one-line flow.
4. `## Steps`: numbered `###` steps, `- [ ]` items, and `> **Decision Point**:` blocks.
5. Reference tables when the work needs them: gating facts, adapter maps.
6. `## Connections`: the skills, agents and workflows it calls.

## Conventions

- **Skills** appear as `/router → sub-skill`, for example `/git → commit`. Never the bare or underscored name.
- **Agents** appear as "the `<name>` agent" at the step that uses it. A one-line brief goes with it: the inputs, the shape of the return, and whether it writes.
  - Never at a human gate.
  - Never inside a skill that forbids agents: `/grill`, `/compile`, `/spec-improve`, `/fusion`, `/orchestrator`.
  - Rai re-checks every load-bearing claim an agent returns.
- **Hand-offs** appear as `[[NN-name]]` plus the step handed to. A workflow names the workflow it hands to and never restates it, so each procedure is written once.
- **No line citations.** Name a file, never `file.md:NN`. Line numbers rot.
- **Diagrams** are D2 fences. Never Mermaid.
- **Prose** passes the Vale gate: `vale --filter='.Name matches "^Rai"' <file>` prints nothing.
- **Numbers are fixed.** A new workflow takes the next free number. A retired number is never reused.
- **Vault edits.** On the hub, commit each finished unit of vault work: fetch and check the behind count first, stage explicit paths, no AI attribution. A replica machine leaves vault edits for the coordinator and never pushes (`03-rai/SYNC-ARCHITECTURE.md`).
- **Code repos** commit through their own flow: 21's gates in a repo with `.project.toml`, `/git → commit` elsewhere.
- **Ideas never die; delete over archive.** No "archive the idea" steps. Sessions are the only thing archived.

## The workflows

### Delivery: how a change moves
| # | Workflow | Use when |
|---|---|---|
| 01 | project | A product from idea to done, vault side: the idea, the kitchen, the hand-off to a repo, the close |
| 02 | task | One change in a repo without `specs/`: helm, a script, a work repo |
| 05 | code review | Reviewing a diff before it merges |
| 06 | shipping | Releasing or deploying |
| 21 | project-init | A repo on the spec-driven standard: init, the feature loop, launch, replan, release |

### Engineering method: how a kind of problem is solved
| # | Workflow | Use when |
|---|---|---|
| 04 | debugging | A bug in code |
| 07 | evaluate a technology | Deciding whether to adopt a tool or a technology |
| 27 | data pipeline | Building or changing a pipeline: a new source, ETL or ELT, an incremental load, a backfill |
| 28 | data platform | Designing, assessing or upgrading a warehouse, lake or lakehouse, modeling included |
| 29 | air-gapped delivery | Shipping into a sealed or offline network |
| 30 | architecture decision | Framing and deciding a design, and writing the decision paper |
| 31 | AI system build | Building or changing an AI feature or product: model choice, harness, evals |
| 34 | diagrams | Drawing a system's architecture and tech stack diagrams for a README or a doc |
| 35 | readme | Writing or rewriting a repo's README to the standard |

### Work and career
| # | Workflow | Use when |
|---|---|---|
| 11 | meeting follow-through | A work meeting: prep, debrief, owned and dated actions |
| 32 | work engagement | A work engagement from the directive to the close-out |
| 33 | career | A proof piece, the profile, an application, a consulting inquiry |

### His machines and Rai
| # | Workflow | Use when |
|---|---|---|
| 10 | news recovery | The scheduled news digest failed or shipped placeholders |
| 16 | machines | Changing, mirroring or standing up a machine |
| 17 | brain healthcheck | A sanity alarm, or after a structural change to Rai |
| 23 | audit | Auditing a vault, a machine, a repo or an architecture |
| 24 | changing Rai | Building or changing a skill, hook, agent, memory path or scheduled job |
| 25 | incident | Something broken on a machine: a job, a timer, sync, the disk, an app |

### Growth and knowledge
| # | Workflow | Use when |
|---|---|---|
| 08 | weekly review | The weekly ritual |
| 12 | learning stage | A learning topic, from open to close |
| 13 | capture sweep | Emptying `00-landing/` and `01-inbox/` |
| 18 | research to home | A question that deserves a verified, written answer in the vault |
| 20 | Arabic writing | Serious Arabic prose, for any destination |

### Life and money
| # | Workflow | Use when |
|---|---|---|
| 09 | monthly money close | Payday |
| 14 | quarterly money review | The 90-day statement review |
| 26 | purchase | Buying hardware or goods, or fighting a vendor over an order |

Retired numbers: 03 (merged into 01), 15, 19. 22 is not shipped in this kit.

## Checks

`/rai → sanity` runs the `Workflows` subsystem, FLOW-1 to FLOW-7. It checks that skills resolve, agents exist and `[[links]]` resolve. It also checks that every workflow sits in this table and in the helm index. No file may cite line numbers, and every header must be complete. A failure makes the verdict DEGRADED, never BROKEN.
