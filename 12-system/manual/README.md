# The Kit Manual

This manual is a pointer map. Each topic names the live doc that owns it today. Those docs change with the kit, so read them rather than a copy. Paths are relative to the vault root (wherever you cloned this kit, `~/helm/` in the docs' own examples).

| Topic | Live doc |
|---|---|
| Overview and vault-wide rules | `AGENTS.md` (root), then `03-rai/AGENTS.md` (Rai's global instructions, loaded every session) |
| Folder map | `AGENTS.md` (folder table and root items), then the `AGENTS.md` inside each numbered folder |
| Architecture of Rai's brain | `03-rai/ARCHITECTURE.md` (layout, one section per directory) |
| Session lifecycle | `03-rai/ARCHITECTURE.md` (cross-file relationships), `03-rai/MEMORY-ARCHITECTURE.md` (capture, injection) |
| Capture pipeline | `AGENTS.md` (Capture pipeline), `00-landing/AGENTS.md`, `01-inbox/AGENTS.md`, `03-rai/skills/triage/SKILL.md` |
| Ideas | `09-ideas/AGENTS.md`, `03-rai/skills/ideas/SKILL.md`, `05-projects/AGENTS.md` for graduated ideas |
| Skills | `03-rai/skills/MANIFEST.md`, then the skill's own `SKILL.md` |
| Agents | `03-rai/agents/MANIFEST.md` |
| Hooks | `03-rai/ARCHITECTURE.md` (`hooks/`), `03-rai/config/settings.json` (registrations) |
| Memory | `03-rai/MEMORY-ARCHITECTURE.md`, `03-rai/semantic-memory/CHROMADB-SCHEMA.md` |
| Templates and naming | `12-system/AGENTS.md` (templates inventory), `12-system/templates/` |
| Knowledge system | `10-knowledge/AGENTS.md`, `03-rai/skills/knowledge/SKILL.md` |
| Personal OS | `02-ana/AGENTS.md`, `03-rai/skills/life/SKILL.md`, `03-rai/skills/routine/SKILL.md` |
| Work and projects | `04-work/AGENTS.md`, `05-projects/AGENTS.md`, `03-rai/skills/work/SKILL.md` |
| Spec-driven projects | `11-workflows/21-project-init.md` (init, feature loop, replan, release, launch), `03-rai/skills/project-init/SKILL.md`, `03-rai/skills/project-init/templates/specs-README.md` (the repo standard) |
| Prose gate | `03-rai/config/vale/README.md`, `03-rai/skills/writing/references/voice.md` |
| News digest | `03-rai/skills/news-digest/SKILL.md`, `08-bawaba/AGENTS.md` |
| Workflows | `11-workflows/AGENTS.md`, `03-rai/skills/workflow/SKILL.md` |
| Config and security | `03-rai/ARCHITECTURE.md` (`config/`), `03-rai/config/settings.json` |
| Multi-machine sync | `03-rai/SYNC-ARCHITECTURE.md` |
| Glossary | `02-ana/identity/definitions.md` (your own terms), `03-rai/MEMORY-ARCHITECTURE.md` (memory terms) |
| Troubleshooting | `03-rai/skills/rai/sanity.md` (brain health), `03-rai/SYNC-ARCHITECTURE.md` (failure modes), `11-workflows/AGENTS.md` (the debugging, incident, news recovery and brain healthcheck workflows) |
| Cheatsheet | `AGENTS.md` and `03-rai/AGENTS.md`, both loaded into every session |

Out of scope: code you build in your own project repos (each one's own `AGENTS.md` and `specs/`), the Claude Code harness itself, and any editor-specific config.
