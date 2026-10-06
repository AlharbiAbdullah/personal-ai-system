# 13-archive/: Session Preservation

## Purpose

This folder preserves session JSONs forever, plus the standing exceptions listed below. Other historical artifacts are deleted: git log is the archive.

Session JSONs are cheap to store and the forensic/wisdom-mining value compounds over time. That's why they get the exception.

## What lives here

- `historical-sessions/`: session JSONs from the `/rai process-sessions` drain. The archive's core.
- `learning/`: retired learning topics, moved here whole at John's explicit request. Frozen reference, not active curricula. Rehearsal happens via `/retain` only.
- `news/`: the news pipeline's archive. Git-tracked, NEVER purged.
  - `daily/`, `weekly/`: prior news digests, moved here automatically by the `/news-digest` pipeline after each run.
  - `digest/`: prior short digests, moved here by the scheduled runner after each new one.
  - `dumps/YYYY-MM-DD/`: the FULL raw collection dumps of every news run (all ~2k tweets/posts collected each day, not just the ~100 displayed). Copied automatically by `present_v5.py` and the scheduled runner.
  - `weekly-runs/weekly-YYYY-Www/`: the weekly magazine's run dirs, copied automatically by the scheduled runner.
- `audits/`: closed audits, their single home. Frozen decision records, not live plans.
- `shopping/`: closed shopping plans for things John actually bought. Frozen decision
  records: what was compared, why the winner won. Not live plans: live ones stay in
  `02-ana/shopping/`.

Nothing else.

## Rules

- **Archive is sessions-only (`historical-sessions/`), plus the `news/`, `learning/`, `shopping/` and `audits/` exceptions above.** Other content (plans, snapshots, stale docs) gets deleted, not archived. New exceptions require John's explicit request.
- **Read-only by default.** Do not modify archived session JSONs. The whole point is that they're frozen.
- **No new content authored here.** If something needs to be written, it belongs in a live folder (`09-ideas/`, `06-learning/`, `10-knowledge/`, etc.).

## What Claude should do

When asked about a past session, treat historical-sessions/ as the authoritative record for what happened that session.

Never move non-session content into 13-archive, except the listed exceptions. A shopping plan for something John bought goes to `shopping/` here, marked `status: purchased` with a closing note naming what he bought. A closed audit goes to `audits/` here. For anything else, ask what a user means when they ask to "archive" a note. Delete is the default. The other option keeps the note in a live folder with an "archived" status.

Never edit archived session JSONs unless the user explicitly asks.
