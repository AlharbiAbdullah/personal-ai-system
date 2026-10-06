# Work Engagement

**Use when:** a work engagement, from the directive to the close-out. That covers a new directive from his manager, or one that changes an open engagement's scope. It also covers a demo to stakeholders, a deploy to the client, a handover to another team, and closing an engagement out.
**Not for:** one meeting goes to 11 meeting follow-through. The decision paper itself is 30 architecture decision. The build runs in 27 data pipeline, 31 AI system build, 21 project-init or 02 task. Shipping into a sealed network is 29 air-gapped delivery. His own products are 01 project. A consulting inquiry before it is agreed is 33 career.
**Done when:** `04-work/<engagement>/` holds the decision paper or proposal, a record for each demo, and a close-out note with the outcome. The runbooks sit in the work repo. When the engagement ends, a retrospective exists in `05-projects/completed/<name>/`.

An engagement is paid work for his employer or a client, from the directive to the close-out. His way names the owner before any architecture, proves everything on a copy of prod, and hands over cleanly.

```d2
direction: down

s0: "0 Open the folder"
s1: "1 Frame"
s2: "2 Decision paper"
s3: "3 Split the work"
s4: "4 Build for the\nprod profile"
s5: "5 Demo"
s6: "6 Prove on a\ncopy of prod"
s7: "7 Package and\nhand over"
s8: "8 Deploy and\nverify live"
s9: "9 Close out"

s0 -> s1 -> s2 -> s3 -> s4 -> s5 -> s6 -> s7 -> s8 -> s9
s1 -> s3: "a build, owner named" {style.stroke-dash: 3}
s5 -> s4: "next milestone" {style.stroke-dash: 3}

out: "Hand-offs" {
  w30: "30 decision paper"
  w11: "11 each meeting"
  wb: "27, 31, 21 or 02\nthe build"
  w29: "29 sealed target"
  w06: "06 other targets"
  w01: "01 retrospective"
}

s2 -> out.w30
s1 -> out.w11
s4 -> out.wb
s7 -> out.w29
s8 -> out.w06
s9 -> out.w01
```

---

## Steps

### 0. Open the folder

- [ ] Each engagement gets its own folder, `04-work/<engagement>/`, with a short, obvious name. It sits beside the other engagements, never inside one. Code lives in `~/work/<name>`.
- [ ] House rules for everything that lands in `04-work/` (its `AGENTS.md` holds the full list):
  - Confidentiality first. Nothing is shared, posted or uploaded without his explicit go. When unsure, the answer is no.
  - No AI or Claude mentions in any output.
  - Formal tone by default.
  - Verify proprietary names, amounts and dates with him; never infer them. Use the full names he gives, never a short form.
  - Diagrams: Excalidraw while editable, PDF when final.

> **Decision Point**: a new engagement, or part of an open one?
> - A directive that closes the old scope, such as a re-scope or a cancellation, closes the engagement. Work after it is a new engagement with its own folder.
> - Otherwise the work stays in the open engagement's folder.

### 1. Frame

- [ ] Take his read first: the business situation and his own view of it. He locks the end state in short answers. Record each answer.
- [ ] Write a context doc from the engagement's own documents first. Then work from those sources only.
- [ ] Name the objective, the owner and the technical authority before any infrastructure. Push for the owner at the first cross-team contact, not after the design.
- [ ] Hand a first read to the `architect` agent. Inputs: the context doc and the directive. It returns the objective, the owner, the technical authority and every open framing question, as the sources state them. It writes nothing. Rai re-checks every load-bearing claim it returns.
- [ ] Each meeting runs through [[11-meeting-to-followthrough]]: its prep before, its debrief and owned, dated actions after.

> **Decision Point**: what does the directive ask for?
> - A decision, or the owner or the objective is missing: the deliverable is a decision paper. Step 2.
> - A build, with the owner and the objective named: step 3.

### 2. Decision paper or proposal

- [ ] Frame and write it with [[30-architecture-decision]]: its steps 1 to 6 decide, step 7 writes the paper for leadership, step 9 records it.
- [ ] When the real deliverable is a decision, the paper is the whole deliverable. No build starts.
- [ ] A new initiative's proposal states the return it brings to the client.
- [ ] The paper lives in `04-work/<engagement>/`.
- [ ] Before a meeting that will decide on it, send the paper and the questions to raise, through [[11-meeting-to-followthrough]]. He writes the framing down instead of arguing it in the room.
- [ ] A version in a second language is written natively, never translated. For Arabic: [[20-arabic-piece-pipeline]].
- [ ] He decides when the paper is done. Offer the gaps once; when he says keep it, keep it.

