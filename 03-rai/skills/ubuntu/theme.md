---
name: theme
description: Manages Linux theming end-to-end on the Omarchy hub. Audits themes against theme.lua as the source of truth, adds/removes themes, verifies app adapters (Hyprland border, Ghostty, Chrome, VS Code, Cursor, Starship, tmux, wallpaper), manages wallpapers, inspects keybindings, debugs why an app did not adapt. Invoked via /ubuntu router. Handles any theme/wallpaper/appearance-related question on the Linux machine.
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, WebFetch
---

# /ubuntu theme - Linux Theme System Manager

This is the Linux port of `/mac theme`: same `theme.lua` format, same themes,
same fidelity rule. **`theme.lua` is the source of truth** (hex-for-hex). No
adapter keeps its own copy of a color. The palette library, upstream sources
and per-theme app mappings (`vscode`, `vscode_ext`, `cursor`) live in the Mac
skill's doc, which both machines follow. See `../mac/theme.md`, the "Palette
reference library" table. Live theme files are
`~/dev-env/common/themes/<name>/theme.lua`, synced by Syncthing to
`~/.config/themes/<name>/theme.lua` on both machines.

## Architecture

```
~/.config/themes/<name>/
    theme.lua          declarative palette + app mapping (same shape as Mac)
    wallpapers/        PNG/JPG pack for this theme
~/.config/themes/current.lua -> <name>/theme.lua   (compat pointer, written by the hook below)

~/.local/bin/theme            switcher (bash), wraps `omarchy theme`. subcommands:
                               list, <name>, reload, cycle, pick, menu, wallpaper, render
~/.local/bin/theme-render     renders theme.lua -> an Omarchy user theme
                               (~/.config/omarchy/themes/<name>/colors.toml + backgrounds/)
                               plus an OpenCode theme JSON
~/.config/omarchy/hooks/theme-set.d/rai-theme-set
                               post-switch hook: everything Omarchy's own
                               colors.toml regeneration does not cover
~/.config/hypr/bindings.lua    binds SUPER+CTRL+T -> theme cycle, SUPER+CTRL+W -> theme wallpaper next
```

Switching flow: `theme <name>` checks that `~/.config/omarchy/themes/<name>/colors.toml`
exists, rendering it from `theme.lua` via `theme-render` if not, then calls
`omarchy theme set <name>`. Omarchy regenerates its own native surfaces from
`colors.toml`, then runs every executable script under `theme-set.d/`,
including `rai-theme-set`.

**Omarchy itself regenerates** (from `colors.toml`, no help needed):

- **Hyprland border**: `hyprctl keyword general:col.active_border`.
- **Ghostty**: `~/.local/state/omarchy/current/theme/ghostty.conf`, which
  `~/.config/ghostty/config` always points at. Live via `SIGUSR2`.
- **Chrome/Chromium**: `BrowserThemeColor` managed policy. Tints the **frame
  only**; the toolbar stays neutral by design.
- **OS color-scheme**: `gsettings org.gnome.desktop.interface color-scheme`
  and `gtk-theme`, which sets the freedesktop portal
  `org.freedesktop.appearance color-scheme`. Chrome, Firefox, Electron, sites
  set to follow the device theme, and GTK4/libadwaita apps all follow it.
- **wallpaper**.
- **shell**: Quickshell reads the same `colors.toml`, so notifications, bar
  and launcher need no separate adapter.
- **btop**, **neovim**.

**`rai-theme-set` covers what Omarchy does not**:

- **Cursor + VS Code**: a generated `rai-themes`-family editor theme named by
  `theme.lua`'s `cursor` field, built by
  `python3 ~/.config/themes/build-editor-themes.py` from the exact palette.
  Omarchy's own editor paths are skipped, since marketplace themes partly
  lack Cursor support and drift from `theme.lua`.
- **tmux status bar**: own rounded-pill layout. Bar is transparent
  (`bg=background`). The **accent** (`border` last-6) marks the
  active-window pill and pane border. The theme's **blue** (`ansi[4]`)
  frames the session and clock pills. Nerd-Font glyphs U+E0B6/U+E0B4 make
  the pill caps.
