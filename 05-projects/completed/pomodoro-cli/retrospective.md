---
type: project-retrospective
status: completed
started: 2025-11-01
ended: 2025-12-15
company: personal
role: solo maker
team_size: 1
domain: devops
tech: [go, cobra, systemd]
impact_level: low
growth_areas: [shipping-small, go-cli-distribution]
---

# pomodoro-cli

> Example of a **completed** project retrospective. When a project ends, it moves to
> `completed/` with this write-up (and any diagrams). The point isn't to brag — it's to mine
> the lessons so the next project is better. Created from the Project Retrospective template.

## Simplicity Theorem

> A terminal timer that nudges you to take breaks, with zero config and no app to open.

A tiny Go CLI that runs 25/5 focus cycles, prints a calm status line, and fires a desktop
notification. Shipped in six weeks of evenings. Small on purpose — it was the warm-up that
taught me Go CLI distribution before [[05-projects/kitchen/open-kit/PRD|open-kit]].

## Simplicity Diagram

```
pomo start ─▶ [25m focus] ─▶ 🔔 break ─▶ [5m] ─▶ repeat ×4 ─▶ long break
                  │
                  └─ status line: ◍ 12:30 left  ·  cycle 2/4
```

---

## The Story

- **Why it existed:** I kept losing afternoons to deep-but-unbroken sessions and burning out by 4pm.
- **How I got involved:** Built it for myself in week one of wanting to learn Go properly.
- **What I owned:** All of it — solo.

## The Work

**Problem:** Existing timers were either phone apps (context switch) or heavyweight desktop apps.
I wanted something that lived in the terminal I already stare at.

**Solution:** A single binary. `pomo start`, `pomo status`, a systemd user timer for the daemon.

### Technical Architecture

| Layer | Technology | My Involvement |
|-------|------------|----------------|
| CLI | Go + Cobra | built |
| Daemon | systemd user service | built |
| Notify | `notify-send` / `osascript` | built |

### Key Technical Decisions

1. **Single binary, no config file** → Why: a timer shouldn't need setup → Outcome: install-and-go,
   which became a principle I carried into open-kit.
2. **systemd user timer over a long-running process** → Why: let the OS own the lifecycle →
   Outcome: survives reboots, zero babysitting.

### Challenges

| Challenge | How I Solved It | What I Learned |
|-----------|------------------|----------------|
| Cross-platform notifications | Shelled out per-OS | Don't abstract early; two `if`s beat a plugin system |
| Distributing the binary | GitHub Releases + `go install` | This is the exact problem open-kit now automates |

---

## The Impact

- **Personal:** Actually take breaks now. Afternoons survive.
- **Portfolio:** 40-ish GitHub stars, a couple of strangers opened issues — first taste of OSS upkeep.

## The Growth

### Skills Gained
- Go CLI structure + distribution: zero → comfortable.
- systemd user units: never → can write one from memory.

### Mindset Shifts
- **Ship small to learn fast.** Six weeks, one tiny thing, three transferable lessons. That trade
  is almost always worth it.

### If I Did It Again
- **Keep:** the no-config rule.
- **Change:** would've written the README *first* — I bolted it on at the end.
- **Avoid:** the half-day I spent on a notification abstraction I deleted.

---

## Connections

- [[05-projects/kitchen/open-kit/architecture|open-kit architecture]] — directly inherited the
  single-binary + distribution lessons.
- **Pattern I notice:** my best learning comes from a tiny shipped thing, not a big planned one.
  Ties to [[02-ana/identity/goals|Goals]] — "go deep, ship real".