### 3. Split the work

- [ ] He owns the input contract, and Rai owns everything downstream. A validator he can run gates the hand-off: green means his inputs match what the build expects.
- [ ] One spec is read at the start of every session. Later decisions go on top of it as dated entries, never tidied into it.
- [ ] Across a team boundary, each side owns its part, and the contract is read off the code. Write it with the contract branch of [[30-architecture-decision]].
- [ ] Once he locks the decisions, run to the checkpoint he names without stopping to ask.
- [ ] Gate: the validator is green on his inputs.

### 4. Build for the prod profile

- [ ] Cut what the target does not need. The MVP runs on its own. Integrations are built in, optional, and ready before access exists.
- [ ] Whatever differs between the demo and the target swaps by config, never by code.
- [ ] Build first, and package only after the product is solid. The plan stays flexible: an unfinished item moves, and no deadline forces it.
- [ ] Dev machines never bend the prod path. A machine-specific change lives only in a local override file.
- [ ] A sealed target: run [[29-air-gapped-delivery]] step 0 during the build, so the client's IT gets one complete request early.
- [ ] The build itself: AI parts run [[31-ai-system-build]], a pipeline runs [[27-data-pipeline]]. The code change runs [[21-project-init]] Phase C in a repo with `.project.toml`, [[02-task]] elsewhere.
- [ ] Every automated check passes before his manual test.
- [ ] Say "tested" only after a real run against the live stack. Import checks and static checks are not a test.
- [ ] A result that looks too easy gets proven, by a checksum or a real run, before he hears it.

### 5. Demo

A demo repeats at each milestone, then comes back to step 4.

- [ ] The demo path is separate from the main build: its own folder or repo, and nothing touches the main one.
- [ ] Run every scripted question on today's data first. Keep only questions that return a good answer from real data.
- [ ] Confirm each named entity in the built dataset during the dry run.
- [ ] Every mode the demo uses works and is rehearsed before the day, online and offline alike.
- [ ] Prove the claim live, for example by cutting Wi-Fi before the offline section. Keep a skip list for online-only questions, and a fallback model.
- [ ] Demo files with personal data stay out of git history.
- [ ] He decides the demo cast.
- [ ] Slides and diagrams follow the audience rules in [[30-architecture-decision]] step 7. Docs describe only what the demo really shows.
- [ ] Hand the dry run to the `qa-tester` agent. Inputs: the question script and the demo stack's address. It returns one row per question: answered from real data or not, with the answer. It writes nothing. Rai re-checks every row the demo rests on.
- [ ] Tear the demo environment down afterwards. A script rebuilds it.
- [ ] After the demo, append a short record to the meeting file that [[11-meeting-to-followthrough]] opened for it. The record holds the date, the audience, what worked, what was asked, and what is owed. The debrief runs through 11.
- [ ] Gate: every dry-run item confirmed before the day.

### 6. Prove on a copy of prod

- [ ] A sealed target: [[29-air-gapped-delivery]] step 3 runs the rehearsal.
- [ ] Any other target: VMs that copy the target machines, run end to end on dummy data.
- [ ] A handover rehearses on VMs that mirror the receiving team's setup.
- [ ] Run the lab on the machine that has the VM tooling. A machine that cannot run the VMs cannot prove the result.
- [ ] The checklist is binary, and any FAIL blocks. Write down what the lab mimics and what it does not.
- [ ] Hand the checklist run to the `qa-tester` agent. Inputs: the checklist and the lab's address. It returns one PASS or FAIL row per item, with evidence. It writes nothing. Rai re-checks every row the gate rests on.
- [ ] Gate: every item PASS.

### 7. Package and hand over

- [ ] A sealed target: hand the bundle to [[29-air-gapped-delivery]] step 2. Its steps 4 to 6 carry, deploy and verify it.
- [ ] Handing the work to another team:
  - They own the operation and its growth. Hand over what exists today; they decide what comes next. Plan a speedy exit, not shared ownership.
  - Simplicity beats capability. Cut a feature that makes the handover complex.
  - The original repo stays whole. The handed-over product lives in its own private repo, seeded with one clean commit, holding only what it needs.
  - Internal files such as `.claude/`, `.agent/` and `project_memory/` never reach them. Stage explicit paths, never `git add -A`.
  - Few, flat docs. One guide takes a new developer from zero to the whole system, end to end.
  - The contract lists only what exists. An endpoint it does not list does not exist.
