# Agents Manifest

11 agents. All kebab-case. Every agent file sets `model: opus` and `effort: xhigh` in its frontmatter. Invocation drives from the `name:` field in each `.md` file.

Two tiers: **specialists** (user invokes explicitly to take on a role) and **methodology** (applied to any problem, not domain-bound).

## Specialists (10)

Each has a distinct persona and scope. Invoke one through the Agent tool with `subagent_type: "<name>"`, or with a direct "use the X agent" prompt.

| Agent | Scope |
|-------|-------|
| `architect` | Distributed systems, architecture decisions, trade-off analysis. Thinks in constraints and principles. |
| `engineer` | Production-grade implementation. TDD, types, tests-first. |
| `designer` | UX/UI, WCAG 2.1 AA, visual hierarchy, spacing, interactions. |
| `pentester` | Authorized security testing, vulnerability assessment. Requires explicit authorization. |
| `qa-tester` | Edge case hunting from user perspective. Evidence-based PASS/FAIL. |
| `reviewer` | Code review, bug catching, security issues. Tests must pass before approval. |
| `artist` | Image prompt engineering for FLUX, GPT-Image-1. Illustrations, diagrams, visual assets. |
| `writer` | Prose craftsman. Locked-in voice across Arabic (Lumen north star) + English, anti-AI rules. Prose, not code. |
| `debugger` | Root-cause specialist. Reproduce, hypothesize, bisect, instrument, prove. Fixes the class, not the symptom. |
| `sre` | Site reliability. Keeps running systems up, diagnoses failures (timers, sync, schedulers). `/devops` builds; `sre` keeps alive. |

## Methodology (1)

Persona-neutral. Applied to any problem.

| Agent | Scope |
|-------|-------|
| `researcher` | Multi-source research synthesis. Query decomposition, parallel search, citation-backed findings. |

## Adding a new agent

1. Scope: what distinct persona or methodology does this bring that no existing agent covers? If the answer is "none," it's a skill, not an agent.
2. File: `agents/<name>.md` with frontmatter `name: <name>`, `description:`, `model: opus`, `effort: xhigh`.
3. Tools: an agent inherits every tool unless its frontmatter narrows them. Rai uses `disallowedTools` (removes tools, keeps MCP and the rest): `reviewer` and `qa-tester` cannot write or edit files, `researcher` cannot run Bash or write files. The other agents inherit all tools. A `permissions:` block in agent frontmatter limits nothing, so none is used.
4. Update this manifest.
5. Invoke it through the Agent tool with `subagent_type: "<name>"`.

## Naming rules

- Filename: kebab-case, matches frontmatter `name:` field
- `name:` field: drives invocation
- No PascalCase in new agents (breaks consistency with skills)
