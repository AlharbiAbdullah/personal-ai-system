---
name: benchmark
description: Scores models and harnesses on John's own work, with Rai loaded, and keeps one leaderboard of every target ever run. Model mode runs the models he picks, each in its home harness. Harness mode runs each harness on the model it can reach. Six areas, 20 tasks each, deterministic checks first and two judges after. Manual only. Use when he says "/rai benchmark", "benchmark the models", "which model is best for Rai", or "compare the harnesses".
allowed-tools: Bash, Read, AskUserQuestion
---

# /rai benchmark: models and harnesses on his own work

A benchmark run sends real tasks to real harnesses and scores what comes back. Every attempt runs
in a bubblewrap sandbox. `~/helm` is an overlay of a vault snapshot, so the live vault is never
written. The snapshot drops every memory record that mentions the benchmark, so no attempt finds
an expected answer through recall. Rai's runtime state and the harness session records go to
scratch, so no run reaches memory. The desktop, the session bus and `~/.cache` are out of reach. The engine is `scripts/bench.py` with `scripts/bench_lib/`. Data lives in
`03-rai/benchmark/`, and its `AGENTS.md` holds the task schema and the check types.

```bash
B=~/helm/03-rai/skills/rai/scripts/bench.py
```

## Routes

Runs use his subscriptions only, on routes inside each provider's terms.

| Harness | Route | State |
|---|---|---|
| Claude Code | Claude Max through `claude -p` | on |
| agy | Google Antigravity through Google's own `agy -p` | on |
| pi | none | off: pi-antigravity breaks Antigravity ToS section 6, and Claude Max tokens are barred outside Anthropic's apps |
| OpenCode | none | off: no subscription route inside a provider's terms |

Turn pi or OpenCode on in `targets.toml` only when he has a compliant route for it, such as an API
key or a supported subscription. Never re-enable one on the routes above.

## Areas

Rules, routing, recall, vault and Arabic test Rai's work. Their tasks are drafted from his real
sessions and run only after he approves them. Coding tasks are written for the bench, each with
hidden tests and a reference solution. Each check passes or fails, and an attempt passes when
every check of its task passes. The headline number is that pass rate. A `judge` check goes to
Opus (Claude Code) and Gemini 3.1 Pro (agy) apart, and the report shows both.

## Run it

1. **Tasks ready?** Run `$B tasks`. An area with fewer than 5 quick tasks marked active needs his
   approval first. Show him the drafts of one area at a time: id, prompt and checks, a few per
   message. He approves, edits or drops each. Then run `$B approve <id> ...`, or
   `$B approve --area <area> --all` when he approves a whole area.
2. **Pick the targets.**
   - Model mode: run `$B models`, then ask with AskUserQuestion (multiSelect) which models to run.
     List the defaults first.
   - Harness mode: `--mode harness` runs each enabled harness on its `harness_mode` model.
   - Effort levels: `--efforts low,medium,high,xhigh,max` runs each picked target once per level,
     each its own leaderboard row. agy takes low, medium, high and max.
3. **First run on a route:** run `$B start --size smoke --models <keys>`, then `$B report` once
   `$B status` says done. It sends two probes per target: is Rai's context loaded, and can the
   agent write a file. Run the real benchmark only on targets that passed both.
4. **Plan, then his go.** Run `$B plan` with the same selection and show him the plan lines:
   attempts, rough time, and that it spends Max and Antigravity quota. Start only on his go:
   `$B start [--mode harness] [--models a,b] [--size quick|full] [--night]`. The run goes to a
   background systemd unit and returns at once.
5. **Watch.** `$B status` shows progress and any paused account. `$B stop <run-id>` stops a run, and
   `$B resume <run-id>` continues it in the background. One runner per run: a second is refused.
6. **Results.** A finished run writes `results/<run-id>/report.md` and regenerates
   `leaderboard.md`. Lead with the leaderboard table for this task set, then the most-failed checks.

## Sizes

| Size | Tasks | Trials | Rough time |
|---|---|---|---|
| quick (default) | the 5 quick tasks per area | 1 | about 15 minutes per model |
| full | all 20 per area | 3 | about 2.5 hours per model |
| smoke | 2 built-in probes | 1 | about 2 minutes per model |

Times assume 4 attempts at a time (`--concurrency`) and about 90 seconds an attempt, plus
judging. A usage limit adds its wait.

A quick run separates tiers, not neighbours: 30 tasks carry about ±18 points of noise. Call a gap
under 15 points a tie unless a full run confirms it.

## How a run behaves

- **Usage limit:** the account pauses until its reset, or for 30 minutes doubling to 3 hours. The
  other account keeps working. The attempt re-runs fresh and is never scored.
- **Crash:** retried twice, then recorded as an infrastructure error and left out of the scores.
- **Timeout:** 15 minutes by default. It counts as the agent's own failure and is scored.
- **`--night`:** dispatches only from 23:00 to 08:00.
- **Rai context for agy:** agy has no Rai edge. Each agy attempt gets a `GEMINI.md` holding the
  identity block session-start gives Claude Code, plus his auto-memory index.
- **Crash safety:** state is written atomically and a torn line is skipped, so a dirty shutdown
  never blocks a resume.

## Rules

- Manual only. Never schedule a run, and never start one without his go: quota is his.
- Never edit a task a run has used. Change the task, and its version changes: old scores stay in
  their own table, and a stopped run that used it refuses to resume.
- Judged Arabic scores are weak evidence. Show him two or three Arabic answers next to their
  verdicts.
- Tests: `cd ~/helm && uv run --offline --python 3.12 --with pytest python3 -m pytest 03-rai/skills/rai/scripts/bench_lib/tests -q -p no:cacheprovider`

A result that feeds a model choice goes on through [[31-ai-system-build]] step 2.
