---
name: theme
description: Manages macOS theming end-to-end. Treats theme.lua as the single source of truth and audits that every tool is generated from it, adds or authors themes, verifies app adapters (iTerm2, Cursor, Antigravity, Starship, JankyBorders, macOS appearance), manages wallpapers, inspects keybindings, debugs why an app did not adapt, and pairs light/dark variants. Invoked via /mac router. Handles any theme/wallpaper/appearance-related question on the Mac.
allowed-tools: Bash, Read, Grep, Glob, Edit, Write, WebFetch
---

# /mac theme - macOS Theme System Manager

**`theme.lua` is the single source of truth.** One palette per theme, one file, and every tool
is GENERATED from it. No adapter keeps its own copy of a color, and no adapter selects a
palette somebody else wrote.

**Omarchy is a reference, and a good one.** It is where most palettes are sourced FROM. It is
not a master these themes must keep matching forever. Once a palette lands in `theme.lua` it is
yours: authoring an original or deriving a variant is normal work, not drift. Doctrine changed
2026-08-14, replacing "Omarchy is the golden standard, every theme must match 1:1".

Why it changed: every place a second copy of the colors lived, it silently drifted.
Cursor ran published extensions and **all 15 themes failed parity, worst dE 70.1**. Starship
kept a hand-written palette block, where `gruvbox` ran the ORIGINAL `#fb4934` red while
`theme.lua` ran the material `#ea6962`. Neither had a check that could catch it, because there
was nothing authoritative to check against. Now there is.

Each theme declares where its palette came from:

- `source = "omarchy"` — copied from an upstream in the reference table. `audit` can diff it
  against that upstream, and `sync` may rewrite it.
- `source = "original"` — authored here (7 of 15 today). It has no upstream, so a diff is
  meaningless and **`sync` must refuse it**. Syncing `everbloom-noir` toward `everbloom` would
  delete the darker floor that is the entire point of the theme. Audit checks originals against
  the house rules instead: lifted ground, loudest accent under the 0.60 calm ceiling,
  `selection_bg` a dim palette-native fill and never a bright accent.

## Palette reference library

Palettes worth sourcing from. Being listed here is not a claim that the local theme still
matches; it records where it started.

| Theme | Mode | Source |
|-------|------|--------|
| catppuccin | dark | basecamp/omarchy@dev `themes/catppuccin/colors.toml` |
| gruvbox | dark | basecamp/omarchy@dev `themes/gruvbox/colors.toml` |
| nord | dark | basecamp/omarchy@dev `themes/nord/colors.toml` |
| tokyo-night | dark | basecamp/omarchy@dev `themes/tokyo-night/colors.toml` |
| miasma | dark | OldJobobo/omarchy-miasma-theme@master `colors.toml` |
| cobalt2 | dark | hoblin/omarchy-cobalt2-theme@main `colors.toml` |
| gruvbox-light | light | Kushal0924/omarchy-gruvbox-light-theme@main `colors.toml` |
| everforest | dark | basecamp/omarchy@master `themes/everforest/colors.toml` |
| kanagawa | dark | basecamp/omarchy@master `themes/kanagawa/colors.toml` |
| ristretto | dark | basecamp/omarchy@master `themes/ristretto/colors.toml` |
| rose-pine | dark | rose-pine/alacritty@main `dist/rose-pine.toml` (Main variant) |
| melange | dark | savq/melange-nvim@master `lua/melange/palettes/dark.lua` |
| bamboo | dark | ribru17/bamboo.nvim@master `lua/bamboo/palette.lua` (multiplex variant) |
| kanagawa-dragon | dark | rebelot/kanagawa.nvim@master `lua/kanagawa/colors.lua` (dragon palette) |
| nightfox | dark | EdenEast/nightfox.nvim@main `extra/nightfox/wezterm.toml` |
| duskfox | dark | EdenEast/nightfox.nvim@main `extra/duskfox/wezterm.toml` |
| nordfox | dark | EdenEast/nightfox.nvim@main `extra/nordfox/wezterm.toml` |
| terramour | dark | atif-1402/omarchy-terramour-theme@main `colors.toml` |

Canonical palettes baked in at `references/omarchy-palettes.toml`. Per-theme app settings at `references/app-mappings.toml`.

## Architecture

