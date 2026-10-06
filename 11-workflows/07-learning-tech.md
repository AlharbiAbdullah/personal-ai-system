# Learning New Tech Workflow

**Use when:** deciding whether to adopt a tool or a technology, or whether to learn one: a library, a framework, a CLI, a service. Evaluating it against the alternatives and what he already uses, spiking it, recording the call, and starting its learning once adopted.
**Not for:** 31 AI system build, for a model or a serving engine for an AI build: its step 2 decides that. 12 learning stage, for learning a topic already open. 30 architecture decision, for a design choice for an organization or a client. 16 machines, for installing or configuring a tool already chosen.
**Done when:** a decision record is written (adopt/reject + why). If adopting, its curriculum is started in `06-learning/`, and hands-on use has started. A reject also leaves a never-re-pitch ruling.

Evaluate before committing. Most new tools aren't worth adopting. Prove value fast or move on.

```
Discover → Evaluate (30 min) → Spike (2-4 hrs) → Decide → Learn deep → Integrate
```

---

## Steps

### 1. Discover

- [ ] Check the declined record first: grep Claude Code's auto-memory index (`MEMORY.md`) for the tool and for "never re-pitch". A declined tool stops here unless John reopens it.
- [ ] What problem does this technology solve?
- [ ] How did I encounter it? (article, recommendation, pain point)
- [ ] Is this solving a problem I actually have, or just interesting?

> **Decision Point**: Real problem or shiny object?
> - Real problem I have now → continue
> - Interesting but no immediate need → capture as [[Seed]] in `09-ideas/` (`/ideas → start-seed`), revisit later
> - Already solved by current stack → stop

### 2. Evaluate (30 minutes max)

- [ ] What are the alternatives? (at least 2-3)
- [ ] Community health: stars, recent commits, open-issues ratio
- [ ] Maintenance: who maintains it, is it a one-person project?
- [ ] Documentation quality: can I get started in 10 minutes?
- [ ] License: compatible with my use case?
- [ ] Hand the evaluation to the `researcher` agent. Inputs: the problem from step 1 and the candidates. Returns: the alternatives with community health, maintenance, docs and license, each cited and dated. It cannot run commands or edit files, and it keeps to the 30 minutes.
- [ ] Rai re-checks each load-bearing claim at its source.

> **Decision Point**: Worth spiking?
> - Yes → continue
> - No clear winner → compare top 2 in the spike
> - All options weak → reconsider if the problem needs a new tool at all

### 3. Spike (2-4 hours max)

- [ ] Create a throwaway project (will NOT become production code)
- [ ] Test the core value proposition: the one thing it claims to do well
- [ ] Hit at least one edge case or non-trivial scenario
- [ ] Note friction points, surprises, and documentation gaps
- [ ] Compare developer experience with alternatives if evaluating multiple
- [ ] Hand the throwaway build to the `engineer` agent. Inputs: the core claim, one edge case, and a scratch folder outside the vault and every real repo. Returns: what worked, what broke, and the friction log. It writes only in that scratch folder, within the 4 hours.
- [ ] Rai re-runs the spike's key result before it counts.

> **Decision Point**: Adopt or not?
> - Adopt → continue to step 4
> - Not ready → document why, and what would change the answer
> - Reject → document why so you don't re-evaluate unnecessarily

### 4. Decision

- [ ] Write a brief decision record (problem, options, choice + why, trade-offs accepted)
- [ ] An ADR fits well here: `/architecture → adr-writer`
- [ ] Hand the draft to the `architect` agent. Inputs: the notes from steps 1 to 3. Returns: a draft record in the shape above. It writes nothing, and the call stays John's, made at step 3.
- [ ] If adopting: capture in `06-learning/` for structured learning
- [ ] If rejecting: file the decision record in the relevant knowledge note
- [ ] A reject also becomes a never-re-pitch ruling in Rai's memory, so step 1 catches it next time.

### 5. Learn Deep

- [ ] Create a learning curriculum: `/learning → start-topic` (→ `06-learning/[topic]/`), and run it through [[12-learning-stage]]
- [ ] Work through fundamentals systematically (not just tutorials): `/learning → teach`
- [ ] Use `/think → explain-simply` for concepts that aren't clicking

### 6. Integrate

- [ ] Apply the technology to a real task using the [[02-task]] workflow
- [ ] First use should be low-risk (non-critical path)
- [ ] When you have real experience, harvest it: [[12-learning-stage]] step 9 → knowledge note in `10-knowledge/`
- [ ] Update the relevant MOC with the new note

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Time Limits

| Phase | Max Time | Why |
|-------|----------|-----|
| Evaluate | 30 minutes | If you can't assess it in 30 min, the docs are bad: red flag |
| Spike | 4 hours | Enough to test core value, not enough to get attached |
| Decide | 15 minutes | You have the data, make the call |

---

## Connections

- Learning structure: `/learning → start-topic` + `12-system/templates/Learning.md`
- Idea capture for "not now": `/ideas → start-seed`
- Applying new tech: [[02-task]]
- The learning itself: [[12-learning-stage]]
- Harvest into knowledge: [[12-learning-stage]]
- Architecture impact: `/architecture → solution-architect`
- A model or serving engine for an AI build: [[31-ai-system-build]] step 2
- Agents: the `researcher` agent (step 2), the `engineer` agent (step 3), the `architect` agent (step 4)
