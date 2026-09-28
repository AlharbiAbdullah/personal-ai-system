---
name: ubuntu
description: >
  Ubuntu/Linux router. USE WHEN the user wants theme management (theme.lua,
  the `theme` switcher, app adapters), Hyprland desktop config, Linux
  automation (systemd units, udev, cron), hardware diagnostics, dotfiles
  bootstrap, or Linux power-user tips. Routes between theme, hyprland,
  diagnostics, dotfiles-bootstrap, tips.
---

# Ubuntu

Linux-specific skills for the Omarchy hub (Ubuntu 26.04 LTS until the
2026-08-25 migration to Omarchy 4). Sibling of `/mac` — same idea, same theme
system, Linux-shaped tooling. For desktop/system config, use `/omarchy` first;
this router keeps the shared theme switcher, diagnostics, bootstrap, and tips
(plus a pre-Omarchy Hyprland reference under `hyprland.md`).

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Audit / add / remove themes; verify app adapters | theme | `theme.md` |
| Linux automation: systemd user units / cron / udev; pre-Omarchy Hyprland reference (classic hyprland.conf, waybar, mako, fuzzel) | hyprland | `hyprland.md` |
| Hardware diagnostics (thermal, memory, Wi-Fi, disk, USB, journal) | diagnostics | `diagnostics.md` |
| Bootstrap a fresh Omarchy box from scratch (`~/dev-env/linux/omarchy/install.sh`) | dotfiles-bootstrap | `dotfiles-bootstrap.md` |
| Power-user tips: shell, Wayland clipboard, pacman, systemd | tips | `tips.md` |

## How to use

1. Pick the sub-skill by task shape.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **theme vs hyprland:** theme is the live Omarchy theme pipeline (colors, wallpapers, app adapters). hyprland is now reference-only for its pre-Omarchy config syntax; its systemd/cron/udev automation content still applies.
- **hyprland vs tips:** hyprland's live content today is automation (systemd/cron/udev); tips is a reference catalog of native features.
- **dotfiles-bootstrap vs theme:** bootstrap is full-machine setup; theme is swapping appearance on an already-configured machine.

## Cross-references

- Omarchy sibling → `/omarchy` (Lua Hyprland, Quickshell shell, themes, hooks, crash diagnosis; wins on the Omarchy box for desktop/system config)
- macOS sibling → `/mac` (theme system is a 1:1 port; palette reference library and per-theme app mappings live in `/mac → theme`)
- Docker / Kubernetes / CI → `/devops`
- Security hardening → `/security`