- **Starship**: rewrites every `[palettes.*]` block from every theme's
  `theme.lua`, not just the active one. This is what stopped Starship's old
  hand-maintained gruvbox red from drifting off `theme.lua`'s.
- **glow**: `~/.config/glow/rai.json`.
- The `~/.config/themes/current.lua` compat pointer, read by OpenCode's
  theme-sync plugin and by fastfetch.

**fastfetch** is palette-driven through Ghostty's regenerated palette. Every
color is an ANSI name, never hardcoded hex, so nothing needs to fire by hand.
The next launch shows the new theme.

**Obsidian is intentionally EXCLUDED** (user choice, 2026-06-10): it stays pinned
to the "Obsidian Nord" community theme (`cssTheme` in each vault's
`appearance.json`). Do not re-wire it without asking.

**theme.lua fields** (same shape the Mac skill documents):

- `vscode` = exact `workbench.colorTheme` label for Omarchy's own VS Code path.
- `vscode_ext` = marketplace extension id.
- `cursor` = the generated editor theme name used by `rai-theme-set` for Cursor + VS Code.

Note: `theme.lua` keeps the `macos = "dark|light"` field for cross-machine
parity with the Mac. On Linux it only decides Omarchy's native light/dark switch
via the `mode` key `theme-render` derives from it. Do not remove it. The same
theme files must work on both machines.

## Subcommands

Invoke with `/ubuntu theme <subcommand> [args]`.

---

### 1. audit: theme.lua parity check

Purpose: find an adapter that drifted from its own theme's `theme.lua`.

Usage: `/ubuntu theme audit [<theme>]`. No arg = audit all local themes.

Steps:
1. For each local theme at `~/.config/themes/<name>/theme.lua`, parse background, foreground, cursor_bg, selection_bg, ansi[], brights[], border, cursor, vscode, vscode_ext.
2. Compare the rendered `~/.config/omarchy/themes/<name>/colors.toml` and each `rai-theme-set` output (Cursor/VS Code generated theme, `~/.config/tmux/theme.conf`, the active `[palettes.<name>]` block in `starship.toml`) against `theme.lua`. Normalize hex to lowercase.
3. Report per-theme: PASS (1:1), DRIFT (any mismatch), MISSING (`colors.toml` not yet rendered).
4. For DRIFT, list every key that differs with `key: local_hex != theme_lua_hex`.

Pass: all themes PASS. Fix: `/ubuntu theme sync <theme>` (re-render), or `theme render <name>`.