- [ ] Ops docs are short and human-runnable: plain commands, no placeholders, no `$(date)`, no backslash continuations, no inline Python.
- [ ] Operator docs use the operators' own language.
- [ ] Prove the restore once before handing over. A backup nobody has restored is not yet a backup. For a sealed target, [[29-air-gapped-delivery]] step 6 proves it.
- [ ] Hand the restore drill to the `sre` agent. Inputs: the restore doc and the lab copy. It returns each step's output and the doc's done checks as PASS or FAIL. It writes only in the lab. Rai re-checks every FAIL.
- [ ] Hand the handover guide to the `writer` agent. Inputs: the architecture doc, the runbook and the contract. It returns one guide in plain English, with every command copied from a run that worked. It writes the draft file only. Rai checks each command against the repo.
- [ ] Gate: the runbook's own done checks pass.

### 8. Deploy and verify live

- [ ] A sealed target: [[29-air-gapped-delivery]] steps 5 and 6.
- [ ] Any other target: [[06-shipping]] from step 0, which records what the target runs now.
- [ ] Write the outcome into `04-work/<engagement>/` the same day: deployed or not, which version, and what the verification showed.
- [ ] Something fails on site: reproduce it before fixing, with [[29-air-gapped-delivery]] step 7 for a sealed target, [[04-debugging]] elsewhere.
- [ ] Gate: the verify section passed, and the outcome is written down.

### 9. Close out

The scope ends by delivery, by a handover, or by a directive that closes it. Then:

- [ ] Write the close-out note in `04-work/<engagement>/`:
  - what shipped, and whether the last deploy happened;
  - what is live, where, and who operates it now;
  - what is owed, by whom, and by when;
  - the open questions, and who must answer each one;
  - where the runbooks, the decision log and the repos are.
- [ ] Bring the decision log up to date: append every decision made since its last entry.
- [ ] Split by audience. The emotional half goes to his journal in `02-ana/`. The architectural half goes to the decision log.
- [ ] Every owed item has an owner and a date.
- [ ] Write the retrospective through [[01-project]]'s close step, in `05-projects/completed/<name>/`. When production work follows a retrospective, update it.
- [ ] Work after the close opens a new engagement at step 0.
- [ ] Owed items live in the Follow-ups section of the file they came from: a meeting file, or this close-out note. The next prep for the engagement reads the open ones first.
- [ ] The close-out is a note of its own in the engagement folder, written when the scope ends. It is never a section of the retrospective.

### 10. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Variant: a video deliverable

A video changes these steps. The rest hold as written.

| Step | For a video |
|---|---|
| 1 | Research the tools and the reference studios before anything is built. Research the client's brand live, from their own site and channel. |
| 2 | Write a decision summary, then the open questions that need management's confirmation before the script locks. The build waits for those answers. |
| 4 | Pick a tool that renders the client's script correctly by design. `/media → remotion` is the current pick. |
| 5 | Versioned renders. He reviews each one. A rejected direction is replaced, not patched. |
| 7 | Replace any clip that shows a readable name tag. Use the client's official terminology. Confirm with the client before any external publication. |
| Files | Renders stay in the work folder outside the vault. `04-work/<engagement>/` keeps the research and the decisions. |

---

## Connections

- Meetings: [[11-meeting-to-followthrough]]. The decision paper: [[30-architecture-decision]]. Arabic documents: [[20-arabic-piece-pipeline]].
- The build: [[31-ai-system-build]], [[27-data-pipeline]], then [[21-project-init]] or [[02-task]].
- Delivery: [[29-air-gapped-delivery]] for a sealed target, [[06-shipping]] for any other.
- The end: [[01-project]] for the retrospective. A consulting inquiry arrives through [[33-career]].
- Skills: `/work → meeting-prep` through 11, `/media → remotion` for a video.
- Agents: the `architect` agent at step 1, the `qa-tester` agent at steps 5 and 6, the `sre` agent and the `writer` agent at step 7.
