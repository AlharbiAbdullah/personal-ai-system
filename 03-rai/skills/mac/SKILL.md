---
name: mac
description: >
  macOS router. USE WHEN the user wants theme management, Mac automation
  (Raycast, Keyboard Maestro, Shortcuts), hardware diagnostics, dotfiles
  bootstrap, or Mac power-user tips. Routes between theme, automation,
  diagnostics, dotfiles-bootstrap, tips.
---

# Mac

macOS-specific skills. For the Ubuntu/Hyprland daily driver, see the sibling
`/ubuntu/` router — same theme system, Linux-shaped tooling.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Audit / add / remove themes; verify app adapters | theme | `theme.md` |
| Automation (Shortcuts, Keyboard Maestro, Raycast, Hammerspoon) | automation | `automation.md` |
| Hardware diagnostics (thermal, memory, Wi-Fi, disk, USB) | diagnostics | `diagnostics.md` |
| Bootstrap a fresh Mac: Brew bundle, defaults write, dotfiles | dotfiles-bootstrap | `dotfiles-bootstrap.md` |
| Power-user tips: shortcuts, hidden defaults, niche features | tips | `tips.md` |

## How to use

1. Pick the sub-skill by task shape.
2. `Read` the file in this directory.
3. Follow that file's instructions.

## When two could fit

- **theme vs automation:** theme is appearance (colors, wallpapers, app adapters); automation is behavior (triggers, macros, scripts).
- **automation vs tips:** automation authors new workflows; tips is a reference catalog of native features.
- **dotfiles-bootstrap vs theme:** bootstrap is full-machine setup; theme is swapping appearance on an already-configured machine.

## Cross-references

- Omarchy sibling → `/omarchy/` (the Linux box since 2026-08-25; Arch + Hyprland Lua + Quickshell)
- Ubuntu/Hyprland sibling → `/ubuntu/` (shares `references/omarchy-palettes.toml` + `references/app-mappings.toml` from this folder — single source of truth)
- Shell + terminal configs (WezTerm, Starship) → covered in `theme` + `dotfiles-bootstrap`
