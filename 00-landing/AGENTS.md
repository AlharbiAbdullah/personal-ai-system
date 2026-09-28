# 00-landing/ — Parking Lot

## Purpose
A place for thoughts to land. No research, no organization, no processing required.
Pre-triage. Anything that deserves more structure belongs downstream.

## Lifecycle
Every note has exactly two exits:
- Move to `01-inbox/` when it deserves research, organization, or instruction
- Delete when it doesn't

There is no archive path. Files sit indefinitely until John triages them.

## Rules
- Writers: manual editor drops only. Claude must not create, move, or edit files here.
- Structure: strict flat. No subfolders.
- No retention cap.

## What Claude does
- Ignore by default. Do not scan for context unless John explicitly references a file.
- Treat referenced content as low-confidence fragments.
- Never sweep, archive, delete, or reorganize without explicit instruction.
- The `/triage process-landing` skill is the one allowed channel for moving/deleting files here; it walks each file interactively, promote-to-inbox or delete.
