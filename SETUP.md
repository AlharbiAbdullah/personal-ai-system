# Setup

From zero to your first session. Plan for about 15 minutes. None of this is hard. It's mostly
putting files in the right place and telling Claude Code where to look.

> **The short version:** clone this into `~/helm`, run `./setup.sh` to wire it into `~/.claude`,
> fill in the `02-ana/identity/` templates, and start Claude Code in `~/helm`.

---

## 0. Prerequisites

Install these first:

| Tool | Why | Check |
|------|-----|-------|
| [Claude Code](https://claude.com/claude-code) | The host this runs inside. Needs 2.1.277+, the first version that reads `AGENTS.md` natively | `claude --version` |
| Python 3.10+ | The hooks are Python (mostly stdlib) | `python3 --version` |
| [uv](https://github.com/astral-sh/uv) | Runs the vector-memory step in an isolated env | `uv --version` |
| git | Clone and track your vault | `git --version` |

> macOS uses zsh, Linux uses bash. Both work. The examples below are shell-agnostic.

---

## 1. Get the kit

Clone it to **`~/helm`** (the default path the system expects):

```bash
git clone <your-fork-url> ~/helm
cd ~/helm
```

> Want a different folder name? `03-rai/config/settings.json` and every hook under
> `03-rai/hooks/` hardcode `~/helm` (there is no environment variable to override it).
> If you use another path, you'll need to edit every `$HOME/helm/...` path in
> `settings.json`, the hook scripts and `03-rai/harness/claude-code/user-instructions.md`
> yourself, or identity will silently fail to load. For a first run, `~/helm` is the
> path of least resistance and the only path this kit is tested against.

---

## 2. Wire it into Claude Code

Claude Code reads its config from `~/.claude`. We point a few entries there at the brain in
`03-rai`. The repo ships a script that does the whole thing: back up what it would replace,
create the links, and verify.

```bash
cd ~/helm
./setup.sh
```

It's safe to re-run: links that are already correct are left alone, and anything it replaces is
moved to a timestamped `~/.claude/.pai-backup-*/` first. To check an existing setup without
changing anything, run `./setup.sh --check`.

<details>
<summary>Prefer to do it by hand? The exact commands the script runs.</summary>

```bash
# Back up an existing config if you have one
[ -e ~/.claude ] && cp -a ~/.claude ~/.claude.backup-$(date +%Y%m%d)

mkdir -p ~/.claude

# Link the brain into Claude Code (force-replaces only these specific entries)
ln -sfn  ~/helm/03-rai/harness/claude-code/user-instructions.md ~/.claude/CLAUDE.md
ln -sfn  ~/helm/03-rai/hooks                ~/.claude/hooks
ln -sfn  ~/helm/03-rai/skills               ~/.claude/skills
ln -sfn  ~/helm/03-rai/agents               ~/.claude/agents
ln -sfn  ~/helm/03-rai/config/settings.json ~/.claude/settings.json
```

</details>

That's the whole integration: identity, skills, agents, hooks, memory, settings, and the
status line now come from your vault.

---

## 3. Verify the wiring

`setup.sh` already runs these at the end. To re-check by hand:

```bash
./setup.sh --check             # all links should report OK
python3 ~/helm/03-rai/hooks/session-start.py >/dev/null && echo "hooks run OK"
uv run --python 3.12 --with chromadb python3 -c "import chromadb; print('chromadb OK')"
```

If those succeed, the machine side is done.

---

## 4. Make it yours (the important part)

`02-ana/` ships as blank templates. Until you fill them in, the assistant knows nothing about you:

1. **Identity** fill in every file in `02-ana/identity/`, replacing each `{placeholder}`. Start
   with `who-i-am.md`, `goals.md`, `projects.md`, and `tech-stack.md`. This is what auto-loads
   each session. It's the single highest-leverage thing you'll do.
2. **Personalize a few skills** (optional, do later):
   - News: `03-rai/skills/news-digest/config.yaml` plus the `REGION_SUBSTRINGS` / `REGION_BOUNDED`
     constants near the top of `present_v5.py`. Set your interests and region.
   - Writing voice: drop 3 to 5 samples of your writing into `02-ana/voice-samples/`.
3. **Fill in the rest** as you go: `02-ana/family/`, `health/` and `financial/budget.md` are
   templates too. The journal and day plans fill themselves as you use `/routine`. Elsewhere in
   the vault, the example notes (a project, a learning board, `north-star.md`) belong to a
   fictional user named John; overwrite or delete them.

> You don't have to do all of this up front. Identity first, the rest as you go.

---

## 5. (Optional) Rename the assistant

The assistant is called **Rai**. To rename it (e.g. to "Ava", "Jarvis", or your own):

```bash
# preview the matches first
grep -rl '\bRai\b' ~/helm/03-rai/identity ~/helm/03-rai/AGENTS.md
# then replace across the brain (pick your name)
grep -rl '\bRai\b' ~/helm/03-rai | xargs sed -i '' 's/\bRai\b/YourName/g'   # macOS
# (on Linux, use:  sed -i 's/\bRai\b/YourName/g')
```

The folder `03-rai` can keep its name. It's only a path.

---

## 6. First session

```bash
cd ~/helm
claude
```

Then ask it: **"Who am I, and what am I working on?"** If it answers from your identity files,
the auto-load is working and you're live. Try a skill next: `/research`, `/architecture`, or
`/news-digest`.

---

## 7. (Optional) Going further

- **Daily news digest** see [`03-rai/skills/news-digest/SKILL.md`](./03-rai/skills/news-digest/SKILL.md). Its
  collectors need a few Python packages. Install them with
  `pip install -r requirements.txt` (the core system needs none, they're all optional).
- **Spec-driven projects** run `/project-init` in a code folder (or `/project-init --plan` first
  to see what it would do without writing anything). It needs [mise](https://mise.jdx.dev), `uv`
  and `git`; `gh` and `git-cliff` are optional, and mise pins `gitleaks` for the repo. v3 ships
  the Python stack pack only. After it, `/grill` talks a feature into a spec and `/compile`
  builds it test-first. The full loop: [`11-workflows/21-project-init.md`](./11-workflows/21-project-init.md).
- **MCP servers** live in `~/.claude.json`, not in the vault. Register one per machine with
  `claude mcp add --scope user ...`; Context7 (current library docs) is a good first one.
- **Prose gate** install [Vale](https://vale.sh), then run `vale sync` once in `~/helm`. The
  `/writing` skills run it before delivering a draft.
- **Multiple machines** see [`03-rai/SYNC-ARCHITECTURE.md`](./03-rai/SYNC-ARCHITECTURE.md).
  Single machine? Ignore it.
- **Publishing your own fork publicly** uncomment the `02-ana/` and `03-rai/memory/` lines in
  `.gitignore` so your private life and accumulated memory stay out of the public repo.
- **Brain healthcheck** run `/map-updater` once (it builds the vault index), then
  `/rai process-sessions` after a few real sessions, then `/rai sanity --baseline`. Before that,
  expect red: [`03-rai/skills/rai/sanity.md`](./03-rai/skills/rai/sanity.md) "On a fresh kit"
  lists what fails and why.
- **Multi-model panel** `/fusion` (and the review step of `/compile`) runs six voices across
  agy, opencode, pi and Claude Code, each inside `bwrap`, in `tmux`, on your own
  subscriptions. Install the harnesses you have; a missing one is skipped. Name only `opus`
  for a Claude-only panel. Image generation (`/media → art`) uses agy on a Google account.

---

## Troubleshooting

- **Identity didn't load** confirm `~/.claude/CLAUDE.md` resolves to
  `~/helm/03-rai/harness/claude-code/user-instructions.md`
  and that `02-ana/identity/` has your `.md` files.
- **A hook errored on start** run it directly: `python3 ~/helm/03-rai/hooks/session-start.py`.
- **chromadb step fails** make sure `uv` is installed. The wrapper is
  `03-rai/semantic-memory/scripts/py-chroma.sh`.
- **Anything else** [`03-rai/skills/rai/sanity.md`](./03-rai/skills/rai/sanity.md) (brain health)
  and the [manual's pointer map](./12-system/manual/README.md) cover common failures in depth.

Welcome aboard. Make it yours.
