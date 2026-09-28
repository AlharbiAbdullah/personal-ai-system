---
type: idea
status: tree
domain: ai
derived_from: ["[[01-inbox/2026-01-01-agent-evaluation-article]]", "[[10-knowledge/ai/what-are-ai-agents]]"]
spawned: []
created: 2026-01-01
grown: 2026-01-01
ready: 2026-01-01
scheduled_start: 2026-02-01
tags: [idea, tree]
---

# Agent Eval Harness

> Example of a **Tree**-stage idea — crystallized, scoped, and ready to graduate into a project.
> One step from `05-projects/kitchen/`. Graduate it with `/ideas graduate`, which writes a PRD
> like [[05-projects/kitchen/open-kit/PRD|open-kit's]]. Compare the earlier
> [[09-ideas/local-first-task-sync|Plant]] stage to see how an idea sharpens.

## Spark
> A small, honest test harness that scores an AI agent on the long tail, not the demo.

## Problem & Solution
**Problem:** Agents look great in a demo and fall apart on edge cases (the thesis of the
[[01-inbox/2026-01-01-agent-evaluation-article|inbox article]]). There's no lightweight way to
measure that for the agents I'm sketching in [[10-knowledge/ai/what-are-ai-agents|my notes]].
**Solution:** A CLI + a folder of task cases (input → expected behavior → checks) that runs an
agent N times and reports reliability, cost, and failure modes.
**Target User:** Me first, then anyone building small agents who's tired of vibes-based eval.

## Requirements
- [ ] Define a case format: input, success checks, allowed tools, max steps.
- [ ] Run a case M times; report pass rate, mean cost, mean steps, failure buckets.
- [ ] Pluggable agent runner (so it's not tied to one framework).
- [ ] Output a readable report + a machine-readable JSON.

## Plan
1. **Phase 1:** case format + runner for one agent, pass-rate only.
2. **Phase 2:** cost/steps/failure-bucketing + the report.
3. **Phase 3:** ship as an `open-kit` template so a new agent project starts with eval wired in.

## First Steps
- [ ] Write 5 real task cases by hand (the article's point: the long tail is where it breaks).
- [ ] Stub the runner against a trivial agent.
- [ ] Decide the report format.

## Success Criteria
- I can answer "is this agent reliable enough to ship?" with a number, not a feeling.
- Catches a regression I'd otherwise have missed.

## Schedule
- **Start:** 2026-02-01 · **First milestone:** pass-rate report on 5 cases · **Review:** end of Feb.

## Risks
- Scope creep into "a benchmark framework". Mitigation: stay a *harness*, ruthlessly small.
- Eval cases that test the demo, not the tail. Mitigation: write the nasty cases first.

## Vault Connections
- [[01-inbox/2026-01-01-agent-evaluation-article|inbox: agent evaluation article]] — the trigger.
- [[10-knowledge/ai/what-are-ai-agents|What Are AI Agents]] — "verification" is the whole point.
- [[05-projects/kitchen/open-kit/PRD|open-kit]] — eventual distribution channel (a template).
