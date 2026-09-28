---
name: dependency-audit
description: >
  Scan project dependencies for outdated versions, CVEs, license conflicts,
  and bloat. USE WHEN the user inherits a codebase, before a major release,
  or on a quarterly maintenance cadence.
---

# Dependency Audit

Know what you ship. Most production bugs and security issues come through
dependencies, not your code.

## When to use

- Inheriting an unfamiliar codebase
- Before a major release
- Quarterly health check
- After a security advisory hits your stack
- Before open-sourcing a private project

## When NOT to use

- Daily dev work — noise
- CI gating (unless you have time to react; else it's just red builds)

## Dimensions to audit

### 1. Outdated versions
- How many majors behind?
- How many minors behind?
- What's the gap on critical deps (framework, runtime, DB driver)?

### 2. Security vulnerabilities
- Known CVEs in current versions
- Severity (critical / high / medium / low)
- Exploitability in our context (transitive dep used by a utility vs core path)

### 3. License compliance
- Are all licenses compatible with our distribution model?
- GPL in a commercial SaaS? Problem.
- Unlicensed packages? Problem.

### 4. Maintenance signal
- Last commit date on the dep's repo
- Open issue count, unanswered PRs
- Sole maintainer vs team
- Active? Abandoned? Contested?

### 5. Bloat
- Which deps are actually used vs installed?
- Any deps duplicating each other's functionality?
- Transitive dep count — why do we have 800 packages for a 10k-line app?

## Process

### 1. Get the inventory
```bash
# Node
npm ls --all --json > deps.json
pnpm licenses list

# Python
pip list --format=json
pipdeptree

# Rust
cargo tree
cargo audit

# Go
go list -m all
```

### 2. Scan for vulnerabilities
```bash
# Node
npm audit --production
pnpm audit

# Python
pip-audit
safety check

# Rust
cargo audit

# Cross-language
trivy fs .
osv-scanner -r .
```

### 3. Check licenses
```bash
# Node
license-checker --summary

# Python
pip-licenses

# Rust
cargo deny check licenses
```

### 4. Find unused / stale deps
```bash
# Node
depcheck
# or
pnpm dlx depcheck

# Python
pip-check-unused  # or grep imports vs installed
pydeps --deps-only

# Rust
cargo machete
```

### 5. Produce the audit report
```
# Dependency Audit: [Project]
Date: YYYY-MM-DD

## Summary
- Total deps: [N direct, M transitive]
- Outdated: [X majors, Y minors behind]
- Vulnerabilities: [critical N, high M, medium K]
- License issues: [list]
- Unused: [list]
- Abandoned: [list]

## Critical (fix this week)
- [Dep] [version] — CVE-YYYY-NNNN (details)

## High (fix this sprint)
- ...

## Medium + Low (track, don't rush)
- ...

## Recommendations
- Upgrade [dep] to [version] — requires [effort] — see migration guide
- Remove unused [dep]
- Replace [abandoned dep] with [alternative]
```

## Upgrade strategy

Not every outdated dep needs immediate action. Prioritize:

1. **Critical CVEs in active paths** — this sprint
2. **High CVEs + framework updates with security fixes** — next sprint
3. **Outdated deps with growing debt** — plan migration (see `/architecture/migration-playbook`)
4. **Abandoned deps** — find alternatives, even if current version works
5. **Bloat** — remove if effort < future maintenance burden

## Anti-patterns

- Upgrading everything at once — can't bisect what broke
- Ignoring transitive deps — they're where supply-chain attacks hit
- License audits at ship-time — discover GPL in commercial product too late
- No audit cadence — debt compounds invisibly
- Accepting all auto-generated upgrades — some major bumps break silently
- Trusting the audit tool blindly — context matters (a CVE in a test-only dep is not the same as in prod)

## Tooling beyond audits

- **Dependabot / Renovate** — automated PRs for dep updates
- **Snyk / GitHub Advanced Security** — continuous vulnerability monitoring
- **SBOM** — software bill of materials; generate with syft or similar
- **SLSA** — supply chain integrity levels

## Examples

- "Audit dependencies on the Matchbox repo"
- "What CVEs exist in our Python deps?"
- "Which packages can we delete?"
- "Upgrade plan for the OpenKit Node stack"
