---
title: "taskflow — running notes"
type: project-notes
created: "2026-01-01"
updated: "2026-01-01"
---

# taskflow — Running Notes

> Example running-notes file. A project's working log: decisions-in-progress, dead ends, the
> "why did I do that" trail. Lighter than the [[05-projects/active/taskflow/PRD|PRD]]; it's a
> diary, not a spec.

## 2026-01-01 — billing spike

Wired Stripe Checkout in test mode. Webhook → mark subscription active. Two gotchas:

- Webhook signature check has to use the **raw** body, not the parsed JSON — lost an hour here.
- Idempotency: Stripe retries webhooks, so the handler must be safe to run twice. Keyed on the
  event id.

Decision: no self-serve plan changes for v1. Upgrade/downgrade = email me. Keeps the surface
tiny while I have 0 users; revisit at 10.

## 2026-01-01 — planning view feedback

Showed the prototype to a maker friend. Quote: "I don't want a backlog, I want *this week*."
That's the whole product. Cutting the backlog view from v1 — the weekly cut is the wedge.

This is exactly the kind of thing that becomes a blog post — feeds
[[09-ideas/learn-in-public-newsletter|the newsletter idea]].

## Open threads
- [ ] Decide on retention metric (weekly active planners, not DAU).
- [ ] Support inbox: just a forwarding alias for now.
