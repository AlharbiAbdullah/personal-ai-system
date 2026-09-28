---
name: dotfiles-bootstrap
description: >
  The "spilled coffee" skill for Linux: restore the full Omarchy environment
  from scratch. USE WHEN setting up a fresh Omarchy machine, recovering from
  disaster, or auditing what the current machine has that a rebuild would
  miss.
---

# Dotfiles Bootstrap (Omarchy)

Assume this machine is gone. The bootstrap is not a script you write on the day of the
disaster: it is a dotfiles repo you keep current, `~/dev-env/linux/omarchy/` in this layout.
Sibling of `/mac/dotfiles-bootstrap`: same philosophy, pacman instead of brew.

## Philosophy

- **Declarative**: package lists + one idempotent script describe the machine
- **Idempotent**: running it twice does no harm (`install.sh` checks before every step)
- **Version-controlled**: `~/dev-env` is a git repo, pushed to a private remote
- **Secrets separate**: never commit keys, tokens, SSH identities; restore them manually or via `restore-backup.sh`

## The layout: `~/dev-env/linux/omarchy/`

```
install.sh              entry point (idempotent; guards on pacman + /usr/share/omarchy)
restore-backup.sh       creds, repos, docker volumes
packages/pacman.txt     pacman package list
packages/aur.txt        AUR package list
config/                 -> ~/.config/ (hypr, omarchy, tmux, mise, Code/Cursor, etc.)
etc/                    -> /etc (sudoers.d, udev rules, polkit rules, systemd overrides)
systemd/                -> ~/.config/systemd/user/ (news, rai-maintenance, and your own timers)
theme, theme-render, new-window   -> ~/.local/bin/
starship.toml, .bashrc  -> matching dotfiles
claude-config.sh        Claude Code symlinks into the vault + MCP registration (e.g. Context7)
GUIDE.md                fresh-box narrative walkthrough (readable before the vault exists)
README.md               quickstart
```

`install.sh` order:

1. sudoers.
2. `gh auth` + clone the vault.
3. pacman/AUR packages, Ghostty, your password manager, Chrome policy dirs.
4. configs (bashrc, starship, full `config/` tree, tmux).
5. fonts.
6. themes (`common/themes/` -> `~/.config/themes/`, `theme-render`, initial `omarchy theme set`).
7. dev tools (mise for Node/gh/claude, uv + a `common/uv-tools.txt` list of real CLIs).
8. Claude Code install + `claude-config.sh`.
9. system units (udev rules, polkit rules, uinput/i2c-dev modules, group memberships, `paccache.timer`, ufw).
10. systemd user units (news-daily/weekly/x-collect, rai-maintenance, your own timers), armed last. `ENABLE_TIMERS=0` stages them without arming, for a side-by-side cutover.

## Quickstart

```bash
gh auth login && git clone <your-dotfiles-repo> ~/dev-env
cd ~/dev-env/linux/omarchy && ENABLE_TIMERS=0 ./install.sh && ./restore-backup.sh
```

Then the manual logins `install.sh` prints at the end: reboot once; `claude` browser login +
the claude-hud plugin; password manager + `gh` auth; Chrome sign-in, including the x.com,
substack.com and medium.com cookies the news collectors read; Obsidian sync re-pair;
`omarchy update`.

## Rebuild inventory (what this machine actually runs)

| Layer | Items |
|---|---|
| Desktop | Hyprland (Lua config), Omarchy's Quickshell (bar, launcher, notifications, idle/lock: no waybar/mako/fuzzel/hypridle.conf/hyprlock.conf) |
| Screenshot/clipboard | grim, slurp, wl-clipboard |
| Media/brightness keys | wpctl (pipewire), ddcutil (DDC/CI: user must be in `i2c` group) |
| Terminal | Ghostty (Omarchy default), tmux + starship |
| Python | uv (via mise), plus `common/uv-tools.txt` real CLIs |
| Theme system | `~/.local/bin/theme` + `theme-render`, `~/.config/themes/` (from `~/dev-env/common/themes/`): see `/ubuntu -> theme` |
| Apps | google-chrome, obsidian, code/cursor, gh, your password manager |
| Vault | `~/helm` + Claude Code symlinks (`claude-config.sh`) |

## What to keep separate (NOT in dev-env)

- SSH/GPG private keys -> password manager + `restore-backup.sh`
- API tokens -> password manager, never a plaintext rc export
- Browser profile -> Chrome sync

## Verification checklist

After running `install.sh` + `restore-backup.sh`:
- [ ] `omarchy-menu toggle apps` (SUPER+SPACE) opens; Quickshell bar is up
- [ ] `theme list` shows every theme; switching updates border + Ghostty + Cursor/VS Code + tmux + starship
- [ ] SUPER+1..0 snaps between workspaces instantly
- [ ] Screenshot binds land in the clipboard
- [ ] SUPER+L locks; volume keys work; brightness keys move the monitor (i2c group active: needs relog)
- [ ] `uv --version` works; `mise ls` shows the pinned tools
- [ ] Git commits work (name + email); `gh auth status` green
- [ ] Claude Code reads the vault; skills resolve; MCP servers registered (`claude mcp list`)
- [ ] Obsidian opens the vault
- [ ] `systemctl --user list-timers` shows news-daily/weekly/x-collect and rai-maintenance armed

## Anti-patterns

- Secrets in `~/dev-env` (git-tracked, pushed)
- Editing live `~/.config` instead of the `dev-env` source: drift is the killer; `omarchy update` also resets anything you edited in place under `/usr/share/omarchy`
- Not regenerating `packages/pacman.txt` / `aur.txt` from `pacman -Qe`: the list rots
- Testing only on the live machine: rehearse the rebuild on a spare box or VM before you need it

## Examples

- "This box died, walk me through the rebuild"
- "What's installed here that dev-env would miss?"
- "Set up a second Omarchy laptop to match this one"
- "Add a new package to the pacman/AUR list"