```
~/.config/themes/<name>/
    theme.lua          declarative palette + app mapping
    wallpapers/        PNG/JPG pack for this theme
~/.config/themes/current.lua -> <name>/theme.lua

~/.local/bin/theme     switcher (bash). subcommands: list, <name>, reload, regen, cycle, pick, wallpaper
~/.aerospace.toml      binds cmd-ctrl-t → theme cycle, cmd-ctrl-w → theme wallpaper next
~/.cache/theme/        last-active wallpaper per theme
~/.hammerspoon/init.lua  HUD alerts on theme change

~/.config/opencode/themes/<name>.json            generated TUI theme (1 per system theme)
~/.config/opencode/tui-plugins/theme-sync.ts     TUI plugin: live-reloads a RUNNING opencode

~/.config/themes/vscode-theme-gen.py      theme.lua -> VS Code theme JSON (379 keys)
~/.config/themes/build-editor-themes.py   generate all + pack one vsix + install both editors
~/.config/themes/editor-parity.py         prove editor colors == theme.lua (dE threshold 1.0)
~/.config/themes/comfort-score.py         rank palettes by eye comfort
~/.config/themes/wallpaper-match.py       score a wallpaper against a palette

~/.config/starship.toml   [palettes.*] blocks REGENERATED by `theme regen`; edit theme.lua
```

Apps affected: **iTerm2** (Dynamic Profile written from `theme.lua`), **OpenCode** (generated custom TUI theme + live-reload plugin), **JankyBorders** (restarted with accent), **Cursor** + **Antigravity** (settings.json `workbench.colorTheme`, pointed at a generated theme), **Starship** (generated `[palettes.*]` blocks), **macOS** (`AppleInterfaceStyle`), **wallpaper** (NSWorkspace helper).

Every adapter that shows a COLOR is generated from `theme.lua`: iTerm2, OpenCode, the two
editors, Starship, and JankyBorders. The only lookups left carry no color of their own
(`AppleInterfaceStyle` is a dark/light flag, the wallpaper is a file path). That is the whole
point: a color exists in exactly one file, so parity is checkable everywhere it matters.

OpenCode adaptation, two layers: (1) on **launch**, opencode reads `tui.json`/`kv.json` (both written by the switcher) so a fresh session already matches; (2) the **`theme-sync` TUI plugin** (registered in `tui.json` `plugin[]`) polls `current.lua` and calls the TUI's `api.theme.set()` so an **already-open** session repaints live — opencode has no built-in live theme reload, and its config watcher reloads agents/skills but not the theme. `--pure` skips the plugin (launch-time still works). The plugin is Mac-only (hardcoded `~` paths); the Ubuntu switcher would need the analogous wiring.

OpenCode theme generation (`update_opencode_theme` in the switcher): the Omarchy signature colors (`background`, `foreground`, the 16 ANSI accents) are written EXACT. But OpenCode also needs neutral chrome elevations the 16-color palette doesn't define (`backgroundPanel`/`backgroundElement`/`border`/`borderSubtle`/`textMuted`) — these are derived by blending `background → foreground` (dark themes step lighter, light themes step darker). The loud selection/accent color is reserved for `borderActive`/`primary`/markdown headings only; it must NEVER be a fill (mapping `backgroundElement = selection_bg` is what made the input box render as a solid garish block — e.g. gruvbox `selection_bg = #d65d0e` orange). After editing the generator, run **`theme regen`** to rebuild all 10 JSONs, then **restart opencode** (a running TUI loaded the old JSONs at startup; the live plugin re-applies on theme *change*, not on file content change).

Editor theme generation (`vscode-theme-gen.py`, built 2026-08-14): same contract as the
OpenCode generator. Signature colors (background, foreground, selection, all 16 ANSI slots)
are EXACT; neutral chrome is derived with the same `mix(bg, fg, t)` ladder, so a palette edit
reaches Cursor with one `theme regen`. All 15 themes live in ONE extension, `rai.rai-themes`,
packed as a vsix and installed into both editors. Theme labels are `<Name> (generated)`.

**Why this replaced published extensions.** Cursor used to be the one adapter that never read
`theme.lua`: the switcher wrote a theme NAME and the extension author owned the colors. When
`editor-parity.py` was first pointed at the old setup, **all 15 themes failed, worst drift
dE 70.1**, and `dark-pro` / `light-pro` / `zenburned` pointed at extensions that were not even
installed. The visible symptom was gruvbox reading harsh in Cursor: local `gruvbox` carries the
gruvbox-MATERIAL palette (red `#ea6962`), while `jdinhlife.gruvbox` ships the ORIGINAL
(red `#fb4934` scream 0.78, orange `#fe8019` scream 0.90, its most-used token color) against a
0.60 calm ceiling. Generation removes the whole class of bug: parity is now 15/15 at dE 0.0.

