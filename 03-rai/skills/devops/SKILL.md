---
name: devops
description: >
  DevOps router. USE WHEN the user needs infrastructure, containerization,
  orchestration, deployment pipelines, or observability work. Routes
  between docker, cloudflare, kubernetes, ci-cd, monitoring.
---

# DevOps

Infrastructure + deploy + observe. Pick the sub-skill by the layer.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Container patterns, Dockerfile, multi-arch builds, registry, secrets | docker | `docker.md` |
| Cloudflare Workers, Pages, KV, D1, Durable Objects, MCP | cloudflare | `cloudflare.md` |
| Kubernetes manifests, Helm charts, kubectl patterns | kubernetes | `kubernetes.md` |
| CI/CD pipelines (GitHub Actions, GitLab, CircleCI) | ci-cd | `ci-cd.md` |
| Observability (Grafana, Prometheus, OpenTelemetry, alerts) | monitoring | `monitoring.md` |

## How to use

1. Pick the sub-skill by infrastructure layer.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **docker vs kubernetes:** docker is image + single-container; kubernetes is orchestration across a cluster.
- **cloudflare vs kubernetes:** cloudflare is serverless edge deploy; kubernetes is self-managed orchestration.
- **ci-cd vs cloudflare:** ci-cd is pipeline definition (build/test/deploy stages); cloudflare is the deploy target.
- **monitoring vs security/sec-updates:** monitoring is production observability (latency, errors); sec-updates is vulnerability intelligence.

## Cross-references

- Infrastructure-as-Code patterns → `/architecture/patterns`
- Container security + hardening → `/security/security-review`
