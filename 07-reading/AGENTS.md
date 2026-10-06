# 07-reading/ — Books Through Claude Code

## Purpose
Books read interactively. Complete coverage, not summaries.
Philosophy: "I don't have time to read books. So I read them through you."

## Structure
- One folder per book or author-curriculum, kebab-case
  (e.g., `robert-greene-curriculum/`).
- Each curriculum has `progress.md` (required).
- Lessons flat: `Lesson NNN - [Topic].md`.
- Tier organization allowed for multi-book or multi-phase curricula (see skill rules).

## Skills
The `/reading` skill group (`03-rai/skills/reading/`) drives all book work:
- `start-book` — scaffold curriculum + progress.md + tier plan
- `teach` — generate a lesson in the right type (Chapter / Law / Practice / Synthesis)
- `audit-coverage`: check a book's coverage when he asks. It is never a closing gate.

Teaching rules — lesson shapes, pacing, named-framework preservation, stories-sacred,
per-chapter treatment standard, quality bar — all live INSIDE the `teach` skill.
