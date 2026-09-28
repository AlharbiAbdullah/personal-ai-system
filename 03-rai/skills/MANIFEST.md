# Skills Manifest

46 skills: 34 routers and 12 leaves, one folder each in `03-rai/skills/` (counted against the filesystem). `synced/` is not a skill and isn't shipped by this kit: it's the harness-managed bucket Claude Code fills with synced Anthropic skills (docs, docx, pdf and others) the first time it needs one. Claude Code discovers `skills/*/SKILL.md` at depth 1; routers dispatch to their sub-skill files internally.

Naming: all folders kebab-case. Router `SKILL.md` has `name:` matching folder. Sub-skill filenames are kebab-case; frontmatter is optional for sub-skill files, and their `name:` matches the filename stem when present.

## Top-level layout

| Type | Skill | Sub-skills | Intent |
|------|-------|-----------|--------|
| R | **architecture** | data-architect, solution-architect, system-design, adr-writer, migration-playbook, patterns, create-cli | System design, ADRs, migration, patterns |
| R | **data** | sql-patterns, streaming | Tactical data patterns |
| R | **devops** | docker, cloudflare, kubernetes, ci-cd, monitoring | Infra + ops + observability |
| R | **coding-standards** | python, typescript, go, rust | Per-language style + review |
| R | **testing** | tdd, pragmatic, unit-test, e2e, api-test, load-test, code-review, verify-completion, dependency-audit, tech-debt-map | Test-write + test-review |
| R | **ai** | rag-design, agent-design | AI engineering (RAG + agents) |
| R | **git** | commit, refactor-clean, pr-description, changelog, code-archaeology | Git workflow |
| R | **security** | web-assessment, prompt-injection, security-review, annual-reports, sec-updates | Security testing, review, reports |
| R | **think** | first-principles, iterative-depth, council, red-team, evals, explain-simply, be-creative, prompting, science, world-threat-model-harness, systematic-debug | 11 reasoning modes |
| R | **research** | web-research, extract-wisdom, competitor, literature, market, academic, browser | Info gathering + synthesis |
| R | **investigation** | osint, private-investigator, recon, combo | People + infra due diligence (auth required) |
| R | **scraping** | apify, brightdata | Multi-page extraction |
| R | **content-analysis** | fabric, parser, documents | Pattern + structure mining |
| R | **media** | art, remotion, write-story | Images, video, fiction |
| R | **business** | sales, presentations, pricing | External-facing go-to-market content |
| R | **writing** | arabic, proposals, prds, social-media, blog | Prose craft (anti-AI voice). Shared `references/voice.md`. |
| R | **obsidian** | cli, markdown, bases | Obsidian CLI, Obsidian Flavored Markdown, Bases |
| R | **life** | telos, quote | Self-model + wisdom capture (reads/writes `02-ana/`) |
| R | **routine** | bills, journal, monthly-mirror, today-prep, tomorrow-prep, weekly-retro | Daily/weekly/monthly rhythm (reads/writes `02-ana/`) |
| R | **investment** | status, recommend, screen, review, ops, convene | Sharia-compliant, paper-first investing: status, recommendations, the Sharia screen, portfolio review, the local paper-portfolio runbook (`ops`), and the council's Restraint Gate (`convene`). Reads/writes `02-ana/financial/investment/`. |
| R | **shopping** | vet, buy, return | Buying physical goods end to end. Vet before spending, run the checkout with a hard stop before Place Order, and fight the vendor when it arrives missing, damaged or used. Plans in `02-ana/shopping/`, live disputes in `02-ana/admin/`. |
| R | **mac** | theme, automation, diagnostics, dotfiles-bootstrap, tips | macOS power-user + admin |
| R | **ubuntu** | theme, hyprland, diagnostics, dotfiles-bootstrap, tips | Linux power-user + admin (theme pipeline, diagnostics, bootstrap, tips; hyprland is pre-Omarchy reference) |
| R | **omarchy** | basics, hyprland, plugins, theming, hooks, capture, diagnose-crash, contributing | Omarchy 4 (Arch + Hyprland) desktop/system config, vendored from `/usr/share/omarchy/default/agents/skills/`. `crash-reporting.md` is a helper that `diagnose-crash` reads. Only relevant if you run Omarchy; ignore otherwise. |
| R | **rai** | sanity, eval, process-sessions, compose-agents, create-skill, upgrade | Brain maintenance |
| R | **recall** | history | Past-session retrieval |
| L | **remember** | — | Memory v3 curated working-memory write (`identity/working-memory.md`, 2,500-char cap). The ONLY sanctioned live write besides turn-capture. |
| L | **workflow** | — | Playbook router over `11-workflows/`: the sequencing layer OVER skills. |
| R | **learning** | start-topic, teach, quiz, audit-coverage | Courses + tutorials (reads/writes `06-learning/`) |
| R | **retain** | learning | Random rehearsal of finished curricula from `13-archive/learning/`, writes `06-learning/retention/ledger.jsonl` |
| R | **reading** | start-book, teach, audit-coverage | Book curricula, full coverage (reads/writes `07-reading/`) |
| R | **knowledge** | new-topic-note, insight, audit-moc, find-connections | Topic notes, MOCs, insights (reads/writes `10-knowledge/`) |
| R | **ideas** | start-seed, promote, graduate, derive | Idea pipeline Seed → Plant → Tree → graduate (reads/writes `09-ideas/`) |
| R | **triage** | process-landing, process-inbox | Capture triage: landing + inbox |
| R | **work** | weekly-planner, meeting-prep | Work rituals (reads/writes `04-work/`) |
| L | **project-init** | — | Puts a folder or repo on the spec-driven, test-driven standard: `specs/` constitution, mise tasks, git gates, the portable `sdd` skill, team memory. Re-running it audits and upgrades. |
| L | **map-updater** | — | Navigation map refresh, run on demand: the vault index `.helm-index/helm-index.md` and, in a code project, `.codemap/codemap.md`. |
| L | **news-digest** | — | Curated news feed from HN, Reddit, X, Substack, Medium, GitHub Trending |
| L | **ask-model** | — | Call an external frontier LLM via OpenRouter for write/translate/judge/critique/summarize/freeform tasks. JSONL-logged. |
| L | **grill** | — | Talk step of the pipeline: pressure-test a feature request, bug report or PRD through question rounds before any code exists, then lock the answers into a spec. In a repo with `.project.toml` it follows the repo's own `.claude/skills/sdd/talk.md`; elsewhere it writes `.agent/decisions.md` and `.agent/plan.md`. Never writes code. |
| L | **spec-improve** | — | One improvement pass over a draft spec or plan before approval: critiques it against Ousterhout's *A Philosophy of Software Design* and a spec lint, then rewrites it and scores the pass 1–10. A score of 3 or less logs `skip`, and a later pass that sees `skip` makes no edits. Safe to queue repeatedly. |
| L | **compile** | — | Build step of the pipeline: implement the approved spec test-first, group by group. In a repo with `.project.toml` it follows the repo's own compile/validate skills, offering `/orchestrator` for 3+ disjoint parallel groups and `/adversarial-review` after validation; elsewhere it executes `.agent/plan.md`. Idempotent: resumes at the first unfinished group. |
| L | **adversarial-review** | — | External multi-model panel review of finished pipeline work via `ask-model`. Hunts subtle state defects, edge-case crashes and spec violations; findings are verified, then fixed inline or sent to the backlog. |
| L | **fusion** | — | Convene a multi-model panel on one open question and synthesize a single answer: several external models plus this session, each answering independently, merged into consensus, disagreements and a recommendation. General-purpose sibling of `adversarial-review`. |
| L | **orchestrator** | — | Run one session as orchestrator + reviewer over N parallel Claude worker sessions: one tmux session and one git worktree per task, monitored, reviewed with evidence, and merged in dependency order. Code projects only, never the vault itself. |
| R | **visual** | plan, explain, teach, compare, trace, data, debug | Single self-contained animated HTML artifacts: crisp auto-layout scenes narrated by beats, light/dark toggle. `plan` renders a planned change for approval, `explain` covers what already exists, `teach` teaches by prediction, `compare` weighs options head-to-head, `trace` walks a bug/incident path, `data` explains a schema/dataset, and `debug` replays a recorded run in a step debugger. One shared engine in `references/engine.html`. |