A theme may be sourced from an upstream Omarchy palette (`source = "omarchy"`
in the Mac skill's palette table). For a deeper parity check, also diff
against that upstream. See `../mac/theme.md` for the `source` convention.

---

### 2. add: install a new theme

Usage: `/ubuntu theme add <name>`.

Steps:
1. Author or copy `<name>/theme.lua` (see `../mac/theme.md` for the palette
   reference library and the exact shape: name, border, macos, vscode, vscode_ext,
   cursor, colors{}).
2. If `~/.config/themes/<name>/` exists, ask to overwrite or abort.
3. Write `~/.config/themes/<name>/theme.lua`.
4. Create `~/.config/themes/<name>/wallpapers/` (empty). Prompt user to `/ubuntu theme wallpapers sync <name>`.
5. Run `theme render <name>` then `theme <name>` to switch, then `/ubuntu theme audit <name>` to confirm 1:1.

---

### 3. adapters: per-app health check

Purpose: after switching themes, verify every app actually updated.

Usage: `/ubuntu theme adapters [<theme>]`. Defaults to current.

| App | Where to read actual | Expected |
|-----|----------------------|----------|
| Ghostty | `cat ~/.local/state/omarchy/current/theme/ghostty.conf` | palette matches `current.lua` |
| tmux | `tmux show -gv window-status-current-format` (running server) / `cat ~/.config/tmux/theme.conf` | bar `bg`=`background` (transparent); active-window pill `bg`=accent; session/clock pill `bg`=`ansi[4]`; `pane-active-border-style fg`=accent |
| Hyprland border | `hyprctl getoption general:col.active_border` | `theme.border` |
| VS Code | `~/.config/Code/User/settings.json` → `workbench.colorTheme` | the generated `theme.cursor` label (installed rai-themes extension) |
| Cursor | `~/.config/Cursor/User/settings.json` → `workbench.colorTheme` | the generated `theme.cursor` label |
| Chrome | `cat /etc/opt/chrome/policies/managed/color.json` | `BrowserThemeColor` = `theme.background` |
| OS color-scheme | `gsettings get org.gnome.desktop.interface color-scheme` | `prefer-dark` if `theme.macos==dark` else `prefer-light` |
| Portal (Chrome/YouTube source) | `gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read org.freedesktop.appearance color-scheme` | `1` (dark) / `2` (light) |
| Obsidian (excluded) | `<vault>/.obsidian/appearance.json` → `cssTheme` | `"Obsidian Nord"` (pinned, switcher never touches it) |
| Starship | grep `^palette` in `~/.config/starship.toml`, plus its matching `[palettes.<name>]` block | palette name matches theme; block colors match `theme.lua` |
| Wallpaper | `omarchy theme current` background, visually | matches a file under `<theme>/wallpapers/` (Quickshell renders it, no separate daemon) |
| fastfetch | run `fastfetch` | theme line + palette-dot strip match `current.lua` |

Emit a table: `app | expected | actual | PASS/FAIL`. Any FAIL → suggest `/ubuntu theme debug <app>`.

---

### 4. coverage: installed-app theming audit

Purpose: find theme-able apps on this machine that the switcher does not touch.

Steps:
1. Known theme-able apps on this box: Ghostty, tmux, VS Code, Cursor, Neovim,
   Chrome, GTK apps (gsettings color-scheme), Quickshell (bar, launcher,
   notifications). Also: btop, fastfetch, starship, glow, Obsidian.
2. Check installs: `which <bin>`, `pacman -Q <pkg>`.
3. For each, check whether Omarchy's own `colors.toml` regeneration covers it or
   `rai-theme-set` does (`grep -E '<app>' ~/.config/omarchy/hooks/theme-set.d/rai-theme-set`).
4. Report table: `app | installed | covered_by | notes`.

There is no known gap today. Every installed theme-able app is covered by
either Omarchy's native regeneration or `rai-theme-set`. Waybar, mako, fuzzel,
hyprlock and WezTerm are **not installed** on this box (Omarchy 4 uses
Quickshell for bar, launcher, notifications and idle/lock). Do not report them
as gaps.

**Obsidian is NOT a gap.** It was deliberately removed from the switcher
(2026-06-10) and pinned to the "Obsidian Nord" theme. Do not report it as a
candidate or re-wire it.

**fastfetch** is NOT a switcher gap. It is intentionally palette-driven, not
regenerated per theme. Config: `~/.config/fastfetch/config.jsonc` (Omarchy's
layout: boxed Hardware/Software/Age sections, tree connectors, nerd icons).
Every color is an ANSI name (`green`/`blue`/`magenta` keys, bright-black `\x1b[90m`
borders) or named logo color, never hardcoded hex. So it resolves through
Ghostty's themed palette (Omarchy-regenerated at
`~/.local/state/omarchy/current/theme/ghostty.conf`) and follows the active
theme automatically with zero switcher changes. The Software box's theme line
reads the live theme name from `~/.config/themes/current.lua` and prints a
palette-dot strip. There is nothing per-theme to add to the switcher.

---

### 5. keys: keybinding inspector

Purpose: prove which config owns the theme/wallpaper keys, flag conflicts.

Steps:
1. Grep each possible owner:
   - `~/.config/hypr/bindings.lua` for `SUPER + CTRL, T/W` and `SUPER + CTRL + SHIFT, T/W`
   - `hyprctl binds` for the live state (config may not be reloaded)
2. Emit table: `binding | owner | action | status`.
3. Status PASS if exactly one owner. WARN if none. FAIL if multiple.

