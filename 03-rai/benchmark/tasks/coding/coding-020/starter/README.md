# Pipeline planner

The nightly batch is a set of tasks with dependencies, declared in TOML (`pipeline.toml`). Before
the scheduler runs anything we want a small planner that checks the file, prints a run order,
groups tasks into levels that can run in parallel, tells us what a failing task blocks, and finds
the critical path that decides how long the night takes.