## Groups (conceptual, for orientation)

Groups map clusters of related skills. They are documentation only. Each of the 46 skills sits in exactly one group.

- **Engineering-domain**: architecture, data, devops, coding-standards, testing, ai, security
- **Engineering-workflow**: git, project-init, map-updater, orchestrator, fusion, ask-model, and the pipeline: grill → spec-improve (repeatable) → approval → compile → adversarial-review
- **Knowledge + content**: research, investigation, scraping, content-analysis, media, business, writing, news-digest, knowledge, learning, retain, reading, ideas, triage, obsidian, visual
- **Thinking**: think
- **Personal**: life, routine, work, shopping, mac, ubuntu, omarchy, investment
- **Brain maintenance**: rai, recall, remember
- **Playbooks**: workflow

## Routers and sub-skills

Routers hold sub-skills as kebab-case `.md` files inside the folder (e.g. `think/council.md`, `testing/tdd.md`, `mac/theme.md`).

## Adding a new skill

1. Scope the workflow. Write it down manually 3 times first. Patterns that don't survive 3 manual uses don't need a skill.
2. Run `/rai create-skill`: it enforces frontmatter, folder layout, naming.
3. Place in the right router (or promote to top-level if it's a new domain).
4. Update this manifest: add the table row and the group entry, and bump the count line.
5. If ambiguous which router, the skill probably needs a clearer scope, not a new router.

## Naming rules

- Folder name: kebab-case, matches frontmatter `name:` field exactly (for top-level routers + leaves).
- Sub-skill filename: kebab-case; its `name:` field matches the filename stem.
- `name:` drives `/invocation` when invoked at top level.
- No name collisions between routers and their sub-skills (a router `/research/` must NOT contain `research.md`).
- Sub-skills are invoked via their router: you type `/architecture` and it reads the requested sub-skill file.

## Routers that are intentionally small

- `/business/`, `/data/`, `/ai/`, `/recall/`: single-domain routers where size reflects current scope, not intent. A sub-skill joins one once its pattern has held up through 3 manual uses (see Adding).
