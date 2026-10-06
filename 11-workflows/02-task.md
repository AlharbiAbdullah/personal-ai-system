# Task Workflow

**Use when:** one unit of work in a repo without `.project.toml`: a feature, a fix or a spike. That covers the helm vault, a script, a work repo, and any code repo not on the project-init standard. Today no repo has `.project.toml`, so most of his code work runs here.
**Not for:** 21 project-init, for a repo with `.project.toml`. 01 project, for a new product from an idea. 04 debugging, for finding the cause of a bug; the fix then runs here. 24 changing Rai, for a skill, hook, agent, memory path or scheduled job.
**Done when:** in an SDD repo, the change passed `! mise run merge`. Elsewhere: behaviour verified, reviewed, merged, worktree removed. In helm, the edits are committed under the vault commit rule.

One unit of work: a feature, a fix or a spike. The first question is what kind of repo it lives in.

> **A method workflow runs inside this one.** [[27-data-pipeline]] for a pipeline and [[31-ai-system-build]] for an AI feature supply the domain steps inside Define and Build. Each one says which of its steps feed the talk and which become the plan's groups.

---

## Steps

### 0. Which kind of repo?

```sh
test -f .project.toml && echo SDD || echo plain     # run at the repo root
```

> **Decision Point**:
> - **SDD** (`.project.toml` exists): the lane decides the steps, and the repo holds the rules. Follow [[21-project-init]] Phase C. The lanes are in the repo's `specs/README.md#lanes`, rendered from the process template `03-rai/skills/project-init/templates/specs-README.md`. Stop reading here.
> - **Plain, and a code project in `~/projects/` that will keep growing:** offer `/project-init` first ([[21-project-init]] Phase B). 1. Adopt it now (Recommended when more than one feature is coming). 2. Do this task plain.
> - **Plain, and it is the helm vault, a script or a one-off:** the steps below.

### 1. Setup

- [ ] Worktree: `git worktree add ../<repo>-<task> -b feat/<task>` (`fix/<task>` for a bug), then `cd` into it.
- [ ] In helm, skip Setup and Merge. Its edits follow step 7.

### 2. Define

- [ ] `/grill "<task>"`. It writes `.agent/decisions.md` and `.agent/plan.md`, or `decisions-<slug>.md` and `plan-<slug>.md` when another task's pair is already there.
  - A code repo that doesn't track `.agent/`: the pair is scratch, and `/grill` keeps it out of git.
  - Helm: `.agent/` files are tracked records. Never exclude, untrack or delete one. They follow the vault commit rule like every vault edit.
- [ ] Optional: `/spec-improve` over the plan file.
- [ ] **Goal** in one sentence, and **Done** as observable behaviour, never "code written".

> **Decision Point**: is the task clear enough to start?
> - Yes: build.
> - No: break it down further, or grill again.

### 3. Build

- [ ] `/compile` carries out the plan file: a failing test first, minimal code, refactor on green. `/testing → tdd` points to the same TDD text.

> **Decision Point**: the task grows past its scope?
> - Capture the extras as separate tasks. Finish the current scope first.

### 4. Verify

- [ ] All tests pass.
- [ ] `/testing → e2e` when integration points exist.
- [ ] `/security → security-review` when auth, input handling or data access changed.

### 5. Review

- [ ] [[05-code-review]] checklist over the full diff against `main`.
- [ ] `/fusion → review` for substantial work.
- [ ] `/git → refactor-clean`: dead code, unused imports. Its checkpoint stages explicit paths, never `git add -A`.

### 6. Merge

- [ ] `/git → commit`, then merge into `main` and run the tests there.
- [ ] `git worktree remove ../<repo>-<task>` and `git branch -d feat/<task>`.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- SDD repos, from init to release: [[21-project-init]]
- Repo process template: `03-rai/skills/project-init/templates/specs-README.md`
- Domain methods inside Define and Build: [[27-data-pipeline]], [[31-ai-system-build]]
- Code review gate: [[05-code-review]]
- Debugging: [[04-debugging]]
- A change to Rai itself: [[24-changing-rai]]
