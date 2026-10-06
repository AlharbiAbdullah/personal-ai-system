# Benchmark: tasks and results for `/rai benchmark`

This folder holds the task set and the results of `/rai benchmark`, the skill that scores models
and harnesses on John's own work. The engine lives in `03-rai/skills/rai/scripts/bench.py`
and `bench_lib/`. The skill text is `03-rai/skills/rai/benchmark.md`.

## Layout

| Path | Holds |
|---|---|
| `targets.toml` | The harness routes and the model catalog. Only routes inside each provider's terms are enabled. |
| `tasks/<area>.jsonl` | One task per line for the Rai areas: `rules`, `routing`, `recall`, `vault`, `arabic`. |
| `tasks/coding/<id>/` | One folder per coding task: `task.json`, `starter/`, `hidden_tests/`, `solution/`. |
| `results/<run-id>/` | One run: `run.json` (what ran), `attempts.jsonl` (one graded attempt per line), `report.md`. |
| `leaderboard.md` | Every target ever run, grouped by task-set version. Regenerated from `results/`. |

## Task schema

One JSON object per line in `tasks/<area>.jsonl`, and the same object in `tasks/coding/<id>/task.json`:

```json
{
  "id": "rules-001",
  "area": "rules",
  "prompt": "The exact text the harness receives.",
  "cwd": "helm",
  "setup": {"files": {"relative/path.md": "content written before the run"}},
  "checks": [{"type": "no_em_dash"}, {"type": "judge", "rubric": "Pass when ..."}],
  "quick": true,
  "status": "active",
  "source": "session 0149ceba",
  "added": "2026-10-01"
}
```

- `id` is `<area>-NNN`. It never changes once a run used it.
- `cwd` is `helm` (the sandboxed copy of the vault, at `~/helm` inside the sandbox) or `work` (an
  empty scratch folder; a coding task gets its `starter/` there).
- `setup.files` paths are relative to the `cwd` root. Optional.
- `quick: true` puts the task in the quick set, 5 per area.
- `status`: only `active` tasks run. A Rai task stays `draft` until John approves it. A coding
  task is `active` once its proof passes: the starter fails its hidden tests and the solution
  passes them (`bench_lib/tests/test_coding_tasks.py`).
- Prompts and fixtures use Latin script. An Arabic task asks in English for Arabic output.

## Check types

Each check passes or fails, and an attempt passes when every check passes. Deterministic checks
run first; `judge` runs only where code cannot decide. Every task needs at least one check the
agent passes only by doing the task (`contains`, `regex`, `skill_used`, `file_read`, `file_exists`,
`file_absent`, `file_contains`, `arabic`, `judge` or `pytest`). The negative text checks fail on
an empty answer.

| Type | Fields | Passes when |
|---|---|---|
| `no_em_dash` | | the final answer has no em dash |
| `no_emoji` | | the final answer has no emoji |
| `english_only` | | the final answer has no Arabic script |
| `arabic` | `min_ratio` (default 0.6) | at least that share of the answer's letters are Arabic script |
| `max_lines` | `n` | the answer has at most `n` non-empty lines |
| `contains` | `any` or `all` (list) | the answer contains any / all of the strings, case-insensitive |
| `not_contains` | `any` (list) | the answer contains none of the strings, case-insensitive |
| `regex` | `pattern` | the pattern matches the answer, case-insensitive |
| `skill_used` | `name` | a tool call invoked the skill, or read a file under `skills/<name>/` |
| `skill_not_used` | `name` (`*` = any skill) | no tool call invoked the skill or read under `skills/<name>/` |
| `file_read` | `path` | a tool call's input names that path |
| `file_exists` | `path` | the file exists after the run, relative to the `cwd` root |
| `file_absent` | `path` | the file does not exist after the run |
| `file_contains` | `path`, `any` or `all` | the file exists and contains the strings, case-insensitive |
| `file_unchanged` | `path` | the file is byte-identical to its state before the run |
| `writes_within` | `paths` (list of prefixes) | every file the run created, changed or deleted sits under one of the prefixes |
| `pytest` | | the task's `hidden_tests/` pass against the final `work` folder |
| `judge` | `rubric`, optional `reference` | both judges (Opus and Gemini) rule pass, each scored apart |

## Results

`attempts.jsonl` rows carry the target, the task, the trial, every check result, both judge
verdicts, the final answer, latency and token usage. Raw harness output stays in
`~/.cache/rai-bench/`, outside the vault. Scores are comparable only within one task-set version,
the hash of every active task.
