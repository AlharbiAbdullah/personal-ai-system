# Audit

**Use when:** auditing his own system to fix what it finds: the vault, Rai, a machine or a repo. A cleanup with a findings list counts. Or reviewing an architecture for a written report, his own, an employer's or a client's.
**Not for:** a check against the project-init standard, which is 21 project-init. A diff before merge, which is 05 code review. One thing broken now, which is 25 incident. A sanity alarm, which is 17 brain healthcheck. A planned change to a machine, which is 16 machines.
**Done when:** fix mode: every worklist box is ticked or closed without action, and the worklist is in `13-archive/audits/`. Report mode: the report is delivered, every load-bearing finding in it verified, and he agreed a fix order.

An audit reads a whole system, verifies every finding, and turns the findings into decisions he makes one at a time. Fix mode executes them through briefed workers. Report mode ends in a written report.

```d2
direction: down

frame: "1. Frame it\nmode, scope, guardrails"
truth: "2. Ground truth first"
lanes: "3. Read-only lanes\na skeptic each, one critic"
verify: "4. Verify every\nload-bearing claim"
frame -> truth -> lanes -> verify

report: "Report mode" {
  write: "5. One honest headline\nsolid, breaks at scale, fix first"
}

fix: "Fix mode" {
  worklist: "6. Worklist by wave"
  decide: "7. He decides\none item at a time" {shape: hexagon}
  guard: "8. Guard every delete"
  execute: "9. Briefed workers\nat most two lanes"
  review: "10. Rai reviews\nand ticks"
  worklist -> decide -> guard -> execute -> review
  review -> decide: "next wave"
}

close: "11. Close\narchive, aftercare"

verify -> report.write: "report"
verify -> fix.worklist: "fix"
report.write -> fix.worklist: "his own system" {style.stroke-dash: 3}
report.write -> close: "a client"
fix.review -> close: "every box closed"
```

---

## Steps

### 1. Frame it

- [ ] Agree the frame with him before any lane runs: the goal, where it runs, the latitude, the output and the guardrails. Latitude is report only, or fix.
- [ ] A big audit goes through `/grill`, which locks the frame.
- [ ] Pick the mode. Fix mode is for his own systems. Report mode is for an architecture review that ends in a report.
- [ ] Report mode gets a fixed scope and a time box. A client audit runs one to two weeks.
- [ ] Report mode takes its lens from the workflow that calls it. [[28-data-platform]] supplies the maturity rubric: nine capability layers scored 0 to 4 against the production-ready bar.
- [ ] Read the declined record first: the closed audits in `13-archive/audits/` and the never-re-pitch memory rulings. A declined item never comes back as a finding.
- [ ] Guardrails: never push. Touchy subsystems (memory, sync, git history) get "explain before you touch this".
- [ ] Client or employer material stays confidential. It goes to no external model panel without his go, and nothing written for it mentions AI.
- [ ] An audit that spans sessions keeps a resume file in its run dir, `~/.local/state/rai/<audit>/`. It holds the loop, the queue, the rules that bit and the closing steps. Read it first after a compaction.

> **Decision Point**: which mode?
> - His own system, and he wants it fixed: fix mode, steps 2 to 4, then 6 to 12.
> - A review that ends in a report: report mode, steps 2 to 5, then 11 and 12.
> - A report on his own system can go on into fix mode at step 6.

### 2. Ground truth first

- [ ] Run the system's own checks before any lane reads a file.
  - Rai: `/rai → sanity`.
  - A repo: the test suite, the linter, one pipeline run, and the commit state.
  - A machine: an inventory of what is installed on each machine in scope.
- [ ] Answer one question from the results: does it work end to end at any layer?
- [ ] Check handoff docs and old findings against the current `main` before trusting them.

### 3. Research, read-only

- [ ] Fan out here, and only here. Research needs no decision from him, so lanes may run in parallel. Decisions stay in one session with him.
- [ ] Fix mode: one lane per area of the system, a skeptic for each lane, and one critic over all lanes for what they missed.
- [ ] Choose the fix-mode lanes by folder or subsystem, one lane each, as the helm cleanup ran its 11 lanes.

- [ ] Report mode with no caller's rubric: run the lenses of his Orca audit. They are architecture, code quality, data pipeline, tests and tooling, and docs and hygiene.
- [ ] Add the three areas his services page names: model serving, infrastructure and failure modes.

