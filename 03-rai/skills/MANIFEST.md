# Skills Manifest

44 skills: 35 routers and 9 leaves, one folder each in `03-rai/skills/` (counted against the filesystem on 2026-10-06). `synced/` is not a skill and isn't shipped by this kit: it is the harness-managed bucket of synced Anthropic skills (docs, docx, pdf and others). Claude Code discovers `skills/*/SKILL.md` at depth 1; routers dispatch to their sub-skill files internally.

Naming: all folders kebab-case. Router `SKILL.md` has `name:` matching folder. Sub-skill filenames are kebab-case; frontmatter is optional for sub-skill files, and their `name:` matches the filename stem when present. Vendored upstream files are exempt from this convention entirely.

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
| R | **media** | art, diagram, remotion, write-story | Images, diagrams, video, fiction |
| R | **business** | sales, presentations, pricing | External-facing go-to-market content |
| R | **writing** | arabic, proposals, prds, social-media, blog | Prose craft (anti-AI voice). Shared `references/voice.md`. |
| R | **obsidian** | cli, markdown, bases | Obsidian CLI, Obsidian Flavored Markdown, Bases (vendored kepano/obsidian-skills, pinned in `.skill-lock.json`) |
| R | **life** | telos, quote | Self-model + wisdom capture (reads/writes `02-ana/`) |
| R | **routine** | bills, journal, monthly-mirror, today-prep, tomorrow-prep, weekly-retro | Daily/weekly/monthly rhythm (reads/writes `02-ana/`) |
| R | **investment** | status, recommend, screen, review, ops, convene | Sharia-compliant, paper-first investing: status, recommendations, the Sharia screen, portfolio review, the local paper-portfolio runbook (`ops`), and the council's Restraint Gate (`convene`). Reads/writes `02-ana/financial/investment/`. |
| R | **shopping** | vet, buy, return | Buying physical goods end to end. Vet before spending, and run the checkout with a hard stop before Place Order. Fight the vendor when it arrives missing, damaged or used. Plans in `02-ana/shopping/`, live disputes in `02-ana/admin/`. |
| R | **mac** | theme, automation, diagnostics, dotfiles-bootstrap, tips | macOS power-user + admin |
| R | **ubuntu** | hyprland, diagnostics, dotfiles-bootstrap, tips | Linux power-user + admin on the Omarchy hub (diagnostics, bootstrap, tips; hyprland is pre-Omarchy reference) |
| R | **omarchy** | basics, hyprland, plugins, theming, hooks, capture, diagnose-crash, contributing | Omarchy 4 (Arch + Hyprland) desktop/system config, vendored from `/usr/share/omarchy/default/agents/skills/`. `crash-reporting.md` is a helper that `diagnose-crash` reads. |
| R | **rai** | sanity, eval, benchmark, process-sessions, compose-agents, create-skill, upgrade | Brain maintenance |
| R | **recall** | history | Past-session retrieval |
| L | **remember** | - | Memory v3 curated working-memory write (identity/working-memory.md, 2,500-char cap). The ONLY sanctioned live write besides turn-capture. |
| L | **workflow** | - | Router over `~/helm/11-workflows/`, John's workflows: his way of doing each kind of work. Matches the work to its workflow, which names the skills and agents its steps use. |
| R | **learning** | start-topic, teach, quiz, audit-coverage | Courses + tutorials (reads/writes `06-learning/`) |
| R | **retain** | learning | Random rehearsal of finished curricula, mode by material (reads `13-archive/learning/`, writes `06-learning/retention/ledger.jsonl`); knowledge + reading sub-skills planned |
| R | **reading** | start-book, teach, audit-coverage | Book curricula, full coverage (reads/writes `07-reading/`) |
| R | **knowledge** | new-topic-note, insight, audit-moc, find-connections | Topic notes, MOCs, insights (reads/writes `10-knowledge/`) |
| R | **ideas** | start-seed, promote, graduate, derive | Idea pipeline Seed -> Plant -> Tree -> graduate (reads/writes `09-ideas/`) |
| R | **triage** | process-landing, process-inbox | Capture triage: landing + inbox |
| R | **work** | weekly-planner, meeting-prep | Work rituals (reads/writes `04-work/`) |
| L | **project-init** | - | Puts a folder or repo on the spec-driven, test-driven standard: `specs/` constitution, mise tasks, git gates, the portable `sdd` skill, team memory. Re-running it audits and upgrades. |
| L | **map-updater** | - | Navigation map refresh, run on demand: the helm index `.helm-index/helm-index.md` (which `session-start.py` injects) and, in a code project, `.codemap/codemap.md`. No hook calls it. |
| L | **news-digest** | - | Curated news feed from HN, Reddit, X, Substack, Medium, GitHub Trending. `weekly_style.md` is the weekly style guide it loads; `digest_style.md` briefs the short digest written after each daily. |
| L | **grill** | - | Pipeline talk step. SDD repo: follows the repo's `.claude/skills/sdd/talk.md` plus vault intake and extra rounds, and offers /spec-improve and /visual plan before `! mise run approve`. Elsewhere: `.agent/decisions.md` + `.agent/plan.md`. |
| L | **spec-improve** | - | One Ousterhout + spec-lint pass over a draft change folder or `.agent/plan.md`, scored 1-10. A score of 3 or less logs `skip`: no edits, stop at approval. Never chains into implementation. |
| L | **compile** | - | Pipeline build step. SDD repo: the repo's `sdd/compile.md` then `validate.md`, plus /orchestrator for 3+ disjoint groups and /fusion review after validate. Elsewhere: executes `.agent/plan.md`. |
| R | **fusion** | review, brainstorm, plan, debug, decide, ask, write-english, write-arabic | Six-voice panel on his subscriptions, no pay-per-call API, one voice per model. Voices: Gemini 3.1 Pro (agy). MiniMax M3 and GLM-5.3 (opencode). DeepSeek V4 Pro and GPT-6.1 Sol xhigh (pi). Opus 5.5 max (Claude Code). Each voice is a read-only session in its own tmux window. Round 1 alone is the vote, round 2 checks the others on evidence. The triggering session coordinates and merges. `review` is the external review /compile runs after validate. |
| L | **orchestrator** | - | One session drives N parallel Claude workers: tmux session + git worktree per task (SDD repo: the `parallel: yes` groups). Hook-written status files, evidence-gated review, dependency-order merge into `feat/<slug>` (never main), guarded teardown. Code projects only, never helm. |
| R | **visual** | plan, explain, teach, compare, trace, data, debug | Single self-contained animated HTML artifacts: crisp auto-layout scenes narrated by beats, light/dark toggle. plan renders a change folder for approval. explain covers what exists, teach teaches by prediction, and compare weighs options head-to-head. trace walks a bug or incident path, and data explains a schema or dataset. debug replays a real recorded run in a step debugger (`references/trace_recorder.py`). One shared engine in `references/engine.html`. |

## Groups (conceptual, for orientation)

Groups map clusters of related skills. They are documentation only. Each of the 44 skills sits in exactly one group.

- **Engineering-domain**: architecture, data, devops, coding-standards, testing, ai, security
- **Engineering-workflow**: git, project-init, map-updater, orchestrator, fusion, and the SDD pipeline: grill -> spec-improve (repeatable) -> `! mise run approve` -> compile -> fusion review
- **Knowledge + content**: research, investigation, scraping, content-analysis, media, business, writing, news-digest, knowledge, learning, retain, reading, ideas, triage, obsidian, visual
- **Thinking**: think
- **Personal**: life, routine, work, shopping, mac, ubuntu, omarchy, investment
- **Brain maintenance**: rai, recall, remember
- **Workflows (his way)**: workflow

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
