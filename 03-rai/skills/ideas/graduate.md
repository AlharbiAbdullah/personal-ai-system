---
name: graduate
description: Graduate a Tree idea to 05-projects/kitchen/<name>/. Scaffold specs/ (mission, tech-stack, roadmap, backlog) from the SDD templates plus research/, fill them from the Tree, and mark the idea graduated.
allowed-tools: Read, Write, Bash, AskUserQuestion
---

# Graduate

Moves a Tree idea into project preparation. It creates `05-projects/kitchen/{name}/` in the shape of a repo's `specs/`, so `/project-init` later reads it as the first source of its talk. The kitchen playbook is `11-workflows/03-kitchen.md`. The init and build playbook is `11-workflows/21-project-init.md`.

```text
05-projects/kitchen/{name}/
├── specs/
│   ├── mission.md
│   ├── tech-stack.md
│   ├── roadmap.md
│   └── backlog/          one file per Tree item that is in no phase and not under Later
└── research/
    └── README.md         origin link, sources, risks (vault only; never copied into a repo)
```

## Instructions

### Step 1: Identify the target

Ask John for the idea slug. Read `~/helm/09-ideas/{slug}.md` and check `status: tree` in its frontmatter.

If the status is not `tree`, tell John to promote it first (`/ideas promote {slug}`).

### Step 2: Confirm the project name

The folder name is usually the idea slug, but it may differ if the project name has been refined. Ask "Project folder name?" and default to the slug. Lowercase kebab-case, no spaces.

### Step 3: Check for collisions

- `~/helm/05-projects/kitchen/{name}/` exists: stop, report it, and ask whether to merge into it or pick another name. Never overwrite a kitchen.
- `~/projects/{name}/specs/mission.md` exists: stop. The project already has a constitution in its repo. Direction changes there go through a replan (`11-workflows/21-project-init.md`, Phase D), not through a kitchen.

### Step 4: Scaffold from the templates

```bash
K=~/helm/05-projects/kitchen/{name}
T=~/helm/12-system/templates/sdd
mkdir -p "$K/specs/backlog" "$K/research"
cp "$T/mission.md" "$T/tech-stack.md" "$T/roadmap.md" "$K/specs/"
```

The templates are the same files `/project-init` fills in a repo. Keep each file's header comment: it states that file's rules for the next writer.

### Step 5: Fill `specs/` from the Tree

Replace every `{UPPER_SNAKE}` placeholder. A field the Tree answers gets the answer. A field it does not answer gets one of these:
- a gap in `mission.md` or `tech-stack.md`: `[NEEDS CLARIFICATION: <the question>]`, which the kitchen or the init talk answers. `roadmap.md` never takes a marker;
- a question that blocks a phase: a line under `## Gates` in `roadmap.md`, `- Phase <n>: <question>`;
- a question that doesn't block a phase yet, or blocks only an item under `## Later`: a line under Open questions in `research/README.md`;
- an optional example line with nothing to say (Glossary, Standing rules, Never use, a second tool, Later, Gates): delete the line and keep the heading.

Map by meaning, not by heading. A Tree uses one of two heading sets, and the table covers both:
- the Tree template: Spark, Problem & Solution, Requirements, Plan, First Steps, Success Criteria, Schedule, Resources Needed, Risks;
- free-form: The Idea, Why This Matters, Target Users, Features, Tech Stack, Architecture, Implementation Plan, Open Questions, Source.

A heading in neither set goes to the field its content answers.

