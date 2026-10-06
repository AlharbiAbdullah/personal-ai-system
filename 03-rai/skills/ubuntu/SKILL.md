---
name: ubuntu
description: >
  Ubuntu/Linux router. USE WHEN the user wants Hyprland desktop config, Linux
  automation (systemd units, udev, cron), hardware diagnostics, dotfiles
  bootstrap, or Linux power-user tips. Routes between hyprland,
  diagnostics, dotfiles-bootstrap, tips.
---

# Ubuntu

Linux-specific skills for the Omarchy hub (Ubuntu 26.04 LTS until the
2026-08-25 migration to Omarchy 4). Sibling of `/mac`, Linux-shaped tooling.
For desktop/system config and themes (stock Omarchy), use `/omarchy` first;
this router keeps diagnostics, bootstrap, and tips
(plus a pre-Omarchy Hyprland reference under `hyprland.md`).

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Linux automation: systemd user units / cron / udev; pre-Omarchy Hyprland reference (classic hyprland.conf, waybar, mako, fuzzel) | hyprland | `hyprland.md` |
| Hardware diagnostics (thermal, memory, Wi-Fi, disk, USB, journal) | diagnostics | `diagnostics.md` |
| Bootstrap a fresh Omarchy box from scratch (`~/dev-env/linux/omarchy/install.sh`) | dotfiles-bootstrap | `dotfiles-bootstrap.md` |
| Power-user tips: shell, Wayland clipboard, pacman, systemd | tips | `tips.md` |

## How to use

1. Pick the sub-skill by task shape.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **hyprland:** reference-only for its pre-Omarchy config syntax; its systemd/cron/udev automation content still applies.
- **hyprland vs tips:** hyprland's live content today is automation (systemd/cron/udev); tips is a reference catalog of native features.

## Cross-references

- Omarchy sibling → `/omarchy` (Lua Hyprland, Quickshell shell, themes, hooks, crash diagnosis; wins on the Omarchy box for desktop/system config)
- macOS sibling → `/mac`
- Docker / Kubernetes / CI → `/devops`
- Security hardening → `/security`
