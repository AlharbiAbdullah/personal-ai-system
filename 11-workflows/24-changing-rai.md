# Changing Rai

**Use when:** building or changing a part of Rai: a skill, a hook, an agent, a memory path, a scheduled job or a harness edge. Also turning recurring work into a skill, and removing a dead part completely.
**Not for:** a sanity alarm, which is 17 brain healthcheck. Something broken right now, which is 25 incident. A findings list over Rai, which is 23 audit, though each fix it makes follows the build rules here.
**Done when:** the change is proven in a sandbox and then live, its docs pass Vale, and his steps went to him as exact lines. It is committed. After a structural change, 17 step 3 passed too.

Rai is the system he works in all day. A change to it is designed with him, built to his rules and proven before it goes live. A big change is built outside the live vault.

```d2
direction: down

size: "1. Size it" {shape: diamond}
limits: "2. Check the constraints\nthe declined record"
research: "3. How others do it"
design: "4. Design with him\n/grill, his approval" {shape: hexagon}
build: "5. Build to his rules"
big: "6. Big change:\na worktree outside the vault"
prove: "7. Prove it\nsandbox, then live"
docs: "8. Docs\nVale, MANIFEST"
his: "9. His steps\nas exact lines" {shape: hexagon}
land: "10. Land it on his go"
after: "11. Aftercare\n17, then 22"

size -> limits
limits -> research: "big"
research -> design -> build
limits -> build: "one fix" {style.stroke-dash: 3}
build -> big: "big"
big -> prove
build -> prove: "one fix" {style.stroke-dash: 3}
prove -> docs -> his -> land -> after
```

---

## Steps

### 1. Size it

> **Decision Point**: how big is the change?
> - Big: a new skill, a rework, a new job or pipeline stage, or a change to the memory design. Run every step.
> - One fix in one file: skip steps 3, 4 and 6. Every build rule and the proof still apply.

- [ ] Work he does by hand again and again becomes a skill he can trigger.
- [ ] A dead part is removed completely, with every live reference to it.

### 2. Check the constraints

- [ ] Read the declined record, and never re-pitch a cut he declined. The skill and agent cut list stays declined.
- [ ] `11-workflows/` is never deleted, and a workflow is never slimmed to its skill order.
- [ ] Low usage is never a reason to remove a skill or an agent.
- [ ] Never restrict Claude's permissions as a fix.
- [ ] Never gitignore information. The root `.gitignore` allows only the five categories in its header.
- [ ] Never add pruning or log rotation to a vault job. Records are kept.
- [ ] Never rewrite helm history.

### 3. Research how others do it

- [ ] Before building a new capability, research how others do it: the tools, first-hand accounts from practitioners, and the failure modes they report.
- [ ] The `researcher` agent takes the outside survey: inputs the question and the constraints. It returns cited options with trade-offs and failure modes, and writes nothing. Rai re-checks every load-bearing claim.
- [ ] Mine his own past sessions with `/recall` for how the work ran before.
- [ ] When he names the proven pattern, it wins over Rai's own design.

### 4. Design with him

- [ ] Reworking a skill: first run the current one on a throwaway target, phase by phase, and list its defects.
- [ ] `/grill` the design in helm. He answers each round by number, or with "do whats recommended".
- [ ] Put a plan with 2 or 3 options, one Recommended, in front of him. The build starts on his approval.
- [ ] Build it complete, not minimal.
- [ ] After his approval, build to the end without new check-ins. The steps in step 9 stay his.

### 5. Build to his rules

- [ ] An advisory hook's command in `settings.json` ends in `|| true`. A deliberate blocker keeps its non-zero exit.
- [ ] A per-prompt hook never touches the network. Probe an offline fallback with a throwaway command, never with `A || B` on the real script.
- [ ] Paths are portable: `$HOME/helm/...` in hook commands, `Path.home()` in Python. Machine values go in `~/.claude/settings.local.json`.
- [ ] Python scripts carry the PEP 723 uv shebang and `chmod +x`. Never system python.
- [ ] A secret lives in your secret manager and is read at runtime (for 1Password, `op read`). Never a key in a tracked file or a unit file.
- [ ] A scheduled `claude -p` prompt never backgrounds work and ends its turn. It polls in the same turn.
- [ ] Jobs heal themselves. Never add a "needs a human" exit for a recoverable state, and keep the coordinator's three self-heal layers.
- [ ] A new capture path runs the session gate's first rule, so headless runs never reach memory.
- [ ] A note it writes has no `: * ? " < > |` in its file name, since Obsidian Sync rejects them. Its diagrams are D2 fences.
- [ ] The vault stays canonical, and each harness is a deletable edge. If you run a second harness, mirror every hook change into its bridge.
- [ ] Both machines get the change. Vault changes reach the replica through the coordinator: never hand-copy a file that rides the maintenance pipeline.
- [ ] A rename sweep updates live references and leaves dated records as written.
- [ ] A skill's last step names the workflow that carries the work on.

