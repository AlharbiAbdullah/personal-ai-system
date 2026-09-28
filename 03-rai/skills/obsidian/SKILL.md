---
name: obsidian
description: >
  Obsidian router. USE WHEN Rai must talk to the running Obsidian app through
  the `obsidian` CLI (search, open, properties, tasks, plugin reload, eval),
  write Obsidian Flavored Markdown (wikilinks, embeds, callouts, properties),
  or author and check Bases (.base files or ```base blocks: views, filters,
  formulas). Sub-skills are the official kepano/obsidian-skills pack, pinned in
  `03-rai/config/.skill-lock.json`.
---

# Obsidian

The vault is `~/helm`, opened in Obsidian on both machines. The CLI (Settings, General, Command line interface) is on since 2026-08-07 and needs the app running. Zero servers: no Local REST API, no MCP.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Query or drive the running app: search, open, create, properties, tasks, daily note, plugin reload, `eval`, screenshot | cli | `cli.md` |
| Write or fix Obsidian syntax: wikilinks, embeds, callouts, frontmatter properties, tags, comments | markdown | `markdown.md` |
| Author or verify a Base: `.base` file or a ```base block, views, filters, formulas, summaries | bases | `bases.md` |

## How to use

1. Pick the sub-skill by what you want to do.
2. `Read` the file in this directory. References live in `references/`.
3. Vault rules still win: templates from `12-system/templates/`, folder AGENTS.md conventions, the voice gate for prose.
4. Diagrams in this vault are D2 fences, not Mermaid. `markdown.md`'s "Diagrams (Mermaid)" section is vendored upstream text; ignore it and use D2.

## Source

Vendored 2026-09-09 from kepano/obsidian-skills (MIT), commit in the lockfile. Sub-skill bodies are verbatim; only the `name:` frontmatter follows the vault convention (name = filename stem). Refresh by re-fetching the three `SKILL.md` files and `references/` at a new commit and updating the lockfile hash.
