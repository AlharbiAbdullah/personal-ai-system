---
name: hyprland
description: >
  Reference for the pre-Omarchy Hyprland + Wayland desktop stack (classic
  hyprland.conf, waybar, mako, fuzzel). Also covers Linux automation (systemd
  user units, timers, cron, udev rules), which still applies today. On the
  Omarchy box, current keybinds, animations, window rules and monitors go
  through `/omarchy → hyprland` (Lua config) instead.
---

# Hyprland & Desktop Automation (pre-Omarchy reference)

**On the Omarchy box, use `/omarchy → hyprland` for keybinds, animations,
window rules and monitors** (`~/.config/hypr/*.lua`, applied with `hyprctl
reload`). The stack below (classic `hyprland.conf`, waybar, mako, fuzzel,
WezTerm) is the pre-Omarchy Ubuntu setup. It is kept as reference for the
syntax and for systemd/udev/cron automation patterns, which still apply
unchanged.

The desktop is config-as-code. Everything lives in dotfiles; `hyprctl` applies
live; `hyprctl reload` re-reads the file.

## The stack on this machine

| Concern | Tool | Config |
|---|---|---|
| Compositor / WM | Hyprland | `~/.config/hypr/hyprland.conf` |
| Status bar | waybar | `~/.config/waybar/` |
| Notifications | mako | `~/.config/mako/config` |
| Launcher | fuzzel (SUPER+D) | `~/.config/fuzzel/fuzzel.ini` |
| Idle / lock | hypridle / hyprlock | `~/.config/hypr/hypridle.conf`, `hyprlock.conf` |
| Wallpaper | swaybg (managed by `~/.local/bin/theme`) | — |
| Screenshots | grim + slurp + wl-copy | binds in hyprland.conf |
| Terminal | WezTerm | `~/.wezterm.lua` |

The Hyprland config is a 1:1 mirror of the Mac AeroSpace setup (cmd → SUPER).
When adding binds, keep that parity in mind.

## Hyprland workflow

1. **Edit** `~/.config/hypr/hyprland.conf` (minimal diff, keep the section banners).
2. **Apply**: `hyprctl reload` (also bound to SUPER+SHIFT+R).
3. **Verify**: `hyprctl binds | grep ...`, `hyprctl getoption <section:option>`.
4. For one-off live experiments without touching the file: `hyprctl keyword <option> <value>`.

### Current bind map (keep this updated when binds change)

- `SUPER + 1..0` — workspace 1..10 (instant: `animation = workspaces, 0`)
- `SUPER + SHIFT + 1..0` — move window to workspace
- `SUPER + arrows` / `SUPER + SHIFT + arrows` — focus / move window
- `SUPER + return` wezterm · `SUPER + N` new-window · `SUPER + B` chrome · `SUPER + O` obsidian · `SUPER + D` fuzzel
- `SUPER + W` kill · `SUPER + F` fullscreen · `SUPER + SHIFT + space` float
- `SUPER + H` focus mode (Omarchy-style: float + center active, dim rest; toggle — via `~/.local/bin/focus-mode`) · `SUPER + minus/equal` narrower/wider, stays centered
- `ALT + slash` togglesplit · `ALT + comma` togglegroup · `ALT +/-` resize
- `CTRL + 3` full screenshot → clipboard · `CTRL + 4` region → clipboard · `Print` full → ~/Pictures
- `SUPER + CTRL + T` theme cycle · `SUPER + CTRL + W` wallpaper next
- `SUPER + SHIFT + R` reload · `SUPER + L` hyprlock
- `XF86Audio*` volume/mute via wpctl (`bindel`/`bindl` — repeat + lock-screen) · `XF86MonBrightness*` via `ddcutil --noverify setvcp 10 ± 10` (DDC/CI; plain `bind`, no repeat — each write ~200ms)
- `ALT + SHIFT` toggles the us/second layout

### Useful hyprctl commands

```bash
hyprctl reload                 # re-read config
hyprctl binds                  # live keybinds
hyprctl clients                # all windows + class/title (for windowrules)
hyprctl activewindow           # focused window details
hyprctl monitors               # outputs, modes, scale
hyprctl workspaces             # workspace state
hyprctl getoption general:gaps_in
hyprctl keyword general:gaps_in 5      # live, not persisted
hyprctl dispatch workspace 3           # scriptable dispatchers
```

