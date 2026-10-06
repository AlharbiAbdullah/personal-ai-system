"""bench_lib: the engine behind /rai benchmark (bench.py is the CLI).

Modules: paths (where things live), tasks (load, validate, select, version), targets (the
catalog), adapters (one per harness: command + output parser), sandbox (bubblewrap overlay over
a vault snapshot), grade (deterministic checks), judge (Opus + Gemini), runner (queue, pause,
resume), report (per-run report + leaderboard).
"""