| File, field | From the Tree: template heading; free-form heading |
|---|---|
| mission: One-liner | Spark; The Idea or the tagline under the title. One sentence. |
| mission: Who it is for | Problem & Solution, Target User; Target Users |
| mission: Problem | Problem & Solution, Problem; Why This Matters |
| mission: Why now | Schedule or Spark; Why This Matters. Otherwise a marker. |
| mission: Scope, In | Requirements; Features, Core Features, Requirements |
| mission: Scope, Out | what the Tree rules out; otherwise a marker |
| mission: Success | Success Criteria; otherwise a marker |
| tech-stack: Runtime, Tooling | Resources Needed and the Solution; Tech Stack, Architecture. Otherwise markers. |
| tech-stack: Distribution | one word, `pypi`, `git`, `service` or `none`; otherwise a marker |
| tech-stack: Standing rules | constraints the Solution or Architecture states; otherwise delete the example line |
| roadmap: Phase 1 | First Steps and Plan phase 1; Implementation Plan phase 1. No plan section: see the phase rules below. |
| roadmap: Phase 2 and on | Plan phase n; Implementation Plan phase n. One `## Phase <n>` section per Tree phase. |
| roadmap: Later | what the Tree itself calls later, a stretch or a nice-to-have; otherwise delete the example line |
| roadmap: Gates | Risks and open assumptions that block a phase; otherwise delete the example line |
| Open Questions, one by one | Sort each by what it blocks. Who, why or scope: a mission marker. A runtime, tool or distribution choice: a tech-stack marker. A phase: a Gate on that phase. Nothing yet, or only a Later item: a line in `research/README.md`. |
| research/README.md: Sources | Source, and the Plant research |

**Phase rules.** Items are feature-sized, `- [ ] <slug>: <title>`, one feat change each. A phase heading is `## Phase <n>: <name>`, named for what the phase delivers.
- The Tree has a Plan or an Implementation Plan: its phase n becomes roadmap Phase n, in the Tree's order. Add a `## Phase <n>` section above `## Later` for each Tree phase past 2. The numbers match the Tree's, so a question on any phase can be a Gate.
- The Tree has no plan section: Phase 1 is the smallest set of Requirements or Features that reaches the Success signal. Phase 2 holds the rest of them.
- Nothing is left for Phase 2: name it `## Phase 2: next` and delete its example item. Its Gate is `- Phase 2: what comes after Phase 1?`.

`{NAME}` is the project name. Slugs are lowercase kebab-case and permanent once the repo exists.

**Backlog.** A Requirement or idea that is in no phase and not under Later becomes one file, `specs/backlog/<YYYY-MM-DD>-<slug>.md`, from `~/helm/12-system/templates/sdd/backlog.md`: `status: open`, an empty `roadmap:`, then What, Why and Notes. With nothing to park, leave the folder empty.

**No vault material in `specs/`.** No wiki-links, vault paths, personal tooling or 1Password item names. The init talk strips them anyway, and the repo's leak gate refuses them. Links and sources go in `research/`.

### Step 6: Write `research/README.md`

```markdown
# {Project Name}: research

Vault only. `/project-init` never copies this folder into a repo.

- Idea: [[09-ideas/{slug}]]
- Sources: {the Tree's Source section, links and notes from its Plant research}
- Risks: {the Tree's Risks, in full}
- Open questions: {the questions that block nothing yet, or only a Later item}
```

Later research notes go in this folder too.

### Step 7: Update the idea file

In the idea's frontmatter:
- `status: graduated`
- append `"[[05-projects/kitchen/{name}/specs/mission|{name}]]"` to the `spawned:` list.

Do NOT delete the idea file. Graduated ideas stay in `09-ideas/` under the "ideas never die" rule.

### Step 8: Check and report

```bash
cd ~/helm/05-projects/kitchen/{name}
grep -rnE '\{[A-Z_]+\}' specs/                # nothing left
grep -rn '\[\[' specs/                        # nothing: links live in research/
grep -rc 'NEEDS CLARIFICATION' specs/*.md     # the open mission and tech-stack questions
sed -n '/^## Gates/,$p' specs/roadmap.md      # the open phase questions
```

Report: "Graduated `{slug}` to `05-projects/kitchen/{name}/`: `specs/` (mission, tech-stack, roadmap, {n} backlog items) and `research/`. Open: {m} markers, {g} Gates. Next: work the kitchen (`11-workflows/03-kitchen.md`), or run `/project-init` in `~/projects/{name}/` (`11-workflows/21-project-init.md`)."

## Rules

- Never graduate without `status: tree`.
- Never delete the idea file on graduation, and never move it out of `09-ideas/`. Lineage stays.
- `specs/` holds the template shape only: no frontmatter added, no links, no vault paths.
- The kitchen specs are deliberately rough. The kitchen or the init talk refines them, not graduation.
- Vault edits stay local for the coordinator.