- [ ] An architecture lens runs `/architecture → solution-architect`, `/architecture → data-architect` and `/devops → docker` side by side on one context, as his Helios review did.
- [ ] A system that serves users gets a threat lens: trust boundaries, the one defended boundary, and what each guard does not claim. `/security → security-review` runs it.
- [ ] The `reviewer` agent runs each lane or lens: inputs the area, the ground-truth results, the declined record and the finding format. It returns findings with file evidence, an action and a risk, and writes nothing.
- [ ] A second `reviewer` agent is each lane's skeptic. It re-reads the source for every finding and returns confirmed, corrected or refuted, with a corrected action where it differs. It writes nothing.
- [ ] One more `reviewer` agent is the critic: inputs every lane's findings; returns what the lanes missed; writes nothing.
- [ ] A lane that needs outside facts, such as what a package does, goes to the `researcher` agent. It returns cited answers and writes nothing.
- [ ] Run heavy lanes in batches of two or three, since a wide burst of large prompts trips the server's rate limit. Resume a failed Workflow run from its run id.
- [ ] Keep heavy scratch on disk under `~/.cache/<audit>/`, never under /tmp, and delete it after each round.
- [ ] Idle or unused is never a finding by itself.
- [ ] A live credential found on the way stays where it is. Flag it, and he revokes it at the source first.

### 4. Verify

- [ ] Rai re-checks every load-bearing claim with its own grep or read before it enters the worklist or the report. A load-bearing claim says a file exists, a mechanism runs or a number holds.
- [ ] Where a skeptic corrected a finding, the corrected action wins.
- [ ] Never say "checked" after a partial matrix. Run the full matrix, or name what went unchecked.
- [ ] Re-run a check rather than trust the last "all clean".

### 5. Report mode: write the report

- [ ] Open with one honest headline.
- [ ] Then three parts: what is solid, what breaks at scale, and what to fix first.
- [ ] The fix order starts with what stops the failure recurring, such as committing what is uncommitted and adding CI.
- [ ] Each recommendation carries 2 or 3 options, the Recommended one first.
- [ ] A client audit delivers the written report as a PDF in his house style, with the score table when a rubric scored it. A short deck only when the client asks.

- [ ] Where the report goes depends on whose system it is.
  - His own system: its findings become the worklist at step 6.
  - An employer's system: the report goes into `04-work/<engagement>/`. Its fixes run in that repo through [[21-project-init]] or [[02-task]].
  - A client's system: the report is the deliverable. Go to step 11.
- [ ] Client code that cannot leave a sealed network stays inside. He runs the ground-truth checks on site and brings out findings only, and Rai works from those.

### 6. Fix mode: the worklist

- [ ] One worklist file, in `03-rai/audits/` while the audit is open. Each line is a checkbox: the id, what it is, the action, risk and effort, and the skeptic's verdict.
- [ ] A repo audit keeps its worklist in the repo. With `.project.toml`, each finding goes to its backlog through `mise run backlog`.
- [ ] Group the findings into waves. The evidence for each finding goes in a JSON file beside the worklist.
- [ ] Plan edits per file, not per finding, so each file is opened once.
- [ ] Split dead weight from what needs his judgment, so he can rule a whole tier at once.
- [ ] Drop anything on the declined record.

### 7. Decide, one item at a time

- [ ] One session with him, one wave at a time. Show the exact actions, the risks and the decisions inside the wave.
- [ ] Explain each item he may not know in two lines, what it is and why, before asking.
- [ ] Each decision gets 2 or 3 numbered options, the Recommended one first with a one-clause reason.
- [ ] Then stop and wait, even when the item is already agreed. Present the route, never run it.
- [ ] He answers by number, or with "do whats recommended" for a whole wave. Take the answer as written.
- [ ] Nothing is installed, removed or changed without his go on that item.
- [ ] Record each ruling on its worklist line. A decline becomes a "considered, declined" line, so it is never re-pitched.

> **Decision Point**: he waves an item off.
> - He says close it anyway: close it without action, and say so on its line. That is a valid close.
> - He says later: the item stays open with his words on it. Never let it drop.

### 8. Guard every delete

