# Cross-Machine Parity

**Triggered by:** "do it on the mac too" / "mirror to the other machine" / "set up on both boxes"
**Cadence:** Per tool, and per add or remove. Ruling 2026-09-09: every add or remove on one machine is mirrored on the other, 1:1.
**Done when:** the tool/config works **LIVE on both machines**, with OS divergences correctly translated (not blind-copied), and the declared lists in `~/dev-env` say so.

The two machines are the Omarchy hub (desktop, primary, sole vault committer) and the Mac (mobility). Each port keeps re-litigating the same OS-divergence + sync-direction lore, and that is exactly where the mistakes happen. This playbook freezes that lore into gates so a port is a checklist, not a re-derivation. When the other machine is asleep, the port goes into this playbook's own Mac parity queue (below) and is applied when it wakes.

```
Delta gate → Read source → Port w/ translation → Declare in dev-env → Single-writer gate → Verify LIVE → Leave for coordinator
```

> **Two gates carry the whole value.** The DELTA GATE stops blind copies (Mac zsh ≠
> hub bash; launchd ≠ systemd). The SINGLE-WRITER GATE stops the Mac from pushing.
> Source of truth: `03-rai/SYNC-ARCHITECTURE.md`.

## Mac parity queue

Empty. When the target machine is asleep, add one line here (what, source machine, date queued); remove it once the port lands live on the target. This queue lives in this playbook.

---

## Steps

### 1. Delta gate — enumerate what diverges BEFORE porting

- [ ] **Shell**: Mac = zsh ↔ hub = bash. **NEVER set up zsh on the hub.** Target
      `.bashrc` (Omarchy skel shape, Omarchy defaults win) / starship-bash / `fzf --bash`.
      A `.zshrc` copied to the hub is a bug.
- [ ] **Terminal**: Ghostty on both. iTerm2 on the Mac only for Arabic (Ghostty is LTR-only).
- [ ] **Window manager**: AeroSpace (Mac, Cmd-based tiling) ↔ Hyprland under Omarchy (Lua config, Quickshell bar).
- [ ] **Scheduler**: launchd (Mac) ↔ systemd timers (hub). A launchd plist has no
      meaning on Linux; it becomes a `.timer` + `.service` unit.
- [ ] **Package manager**: Homebrew `Brewfile` ↔ `pacman.txt` + `aur.txt`. Shared as a tool on both machines: mise (each machine keeps its own live `~/.config/mise/config.toml`, not a synced dev-env file), uv tools (`common/uv-tools.txt`), editor extensions (`common/editor-extensions.txt`).
- [ ] **Paths**: `~/Library/...`, `/Users/...` (Mac) ↔ `~/.config/...`, `~/.local/...`,
      `/home/...` (hub). Map every absolute path.

> **Decision Point**: is this config genuinely 1:1, or does one side need a translated
> equivalent?
> - Pure data (themes, dotfile values, vault content) → ports nearly straight.
> - OS-bound mechanism (scheduler, WM, terminal, shell) → translate, don't copy. Write
>   the divergence down in this step before touching the target.

### 2. Read the source machine's config

- [ ] Read the working config on the machine where it already runs. Do not port from
      memory or from the repo if the live file is newer.
- [ ] For desktop look-and-feel work, route through **`/mac → theme`** or
      **`/omarchy → theming`** so the full adapter set is in view. Every themed app follows
      `theme.lua` hex-for-hex; the `theme-set` hook generates the colours. **Obsidian is EXCLUDED, pinned.**

### 3. Port to the target with translation (not a blind copy)

- [ ] Apply the step-1 deltas: rewrite paths, swap shell idioms, convert the scheduler
      unit (launchd plist → systemd `.timer`+`.service` via **`/omarchy`**, or the
      reverse via **`/mac → automation`**).
- [ ] Desktop config: drive it with **`/omarchy → theming`** / **`/omarchy → hyprland`**
      (or the Mac equivalents). Themes live in `~/dev-env/common/themes/` and regenerate per machine.
- [ ] Ghostty reloads via SIGUSR2; **JankyBorders needs a full restart**.

> **Decision Point**: did the target gain something the source lacks (e.g. a systemd
> `RECOVERY=1` env, a bar module with no Mac analog)? That's allowed: 1:1 is about
> *parity of capability*, not byte-identical files. Note the intentional divergence.

### 4. Declare it in dev-env

- [ ] `~/dev-env` is the one checkout, Syncthing-mirrored to both machines. Update the declared
      list the port belongs to (`Brewfile`, `pacman.txt`/`aur.txt`, mise, uv-tools, editor-extensions)
      in the same change. A tool that runs but is not declared is not ported.
- [ ] Commit in dev-env from whichever machine made the change. Never commit the same repo on both machines at once.

### 5. Single-writer gate (the one that bites)

- [ ] Confirm the sync direction: **the hub is the SOLE coordinator and ONLY origin
      writer** for helm. The Mac is a **passive replica**.
- [ ] **The Mac NEVER `git push` helm.** If you ported a vault file from the Mac side,
      its churn stays local for the coordinator's next run. Source: `03-rai/SYNC-ARCHITECTURE.md`.
- [ ] Reaching the hub to apply or verify the port: **keyless SSH**,
      never GitHub round-trips from the Mac.

### 6. Verify the tool runs LIVE on the target

- [ ] **The file landing is NOT "done."** Run the tool on the target machine and watch it
      work: reload the WM/terminal, fire the timer, source the shell, open the app.
- [ ] Scheduler ports: confirm the unit is enabled + the next run is scheduled (e.g.
      `systemctl --user list-timers` for the news timers `news-daily.timer` /
      `news-weekly.timer`); a `RECOVERY=1` manual run via
      `03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh` proves it end-to-end.
- [ ] Theme/desktop ports: eyeball it live, palette applied, border restarted, no stark
      foreground (~75–82% brightness floor).

### 7. Sync (leave for the coordinator)

- [ ] Vault edits stay **local** on the Mac. The hub coordinator commits + pushes
      at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` helm from the Mac**: single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.
- [ ] If the port lives in a **code project** under `~/projects/` (not the vault), that's
      the one case you commit it yourself: run **`/git → commit`** there.

---

## Connections

- Desktop adapters: `/mac → theme`, `/omarchy → theming`, `/omarchy → hyprland`
- Scheduler translation: `/omarchy`, `/mac → automation`
- Dotfiles bootstrap on a fresh box: `/mac → dotfiles-bootstrap`, `~/dev-env/linux/omarchy/install.sh`
- Single-writer sync (read this before any cross-machine edit): `03-rai/SYNC-ARCHITECTURE.md`
- Dev-env: `~/dev-env` (one checkout, Syncthing-mirrored)
- Code-project port (the one that DOES commit): `/git → commit`
