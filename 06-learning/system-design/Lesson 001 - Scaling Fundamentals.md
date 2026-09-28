---
type: lesson
topic: system-design
lesson: 001
mode: mid
created: 2026-01-01
---

# Lesson 001 — Scaling Fundamentals

> Example lesson. The `/learning teach` skill generates these. It teaches by making you *engage*
> before it reveals — predict, explain back, decide — because passive reading decays. Answer the
> drills in your head (or out loud to the assistant) **before** you read the reveal. Tracked in
> [[06-learning/system-design/progress|progress.md]].

## The core idea
Scaling is about removing the thing that can't be duplicated. You scale **up** (a bigger machine)
or **out** (more machines). Out wins long-term, but only if the work is *stateless* — if any
request can hit any box. State is the enemy of horizontal scale.

## Build-up

1. **Vertical (up):** bigger CPU/RAM. Simple, no code change. Ceiling: one machine's max, and it's
   a single point of failure.
2. **Horizontal (out):** more machines behind a load balancer. No hard ceiling. Cost: your app
   must hold no per-request state in memory.
3. **Statelessness:** push session/state to a shared store (DB, cache). Now boxes are cattle, not
   pets — kill one, spin one up, nobody notices.

## Drill 1 — predict before you reveal
> taskflow keeps the logged-in user's session **in server memory**. You add a second server behind
> a round-robin load balancer. What breaks?

<details><summary>Reveal</summary>

Users get randomly logged out. Request 1 lands on server A (has their session); request 2 lands on
server B (doesn't). The fix: move sessions to a shared store (Postgres/Redis) so the servers are
stateless. **This is the exact decision taskflow faces before it can run more than one box.**
</details>

## Drill 2 — explain it back
> In one sentence, why does horizontal scaling *require* statelessness?

<details><summary>Reveal</summary>

Because horizontal scaling means any machine must be able to serve any request — and that's only
true if no machine holds state the others lack.
</details>

## Apply it
[[05-projects/active/taskflow/PRD|taskflow]] runs on one VM today. **Decision for the project:**
before adding a second server, move sessions out of memory. Cheap now, painful later.

## Takeaway (→ knowledge)
> "Scale out by making the unit of work stateless; state belongs in a shared store, not in the
> process." → candidate atomic note for `10-knowledge/`.

## Next
Lesson 002 — Caching. Where to put it, and why invalidation is one of the two hard problems.
