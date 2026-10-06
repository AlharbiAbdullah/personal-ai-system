# Capture Sweep

**Use when:** emptying `00-landing/` and `01-inbox/`. Each landing item gets promoted or deleted. Each inbox item gets researched, rated, and routed to its home or deleted.
**Not for:** 12 learning stage, for the material of a topic he is running: that topic consumes it. 18 research to home, for one question that deserves a full write-up. 26 purchase, for choosing and buying.
**Done when:** `00-landing/` and `01-inbox/` hold nothing but the items he keeps for later. Every other item is deleted, or sits in its home.
**Cadence:** Weekly, as step 1 of the weekly review.

His parking-lot rule, applied to both capture folders. This file owns the one routing table. The triage skills follow it, and where they differ, this file wins.

```d2
direction: right

landing: "00-landing/\n1 promote or delete"
inbox: "01-inbox/\n2 enrich and rate"
gate: "3 Delete gate\nD and C, one batch"
route: "4 Route\nthe routing table"
stage: "Claimed by a stage\n12 consumes it"
gone: "Deleted\ngit log keeps it"

landing -> inbox: "promote"
landing -> gone: "delete"
inbox -> gate: "C and D"
inbox -> route: "A and B"
gate -> gone: "his yes"
landing -> stage: "claimed" {style.stroke-dash: 3}
inbox -> stage: "claimed" {style.stroke-dash: 3}
```

> **Parking-lot rule.** A landing item has two exits: it earns a place in the inbox, or it is deleted. An inbox item has two exits too: it becomes a note in its home, or it is deleted. Git log is the archive, and not everything deserves a note. The one exception is an item he keeps for later, on his word.

---

## Steps

### 1. Drain landing: promote or delete

- [ ] Run `/triage → process-landing`. It walks every item in `00-landing/` with him, one at a time. It is the only channel that moves or deletes a landing file.
- [ ] Each item gets promoted to `01-inbox/` or deleted. He decides every file.
- [ ] Skip exists only for an item he keeps for later, on his word. The topic that uses it consumes it at [[12-learning-stage]] step 8.

> **Decision Point**: is this still a live question for him this week?
> - Yes: promote it to the inbox.
> - No, or he cannot remember why he captured it: delete it. The capture already did its job.

### 2. Research the inbox

- [ ] Run `/triage → process-inbox`. It enriches every unclaimed item in place with the research template: what it is, why he should care, why it matters.
- [ ] Rate each item A, B, C or D, for relevance to him, never generic importance. An item that cannot be tied to his goals or identity rates lower.
- [ ] The rating is the routing signal. A and B go to step 4. C and D go to the delete gate.
- [ ] Hand the enrichment to the `researcher` agent, all items in parallel. Inputs: the item files, `02-ana/identity/goals.md`, `who-i-am.md` and `vision.md`. Returns: per item, the template text with its sources, and a suggested rating and home. It cannot write files.
- [ ] Rai re-checks every load-bearing claim the agent returns, then writes the enrichment into the file. The rating and the delete gate stay with Rai.

### 3. Delete gate

- [ ] D: delete.
- [ ] C: delete, unless it cross-links to something already live.
- [ ] A and B go on to step 4.
- [ ] Show him the D and C deletions as one batch, and delete on his yes. A delete needs his go.

> **Decision Point**: will he reread it, or link to it from real work?
> - Yes: route it at step 4.
> - No: delete it. Git log keeps the record, and the vault stays a working set.

### 4. Route the survivors

- [ ] Propose each item's home from the table, and move it on his confirmation.
- [ ] The enriched file moves whole, research included. When the home has a scaffold skill, the skill writes the note from the enriched file, and the inbox file is then deleted.
- [ ] Never hand-build a note shape. The templates are in `12-system/templates/`.

| The item is | Its home | How |
|---|---|---|
| material to study: a course, a book, an article, a paper | the topic he is running, in `06-learning/` or `07-reading/`. For later: it stays where it is, kept on his word | Ask which. [[12-learning-stage]] opens a new topic |
| a tool, a library or a concept | `10-knowledge/<domain>/`. A tool joins its topic note's Toolbox | `/knowledge → new-topic-note` |
| an idea | `09-ideas/`, as a Seed | `/ideas → start-seed` |
| a project | `09-ideas/`, as a Seed. Only `/ideas → graduate` opens a kitchen | `/ideas → start-seed` |
| research for a project | `05-projects/kitchen/<name>/research/` while it has a kitchen. `05-projects/active/<name>/research/` after its repo's G1 merge | move whole |
| a feature for a repo with `.project.toml` | that repo's backlog, never `09-ideas/` | `mise run backlog -- <topic>`, run in the repo |
| a work item | `04-work/<engagement>/` | move whole. The folder's house rules apply |
| personal or life | the right folder in `02-ana/` | move whole |
| research for a purchase | the item's plan in `02-ana/shopping/` | [[26-purchase]] step 5 |
| a question that deserves a verified write-up | the home 18 picks | [[18-deep-research-to-home]] step 1 |

- [ ] An article or a paper he wants to read later stays in the capture folder, on his word. It waits there until a topic he runs uses it.

- [ ] Ideas never die. A Seed is never pruned or archived later: its status lives in its frontmatter.

### 5. Confirm both folders are empty

- [ ] `00-landing/` holds nothing but its `AGENTS.md` and the items a stage claims.
- [ ] `01-inbox/` holds nothing but its `AGENTS.md` and the items a stage claims.
- [ ] An unclaimed item still there failed a gate. Go back and force the decision. Done means empty of everything this sweep owns, not mostly processed.

### 6. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Called by [[08-weekly-review]] step 1.
- Skills: `/triage → process-landing`, `/triage → process-inbox`, `/knowledge → new-topic-note`, `/ideas → start-seed`, `/ideas → graduate`.
- Agents: `researcher` (step 2).
- Workflows: [[12-learning-stage]] consumes the items a stage claims. [[26-purchase]] takes purchase research into its plan. [[18-deep-research-to-home]] takes a question that deserves a write-up.
