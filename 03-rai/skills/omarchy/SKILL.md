---
name: omarchy
description: >
  Omarchy (Arch + Hyprland) router. USE WHEN the user customizes the Linux
  desktop or system config on the Omarchy box: ~/.config/hypr/ (Lua keybinds,
  monitors, window rules, animations), ~/.config/omarchy/ (shell.json bar,
  plugins, idle/lock, hooks), terminals (ghostty, alacritty, foot, kitty),
  themes/backgrounds/fonts, screenshots/recordings, reminders, user-facing
  `omarchy` commands, or a process that crashed/segfaulted (coredumpctl).
  Routes between basics, hyprland, plugins, theming, hooks, capture,
  diagnose-crash, contributing.
---

# Omarchy

Omarchy-specific skills for the Linux daily driver (Omarchy 4, Arch + Hyprland,
migrated 2026-08-25). Sibling of `/ubuntu` (diagnostics,
bootstrap, tips; its Hyprland sub-skill is now pre-Omarchy reference only) and
`/mac`. Themes on the hub are stock Omarchy.

Sub-skill files are vendored from upstream
`/usr/share/omarchy/default/agents/skills/` (omarchy 4.0.4-1) so the vault stays
the only canonical home and the Mac can read them too. After `omarchy update`,
re-sync with `diff -r /usr/share/omarchy/default/agents/skills/omarchy/ .`
and copy over what changed. `basics.md` = upstream `SKILL.md` body;
`diagnose-crash.md` + `crash-reporting.md` = upstream `diagnose-crash/`.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Anything Omarchy: safety rules (never edit `/usr/share/omarchy/`), `omarchy` CLI discovery, config locations, refresh/reset, decision framework. Read FIRST for any task below | basics | `basics.md` |
| Hyprland Lua config: keybinds, monitors, window rules, animations, looknfeel | hyprland | `hyprland.md` |
| Omarchy shell (Quickshell): bar layout, widgets, plugins, notifications, idle/lock | plugins | `plugins.md` |
| Themes, backgrounds, fonts, custom theme overlays | theming | `theming.md` |
| Scripts on system events (theme-set, update, boot, low battery) | hooks | `hooks.md` |
| Screenshots, screen recordings, OCR capture, file sharing | capture | `capture.md` |
| A process segfaulted / aborted / dumped core; "why did X crash" | diagnose-crash | `diagnose-crash.md` (then `crash-reporting.md` only if it is Omarchy's bug) |
| Report an Omarchy bug or submit a fix upstream | contributing | `contributing.md` |

## How to use

1. Read `basics.md` (safety + CLI), then the sub-skill file by task shape.
2. Follow that file's instructions.
3. Hyprland edits: validate with `hyprctl reload` + `hyprctl configerrors`.

## When two could fit

- **omarchy vs ubuntu:** on the Omarchy box, this router wins for desktop/system config. `/ubuntu/hyprland` describes the old waybar/mako/fuzzel stack and is reference only; `/ubuntu/diagnostics` and `/ubuntu/tips` still apply (systemd, journal, hardware).
- **diagnose-crash vs /ubuntu/diagnostics:** diagnose-crash is one dead process from a core dump; diagnostics is the machine (thermal, memory, Wi-Fi, disk).
- **hooks vs /ubuntu/hyprland automation:** hooks run on Omarchy events; systemd user units / udev / cron stay in `/ubuntu`.

## Cross-references

- Ubuntu-era Hyprland sibling → `/ubuntu` (diagnostics, dotfiles bootstrap, tips)
- macOS sibling → `/mac` (theme system is a 1:1 port; single source of truth, do not fork). Palette reference library and per-theme app mappings live in `/mac → theme`.
- Omarchy facts from the migration (Lua config, Quickshell, pkg names, refresh clobbers user files) → keep them in Rai's memory
