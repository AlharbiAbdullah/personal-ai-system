# Shipping Workflow

**Use when:** releasing or deploying: shipping a change, cutting a release, publishing a package, deploying a service or the site, or updating a running box.
**Not for:** 29 air-gapped delivery, for a sealed or offline target. 21 project-init Phase E, for the version, changelog and tag in a repo with `.project.toml`; the build, deploy, verify and rollback steps here still apply. 25 incident, for one of his machines that broke.
**Done when:** deployed, post-deploy verification green, release tagged, rollback plan written.

From "works locally" to deployed and verified in production.

> **SDD repo** (`.project.toml` at the root): the version bump and CHANGELOG in step 1 and
> the tag in step 6 are one human gate, `! mise run release -- <bump>`. Never bump, tag or
> edit `CHANGELOG.md` by hand. Skip the `/git → commit` in step 6 too: only the human gates
> move `main`. The build, deploy, verify and rollback steps still apply. The release itself
> is Phase E of [[21-project-init]].

```
Record state → Checklist → Build → Containerize → Deploy → Verify → Tag → Rollback plan
```

---

## Steps

### 0. Record What Runs Now

- [ ] Before anything else, record what the target runs now: the version or commit, the environment switch, health and free disk.
- [ ] Stop on a mismatch with what you expected. Nothing changes until it is explained.

### 1. Pre-Ship Checklist

- [ ] All tests pass (`/testing → e2e` included)
- [ ] Code review complete ([[05-code-review]])
- [ ] README is current (setup, usage, architecture)
- [ ] Version bumped (semver: breaking.feature.fix)
- [ ] CHANGELOG updated if applicable (`/git → changelog`)
- [ ] No TODO/FIXME items left unaddressed for this release
- [ ] Environment variables documented

### 2. Clean Build

- [ ] Fresh install from scratch (delete node_modules, .venv, etc.)
- [ ] Build succeeds with zero warnings
- [ ] All tests pass on the clean build

> **Decision Point**: Build issues?
> - Fix them. Never ship a build that doesn't pass locally.

### 3. Containerize (if applicable)

- [ ] Dockerfile follows `/devops → docker` best practices
- [ ] Multi-stage build (build stage vs runtime stage)
- [ ] Image size is reasonable
- [ ] No secrets baked into the image
- [ ] Container runs and passes a smoke test locally

### 4. Deploy

- [ ] Choose deployment target:
  - `docker compose up`: single host
  - Kubernetes manifests: orchestrated (`/devops → kubernetes`)
  - Package publish: library/CLI
  - Cloud deploy: serverless/managed service
  - Cloudflare Workers: the site, `/devops → cloudflare`

> **Decision Point**: A sealed or offline target?
> - Yes → [[29-air-gapped-delivery]] takes the delivery: step 0 for a new target, then steps 1 to 6. Come back here at step 6.
> - No → continue

> **Decision Point**: First install, or an update in place?
> - First install → the from-scratch path
> - Update on a box that holds data → in place. Never run the from-scratch path there, and never `rsync --delete` onto it.

> **Decision Point**: Deployment strategy?
> - Low risk → rolling deploy
> - Medium risk → blue-green (run both, switch traffic)
> - High risk → canary (route small % first, monitor)
> - See `/devops → ci-cd` for pipeline patterns

- [ ] Recreate containers (`docker compose up -d`), never `restart`. A restart keeps the old container config and ships nothing new.
- [ ] An irreversible public step, such as a domain or a registry publish: prepare and verify it, then John decides and runs it.
- [ ] Hand the deploy run to the `sre` agent. Inputs: the target, the deploy commands and the step 0 record. Returns: each command with its output, then health and logs. It runs only those commands, never a step marked for John.
- [ ] Rai re-checks the health it reports before step 5.
- [ ] Deploy to staging first if available
- [ ] Verify on staging before promoting to production
- [ ] Deploy to production

### 5. Post-Deploy Verification

- [ ] Run `/testing → e2e` against the live environment
- [ ] Check logs for errors (first 10 minutes): `/devops → monitoring`
- [ ] Verify core user flows work end-to-end
- [ ] Monitor metrics/alerts if observability is set up
- [ ] Verify from where the consumer sits: a remote machine, never the server's own browser. Some bugs only show from a remote origin.
- [ ] Hand the core flows to the `qa-tester` agent. Inputs: the live address and the flows. Returns: PASS or FAIL per flow, with evidence. It cannot edit files.
- [ ] Rai re-runs any FAIL before acting on it.

> **Decision Point**: Something wrong in production?
> - Minor → hotfix using [[04-debugging]] + [[02-task]]
> - Major → execute the rollback plan (step 7)

### 6. Tag Release

- [ ] `/git → commit` (code repo). Commit before the tag: a commit made after the tag is not in the release.
- [ ] `git tag v[X.Y.Z]`
- [ ] `git push --tags`
- [ ] Update `05-projects/projects-moc.md` if this changes project status
- [ ] The tag, the release payload and the registry artifact carry the same code. A fix that lands after the tag ships as the next patch, never under the tagged version.
- [ ] Publish only from the hub, aligned with origin.
- [ ] A branch that deploys on push gets no push without his explicit "ship". The site's `main` is one.

### 7. Rollback Plan

Document this BEFORE deploying:

- [ ] How to revert: `git revert` or redeploy the previous tag
- [ ] Previous working version/tag: `v[___]`
- [ ] Database migration rollback needed? (if yes, document steps)
- [ ] Who to notify if a rollback happens
- [ ] Keep the plan in a dated runbook with two more lists: Do not (the commands that would break this box) and Known, deferred on purpose.
- [ ] Hand the draft to the `sre` agent. Inputs: the previous tag, the deploy commands and any data migration. Returns: rollback commands that are safe to re-run. It writes the plan only. When a rollback runs, it runs the plan and reports health after.
- [ ] Rai checks every command in the plan against the repo before the deploy.

### 8. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Containerization: `/devops → docker`
- Orchestration: `/devops → kubernetes`
- CI/CD pipelines: `/devops → ci-cd`
- Monitoring post-deploy: `/devops → monitoring`
- The site on Cloudflare Workers: `/devops → cloudflare`
- Pre-ship code review: [[05-code-review]]
- If something breaks: [[04-debugging]]
- A sealed or offline target: [[29-air-gapped-delivery]]
- The release gate in an SDD repo: [[21-project-init]] Phase E
- Agents: the `sre` agent (steps 4 and 7), the `qa-tester` agent (step 5)
