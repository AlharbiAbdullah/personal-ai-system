# Shipping Workflow

**Triggered by:** "ship this" / "deploy {project}" / "cut a release"
**Cadence:** Per release
**Done when:** deployed, post-deploy verification green, release tagged, rollback plan written.

From "works locally" to deployed and verified in production.

> **SDD repo** (`.project.toml` at the root): the version bump and CHANGELOG in step 1 and
> the tag in step 6 are one human gate, `! mise run release -- <bump>`. Never bump, tag or
> edit `CHANGELOG.md` by hand. Skip the `/git → commit` in step 6 too: only the human gates
> move `main`. The build, deploy, verify and rollback steps still apply. The release itself
> is Phase E of [[21-project-init]].

```
Checklist → Build → Containerize → Deploy → Verify → Tag → Rollback plan
```

---

## Steps

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

> **Decision Point**: Deployment strategy?
> - Low risk → rolling deploy
> - Medium risk → blue-green (run both, switch traffic)
> - High risk → canary (route small % first, monitor)
> - See `/devops → ci-cd` for pipeline patterns

- [ ] Deploy to staging first if available
- [ ] Verify on staging before promoting to production
- [ ] Deploy to production

### 5. Post-Deploy Verification

- [ ] Run `/testing → e2e` against the live environment
- [ ] Check logs for errors (first 10 minutes): `/devops → monitoring`
- [ ] Verify core user flows work end-to-end
- [ ] Monitor metrics/alerts if observability is set up

> **Decision Point**: Something wrong in production?
> - Minor → hotfix using [[04-debugging]] + [[02-task]]
> - Major → execute the rollback plan (step 7)

### 6. Tag Release

- [ ] `git tag v[X.Y.Z]`
- [ ] `git push --tags`
- [ ] Update `05-projects/projects-moc.md` if this changes project status
- [ ] `/git → commit` (code repo)

### 7. Rollback Plan

Document this BEFORE deploying:

- [ ] How to revert: `git revert` or redeploy the previous tag
- [ ] Previous working version/tag: `v[___]`
- [ ] Database migration rollback needed? (if yes, document steps)
- [ ] Who to notify if a rollback happens

---

## Connections

- Containerization: `/devops → docker`
- Orchestration: `/devops → kubernetes`
- CI/CD pipelines: `/devops → ci-cd`
- Monitoring post-deploy: `/devops → monitoring`
- Pre-ship code review: [[05-code-review]]
- If something breaks: [[04-debugging]]
