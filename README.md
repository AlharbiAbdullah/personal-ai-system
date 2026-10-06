# Personal AI System

A Markdown vault of identity, skills and memory that Claude Code loads every session, so it knows you.

Status: working · kit, personal files ship as blank templates · 2026-10

![You fill in your identity and send prompts to a Claude Code session, which loads identity and skills from the Markdown vault, takes a snapshot and pointers from memory, and calls the Claude models; a batch step scans past sessions, has the model distill them, stores facts and sessions in memory, and renders learned rules back into the vault; checks cover the whole project.](docs/diagrams/architecture.excalidraw.svg)

## What it does

Turns Claude Code into an assistant with your context. Your identity and its rules load every
session, past sessions are recalled on demand, and preferences you confirm become standing rules.
Skills and agents cover research, writing, software, notes, ideas and a daily news digest.
The assistant is called Rai; [SETUP.md](SETUP.md) shows how to rename it.

## How it works

1. **You.** Fill in the blank templates in `02-ana/identity/` once, then send prompts to
   Claude Code each turn.
2. **Vault.** Plain Markdown, browsable in Obsidian: your identity, Rai's rules, the skills
   and agents (44 and 11 as of 2026-10-06), notes and 31 workflows.
3. **Session.** Claude Code loads identity and the memory snapshot through `~/.claude/CLAUDE.md`
   imports, which `session-start.py` keeps current; `memory-injection.py` adds pointers per
   prompt; `turn-capture.py` appends notes on each turn to a daily log.
4. **Model.** The Claude models answer in the session. The batch calls them through
   `claude -p` to distill past sessions.
5. **Batch.** `/rai process-sessions` scans transcripts, classifies them, distills the worthy
   ones, then stores and archives them. A curation pass renders confirmed rules to the vault.
6. **Memory.** ChromaDB holds four collections, rebuildable from committed text: a JSON Lines
   index, the session archive, the daily logs. The frozen snapshot is what the next session loads.
7. **Checks.** `/rai sanity` asserts each subsystem produces fresh output. pytest proves every
   check fires, `setup.sh --check` covers the wiring, and Vale gates the prose.

## Tech stack

![Tech stack: git; Claude; Claude Code; uv; Markdown, Obsidian; ChromaDB, JSON Lines; pytest, Vale](docs/diagrams/tech-stack.excalidraw.svg)

## Decisions

- **Live writes to text, the vector store only from the batch:** text merges cleanly from more
  than one place. The database keeps one writer, so its files never conflict. Cost: a
  session reaches the vector store only after the next batch run.
- **A frozen snapshot at session start over live queries:** every session opens with the same
  cheap context, and `session-start.py` runs on plain Python with no ChromaDB. Cost: the
  snapshot is only as fresh as the last batch run.
- **Function checks over structure checks:** an older healthcheck tested that files existed
  and stayed green while the brain was broken for three months. Cost: every sanity check needs
  a fault test that proves it fires.
- **The vector store rebuilt locally over committed:** it is a large derived binary and was the
  biggest source of git bloat. Cost: each machine rebuilds it from committed text.

## Run it

Needs [Claude Code](https://claude.com/claude-code) 2.1.277+, Python 3.10+,
[uv](https://github.com/astral-sh/uv) and git. Clone to the path [SETUP.md](SETUP.md) names
(the hooks expect it), then from the repo root:

```sh
./setup.sh           # link the brain into Claude Code, backing up what it replaces
./setup.sh --check   # every link reports OK
claude               # ask: "Who am I, and what am I working on?"
```

[SETUP.md](SETUP.md) covers the identity templates, optional features and troubleshooting.

## Checks

```sh
./setup.sh --check    # every Claude Code link points at this repo
uv run --offline --python 3.12 --with chromadb --with pytest \
  python3 -m pytest 03-rai/skills/rai/scripts/tests -q -p no:cacheprovider   # each sanity check fires on its fault
uv run --offline --with pytest pytest 03-rai/hooks/tests -q -p no:cacheprovider   # hooks and memory routing
vale sync && vale --filter='.Name matches "^Rai"' draft.md   # the blocking prose set is empty
```

No CI: run these by hand. On 2026-10-06 the two test suites passed 366 and 81 tests.

## Layout

```
02-ana/         you: blank templates for identity (auto-loaded), journal, todos and more
03-rai/         the brain: skills, agents, hooks, memory, config
00-landing/     quick captures, promoted to the inbox or deleted
01-inbox/       research queue: each item enriched, rated and routed
05-projects/    project plans; code lives in its own repos
09-ideas/       ideas from seed to graduated project
10-knowledge/   topic notes and maps of content
11-workflows/   your way of doing each kind of work
12-system/      templates and the kit manual
docs/           README diagrams, feature tour
```

Work, learning, reading, the news digest and the archive have their own numbered folders.

## Docs

- [SETUP.md](SETUP.md): from zero to the first session, including renaming the assistant.
- [12-system/manual/README.md](12-system/manual/README.md): which live doc owns each topic.
- [03-rai/MEMORY-ARCHITECTURE.md](03-rai/MEMORY-ARCHITECTURE.md): capture, batch, injection,
  recall and self-evolve.
- [docs/features.md](docs/features.md): a tour of the skills, and the worked examples.
- [docs/diagrams/diagrams.py](docs/diagrams/diagrams.py): the scene script behind both diagrams.

## License

[MIT](LICENSE). Rai started as an adaptation of PAI v4.0.3 (Personal AI Infrastructure, by Daniel Miessler).
