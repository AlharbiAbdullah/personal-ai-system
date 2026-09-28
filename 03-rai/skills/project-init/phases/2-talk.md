# P2 Talk: intake and constitution

**Runs in:** SCAFFOLD, ADOPT, MIGRATE, EXTEND + v2 migrate. EXTEND runs it only for the gaps P8 lists. **Writes:** product text in `specs/`, with the Write tool, uncommitted. P4 carries it onto `plan/project-init` and P7 commits it there.

This file is the Rai side: where the evidence comes from and how it is cleaned. The conversation itself is the repo's own talk text, so every repo and harness talks the same way. Use sections 1 to 3 of [`templates/skills/sdd/talk.md`](../templates/skills/sdd/talk.md): evidence first, the free-text opener, decision rounds, the constitution checklist. P4 renders that same file into the repo as `.claude/skills/sdd/talk.md`.

## Sources, in order

Read all of them before the first question. The vault is read-only here.

1. `~/helm/05-projects/kitchen/<name>/specs/*`, as `/ideas graduate` leaves them. Copy them, then sanitize the copy.
2. Legacy `kitchen/<name>/{PRD,ROADMAP,BUILD-LOG}.md`, and `05-projects/active/<name>/*`.
3. The idea: `grep -l '^spawned:.*<name>' ~/helm/09-ideas/*.md`, else `~/helm/09-ideas/<name>.md`.
4. Repo docs: README, `docs/{PRD,SPEC,ARCHITECTURE}.md`, `MISSION.md`, `PLAN.md`, `TODO.md`, `.agent/*.md` (D7: a tracked `.agent/` is read here, and P4 untracks it), a legacy `CLAUDE.md`, and the v2 `AGENTS.md`, `docs/spec.md` and `project_memory/facts.md`. In MIGRATE, also `project_memory/accumulated_knowledge.json` as it is. P4's `migrate-v1 --apply` then renders it into `specs/backlog/<date>-legacy-knowledge.md` and removes it.
5. `gh issue list --limit 50` when a remote exists.
6. Lockfiles and config: runtime deps, the Python pin, existing CI.
7. The locked language standard (`~/helm/03-rai/skills/coding-standards/<lang>.md`), plus only the team-safe principles from `~/helm/02-ana/identity/tech-stack.md`. Personal habits stay out.

Then the P1 probe: every pass is a characterization scenario, every crash a `[gap]` scenario plus the Phase 1 roadmap item. Its `trunk` block holds the candidates for the Trunk section.

## Sanitize, before anything is written

- `[[x]]` becomes `x`.
- Drop vault paths, home paths, personal tooling and 1Password item names. An env secret keeps only the `op://<vault>/<item>/<field>` shape in `.env.example`, filled by the human.
- Provenance goes in frontmatter with no path: `source: vault-kitchen 2026-09-23`.
- The gitleaks leak rules block what this misses (I14). P5 runs them.

## The conversation

Pre-fill every field of the constitution checklist (`talk.md` section 3) from the sources first, then run `talk.md` sections 1 to 3 for what is still open. Thin sources (SCAFFOLD with no kitchen) open with its free-text prompt. On top of `talk.md`:

