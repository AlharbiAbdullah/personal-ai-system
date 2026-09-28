---
name: system-design
description: >
  Design a specific system: API, service, microservice boundary, data flow.
  USE WHEN the user is scoping ONE concrete system — not cross-cutting
  patterns (use /architecture/patterns) or decisions (use /architecture/adr-writer).
---

# System Design

Design one concrete system from scratch (or redesign an existing one).

## When to use

- New service, API, or component getting designed before coding
- Redesign of an existing system that has scaled past its shape
- Interview-style system design question (practice)

## When NOT to use

- Capturing a decision post-design → `/architecture/adr-writer`
- Picking patterns abstractly → `/architecture/patterns`
- Data pipeline shape → `/architecture/data-architect`
- Full migration sequence → `/architecture/migration-playbook`

## Workflow

1. **Clarify requirements**
   - **Functional**: what must it do? (list concrete verbs)
   - **Non-functional**: scale, latency, availability, consistency, durability
   - **Constraints**: budget, team size, existing stack, compliance
   - **Assumptions**: explicit, written down, flagged for review

2. **Scope + scale estimates**
   - Users (DAU/MAU), requests per second, data volume
   - Read:write ratio
   - Growth trajectory (3-year horizon)

3. **API design**
   - Resources / endpoints / method verbs
   - Request + response schemas
   - Auth model
   - Versioning strategy
   - Rate limits

4. **Data model**
   - Entities + relationships
   - Storage choice per entity (relational, document, key-value, time-series, graph)
   - Sharding / partitioning strategy
   - Indexes + access patterns

5. **Components + flow**
   - Draw the boxes: web/api tier, app/service tier, cache, queue, DB, workers
   - Connect them with arrows labeled with protocols (HTTP, gRPC, async msg)
   - Highlight sync vs async paths

6. **Scaling plan**
   - Horizontal scale points + bottlenecks
   - Caching strategy (where, TTLs, invalidation)
   - Queue + worker for async work
   - Read replicas + write master strategy

7. **Failure modes**
   - What breaks at 10× load? 100×?
   - What happens on dependency failure?
   - Degradation strategy (graceful vs hard fail)
   - Monitoring + alerting

8. **Operational concerns**
   - Deployment strategy (blue-green, canary, rolling)
   - Observability (logs, metrics, traces)
   - Security (auth, PII handling, rate limit abuse)
   - Cost model

## Output

A system design doc. Usually ~2–5 pages with at least one architecture diagram.

```
# [System Name] Design
Author: [Name] | Date: YYYY-MM-DD | Status: Draft

## 1. Requirements
## 2. Scope + scale
## 3. API
## 4. Data model
## 5. Architecture diagram
[diagram — ASCII or image]
## 6. Key flows (request lifecycle)
## 7. Scaling strategy
## 8. Failure modes + mitigations
## 9. Observability
## 10. Security
## 11. Cost estimate
## 12. Open questions
```

## Common patterns (cross-reference)

- Stateless app tier + stateful storage tier
- CDN at edge, load balancer, autoscaling app instances
- Cache layer (Redis) for hot reads
- Queue (SQS/Kafka) for async work
- Database per service in microservices; shared DB anti-pattern
- Circuit breakers + retries with exponential backoff + jitter

See `/architecture/patterns` for the pattern library.

## Anti-patterns

- Starting with tech choices before understanding requirements
- Designing for hypothetical 100× scale when you have 10 users
- Ignoring the failure mode section — it's where production pain lives
- No diagram — words alone don't communicate architecture
- Skipping cost — infra surprises kill projects

## Examples

- "Design the Helios air-gapped chat service"
- "Redesign the Taskflow API for multi-tenant isolation"
- "System design for GeoContext unified API"
- "Sketch the OpenKit compliance report generator backend"