- [ ] Records are never deleted: session JSONs, PRDs, logs, `.agent/` records and the archive exceptions.
- [ ] A tracked file leaves with `git rm` and moves with `git mv`, never through the Obsidian UI. Git history keeps it.
- [ ] Before a delete in the vault, confirm Obsidian Sync is paired, so the delete propagates instead of coming back.
- [ ] A folder with its own `.gitignore`: run `git ls-files '<dir>/**/.gitignore'` first. Move its secret patterns into the root `.gitignore` in the same commit.
- [ ] After big deletes, check what the replica still holds before the maintenance timer restarts.
- [ ] Outside git, on Drive or a disk, stage candidates in a `safe_to_delete` folder with a note on each. Delete when he approves.
- [ ] A machine audit declares every add and remove in dev-env and queues its mirror in the same turn. [[16-machines]] steps 6 and 7 hold the procedure.
- [ ] A rename sweep updates live references and leaves dated records as written.

### 9. Execute through briefed workers

- [ ] Write one brief per wave in the run dir, `briefs/<wave>.md`. It names the executor role, the exact steps, the never-touch list and the report path.
- [ ] Every brief carries the STOP rule, an inbox file for blocking questions, and the done marker as the last action. Never push, no AI attribution, explicit pathspecs.
- [ ] The STOP rule: a check that does not match skips that step and what depends on it. The question goes to the inbox, and the worker goes on.
- [ ] A denied command is never worked around. The worker reverts that partial edit and records the command and the reason.
- [ ] The `general-purpose` agent runs each brief in the background: inputs the brief and its common rules file. It edits and commits inside its scope, and returns a report and a done marker.
- [ ] At most two lanes at once, with disjoint folder scopes. One runs in the main checkout and owns the maintenance timer. The other runs in a git worktree outside the vault, on its own branch.
- [ ] Never two executors committing in one working tree.
- [ ] A worker in the vault stops `rai-maintenance.timer` first and waits until the service's `ActiveState` is no longer `activating`. It restarts the timer at the end, even on failure.
- [ ] In a code repo, fixes run through the repo's own flow: 21's lanes with `.project.toml`, 02 elsewhere. Parallel fixes there may run under `/orchestrator`, which needs his explicit permission rule. Never in the vault.
- [ ] A step the classifier denies becomes a script he runs. Each edit in it asserts what it expects, nothing is written when an assert fails, and a re-run is safe.
- [ ] Rai never runs that script, not even to test a guard. Check a guard with `test -e` or `bash -n`. The reviewing session never does a worker's denied step either.
- [ ] A leak found mid-run, such as secrets in a commit, is an incident: hand it to [[25-incident]] step 5.

> **Decision Point**: he asks why it is slow.
> - Run two lanes with disjoint scopes, and never more. Four sessions on one audit file was too much for him.

### 10. Review each hand-back

- [ ] Check that the maintenance timer runs again. A dead worker leaves it stopped.
- [ ] Review the worker's commits with Rai's own evidence: `git log`, `git show`, a grep for each claim, and the inbox.
- [ ] Fix small review items and commit them. Tick the worklist boxes.
- [ ] Merge a worktree lane after review, with the maintenance timer stopped. Rebase it on `main`, fast-forward, then remove the worktree and its branch.
- [ ] Present the next wave while the next worker runs, so the session stays free to talk with him.
- [ ] Progress, when he asks: a table of waves, or the share of boxes ticked as a percentage.

### 11. Close

- [ ] Fix mode: every box is ticked or closed without action.
- [ ] Move the worklist and its evidence file to `13-archive/audits/`.
- [ ] Move his rulings into the workflow for that kind of work. A ruling with no workflow becomes a memory ruling.
- [ ] Skills, agents, hooks or memory changed: run [[17-brain-healthcheck]] step 3.
- [ ] Name the loose ends outside the list in the closing message, such as a backup to delete after a few clean days.
- [ ] Report mode: file the report where step 5 says, and record the fix order he agreed.

### 12. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.
- [ ] Code repos commit through their own flow: 21's gates with `.project.toml`, `/git → commit` elsewhere.

---

## Connections

- Skills: `/grill` (the frame), `/rai → sanity` (Rai's ground truth), `/architecture → solution-architect`, `/architecture → data-architect` and `/devops → docker` (the architecture lens), `/security → security-review` (the threat lens), `/orchestrator` (parallel fixes in a code repo), `/git → commit`.
- Agents: the `reviewer` agent (lanes, skeptics, the critic), the `researcher` agent (outside facts), the `general-purpose` agent (background executors).
- Workflows: [[28-data-platform]] calls report mode and supplies its rubric. [[16-machines]] mirrors a machine change. [[25-incident]] takes a leak found mid-run. [[21-project-init]] and [[02-task]] carry repo fixes. [[17-brain-healthcheck]] is the aftercare.