- **Always settle** the mission one-liner and the distribution (pypi, git, service or none). P4 reads both from the specs: the first line under `## One-liner` in `specs/mission.md` becomes the pyproject `description`, and the `## Distribution` section of `specs/tech-stack.md` holds one word, `pypi`, `git`, `service` or `none`.
- **The first roadmap phase** holds the probe gaps, when there are any.
- **A service the probe could not reach** (P1 printed `service ..... little signal`): the first feat change gets the service's health check as a Run-it row. Record it in the roadmap item, since the change folder comes later.
- **The later phases** come from the sources too. The checklist asks for at least 2. Sources are TODOs, issues, plans and code evidence, such as a parameter no interface exposes. Prefill them. When no source names a second phase, the round asks for it: 2 or 3 options drawn from the evidence, one (Recommended).
- **The Trunk section** of `specs/tech-stack.md` joins the constitution checklist (v3.1). It decides how much of each later diff a human reads: a path an entry matches is trunk, and its diff is read at merge. Everything else is leaf, and its diff is skimmed against proof. Ask one question, after the upstream ones (a round of its own when round 1 is full). Show every candidate from P1's `trunk` block with its why, then offer:
  1. Keep all N (Recommended: each one has static evidence, and a missed trunk file would be skimmed as leaf).
  2. Edit: drop some, or add paths the scan cannot see (a public interface, a money or auth module). Each added line needs its why.
  3. Start empty: every path is leaf until a later branch adds an entry.

  Write the answer under `## Trunk`, one line per entry: `- <glob>: <why>`, the glob from the repo root. Keep the template's comment line and drop its placeholder line. Start empty leaves the section with its comment only, which is valid. With no candidates, skip the question and write the section empty. SCAFFOLD has no code yet: write the section with its comment line only, and P3 asks the question once `uv init --package` has made the entrypoint ([3-scaffold.md](3-scaffold.md)). A headless run keeps all candidates, since a marker is not a valid entry. Adding an entry later is free, and removing or narrowing one needs `--gate-change` at merge.
- **The remote question (D2)** is asked only when there is no `origin`. 1. Private GitHub repo: the default, Recommended unless the talk showed a throwaway. 2. Local only: Recommended for a throwaway such as tipcalc. A GitHub answer is passed to P4 and P7 as `--remote github`. Specs do not record it.

## Writes

From `~/helm/12-system/templates/sdd/`: `specs/mission.md`, `specs/tech-stack.md` (its `## Trunk` section included), `specs/roadmap.md`, `specs/capabilities/<entry>.md` (characterization + gaps; `config.md` when env knobs exist), and `specs/backlog/` seeds from TODOs and issues. `specs/README.md` is machinery: P4 renders it.

In a v2 migration, also: one ADR per D-NNN in `project_memory/decisions/` with `aliases: [D-NNN]`, and one retiring lesson appended to `project_memory/lessons.md` for each lesson the `migrate-v2` prompt named ([9-migrate.md](9-migrate.md)).

## Check before leaving P2

- `grep -rnE '\{[A-Z_]+\}' specs/` returns nothing: every template placeholder is filled or turned into a marker.
- `specs/tech-stack.md` has a `## Trunk` section: the template's comment line, then one `- <glob>: <why>` line per entry, or none.
- `specs/` holds no vault path. Each template's header comment stays: it states that file's rules for the next writer.
- Every scenario follows the grammar in `templates/specs-README.md#formats`: one SHALL per requirement, IDs `<cap>.<slug>`.

## tipcalc

```text
sources ..... README (no fence), pyproject, lockfile, probe; vault: nothing named tipcalc
prefilled ... audience, problem, scope, runtime python/uv, Phase 1 entrypoint-hardening (5 gaps),
              Phase 2 percent-flag (code: tip() takes a percent the CLI reads only from the env)
round 1 ..... 1. mission one-liner  2. distribution: none / PyPI  3. private GitHub / local only
answers ..... "tiny CLI that prints the tip for a bill" | none | local only
round 2 ..... 4. trunk: keep the 1 candidate (Recommended) / edit / start empty
answer ...... keep all: - src/tipcalc/__init__.py: the entrypoint of the tipcalc command (tipcalc:main)
rules ....... S-1 external input parsed by pydantic at the boundary, env via pydantic-settings
              (env_ignore_empty=True) | S-2 secrets are op:// pointers only | S-3 scripts are uv PEP 723
writes ...... specs/mission.md tech-stack.md roadmap.md capabilities/cli.md capabilities/config.md
              (no backlog/: tipcalc has no TODO and no remote with issues)
```

## Next

[3-scaffold.md](3-scaffold.md). EXTEND goes back to [8-extend.md](8-extend.md).
