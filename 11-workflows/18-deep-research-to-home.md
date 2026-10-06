# Research to Home

**Use when:** a question deserves a verified, written answer that lives in the vault. That covers a concept, a comparison of options, a survey of a field, or the research behind an idea or a work decision. It also covers a capture item that needs a full write-up.
**Not for:** 26 purchase, for the research behind a buy: its plan in `02-ana/shopping/` is the home. 07 evaluate a technology, for adopting a tool. 30 architecture decision, for a design decision and its paper.
**Done when:** a verified, cited report sits in one permanent home, with every load-bearing claim re-checked, and the helm index lists it.

A research run that ends in the transcript is lost. This workflow takes a sharp question to a verified, cited report in a permanent home, then indexes it. The two gates, scope and route, carry the value.

```
Scope gate → Research → Verify the claims → Route → Land it → Index → Sync
```

> **The output is worthless if it dies in the transcript.** A run that ends without a routed, indexed home is not finished.

---

## Steps

### 1. Scope gate

- [ ] Read the question. Is it specific enough to research as it stands?
- [ ] Underspecified, such as "best vector DB": stop. Ask 2 or 3 clarifying questions first: the use case, the constraints, the region, the time horizon, whatever narrows it.
- [ ] Weave the answers into one refined question. Never run on the vague one.
- [ ] A question about what to buy is purchase research: [[26-purchase]] step 1 takes it.

> **Decision Point**: a vague question gives a vague report, and that report earns no home.
> - Sharp question in, or no run.
> - He resists narrowing: name the trade-off, a broad query gives a shallow survey, and let him choose.

### 2. Research

- [ ] Run `/deep-research` with the refined question. It fans out the searches, fetches the sources, checks the claims and writes a cited report.
- [ ] `/deep-research` is not available in this session: hand the question to the `researcher` agent. Inputs: the refined question, its constraints and today's date. Returns: a cited report, with a confidence level per claim and the date of each source. It cannot write files or run Bash.
- [ ] Never redo the fan-out by hand.

### 3. Verify the load-bearing claims

- [ ] Before anything lands, Rai re-checks every load-bearing claim: each number, name, version and date a decision would rest on. Open the cited source and confirm it says so.
- [ ] A claim that fails is fixed or cut, never landed.
- [ ] A contested claim gets a second model's view through `/fusion → ask`.

### 4. Route: pick one home

- [ ] Route by what the report is, not by what it is about. The homes and their scaffold skills are the routing table at [[13-capture-sweep]] step 4. Where this list and that table differ, the table wins.

> **Decision Point**: what is the report?
> - A durable concept or mental model: a topic note in `10-knowledge/<domain>/`, through `/knowledge → new-topic-note`.
> - A survey of a field, such as a literature review done with `/research → literature`: a topic note in `10-knowledge/<domain>/`. A survey that serves one project goes in that project's `research/` folder.
> - Research for a purchase: the item's plan in `02-ana/shopping/`, at [[26-purchase]] step 5. Never `10-knowledge/`.
> - It sparked an idea, not just a fact: a Seed in `09-ideas/`, through `/ideas → start-seed`.
> - Work for a live engagement: `04-work/<engagement>/`, under that folder's house rules.
> - Nothing fits cleanly: a topic note is the default home. Never leave it in the transcript.

### 5. Land it

- [ ] Run the chosen home's scaffold skill, or move the report whole where the table says so.
- [ ] Carry the citations through. An uncited landing throws away the verification.
- [ ] No archive verbs. Git log is the archive, and ideas never die.

### 6. Index it

- [ ] Run `/map-updater`, so the helm index lists the new report. An unindexed report is a buried report.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Research: `/deep-research`, with the `researcher` agent as the fallback at step 2.
- Homes: `/knowledge → new-topic-note`, `/ideas → start-seed`, the routing table at [[13-capture-sweep]] step 4, and [[26-purchase]] for a buy.
- A second opinion on a contested claim: `/fusion → ask`.
- Index: `/map-updater`.
- Sent here by [[13-capture-sweep]] and [[08-weekly-review]], for an item that deserves a write-up.
