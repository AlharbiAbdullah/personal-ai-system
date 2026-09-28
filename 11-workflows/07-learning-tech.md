# Learning New Tech Workflow

**Triggered by:** "should I adopt {tool}" / "evaluate {tech}" / "learn {framework}"
**Cadence:** Ad-hoc
**Done when:** a decision record is written (adopt/reject + why), and if adopting, a `06-learning/` curriculum exists.

Evaluate before committing. Most new tools aren't worth adopting — prove value fast or move on.

```
Discover → Evaluate (30 min) → Spike (2-4 hrs) → Decide → Learn deep → Integrate
```

---

## Steps

### 1. Discover

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

> **Decision Point**: Worth spiking?
> - Yes → continue
> - No clear winner → compare top 2 in the spike
> - All options weak → reconsider if the problem needs a new tool at all

### 3. Spike (2-4 hours max)

- [ ] Create a throwaway project (will NOT become production code)
- [ ] Test the core value proposition — the one thing it claims to do well
- [ ] Hit at least one edge case or non-trivial scenario
- [ ] Note friction points, surprises, and documentation gaps
- [ ] Compare developer experience with alternatives if evaluating multiple

> **Decision Point**: Adopt or not?
> - Adopt → continue to step 4
> - Not ready → document why, set a reminder to re-evaluate
> - Reject → document why so you don't re-evaluate unnecessarily

### 4. Decision

- [ ] Write a brief decision record (problem, options, choice + why, trade-offs accepted)
- [ ] An ADR fits well here: `/architecture → adr-writer`
- [ ] If adopting: capture in `06-learning/` for structured learning
- [ ] If rejecting: file the decision record in the relevant knowledge note

### 5. Learn Deep

- [ ] Create a learning curriculum: `/learning → start-topic` (→ `06-learning/[topic]/`)
- [ ] Work through fundamentals systematically (not just tutorials): `/learning → teach`
- [ ] Use `/think → explain-simply` for concepts that aren't clicking

### 6. Integrate

- [ ] Apply the technology to a real task using the [[02-task]] workflow
- [ ] First use should be low-risk (non-critical path)
- [ ] When you have real experience, harvest it: [[12-harvest-curriculum]] → knowledge note in `10-knowledge/`
- [ ] Update the relevant MOC with the new note

---

## Time Limits

| Phase | Max Time | Why |
|-------|----------|-----|
| Evaluate | 30 minutes | If you can't assess it in 30 min, the docs are bad — red flag |
| Spike | 4 hours | Enough to test core value, not enough to get attached |
| Decide | 15 minutes | You have the data, make the call |

---

## Connections

- Learning structure: `/learning → start-topic` + `12-system/templates/Learning.md`
- Idea capture for "not now": `/ideas → start-seed`
- Applying new tech: [[02-task]]
- Harvest into knowledge: [[12-harvest-curriculum]]
- Architecture impact: `/architecture → solution-architect`
