# Theme Rollout

**Triggered by:** "add this theme" / "{X} didn't adapt/repaint" / "roll out {theme}"
**Cadence:** Ad-hoc (recurs every time theme work happens)
**Done when:** every WIRED adapter on BOTH machines has actually repainted to the new theme: verified per-adapter, not assumed.

Dozens of past PRDs are whack-a-mole. One adapter silently doesn't repaint, and the
whole rollout reads as "done" until eyes catch it days later. This playbook is the
ordering and the gates. The actual propagation is the `/mac → theme` and
`/ubuntu → theme` skills. The verify step (4) is the entire point.

```
Source theme.lua (dev-env) → Syncthing → Mac adapters → Omarchy hub adapters → Verify-each-repainted → Leave for coordinator
```

Fidelity is exact, hex-for-hex from `theme.lua`: no palette gate, no softening.
Obsidian is the one standing exception (pinned to "Obsidian Nord", never touched).

---

## Steps

### 1. Source the palette

- [ ] Pin the source theme: one `<name>/theme.lua` under `~/dev-env/common/themes/`
      (background, foreground, cursor/selection, 8 ANSI + 8 brights, plus a
      `wallpapers/` pack). Run `python3 common/themes/comfort-score.py` if choosing
      between candidates.
- [ ] Every adapter reads this file exactly as written. No adapter keeps its own
      copy of a color and none may adjust brightness or hue on the way in.
- [ ] Syncthing carries `theme.lua` + `wallpapers/` to both machines under
      `~/.config/themes/<name>/`.

### 2. Mac adapters: `/mac → theme`

- [ ] Run **`/mac → theme regen`** to propagate the palette to every Mac adapter:
      **WezTerm, VS Code, Cursor, Starship, JankyBorders, OpenCode, macOS appearance,
      wallpaper.**
- [ ] **JankyBorders needs a restart** to repaint: it does not live-reload.
- [ ] **Obsidian is EXCLUDED** (pinned theme). Never touch it.

### 3. Linux hub adapters: `/ubuntu → theme` (over keyless SSH from the laptop)

- [ ] Run **`theme <name>`** on the hub. It renders `theme.lua` into an Omarchy user
      theme (`theme render`, if not already rendered) and calls `omarchy theme set`.
- [ ] Omarchy itself regenerates: **Hyprland border, Ghostty, Chrome policy, shell/
      wallpaper, gsettings light/dark (+ the freedesktop portal), btop, neovim.**
- [ ] The `rai-theme-set` post-switch hook covers what Omarchy does not:
      **Cursor + VS Code** (generated `rai-themes`-family editor themes, via
      `~/.config/themes/build-editor-themes.py`). **tmux** status bar.
      **Starship** (every `[palettes.*]` block, not just the active one).
      **glow**. The `~/.config/themes/current.lua` compat pointer (OpenCode
      theme-sync, fastfetch).
- [ ] **fastfetch** is palette-driven through Ghostty's regenerated palette: nothing
      to fire by hand, next launch shows it.
- [ ] **Obsidian is EXCLUDED** here too.

### 4. VERIFY GATE: walk EACH adapter, confirm it actually repainted

- [ ] This is the step that gets skipped and causes the whack-a-mole. **Do not assume.
      Look at each surface.**
- [ ] Mac (8): WezTerm, VS Code, Cursor, Starship, JankyBorders (restarted?), OpenCode,
      macOS appearance, wallpaper.
- [ ] Omarchy hub (10): Hyprland border, Ghostty, Chrome policy, gsettings/portal
      light-dark, wallpaper, Cursor, VS Code, tmux, Starship, fastfetch (next launch).
- [ ] Run `/ubuntu → theme adapters` for a table of expected-vs-actual on the hub.

> **Decision Point**: any adapter still showing the OLD theme?
> - It did NOT repaint. Go back to its skill step, re-wire, re-fire the reload/restart.
> - **The rollout is NOT done while a single wired adapter is stale.** "Looks done"
>   is the failure mode this gate exists to kill.

### 5. Sync (leave for the coordinator)

- [ ] Vault / config edits stay **local**. The Linux coordinator commits + pushes at its
      next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac**: single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Adapter map (verified)

| Machine | Adapters | Reload mechanism |
|---------|----------|------------------|
| Mac (8) | WezTerm, VS Code, Cursor, Starship, JankyBorders, OpenCode, macOS appearance, wallpaper | JankyBorders = **restart**; rest auto/relaunch |
| Omarchy hub (10) | Hyprland border, Ghostty, Chrome policy, gsettings/portal light-dark, wallpaper, Cursor, VS Code, tmux, Starship, fastfetch | Omarchy live-applies its own surfaces on `theme set`; `rai-theme-set` extras apply in the same call; fastfetch is palette-driven (next launch) |
| Excluded | Obsidian (pinned) | never touch |

---

## Connections

- Mac propagation: `/mac → theme`
- Omarchy hub propagation: `/ubuntu → theme`
- Shared theme source: `~/dev-env/common/themes/<name>/theme.lua`, synced by Syncthing to `~/.config/themes/<name>/theme.lua` on both machines
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
- Omarchy desktop internals (Hyprland, Quickshell): `/omarchy`
- Capture a recurring rollout fix worth keeping: [[08-weekly-review]]
