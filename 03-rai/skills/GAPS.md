# Skills GAPS

Open skill gaps: work that is known but not yet done. `/rai upgrade` reads this file.

## Open

- **Security authorization format.** Standardize the authorization block across
  `security/prompt-injection`, `security/web-assessment` and `investigation/*`. Pick one
  canonical phrasing ("written approval via email/ticket stating target + scope + explicit
  go-ahead") and use it in each file.
- **`media/remotion` external services.** Rendering with audio, TTS and stock footage libraries
  is not covered yet.
- **`news-digest` template factoring.** `SKILL.md` is long. The headless collectors
  (`_collect_x_headless.py`, `_collect_web_headless.py`) are the primary path. The file still
  contains the Browser Collection Template and the per-source MCP algorithms, which serve only
  as the interactive fallback. Move that fallback text into a reference file so `SKILL.md`
  describes the headless pipeline.

- **`retain` knowledge/reading sub-skills.** `/retain` only rehearses finished curricula
  (`learning.md`). Rehearsing `10-knowledge/` topic notes or finished `07-reading/` books is not
  built yet.

## Deferred until proven by use

- **`/ai/` sub-skills `eval-harness` and `prompt-patterns`.** Add them to `/ai/` only after
  manual use shows the need.
- **`coding-standards/swift`.** Add it when Swift becomes a recurring language (iOS, macOS
  native).

## Rules for this file

- Items here are not yet scoped or scheduled.
- Promote one with `/rai create-skill` when it is ready to build.
- Delete an item once it is done. Git log keeps the history.
- Append new gaps found during deep-work passes.
