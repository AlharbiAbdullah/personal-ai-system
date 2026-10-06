---
name: tips
description: >
  Ubuntu/Linux power-user tips, hidden settings, native features people miss.
  USE WHEN the user wants the "right" way to do something on Linux or
  discovers they've been fighting the OS.
---

# Ubuntu Tips

Native features worth knowing on this Omarchy 4 (Arch + Hyprland) machine.
Shortcuts that save hours over a year. Source of truth for bindings is
`~/.config/hypr/bindings.lua`; re-check it if a shortcut below ever misfires.

## This machine's bind map (muscle memory)

Unified map (2026-08-27, amended 2026-09-11): **SUPER/CTRL for the system**,
**ALT for launching an app**. The same letter reaches the same app on the Mac,
where ALT is OPTION. Full table: `~/dev-env/KEYBINDINGS.md`. Live source:
`~/.config/hypr/bindings.lua`.

- `SUPER + SPACE`: Omarchy apps launcher · `SUPER + CTRL + SPACE`: Omarchy root menu
- `SUPER + 1..0`: workspaces (instant, no animation)
- `SUPER + SHIFT + 1..0`: throw window to workspace
- `SUPER + arrows`: focus · `SUPER + SHIFT + arrows`: move window
- `SUPER + RETURN`: terminal (Ghostty) · `ALT + B`: Chrome · `ALT + O`: Obsidian · `ALT + H`: Herdr
- `SUPER + B`: toggle top bar · `SUPER + TAB`: focus/reveal next window · `SUPER + SHIFT + SPACE`: float
- `CTRL + 3`: full screenshot → clipboard · `CTRL + 4`: region → clipboard · `Print`: Omarchy's own capture flow
- `SUPER + CTRL + T`: theme menu · `SUPER + CTRL + SHIFT + T`: next theme · `SUPER + CTRL + W`: background menu · `SUPER + CTRL + SHIFT + W`: next wallpaper
- `SUPER + H`: focus mode · `SUPER + K`: keybindings cheat sheet
- `SUPER + L`: lock · `ALT + SHIFT`: us ⇄ second layout
- Volume/mute keys: wpctl (work on lock screen) · Brightness keys: ddcutil over DDC/CI (desktop monitor, no kernel backlight)

## Wayland clipboard from the terminal

The `pbcopy`/`pbpaste` of this machine:

```bash
echo "hi" | wl-copy                  # copy
wl-paste                             # paste
wl-paste --list-types                # what's on the clipboard
grim -g "$(slurp)" - | wl-copy       # region screenshot → clipboard
wl-copy < image.png                  # put an image on the clipboard
```

## Shell power (bash)

- `Ctrl+R`: reverse history search (fzf takes it over if wired)
- `Ctrl+A / Ctrl+E / Ctrl+U / Ctrl+W / Ctrl+L`: line start/end, clear line, delete word, clear screen
- `Ctrl+Z` → `fg`: suspend/resume
- `!!`: last command (`sudo !!` is the classic) · `!$`: last arg · `Alt+.`: cycle last args
- `cd -`: previous directory
- `^foo^bar`: re-run last command with substitution

## pacman fluency (no apt, no snap on this box: Arch/Omarchy)

```bash
pacman -Qi <pkg>                     # description, deps, size (installed)
pacman -Si <pkg>                     # same, from the repo (not-yet-installed)
pacman -Ss <term>                    # find a package
pacman -Qe                           # what YOU installed explicitly (vs deps)
pacman -Qdt                          # orphaned deps, safe to `pacman -Rns` after review
pacman -F <missing-binary>           # which package ships a file (needs `pacman -Fy` once)
paccache -d / paccache -r            # dry-run / actually prune the package cache (paccache.timer runs weekly)
```

`omarchy update` and `omarchy pkg remove` wrap pacman for the common cases.

## systemd fluency

```bash
systemctl --user list-timers         # your scheduled jobs
systemctl status <unit>              # state + recent log lines in one
journalctl -u <unit> -e              # full log, jump to end
journalctl -f                        # live tail everything
systemd-analyze blame                # what slowed down boot
systemctl --failed                   # anything dead right now
busctl / loginctl lock-session       # lock from a script
```

`systemctl edit <unit>`: override a vendor unit without touching /usr.

## Files + navigation

```bash
xdg-open .                           # `open .` equivalent
nautilus --select <file>             # reveal in file manager
fd <pattern>                         # find, but good (fd-find)
rg <pattern>                         # grep, but good
ncdu /                               # interactive disk usage
stat <file>                          # everything about a file
```

## Hidden gems

- **`omarchy-menu toggle apps`** (bound to SUPER+SPACE): pipe-free app picker; `omarchy menu` for the full tree
- **GTK dark mode for legacy apps**: `gsettings set org.gnome.desktop.interface color-scheme prefer-dark`
- **`systemd-run --user --on-calendar=...`**: one-shot scheduled command, no unit file
- **`script -r` / `scriptreplay`**: record and replay a terminal session
- **`/proc/pressure/{cpu,memory,io}`**: PSI: is the machine *actually* under pressure
- **`timedatectl`, `localectl`, `hostnamectl`**: system facts in one command each
- **`ip -br a`**: readable network interface summary
- **`tldr <cmd>`**: examples instead of manpages
- **Magic SysRq** `Alt+SysRq+REISUB`: last-resort safe reboot of a frozen box (if enabled)

## Hyprland niceties

```bash
hyprctl clients                      # every window + class (for rules)
hyprctl dispatch workspace e+1       # scriptable everything
hyprctl keyword general:gaps_in 0    # live-tweak without editing config
hyprctl reload                       # re-read ~/.config/hypr/*.lua
```

Arabic layout: `ALT+SHIFT` toggles. Omarchy's Quickshell bar (not waybar) can
show the active layout if you ever lose track: check `omarchy-menu.jsonc`
widgets.

## Obscure but useful

```bash
notify-send "title" "body"           # toast via Omarchy's Quickshell notification daemon (not mako)
loginctl lock-session                # lock programmatically
cat /etc/os-release                  # exact OS version (Arch Linux; `pacman -Q omarchy` for the Omarchy version)
ldd <binary>                         # what libs it needs
strace -f -e trace=file <cmd>        # what files a command actually touches
lsof +D <dir>                        # who has files open in a dir
fuser -v <file>                      # which process holds a file
```

## Productivity patterns

- **One workspace per project**: SUPER+number is instant; let muscle memory do the routing
- **`omarchy menu` providers for repeated choices**: power menu, and `omarchy-menu.jsonc` can add custom rows with a `provider` command
- **systemd user timers over cron**: they log to journalctl and inherit session env
- **`pacman -Qe` quarterly**: feeds the dotfiles rebuild list

## Examples

- "What's the Linux equivalent of pbcopy?"
- "How do I find which package provides a command?"
- "Schedule a script without writing a unit file"
- "Lock the screen from a script"
