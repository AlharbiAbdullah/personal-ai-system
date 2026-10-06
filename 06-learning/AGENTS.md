# 06-learning/ — Courses & Curricula

## Structure
- One folder per topic, kebab-case (e.g., `master-data-path/`, `python-fundamentals/`).
- Each topic has `progress.md`.
- Large curricula allow Phase/Module subfolders:
  - `master-data-path/Phase N - [Name]/Lesson NNN - [Subtopic].md`
- Small topics stay flat: `Lesson NNN - [Subtopic].md`.
- Retired topics live in `13-archive/learning/` (moved whole, frozen).

## Code location
Build code for a new stage lives in `~/projects/<topic>-lab/` (e.g. `~/projects/python-lab/`),
outside the vault. Finished practice code already committed in the vault stays where it is;
this rule only governs where a not-yet-started stage's code lands.

## progress.md (required per topic)
Frontmatter: `type: progress-tracker`, `created:`, `mode: beginner | mid | expert`.
Body: current lesson, last session date, stuck-on line, lesson table.
Icons: ✅ done, 🔄 in progress, ⬜ not started, ⏸️ paused.

## Skills
Learning work is driven by the `/learning` skill group (`03-rai/skills/learning/`):
- `start-topic` — create topic + progress.md
- `teach` — generate mode-aware lesson
- `quiz` — retrieval practice on recent lessons
- `audit-coverage`: check a topic's coverage when he asks. It is never a closing gate: a stage closes on his word.

Lesson shape, mode definitions, writing rules, and anti-patterns live inside the
`teach` skill, not here.
