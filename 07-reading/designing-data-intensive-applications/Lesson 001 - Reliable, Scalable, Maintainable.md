---
type: lesson
book: "Designing Data-Intensive Applications"
chapter: 1
lesson: 001
mode: mid
created: 2026-01-01
---

# Lesson 001 — Reliable, Scalable, Maintainable Applications

> Example reading lesson (Chapter type). The `/reading teach` skill teaches a chapter in full —
> the ideas, the named frameworks kept intact, with engagement before reveal — not a summary.
> Tracked in [[07-reading/designing-data-intensive-applications/progress|progress.md]].

## The chapter in one line
Every data system is judged on three properties — **reliability, scalability, maintainability** —
and the whole book is about the trade-offs you make to get them.

## Reliability
The system keeps working *correctly* even when things go wrong (faults). Key distinction:

- **Fault** = one component misbehaves. **Failure** = the whole system stops serving.
- The goal is to prevent faults from becoming failures.
- Faults come in three flavors: **hardware** (disks die), **software** (a bug cascades), **human**
  (the biggest source — misconfiguration).

> Kleppmann's frame, kept intact: *build systems that tolerate faults, and deliberately trigger
> them (chaos) so the tolerance is real, not theoretical.*

## Scalability
Not a yes/no property — a question: "**if load grows in a specific way, what are our options?**"

- Describe load with **load parameters** (requests/sec, read/write ratio, fan-out).
- Describe performance with **percentiles**, not averages. p99 latency is what your worst-served
  users actually feel — and they're often your most valuable.

## Drill — predict before you reveal
> Your API's *average* response time is 80ms and everyone's happy. Why might Kleppmann still say
> you have a latency problem?

<details><summary>Reveal</summary>

The average hides the tail. If p99 is 2 seconds, 1 in 100 requests is painfully slow — and a
single user page that makes 100 calls will *almost always* hit that slow path. Measure tail
percentiles (p95/p99), not the mean. This is the chapter's most practical, most-cited lesson.
</details>

## Maintainability
The majority of a system's cost is *after* it ships. Three design principles:

- **Operability** — make it easy to keep running (good telemetry, no surprises).
- **Simplicity** — manage complexity; remove accidental complexity (good abstractions).
- **Evolvability** — make it easy to change (the only constant is changing requirements).

## Connect it
- [[06-learning/system-design/Lesson 001 - Scaling Fundamentals|Scaling fundamentals]] — "describe
  load before you scale" is the same instinct.
- [[05-projects/active/taskflow/notes|taskflow]] — start logging p99, not just averages, before
  the first real users arrive.

## Takeaway (→ knowledge)
> "Measure performance with tail percentiles; the average lies." → atomic note candidate.

## Next
Chapter 2 — Data Models & Query Languages (relational vs document vs graph).
