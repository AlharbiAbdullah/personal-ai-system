---
name: ci-cd
description: >
  CI/CD pipelines: GitHub Actions, GitLab CI, CircleCI patterns. USE WHEN
  the user wires build/test/deploy pipelines, adds a workflow, or debugs
  failing CI.
---

# CI/CD

Build → test → deploy, automated on every change.

## When to use

- Any codebase shipped more than once
- Anything that enters production
- PR gate for quality (tests, lints, security scans)

## When NOT to use

- Pure personal prototypes that never ship — run tests locally
- Scripts that only run manually — just run them

## Design principles

- **Every commit runs**: lint + test + build
- **Every PR runs**: same, plus stricter checks
- **Every main-branch merge runs**: same, plus deploy to staging
- **Every tag runs**: deploy to prod (with manual approval for risky envs)
- **Fast feedback**: CI under 10 minutes; split into parallel jobs
- **Cached dependencies**: don't reinstall node_modules every run
- **Matrix builds** for cross-platform or cross-version verification
- **Secrets**: from the CI provider's secret store, never in code

## GitHub Actions skeleton

`.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install ruff
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python: ['3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
          cache: 'pip'
      - run: pip install -e '.[test]'
      - run: pytest -xvs
```

Deploy workflow (separate file):

```yaml
name: Deploy

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production  # enables approval gate
    permissions:
      id-token: write  # for OIDC to cloud
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123:role/deploy
          aws-region: us-east-1
      - run: ./scripts/deploy.sh
```

## GitLab CI skeleton

`.gitlab-ci.yml`:

```yaml
stages:
  - lint
  - test
  - build
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  paths:
    - .cache/pip

lint:
  stage: lint
  image: python:3.12
  script:
    - pip install ruff
    - ruff check .

test:
  stage: test
  image: python:3.12
  script:
    - pip install -e '.[test]'
    - pytest -xvs

deploy_prod:
  stage: deploy
  only:
    - main
  when: manual
  script:
    - ./scripts/deploy.sh
```

## Patterns

### Caching
- Cache dependency dirs: pip, poetry, npm, cargo, go modules
- Cache key: lockfile hash (`pyproject.toml`, `package-lock.json`)
- Bust cache when lockfile changes

### Matrix builds
- Cross-version (Python 3.11, 3.12, 3.13)
- Cross-OS (ubuntu, macos, windows)
- Cross-backend (Postgres, SQLite)

### Environment protection
- GitHub: `environment: production` blocks until approved
- GitLab: `when: manual`
- Required reviewers, wait timers, deployment windows

### Secrets
- Store in provider: GitHub Secrets, GitLab CI/CD Variables
- OIDC to cloud providers (no static keys)
- Never print to logs (`::add-mask::` in GitHub)

### Artifacts
- Build once, deploy multiple times
- Store binaries/images/packages between jobs
- Don't rebuild on each deploy target

### Canary + blue-green
- Deploy to staging → smoke test → deploy to prod
- Prod deploy with traffic split (canary 5% → 50% → 100%)
- Auto-rollback on error-rate spike

## Debugging failing CI

1. **Read the actual error** — first failing step, first error line
2. **Reproduce locally** — run the same command the CI runs
3. **Check the environment** — env vars, OS, runtime version mismatch
4. **Add debug output** — print working dir, env, versions
5. **Re-run with SSH** (GitHub Actions: `ssh-debug` action; CircleCI: `Rerun with SSH`)
6. **Compare to a known-good run** — what changed?

## Anti-patterns

- Flaky tests in the blocking path — fix or quarantine
- Secrets in code or `.env` files committed
- Long-running CI (30+ min) — split, parallelize, cache
- Deploy-on-push to prod without gates
- No rollback plan
- Ignoring CI failures — "just re-run"

## Examples

- "Write a GitHub Actions workflow for a Python+FastAPI project"
- "GitLab CI to build Docker + deploy to k8s"
- "Why is my CI failing only on Windows?"
- "Set up a canary deploy for the Taskflow API"