Expected baseline (`bindings.lua`): `SUPER+CTRL+T` opens the Omarchy theme menu,
`SUPER+CTRL+W` opens the background menu, `SUPER+CTRL+SHIFT+T` runs
`theme cycle`, `SUPER+CTRL+SHIFT+W` runs `omarchy-theme-bg-next`. If the live
`hyprctl binds` disagrees with the file, suggest `hyprctl reload`.

---

### 6. wallpapers: pack management

Usage:
- `/ubuntu theme wallpapers list [<theme>]`
- `/ubuntu theme wallpapers check`: cross-theme md5 dedup, missing folders
- `/ubuntu theme wallpapers sync <theme>`: pick a fresh pack for one theme

Source, folder allowlist, filters, and the color-matching method are documented
once in `../mac/theme.md` (§6). In short: `dharmx/walls` only, 17 allowlisted
folders, landscape ≥1920px, 4 palette-matched wallpapers per theme. Download to
`~/.config/themes/<name>/wallpapers/`, keep upstream filenames.

Both machines should carry the same picks so a theme looks identical across
them. Sync by copying the chosen files over (`rsync`), not by re-running the
picker independently on each box.

When rsyncing, stage a mirror tree that already has the `<theme>/wallpapers/`
shape and copy it with a plain `rsync -a mirror/ linux:.config/themes/`. Never
combine `--delete` with `--include`/`--exclude` filters here. On 2026-08-12 a
filter naming `wallpapers/***` against a source tree that lacked that level
deleted every wallpaper directory on the Linux box.

---

### 7. debug: inspect a stale adapter

Usage: `/ubuntu theme debug <app>` or `debug all`.

