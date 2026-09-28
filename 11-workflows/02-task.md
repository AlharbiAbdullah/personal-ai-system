# Task Workflow

**Triggered by:** "do this task" / "implement {feature}" / "fix {bug}" (one unit of work)
**Cadence:** Per task.
**Done when:** in an SDD repo, the change passed `! mise run merge`. Elsewhere: behaviour verified, reviewed, merged, worktree removed.

One unit of work: a feature, a fix or a spike. The first question is what kind of repo it lives in.

---

## Step 0: which kind of repo?

```sh
test -f .project.toml && echo SDD || echo plain     # run at the repo root
```

> **Decision Point**:
> - **SDD** (`.project.toml` exists): the lane decides the steps, and the repo holds the rules. Follow [[21-project-init]] Phase C. The lanes are in the repo's `specs/README.md#lanes`, rendered from the process template `03-rai/skills/project-init/templates/specs-README.md`. Stop reading here.
> - **Plain, and a code project in `~/projects/` that will keep growing:** offer `/project-init` first ([[21-project-init]] Phase B). 1. Adopt it now (Recommended when more than one feature is coming). 2. Do this task plain.
> - **Plain, and it is the helm vault, a script or a one-off:** the steps below.

---

## Plain repo steps

### Setup

- [ ] Worktree: `git worktree add ../<repo>-<task> -b feat/<task>` (`fix/<task>` for a bug), then `cd` into it.
- [ ] In helm, skip Setup and Merge. Vault edits stay local for the coordinator.

### Define

- [ ] `/grill "<task>"`. It writes `.agent/decisions.md` and `.agent/plan.md`, or `decisions-<slug>.md` and `plan-<slug>.md` when another task's pair is already there.
  - A code repo that doesn't track `.agent/`: the pair is scratch, and `/grill` keeps it out of git.
  - Helm: `.agent/` files are tracked records. Never exclude, untrack or delete one. They stay local for the coordinator like every vault edit.
- [ ] Optional: `/spec-improve` over the plan file.
- [ ] **Goal** in one sentence, and **Done** as observable behaviour, never "code written".

> **Decision Point**: is the task clear enough to start?
> - Yes: build.
> - No: break it down further, or grill again.

### Build

- [ ] `/compile` carries out the plan file: a failing test first, minimal code, refactor on green. `/testing → tdd` points to the same TDD text.

> **Decision Point**: the task grows past its scope?
> - Capture the extras as separate tasks. Finish the current scope first.

### Verify

- [ ] All tests pass.
- [ ] `/testing → e2e` when integration points exist.
- [ ] `/security → security-review` when auth, input handling or data access changed.

### Review

- [ ] [[05-code-review]] checklist over the full diff against `main`.
- [ ] `/adversarial-review` for substantial work.
- [ ] `/git → refactor-clean`: dead code, unused imports.

### Merge

- [ ] `/git → commit`, then merge into `main` and run the tests there.
- [ ] `git worktree remove ../<repo>-<task>` and `git branch -d feat/<task>`.

---

## Connections

- SDD repos, from init to release: [[21-project-init]]
- Repo process template: `03-rai/skills/project-init/templates/specs-README.md`
- Code review gate: [[05-code-review]]
- Debugging: [[04-debugging]]
