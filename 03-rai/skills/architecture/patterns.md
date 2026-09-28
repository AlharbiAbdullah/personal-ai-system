---
name: patterns
description: >
  Reference library of architectural patterns. USE WHEN the user wants to
  pick a pattern (microservices, event-driven, CQRS, saga, hexagonal, etc.)
  or needs a quick summary of a named pattern.
---

# Architectural Patterns

A reference catalog. Describe each pattern: what it is, when it fits, when
it doesn't, and common pitfalls.

## When to use

- Deciding which pattern to apply to a specific design
- Looking up a named pattern the team mentioned
- Teaching / onboarding someone to the language of architecture

## When NOT to use

- Designing one specific system → `/architecture/system-design`
- Capturing a decision already made → `/architecture/adr-writer`
- Learning a deep tech (e.g. Kafka internals) → `/research/literature` or vendor docs

## Service boundary patterns

### Monolith
- **What**: single deployable, shared process, shared DB
- **When**: small team, unclear boundaries, early-stage product
- **Not when**: multiple teams stepping on each other, or scale demands differ per feature
- **Pitfall**: "we'll split it later" that never happens

### Modular monolith
- **What**: monolith with enforced internal module boundaries (package structure, dependency rules)
- **When**: want monolith's operational simplicity + future extractability
- **Not when**: boundaries are actually already distinct and independent
- **Pitfall**: modules cheating past boundaries — needs tooling enforcement

### Microservices
- **What**: independent deployables per bounded context, each with its own data store
- **When**: teams truly independent, scale profiles differ, org boundaries align
- **Not when**: small team, unclear boundaries, low op maturity
- **Pitfall**: distributed monolith — microservices coupled via shared DB or synchronous chains

### Serverless / FaaS
- **What**: functions triggered by events, no persistent server
- **When**: spiky or event-driven workloads, minimal ops preferred
- **Not when**: long-running jobs, heavy state, sub-100ms latency critical
- **Pitfall**: cold starts, vendor lock-in, cost at scale

## Communication patterns

### Synchronous request/response
- HTTP/REST, gRPC
- Simplest; coupling is tight
- Good for: end-user-facing APIs, where answers must be immediate

### Asynchronous messaging
- Queues (SQS, RabbitMQ), event bus (Kafka, Kinesis, NATS)
- Producer + consumer decoupled in time
- Good for: background work, fan-out, resilience to consumer downtime

### Event-driven
- Services emit events when state changes; others react
- Good for: loose coupling, audit log, reactive UIs
- Pitfall: no central flow — harder to trace end-to-end

### Publish/subscribe
- One emitter, many subscribers
- Good for: notifications, cache invalidation, multi-consumer fan-out
- Pitfall: consumer version skew; event schema evolution

## Data patterns

### CQRS (Command Query Responsibility Segregation)
- **What**: write model distinct from read model; eventual consistency
- **When**: reads and writes have very different shapes/scales
- **Not when**: simple CRUD
- **Pitfall**: complexity cost rarely justified for normal apps

### Event Sourcing
- **What**: state derived from event log; events are source of truth
- **When**: audit trail mandatory, need time-travel, complex state transitions
- **Not when**: simple CRUD, schema will change often
- **Pitfall**: event schema evolution; snapshotting performance

### Saga (distributed transaction)
- **What**: long-running transaction across services via events or orchestrator
- **When**: transaction spans service boundaries
- **Not when**: one service + one DB (use a DB transaction)
- **Pitfall**: compensation logic is easy to get wrong

### Outbox pattern
- **What**: write domain change + outgoing event in one DB transaction; separate publisher reads the outbox
- **When**: need atomic "write + publish" without 2PC
- **Pitfall**: poll interval + idempotent consumers required

### CDC (Change Data Capture)
- **What**: replicate DB changes as events (Debezium, Fivetran)
- **When**: data warehousing, feeding stream processors from OLTP
- **Pitfall**: schema drift, reprocessing cost on schema change

## Code-level patterns

### Hexagonal / Ports + Adapters
- **What**: core business logic surrounded by adapters for external concerns (DB, HTTP, message bus)
- **When**: you want the core testable + tech-stack-agnostic
- **Pitfall**: over-abstraction for small apps

### Clean Architecture
- **What**: Uncle Bob's concentric rings: entities, use cases, interfaces, frameworks
- **When**: complex domain logic worth isolating
- **Pitfall**: ceremonies for simple CRUD

### Layered / N-tier
- **What**: presentation → business logic → data access
- **When**: default for most line-of-business apps
- **Pitfall**: anemic domain model — layers become pass-throughs

## Resilience patterns

### Circuit breaker
- **What**: after N failures to a dependency, stop trying for a cooldown
- **When**: dependency failures cascade
- **Implementation**: Hystrix (legacy), resilience4j, custom

### Retry with exponential backoff + jitter
- **What**: retry failed requests, spacing out exponentially + with random jitter
- **When**: transient failures expected
- **Pitfall**: retry storms on cascading failure

### Bulkhead
- **What**: isolate resources (thread pools, connection pools) per dependency
- **When**: one slow dependency can exhaust all threads
- **Pitfall**: tuning pool sizes

### Timeout + deadline propagation
- **What**: every remote call has a timeout; deadlines propagate down the call tree
- **When**: always
- **Pitfall**: timeouts set too high; not propagating them through

## Examples

- "What's the CQRS pattern and when should I use it?"
- "Pick a resilience pattern for the Helios-to-Dremio connection"
- "Explain saga vs 2PC for cross-service transactions"
- "Is hexagonal architecture worth it for OpenKit?"