Per-app steps:
- **border**: `hyprctl getoption general:col.active_border`. If wrong, the keyword call failed. Run `~/.local/bin/theme reload` and check Hyprland is running (`$HYPRLAND_INSTANCE_SIGNATURE`).
- **ghostty**: `cat ~/.local/state/omarchy/current/theme/ghostty.conf` (Omarchy-generated; `~/.config/ghostty/config` always points `config-file` at this path). If stale, `theme reload` re-runs `omarchy theme set`. Ghostty live-reloads on its own file-watch.
- **vscode / cursor**: read `settings.json`, show the `workbench.colorTheme` line. It must match `theme.lua`'s `cursor` field (the generated editor theme, built by `build-editor-themes.py`), or VS Code/Cursor silently falls back to its default. `rai-theme-set` rebuilds and installs the theme on every switch. If the extension is missing, run `python3 ~/.config/themes/build-editor-themes.py` by hand.
- **tmux**: `cat ~/.config/tmux/theme.conf` (generated, sourced by `~/.config/tmux/tmux.conf` via a guarded `if-shell`). On a running server compare `tmux show -gv status-style` against the file. If it lags, `rai-theme-set`'s `tmux source-file` didn't fire (no server was up at switch time; it self-heals on the next switch or tmux start). `tmux source-file` only hits the default socket. Sessions on a non-default socket won't live-update until restarted.
- **chrome**: `cat /etc/opt/chrome/policies/managed/color.json` (and `/etc/chromium/policies/managed/color.json`). `rai-theme-set` only writes if the dir is user-writable (`[[ -w "$dir" ]]`) and silently skips otherwise. A one-time `sudo chmod a+rw` on both dirs is required (an `omarchy update` can reset ownership to root, so re-check after a big update: `test -w /etc/opt/chrome/policies/managed`). Verify live state at `chrome://policy` (BrowserThemeColor under Platform policies). Frame-only by design: it tints the frame, the toolbar stays neutral. Chrome reads policy at launch, so a running window keeps the old color until it restarts or "Reload policies" in `chrome://policy`.
- **color-scheme**: `gsettings get org.gnome.desktop.interface color-scheme` (expect `prefer-dark`/`prefer-light` per the theme's `macos` marker; Omarchy sets this on switch). The value Chrome/Firefox actually read comes from the portal. Call `gdbus call --session --dest org.freedesktop.portal.Desktop --object-path /org/freedesktop/portal/desktop --method org.freedesktop.portal.Settings.Read org.freedesktop.appearance color-scheme`. `1`=dark, `2`=light, `0`=no-preference (sites fall back to light). If the portal stays `0` after a switch, confirm `xdg-desktop-portal-gtk` or `-gnome` is running (`pgrep -af xdg-desktop-portal`). If a site ignores it, its appearance is pinned rather than set to follow the device. gsettings persists in dconf, so it survives reboot without a re-apply.
- **obsidian**: intentionally excluded from the switcher. Verify `cssTheme` is `"Obsidian Nord"` in `<vault>/.obsidian/appearance.json`. If colors look wrong, the fix is in Obsidian itself, not the switcher.
- **starship**: `sed -n '1,60p' ~/.config/starship.toml`, highlight `palette` + `[palettes.<name>]`. A missing `[palettes.<name>]` section for the active theme means the prompt silently falls back. `rai-theme-set` regenerates every theme's block on each switch.
- **wallpaper**: `omarchy theme current` and visually compare against `<theme>/wallpapers/`. No standalone process to check. Quickshell renders it directly from `colors.toml`.
- **fastfetch / glow**: run `fastfetch` or `glow <file>`. Both read the live theme (`current.lua` for fastfetch, `~/.config/glow/rai.json` regenerated by `rai-theme-set`).

Emit findings with absolute paths.

---

### 8. remove: delete a theme

Usage: `/ubuntu theme remove <name>`.

Steps:
1. Refuse if `<name>` is current. Suggest switching first.
2. Confirm with user before deleting.
3. Delete `~/.config/themes/<name>/` and `~/.cache/theme/<name>.wallpaper`.
4. Do not touch `~/.local/bin/theme` (it globs the themes dir).

---

### 9. list: overview

Usage: `/ubuntu theme list` or no args.

Columns: name, mode (dark/light), current (marked), rendered (colors.toml exists: yes/no), wallpaper_count.
At the bottom, print the current theme's palette as a color strip.

---

### 10. sync: re-render from theme.lua (audit fix)

`/ubuntu theme sync <theme>` re-runs `theme render <theme>` so
`~/.config/omarchy/themes/<theme>/colors.toml` and every `rai-theme-set` output
match `theme.lua` again. If `<theme>` is current, re-run `omarchy theme set
<theme>` afterward so the live surfaces pick it up. Only after user confirms.

---

## Fix suggestions

| Symptom | Fix |
|---------|-----|
| Audit shows DRIFT | `/ubuntu theme sync <theme>` then `adapters` to re-apply |
| Border didn't change | `hyprctl reload` then `theme reload`. Verify `hyprctl getoption general:col.active_border` |
| Ghostty stale | `theme reload`. Confirm `~/.config/ghostty/config`'s `config-file` still points at `~/.local/state/omarchy/current/theme/ghostty.conf` |
| VS Code / Cursor didn't update | Generated theme missing. Run `python3 ~/.config/themes/build-editor-themes.py`, check the extension named by `theme.lua`'s `cursor` field is installed |
| Chrome frame didn't update | Running window keeps the old policy until restart, or reload via `chrome://policy` |
| Theme/background menu key does nothing | `/ubuntu theme keys`. If config and live binds differ, `hyprctl reload` |

## Rules

- **`theme.lua` is the source of truth.** No adapter keeps its own copy of a color. See `../mac/theme.md` for the palette reference library and per-theme app mappings (shared with both machines).
- **Write minimal diffs.** Change only the lines that must change.
- **Keep `~/.local/bin/theme` as the only switcher.** The skill inspects, validates, and edits configs. The wrapper script and `rai-theme-set` hook apply them.
- **Source of truth for local themes is `~/.config/themes/`** (synced from `~/dev-env/common/themes/` by Syncthing).
- **Keep `theme.lua` cross-machine compatible**, same fields as the Mac, including `macos`.

## References

- `../mac/theme.md`: palette reference library, wallpaper rules (§6), per-theme app mappings (shared)
- `~/.local/bin/theme`: switcher source
- `~/.local/bin/theme-render`: theme.lua -> Omarchy user theme renderer
- `~/.config/omarchy/hooks/theme-set.d/rai-theme-set`: post-switch hook (Cursor/VS Code, tmux, Starship, glow, current.lua)
- `~/.config/hypr/bindings.lua`: THEME + WALLPAPER bind section