### 6. Build a big change outside the live vault

- [ ] Build in a git worktree outside the vault, on its own branch. Never edit live skills mid-build: sessions in between would break, and the coordinator can wipe uncommitted edits.
- [ ] Build scratch goes on disk under `~/.cache/<build>/`, never under /tmp.
- [ ] A build in parts runs as briefed background workers, in the loop of [[23-audit]] step 9.
- [ ] The `engineer` agent builds each part test-first: inputs its brief and the approved design. It commits on the branch and returns a report.
- [ ] Rai re-checks each worker's claims read-only against the real repos before accepting the part.

### 7. Prove it

- [ ] Prove the change in a sandbox or a scratch repo first, then live.
- [ ] Code gets its tests first. A new sanity check ships with the fault test that proves it fires.
- [ ] A script that writes into the home folder runs against a throwaway HOME first.
- [ ] A scheduled job: finish the edit before its next fire. Check syntax with `bash -n`, `py_compile` or a YAML parse, and never fire its collectors by hand.
- [ ] A change to the coordinator or the memory pipeline lands between coordinator runs, at 04, 10, 16 and 22 local. Stop `rai-maintenance.timer` while editing, and restart it after.
- [ ] The `qa-tester` agent runs the proof: inputs the change, the sandbox path and the cases. It returns one PASS or FAIL row per case with evidence, and writes nothing. Rai re-checks each FAIL, and every PASS the landing rests on.
- [ ] A skill's text has no code to test. Prove it with a dry run on a throwaway target, phase by phase, the way project-init v2 was walked on tipcalc.

### 8. Docs

- [ ] Every doc it touches passes Vale: `vale --filter='.Name matches "^Rai"' <file>` reports no alert.
- [ ] A skill: `/rai → create-skill` validates the name, the frontmatter with its USE WHEN line, the router table and the MANIFEST row.
- [ ] Update the counts: `03-rai/skills/MANIFEST.md` for a skill, `03-rai/agents/MANIFEST.md` for an agent.
- [ ] Docs state today only, with no changelog narration.

### 9. His steps stay his

- [ ] An edit to `03-rai/config/settings.json`, its hooks or its permissions, goes to him as the exact line or as a script. The classifier denies it to Rai as self-modification.
- [ ] The script asserts what it expects before each edit, writes nothing when an assert fails, and is safe to re-run.
- [ ] Rai never runs it, not even to test a guard. Check a guard with `test -e` or `bash -n`.
- [ ] Sudo steps, pushes and publication are his too.

### 10. Land it

- [ ] Before the merge, the `reviewer` agent reads the branch diff against the step 5 rules. It returns one row per rule broken, with the line, and writes nothing. Rai re-checks each row.
- [ ] A worktree build merges into helm `main` only when he says. The merge is what makes it live.
- [ ] Rai rebases the branch on `main` and fast-forwards it after review, with the maintenance timer stopped.
- [ ] Deleting a folder: run `git ls-files '<dir>/**/.gitignore'` first, and move its secret patterns into the root `.gitignore` in the same commit.

### 11. Aftercare

- [ ] A structural change adds, removes or renames a skill, an agent, a hook, a memory path or a job. After one, run [[17-brain-healthcheck]] step 3.

### 12. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Skills: `/grill` (the design), `/recall` (his past sessions), `/rai → create-skill` (validate a skill), `/rai → sanity` (the aftercare, through 17), `/git → commit`.
- Agents: the `researcher` agent (the outside survey), the `engineer` agent (test-first build workers), the `qa-tester` agent (the proof), the `reviewer` agent (the rule check before the merge).
- Workflows: [[23-audit]] step 9 runs the worker loop. [[17-brain-healthcheck]] is the aftercare. [[25-incident]] sends a fix here when the fix changes Rai.
