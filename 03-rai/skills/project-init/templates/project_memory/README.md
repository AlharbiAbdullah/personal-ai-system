# project_memory

Every fact has one home. Before writing one down, find its row.

| Fact | Home |
|---|---|
| why, who, scope | `specs/mission.md` |
| stack, standing rules, env types | `specs/tech-stack.md`, `.env.example` |
| what is true now | `specs/capabilities/`, proved by tagged tests |
| next, maybe later | `specs/roadmap.md`, `specs/backlog/` |
| why of one change | its `specs/changes/<date>-<slug>/` (frozen) |
| a choice later changes must respect | `decisions/<date>-<slug>.md` |
| what surprised us | `lessons.md` (append only) |
| how to work | `specs/README.md`, `AGENTS.md` |
| commands | `mise.toml` (`mise tasks ls`) |
{IF_TEAM}| who may merge | `team.md` |
| where work stopped | derived: `mise run status` |

Formats: `specs/README.md#roadmap-backlog-decisions-lessons`.
