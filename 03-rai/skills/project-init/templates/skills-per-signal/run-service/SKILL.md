---
name: run-{SERVICE}
description: >
  Start {SERVICE} locally and check that it is up. USE WHEN asked to run, start or try
  {SERVICE}, or to check a change in the running service.
---

# run-{SERVICE}

{START_LINE}{SERVICE_COMMANDS}

## Check that it is up

Start it in the background and note its PID. Wait for its first log line, then call the route the change touches. Stop it by that PID: `kill <pid>`. Never `pkill -f`, which matches other processes too.

## Failure modes

- `address already in use`: another copy is running. Find its PID with `ss -ltnp` and stop that one.
- A secret is missing: `.env` needs the `op://` pointer that `.env.example` names.
- `ModuleNotFoundError` after a dependency change: run `mise install`, which runs `uv sync --locked`.
