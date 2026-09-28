---
type: learning-memory
created: 2026-01-01
topic: fastapi
tags: [python, fastapi, backend]
---

# FastAPI dependency injection clicked

> Example file memory. `03-rai/memory/learning/` holds durable things the assistant learned
> *about how you work and what you know*, so future sessions don't re-explain them. The
> batch distill (`/rai process-sessions`) writes these. Ships empty; this is a sample so you
> can see the format.

**What landed:** FastAPI's `Depends()` is just function composition — a dependency is a function
whose return value is injected into the handler, and FastAPI caches it per-request. Once I saw it
as "a function that runs before the handler and hands back a value", auth/db-session/config
patterns all collapsed into the same shape.

**Why it matters for John:** he reaches for FastAPI on backend work
([[02-ana/identity/tech-stack|tech-stack]]) and was over-using globals for the DB session. The
injected-session pattern is the idiomatic fix — prefer it in future FastAPI code.

**How to apply:** when reviewing or writing John's FastAPI code, use `Depends()` for shared
per-request resources (DB session, current user, settings) instead of module-level globals.

Related: [[06-learning/system-design/Lesson 001 - Scaling Fundamentals|statelessness]] — a
per-request injected session is also the stateless-friendly choice.