Coverage: 379 color keys and 37 token rules per theme, including the integrated terminal's 16
ANSI slots (so it matches iTerm2 to the hex) and `editorGhostText` (Cursor's inline AI
suggestions, which render at VS Code's default grey if left unstyled).

## Subcommands

Invoke with `/mac theme <subcommand> [args]`. Each subcommand below lists its purpose, usage, steps, and pass criteria.

---

### 1. audit — source-of-truth check

Purpose: Prove every tool is showing the palette in `theme.lua`. This is the reason this skill
exists. It used to mean "does `theme.lua` still match Omarchy", which asked the wrong question:
it could not see a single one of the editor or prompt drifts, and it reported MISSING forever
for the 7 themes that were authored here.

Usage: `/mac theme audit [<theme>]`. No arg = audit all local themes.

Steps, in priority order. 1 and 2 are the real audit; 3 is informational.

1. **Generated adapters must match `theme.lua` exactly.** Run
   `python3 ~/.config/themes/editor-parity.py [<theme>]` for Cursor and Antigravity. For
   Starship, compare each `[palettes.<name>]` block in `~/.config/starship.toml` against
   `ansi[1..4]` and `border`. For iTerm2 and OpenCode, confirm the generated files are newer
   than `theme.lua`; if not, run `theme regen`.
   FAIL is a real bug. Fix with `theme regen`, never by hand-editing the generated file.

2. **The palette must satisfy the house rules**, whatever its source:
   - `selection_bg` is a dim palette-native fill, not a bright accent. Compare against the
     background: it should sit roughly 12 to 20 percent toward the foreground. A loud fill is
     the gruvbox-orange-block bug.
   - Loudest chromatic accent stays under the 0.60 scream ceiling (see `comfort-score.py`).
   - Light themes declare `macos = "light"`.
   - `background` and `foreground` clear a readable contrast gap.
   Report the comfort score from `comfort-score.py` so a new theme can be placed in the set.

3. **Provenance, informational only.** For `source = "omarchy"` themes, diff against
   `references/omarchy-palettes.toml` and report differences as INFO, not FAIL. A difference
   means the local theme was tuned after import, which is allowed. Only report FAIL here if the
   user asked to keep that theme pinned to upstream.
   For `source = "original"`, skip this step entirely. There is no upstream to diff.

Pass: step 1 clean for every theme, step 2 clean for every theme.
Fix: `theme regen` for step 1. Step 2 needs a palette decision, so surface it and ask.

---

### 2. add — install or author a theme

Purpose: Create a new theme, either sourced from the reference library or authored here.

Usage: `/mac theme add <name>`.

Steps:
1. Decide the palette source. Both are first-class:
   - **Sourced.** `<name>` is in the reference table, or the user names an upstream to fetch.
     Copy the palette verbatim and set `source = "omarchy"`.
   - **Authored.** No upstream. Set `source = "original"`. Do NOT refuse for being off the
     reference list: 7 of the 15 installed themes were authored here. Deriving a variant of a
     theme the user already likes (what `everbloom-noir` and `gruvbox-material-soft` are) is far
     more reliable than starting from a blank slate, so offer that first.
     Check the result with `comfort-score.py` before installing, and say where it lands in the
     set. That script scores a palette, it does not invent one; the palette is a design decision
     and belongs to the user.
2. If `~/.config/themes/<name>/` already exists, ask to overwrite or abort.
3. Read the border accent from `references/app-mappings.toml`, or pick one from the palette per
   the border rule in that file's header.
4. Write `~/.config/themes/<name>/theme.lua` with this exact shape:
   ```lua
   return {
     name = "<name>",
     border = "<border hex>",           -- from app-mappings
     macos = "<dark|light>",            -- from palette.mode
     source = "<omarchy|original>",     -- provenance; gates sync
     vscode = "<Name> (generated)",     -- derived, see below
     cursor = "<Name> (generated)",     -- derived, see below
     colors = {
       background = "<bg>",
       foreground = "<fg>",
       cursor_bg = "<cursor>",
       cursor_fg = "<bg>",
       selection_bg = "<sel_bg>",
       selection_fg = "<sel_fg>",
       ansi = { 8 normal hexes },
       brights = { 8 bright hexes },
     },
   }
   ```
   `vscode` and `cursor` are both the DERIVED generated name (see Editor themes
   below): the theme name title-cased, hyphens to spaces, plus " (generated)".
   No extension to pick, no marketplace to search.

5. Run `theme regen` so the new theme is built into `rai.rai-themes` and installed.
6. Create `~/.config/themes/<name>/wallpapers/` (empty). Prompt user to `/mac theme wallpapers sync <name>` to populate.
7. Run `/mac theme audit <name>` to confirm 1:1, then `python3 ~/.config/themes/editor-parity.py <name>` to confirm the editor matches.

Pass: audit returns PASS and parity returns PASS.

---

### 3. adapters — per-app health check

Purpose: After switching themes, verify every app actually updated.

Usage: `/mac theme adapters [<theme>]`. Defaults to current.

Steps (for each app, compare expected vs actual):

| App | Where to read actual | Expected |
|-----|----------------------|----------|
| macOS appearance | `defaults read -g AppleInterfaceStyle` (empty = light) | `theme.macos` |
| Cursor | `~/Library/Application Support/Cursor/User/settings.json` → `workbench.colorTheme` | `theme.cursor` |
| Antigravity | `~/Library/Application Support/Antigravity IDE/User/settings.json` → `workbench.colorTheme` | `theme.cursor` |
| Editor colors | `python3 ~/.config/themes/editor-parity.py <theme>` | PASS at dE 0.0 |
| Starship | grep `^palette` in `~/.config/starship.toml` | matches theme name |
| OpenCode | `~/.config/opencode/tui.json` + `~/.config/opencode/themes/<theme>.json` | `theme` matches theme name + custom JSON exists + `tui.json` `plugin[]` registers `tui-plugins/theme-sync.ts` (live reload) |
| JankyBorders | `pgrep -fl borders` and check launched with `active_color=<border>` | `theme.border` |
| iTerm2 | `readlink ~/.config/themes/current.lua` | `<name>/theme.lua` |

Emit a table: `app | expected | actual | PASS/FAIL`. Any FAIL becomes a suggestion to run `/mac theme debug <app>`.

---

### 4. coverage — installed-app theming audit

Purpose: Find theme-able apps on the Mac that the switcher does not touch.

Steps:
1. Known theme-able apps list (static): WezTerm, Ghostty, iTerm2, Alacritty, Kitty, Terminal.app, VS Code, Cursor, Zed, Xcode, Sublime Text, Neovim, Notion, Slack, Discord, Firefox, Arc, Raycast, Rectangle, JankyBorders.
2. Check `/Applications` and `~/Applications` with `mdfind`/`ls` or `brew list --cask` and `brew list`.
3. For each installed theme-able app, check if `~/.local/bin/theme` references it (`grep -E '<app>' ~/.local/bin/theme`).
4. Report table: `app | installed | wired_in_switcher | theme_file_for_current_theme`.

Gaps become candidates for wiring into `~/.local/bin/theme`.

---

### 5. keys — keybinding inspector

Purpose: Prove which config owns `cmd-ctrl-t` and `cmd-ctrl-w` and flag conflicts.

Steps:
1. Grep each possible owner:
   - `~/.aerospace.toml` for `cmd-ctrl-t` and `cmd-ctrl-w`
   - `~/.hammerspoon/init.lua` for `hs.hotkey.bind`
   - `~/.config/karabiner/karabiner.json` for matching `key_code` + `modifiers`
   - `~/Library/Application Support/com.raycast.macos/` (hotkeys plist) — best-effort via `defaults read`
   - `~/.config/skhd/skhdrc`
2. Emit table: `binding | owner | action | status`.
3. Status PASS if exactly one owner. WARN if none. FAIL if multiple.

Expected baseline: `aerospace.toml` owns both `cmd-ctrl-t` and `cmd-ctrl-w`, pointing at `~/.local/bin/theme cycle` and `wallpaper next` respectively. If something else owns them, that is a conflict — flag it.

---

### 6. wallpapers — pack management

Purpose: Manage wallpaper folders: list, dedup, sync.

Usage:
- `/mac theme wallpapers list [<theme>]`
- `/mac theme wallpapers check` — cross-theme md5 dedup, naming convention, missing folders
- `/mac theme wallpapers sync <theme>` — pick a fresh pack for one theme

**Source: `dharmx/walls` ONLY** (`https://github.com/dharmx/walls`, branch `main`).
Every other wallpaper repo is rejected, including the Omarchy per-theme
`backgrounds/` dirs that earlier versions of this skill used.

**Folder allowlist** (2026-08-12). Pull only from these 17 top-level folders:

```
abstract  anime  apeiros  apocalypse  centered  evangelion  gruvbox  logo
manga  minimal  nord  pixel  poly  radium  retro  solarized  spam
```

Any other folder in the repo (`aerial`, `flowers`, `mountain`, `nature`,
`monochrome`, `unsorted`, …) is off-limits. Note the spelling `apeiros`.

Hard filters, applied before any picking:
- landscape only (width > height)
- width ≥ 1920px

Selection rule: 4 wallpapers per theme, matched to that theme's palette. Match on
measured color, not filename. Working method:
1. `GET api.github.com/repos/dharmx/walls/git/trees/main?recursive=1` for the file
   list, filter to the allowlisted folders.
2. For each candidate, read original dimensions and a 64px thumbnail through the
   weserv proxy (`https://images.weserv.nl/?url=raw.githubusercontent.com/dharmx/walls/main/<path>&output=json`
   for metadata, `&w=64&output=jpg` for pixels) so no full-size download is needed
   for scoring.
3. Score each candidate against the theme palette (background, foreground, ansi,
   brights) as a weighted dominant-color distance in CIELAB, plus a lightness
   term that keeps dark wallpapers on dark themes and light on light.
4. Assign globally so no image is reused across themes, capped at 3 per source
   folder per theme for variety.
5. Download the 56 winners full-size from `raw.githubusercontent.com`, keeping
   upstream filenames. Do not rename.
6. Clear `~/.cache/theme/<theme>.wallpaper` for rewritten themes, then
   `theme reload` so the live desktop does not point at a deleted file.

Check steps:
1. For each theme folder, list wallpapers and `md5sum` each.
2. Report duplicates across themes.
3. Flag themes with zero wallpapers.

---

### 7. pair — light/dark twin binding

Purpose: Bind a dark theme to its light sibling so macOS appearance changes can flip between them.

Usage: `/mac theme pair <dark> <light>` (e.g. `gruvbox gruvbox-light`).

Steps:
1. Validate both themes exist.
2. Validate `<dark>.macos == "dark"` and `<light>.macos == "light"`.
3. Append `light_variant = "<light>"` to `<dark>/theme.lua` (top-level field).
4. Append `dark_variant = "<dark>"` to `<light>/theme.lua`.
5. Print a one-liner launchd plist the user can install at `~/Library/LaunchAgents/com.local.theme-auto.plist` that watches `AppleInterfaceStyle` and runs the paired theme. Do NOT install without user approval.

---

### 8. debug — inspect why an app did not adapt

Purpose: Deep-dive a single app's actual state vs expected.

Usage: `/mac theme debug <app>` or `/mac theme debug all`.

Per-app steps:
- **vscode / cursor**: read settings.json, find `workbench.colorTheme`, show the line with line number. If absent, show top 5 lines around where it would be inserted.
- **starship**: `sed -n '1,60p' ~/.config/starship.toml`, highlight palette + [palettes.<name>] section.
- **opencode**: read `~/.config/opencode/tui.json`, `~/.local/state/opencode/kv.json`, and `~/.config/opencode/themes/<current>.json`; verify all point at the current theme.
- **borders**: `ps -o pid,args -p $(pgrep -f borders)` — show what args borders was started with.
- **wezterm**: `readlink ~/.config/themes/current.lua`; then show first 20 lines of that file.
- **macos**: `defaults read -g AppleInterfaceStyle 2>/dev/null || echo "light"`.
- **wallpaper**: `osascript -e 'tell application "System Events" to get picture of every desktop'`.

Emit findings with absolute paths so the user can jump.

---

### 9. remove — delete a theme

Usage: `/mac theme remove <name>`.

Steps:
1. Refuse if `<name>` is the current theme. Suggest switching first.
2. Confirm with user before deleting.
3. Delete `~/.config/themes/<name>/` (including wallpapers).
4. Delete `~/.cache/theme/<name>.wallpaper` if exists.
5. Do not touch `~/.local/bin/theme` (it lists themes via directory glob).

---

### 10. list — overview

Usage: `/mac theme list` or `/mac theme` with no args.

Output columns:
- name
- mode (dark/light)
- current (★ if active)
- omarchy_match (✓ PASS / △ DRIFT / ✗ UNSUPPORTED)
- wallpaper_count

One line per theme. At the bottom, print the current theme's full palette preview as a color strip.

---

## Sync subcommand

`/mac theme sync <theme>` — overwrite `<theme>/theme.lua` colors from
`references/omarchy-palettes.toml`, leaving app-mapping fields intact.

**Refuse when `source = "original"`.** There is no upstream to sync from, and guessing at a
near neighbour destroys the work: syncing `everbloom-noir` toward `everbloom` would undo the
darker floor the theme exists for. Say so and stop.

Only for `source = "omarchy"` themes the user explicitly wants re-pinned to upstream. Never
run it to "fix" an audit, because since 2026-08-14 a difference from upstream is not a failure.
Always confirm first, and follow with `theme regen` so every generated adapter picks it up.

---

### 11. refresh-palettes — fetch upstream palette updates (maintenance)

Purpose: Pull the latest canonical palettes from the upstream Omarchy repos and update `references/omarchy-palettes.toml`.

Usage: `/mac theme refresh-palettes`

Steps:
1. For each tracked theme, curl the upstream `colors.toml` to a temp file:
   ```bash
   for t in catppuccin gruvbox nord tokyo-night; do
     curl -s "https://raw.githubusercontent.com/basecamp/omarchy/dev/themes/$t/colors.toml" > /tmp/$t.toml
   done
   for t in everforest kanagawa ristretto; do
     curl -s "https://raw.githubusercontent.com/basecamp/omarchy/master/themes/$t/colors.toml" > /tmp/$t.toml
   done
   curl -s "https://raw.githubusercontent.com/OldJobobo/omarchy-miasma-theme/master/colors.toml" > /tmp/miasma.toml
   curl -s "https://raw.githubusercontent.com/hoblin/omarchy-cobalt2-theme/main/colors.toml" > /tmp/cobalt2.toml
   curl -s "https://raw.githubusercontent.com/Kushal0924/omarchy-gruvbox-light-theme/main/colors.toml" > /tmp/gruvbox-light.toml
   ```
2. Diff each fetch against the corresponding section in `references/omarchy-palettes.toml`.
3. Print the diff and ask the user before writing.
4. On confirm, update the file and bump the fetch date in the header comment.

---

## Fix suggestions

| Symptom | Fix |
|---------|-----|
| Audit shows DRIFT | `/mac theme sync <theme>` then `/mac theme adapters` to re-apply |
| Editor didn't update | `rai.rai-themes` missing or stale. Run `theme regen`, then `editor-parity.py`. |
| Borders crashed | `~/.local/bin/theme` pkills then relaunches. If it stays dead, check `/tmp/borders.log`. |
| `cmd-ctrl-t` does nothing | Run `/mac theme keys`. If aerospace owns it, reload aerospace with `aerospace reload-config`. |
| Wallpaper did not change | macOS caches per-desktop. `killall Dock` forces a refresh. |
| Editor parity DRIFT | The theme is on a published extension, not a generated one. Repoint `theme.lua`'s `cursor`/`vscode` to `<Name> (generated)` and `theme regen`. |

## Rules

- **`theme.lua` is the only place a color is written by hand.** Every other file that holds a
  color is generated from it. If you find yourself typing a hex into `starship.toml`, an editor
  theme, or an iTerm2 profile, stop: that is the duplicate-source bug this system was rebuilt to
  remove. Fix the generator instead.
- **Authoring a palette is allowed; drifting from your own file is not.** Original themes are
  normal. What is forbidden is a tool showing colors that `theme.lua` does not contain.
- **Write minimal diffs.** When editing `theme.lua` or app settings, change only the lines that must change.
- **No auto-install of launchd agents or brew casks.** Always print the exact command and let the user run it. `rai.rai-themes` is exempt: it is generated locally from `theme.lua`, not fetched, and `theme regen` reinstalls it by design.
- **Keep `~/.local/bin/theme` as the only switcher.** Do not duplicate logic in the skill. The skill inspects, validates, and edits configs; the bash script applies them.
- **Source of truth for local themes is `~/.config/themes/`**. Not `.claude/`, not Obsidian, not anywhere else.
- **Light themes must declare `macos = "light"`**. The switcher reads this field to set `AppleInterfaceStyle`.

## References

- `references/omarchy-palettes.toml` — baked canonical palettes for all 7 themes
- `references/app-mappings.toml` — border accent per theme (editor names are derived, not listed)
- `~/.local/bin/theme` — switcher source
- `~/.aerospace.toml:104-107` — theme keybindings section

## Refresh palettes from upstream

This is now subcommand 11 above (`/mac theme refresh-palettes`). The manual section was removed in favor of the formalized subcommand.
