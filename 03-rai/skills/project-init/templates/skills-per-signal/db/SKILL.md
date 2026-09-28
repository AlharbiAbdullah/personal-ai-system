---
name: db
description: >
  Database migrations for {NAME} with alembic. USE WHEN a change adds or edits a model or a
  migration, or when asked where the schema stands.
---

# db

The migrations are configured by `{DB_CONFIG}`. Run every command below from `{DB_DIR}`.

## Commands

- The newest revisions, with no database needed: `uv run --locked alembic heads`. project-init's selftest runs it and fails unless it exits 0.
- Where this database stands: `uv run --locked alembic current`. It connects to the database that `.env` names.
- A new migration: `uv run --locked alembic revision --autogenerate -m "<what>"`. Read the file before you commit it: autogenerate misses renames and server defaults.
- Apply: `uv run --locked alembic upgrade head`.

## Failure modes

- `Can't locate revision`: this branch is behind the default branch. Bring it up to date first.
- After a merge that leaves two heads: `uv run --locked alembic merge heads -m "merge heads"`, in its own change.
- `connection refused`: the database is not running, or `.env` points somewhere else.
