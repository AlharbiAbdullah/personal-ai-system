# Machines

**Use when:** changing something on a machine: an app, a package, a key, a shell or editor setting, a timer, a desktop behaviour. Also mirroring a change to the other machine, and standing up a machine: a fresh box, a reinstall, a restore, the incoming laptop.
**Not for:** `25 incident` (something on a machine broke). `24 changing Rai` (a skill, hook, agent, memory path or Rai's scheduled job). `26 purchase` (buying the hardware).
**Done when:** the change runs live on the hub, proven from config and state, and is declared in dev-env. The other machine matches it or holds a line in the parity queue. A stood-up machine passed its day-2 timer check.

Three modes: change a machine, mirror the change 1:1, stand up a machine. The hub (the Omarchy desktop) is the primary machine and the only GitHub writer. The other machine is a laptop, a pull-only replica.

```d2
direction: right

change: "Change a machine\n1-6: declined record, explain,\nOmarchy first, verify, declare"
mirror: "Mirror 1:1\n7-9: queue, translate,\nverify on the target"
setup: "Stand up a machine\n10-13: back up, install,\nrestore, day 2"

change -> mirror: "same turn"
setup -> change: "then every change\nruns 1-9"
```

---

## Steps

Change a machine: steps 1 to 6. Mirror it: steps 7 to 9. Stand up a machine: steps 10 to 13, after which every change runs 1 to 9. Themes and wallpapers are stock Omarchy: nothing to roll out.

### 1. Change: check the declined record

- [ ] Before proposing anything, check the record of declined items: the never-re-pitch rulings in Rai's memory and the last machine audit.
- [ ] A declined item is never pitched again. When he raises it himself, answer from the record.

### 2. Change: explain, then wait

- [ ] Two lines: what it is and why. Then 2 or 3 numbered options, the (Recommended) one first with a one-clause reason. Then stop until he answers.
- [ ] One item per turn, with a go or no-go between items, even when the item is already agreed.
- [ ] Defaults stay until he finds a use for a change. A question about a setting is not a request to change it, and "investigate only" means change nothing.
- [ ] Stable over beta, and the official way over a custom one.

### 3. Change: Omarchy first

- [ ] The Omarchy default beats a hand-rolled override, and Omarchy wins every overlap.
- [ ] Config goes in the user Lua files under `~/.config/hypr/`, never under `/usr/share/omarchy`. Most `.conf` files in that folder are dead: check one is live before editing it.
- [ ] Hyprland takes Lua: `hyprctl eval 'hl.config({...})'` and `hl.dsp.*` dispatchers. `hyprctl keyword` is dead.
- [ ] After a big Omarchy update, diff the user Lua files against `/usr/share/omarchy/config/hypr/`. `omarchy refresh hyprland` overwrites them.

### 4. Change: keys, editors, secrets, sync

- [ ] Keys: Super or Ctrl (with Shift) for the system, Alt plus one letter to launch an app, the same on both machines. Write the modifiers as words.
- [ ] A new key goes into `~/dev-env/KEYBINDINGS.md` and dev-env first, then live. That file feeds the Super+K sheet. Check `hyprctl binds -j` for a collision first.
- [ ] Editor keys are Ctrl only. Web-app binds never take focus, with Obsidian the one exception.
- [ ] VS Code and Cursor are both his IDEs: an install in one is an install in both. One extension list (`common/editor-extensions.txt`) and one settings file (`common/vscode/settings.json`) serve both. One setting per turn.
- [ ] A new secret goes into your secret manager first, then an rc line that loads it into the environment (for 1Password, `op read 'op://…'`) in the untracked `.local` rc. Never into a tracked file, a Brewfile, an `.example` or a unit. A scheduled unit calls `op read` itself.
- [ ] A privileged edit: Rai writes the content to a temp file, and he runs one short `sudo bash <file>` line. Sudo and passwords stay his.
- [ ] An edit the classifier blocks (settings.json hooks or permissions) goes to him as [[24-changing-rai]] step 9 says. Run a destructive command as one plain command with absolute paths.
- [ ] A new Syncthing folder: write its `.stignore` first. Configure through `syncthing cli config`, and never print `config.xml`.

### 5. Change: verify without stealing focus

- [ ] Never launch a GUI app, a web app or a browser window mid-session. Verify from config and state: the `.desktop` file, `hyprctl clients -j`, `hyprctl binds -j`, the script source.
- [ ] Shell and terminal changes: test the real path in a real PTY (`script -qc 'bash -i' /dev/null`). Test Ghostty keybinds with `ghostty +show-config` under a throwaway `XDG_CONFIG_HOME`.
- [ ] A dead bind: run its command by hand and look for the Lua parse error.
- [ ] Only a launch can prove it: ask first, or hand him the one command. From SSH, launch through `systemd-run --user --scope`.
- [ ] Cursor ignores some shared settings, so he checks Cursor's behaviour in the app.
- [ ] Timers and units go to the `sre` agent. Inputs: the job, its schedule, the units in `~/dev-env/linux/omarchy/systemd/`. It writes the `.timer` and `.service` pair in dev-env with the `OnFailure=alert@%N.service` guard. It returns the proof it fires: the next run in `systemctl --user list-timers`, then the service's journal after the first run.
- [ ] A oneshot unit is done when `systemctl --user show -p ActiveState` says so, not `is-active`.
- [ ] The `qa-tester` agent runs the live check. Inputs: the change list and the target machine. It returns one PASS or FAIL row per item with evidence from config and state. It cannot edit files and launches no GUI app.
- [ ] Rai re-checks every FAIL, every PASS the change rests on, and every unit the `sre` agent wrote.

### 6. Change: declare it in dev-env

- [ ] Update the list the change belongs to, in the same change: `linux/omarchy/packages/pacman.txt` or `aur.txt`, `mac/Brewfile`, `common/uv-tools.txt`, `common/editor-extensions.txt`, `common/vscode/settings.json`, or the tracked config under `linux/omarchy/config/`.
- [ ] A tool that runs but is not declared is not done.
- [ ] Project tools (ruff, ty, marimo) and libraries go per project with `uv add --dev` or `uv add`, never into the uv tools list.
- [ ] dev-env commits happen on the hub only, and only when he says. Never run git on one repo from both machines at once.
- [ ] Add the mirror step to the parity queue in the same turn.
- [ ] Record the change in the declared dev-env list. A change that settles a decision also gets a memory ruling with its revert line.

### 7. Mirror: queue it and reach the other machine

- [ ] Every add or remove on one machine is mirrored on the other, 1:1. The other machine is the laptop.
- [ ] The target is asleep: add one line to the parity queue below (what, source machine, date). Remove it once the port runs live there.
- [ ] Tailscale shows a sleeping machine as offline. Check local reachability before calling it down.
- [ ] Vault files reach the other machine through the coordinator. Never hand-copy them.

### 8. Mirror: translate, never blind-copy

- [ ] Read the live config on the source machine, not a memory or an older repo copy.
- [ ] Map every divergence before touching the target:
  - Shell: the Mac stays zsh and the hub bash; never zsh on the hub. The hub carries the alias superset.
  - Scheduler: a launchd plist becomes a systemd `.timer` and `.service` pair, and back.
  - Window manager: AeroSpace and Hammerspoon on the Mac, Hyprland on the hub.
  - Packages: `mac/Brewfile` against `pacman.txt` and `aur.txt`.
  - Paths: `/Users/...` and `~/Library/...` against `/home/...` and `~/.config/...`.
- [ ] Auth is per machine. Each machine logs in itself: Claude, opencode, `gh`. Never copy an OAuth token or a cookie jar. A static API key comes from 1Password.
- [ ] Parity means the same capability, not identical bytes. A deliberate divergence gets one note next to the change.

### 9. Mirror: work on the Mac over SSH

- [ ] Check the PATH and aliases with `zsh -ic`. A plain `ssh mac` command does not read `.zshrc`.
- [ ] Move files to `~/.Trash/<tag>` instead of a bulk `rm -rf`.
- [ ] Sudo and Finder steps cannot run over SSH: hand him that list first, so he runs them in parallel.
- [ ] Removing a launchd job: `launchctl bootout` first, then kill the process, then `rm`. Prove it with `launchctl list | grep <label>`.
- [ ] Keep destructive and non-destructive steps in separate SSH scripts.
- [ ] Verify on the target with the `qa-tester` agent as in step 5, then delete the queue line.

### 10. Stand up: prepare first

- [ ] The live machine is the source of truth, not a repo copy or a memory. Back-sync its live configs into dev-env first: the repo drifts.
- [ ] Back up first: the offsite backup holds the synced folders and the vault. Its credentials live in your secret store.
- [ ] A rotated backup credential goes into the secret store the same day.
- [ ] What the backup skips (credentials, dotfiles, app state, the `/etc/` pieces) moves by your dotfiles repo's own backup script.
- [ ] Follow the checklist from the last stand-up's retrospective, phase by phase.
- [ ] Replacing a box: quiesce the old one last, its timers off and its last commits pushed (`quiesce-ubuntu.sh`). One machine writes the vault and ChromaDB.

### 11. Stand up: install and restore

- [ ] Run `~/dev-env/linux/omarchy/install.sh`. With `ENABLE_TIMERS=0` it stages the units without arming them.
- [ ] The laptop runs none of the hub's timers: the hub alone runs the scheduled jobs.
- [ ] Reinstalling or restoring an existing box: run `restore-backup.sh` before `tailscale up`, so the box keeps its tailnet identity.
- [ ] From the offsite backup: install the backup tool, configure it with the credentials from the secret store, list the snapshots and restore the latest.
- [ ] `gh auth login` is his: a browser login. The git credential helper points at the mise shim `~/.local/bin/gh`. Never run bare `gh auth setup-git`: it pins a versioned path that mise later prunes.
- [ ] After a restore, `git fetch` and `git reset origin/main` any repo whose `.git` rolled back, then commit the leftovers.
- [ ] Run `git branch -vv` on every repo and restore any lost upstream tracking.
- [ ] Clear the old host key on the other machine with `ssh-keygen -R`.
- [ ] `~/.claude/skills` and `~/.agents/skills` are each one symlink to `03-rai/skills`, never a real folder.
- [ ] Grep for stale absolute home paths: `grep -rl '/Users/john' ~/.claude/ ~/.claude.json ~/.config/ ~/.local/bin/`.

### 12. Stand up: the steps he does by hand

- [ ] Logins no script can do: Claude, 1Password and its SSH agent, `gh`, opencode, Chrome and the news sites.
- [ ] Obsidian Sync: he re-pairs it, then `"cli": true` goes into `obsidian.json` with the app closed.
- [ ] Per machine, never synced: Context7 in `~/.claude.json` (`claude-config.sh` registers it), `git config --global init.defaultBranch main`, the Ghostty start folder, the Claude Code view dragged into the VS Code side bar.
- [ ] Run `cursor --list-extensions` against `common/editor-extensions.txt` before assuming the toolchain is there.

### 13. Stand up: day 2

- [ ] Read `journalctl --user -u <service>` for every timer's service after its first run. An armed timer proves nothing.
- [ ] The `sre` agent may walk the list. Inputs: `systemctl --user list-timers` and each service's journal. It returns one row per timer: the last run, the exit code, whether its output exists. It writes nothing. Rai re-checks every row that is not clean.
- [ ] A timer misfires on its first run: check the restore steps above before debugging the job.

### 14. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Parity queue

When the target machine is asleep, add one line here: what, source machine, date queued. Remove it once the port runs live on the target.

- (empty)

---

## Connections

- Desktop: `/omarchy → hyprland`, `/omarchy → basics`. Scheduler translation: `/mac → automation`. Fresh-box bootstrap: `/ubuntu → dotfiles-bootstrap`, `/mac → dotfiles-bootstrap`.
- Agents: the `sre` agent at steps 5 and 13, the `qa-tester` agent at steps 5 and 9.
- Files: `~/dev-env` (one checkout per machine, the working tree synced by Syncthing), `~/dev-env/KEYBINDINGS.md`, `03-rai/SYNC-ARCHITECTURE.md` (roles, Syncthing, the single writer).
- Records: the last machine audit in `13-archive/audits/` (keeps and declines) and the retrospective of the last stand-up.
- Workflows: [[25-incident]] when something broke, [[26-purchase]] for the hardware.