### Window rules

Get the class first: `hyprctl clients | grep -B5 -i <app>`. Then:

```ini
windowrulev2 = float, class:^(pavucontrol)$
windowrulev2 = workspace 5, class:^(obsidian)$
windowrulev2 = opacity 0.95, class:^(org.wezfurlong.wezterm)$
```

### Animations philosophy (settled — don't regress)

Workspace transitions are **instant** (`animation = workspaces, 0`). Window
open/close/fade kept subtle at speed 2. John hates sluggish transitions;
never re-enable workspace slide.

### Monitors

```ini
monitor = ,preferred,auto,1          # current: any output, native, scale 1
monitor = eDP-1,2880x1800@90,0x0,2   # example HiDPI pinned config
```

`hyprctl monitors` for names. Fractional scale (1.25/1.5) works but check
XWayland blur; prefer integer scale.

## Automation (Linux equivalents of Raycast/KM/Hammerspoon)

| Need | Tool |
|---|---|
| Run on schedule | **systemd user timer** (preferred) or cron |
| Run at login / on session start | `exec-once` in hyprland.conf, or systemd user unit |
| React to hardware events | **udev rules** (`/etc/udev/rules.d/`) |
| React to window/workspace events | **Hyprland IPC socket** (socat listener) |
| Quick launcher actions | **fuzzel** in dmenu mode (`fuzzel --dmenu`) |
| Hotkey → script | `bind = ..., exec, <script>` in hyprland.conf |

### systemd user unit + timer (the default answer)

```bash
# ~/.config/systemd/user/foo.service
[Unit]
Description=Do the thing
[Service]
Type=oneshot
ExecStart=%h/.local/bin/foo

# ~/.config/systemd/user/foo.timer
[Unit]
Description=Run foo hourly
[Timer]
OnCalendar=hourly
Persistent=true
[Install]
WantedBy=timers.target
```

```bash
systemctl --user daemon-reload
systemctl --user enable --now foo.timer
systemctl --user list-timers
journalctl --user -u foo.service -e
```

### Hyprland event-driven scripts

```bash
socat -U - UNIX-CONNECT:$XDG_RUNTIME_DIR/hypr/$HYPRLAND_INSTANCE_SIGNATURE/.socket2.sock |
while read -r line; do
  case "$line" in
    workspace\>\>*) echo "switched to ${line#workspace>>}" ;;
    activewindow\>\>*) ... ;;
  esac
done
```

Run it from `exec-once` to react to workspace/window/monitor events.

### fuzzel as a script menu

```bash
choice=$(printf 'lock\nsuspend\nreboot\npoweroff' | fuzzel --dmenu -p "power> ")
```

Bind to a key for instant custom menus — the Raycast-script-command analog.

## Patterns

- **Config is the API.** Never click through GUIs for things hyprland.conf/gsettings can declare.
- **`exec` runs through /bin/sh** — pipes and `$(...)` in binds are evaluated at press time.
- **Version-control everything** — hypr/, waybar/, mako/, fuzzel/ are all plain text. See `dotfiles-bootstrap.md`.
- **Live-test with `hyprctl keyword`, persist in the file.** Don't let live state drift from config.

## Anti-patterns

- Editing config without `hyprctl reload` and then debugging "why didn't it work"
- Overlapping binds — Hyprland takes them globally and silently shadows app shortcuts (e.g. CTRL+3/4 shadow Chrome tab-jump; accepted tradeoff for screenshots)
- cron for user-session tasks that need Wayland env vars — use systemd user units (they inherit the session environment via `systemctl --user import-environment`)
- Autostart sprawl: keep `exec-once` minimal (waybar, mako, hypridle, polkit agent, theme reload)

## Examples

- "Add a bind to move the focused window to the next monitor"
- "Make Spotify always open on workspace 9"
- "Run my backup script every night at 2am"
- "Show a notification whenever I switch to workspace 5"
- "Why is my bind not firing?"
