---
name: tips
description: >
  macOS power-user tips, hidden settings, native features people miss.
  USE WHEN the user wants to know the "right" way to do something on Mac
  or discovers they've been fighting the OS.
---

# Mac Tips

Native features worth knowing. `defaults write` tweaks. Keyboard shortcuts
that save hours over a year.

## Keyboard shortcuts worth memorizing

### Global
- `⌘ ⇥` — cycle apps
- `⌘ `` ` `` (backtick) — cycle windows of current app
- `⌃ ←/→` — switch spaces
- `⌃ ↑` — Mission Control
- `⌘ ␣` — Spotlight / Raycast
- `⇧ ⌘ .` — show hidden files in Finder (toggle)
- `⌥ ⌘ D` — toggle Dock
- `⌃ ⌘ Q` — lock screen immediately

### Screenshots
- `⇧ ⌘ 3` — full screen
- `⇧ ⌘ 4` — selection (hold Space after to move; ⌥ to expand from center)
- `⇧ ⌘ 5` — recording panel
- Add `⌃` to any of above → copy to clipboard instead of file

### Text
- `⌥ ←/→` — jump by word
- `⌘ ←/→` — jump to line start/end
- `⌥ ⌫` — delete prev word
- `⌘ ⌫` — delete to line start
- `fn ⌫` — forward delete
- `⌃ A / ⌃ E` — line start/end (Emacs bindings work in most text fields!)
- `⌃ K` — kill to end of line

### Finder
- `⌘ ⇧ G` — go to path (paste `/etc/` or similar)
- `⌘ ⇧ .` — show/hide hidden files
- `⌘ I` — info; `⌥ ⌘ I` — Get Info stays open for next selection
- `⌘ ⌥ C` — copy path
- `⌘ ⌥ V` — move (not copy) when pasting
- Spacebar — Quick Look (any file type)
- `⌥` while dragging — copy instead of move

### Preview
- `⌘ K` — insert signature
- `⌘ ⇧ A` — annotation toolbar
- `⌘ S` — save
- `⌥` click + drag a PDF page — duplicate it

## Hidden gems

### Text replacement (system-wide)
System Settings → Keyboard → Text Replacements. Works in every native text field.
- `;eml` → your email
- `;addr` → your address
- `omw` → "on my way"

### Dictation
`fn fn` (double-tap). Transcribes into any text field. Offline on Apple Silicon.

### Live Text
Select text in any image — click + drag inside a photo in Preview, Quick Look, or camera.

### Universal Clipboard
Copy on iPhone → paste on Mac (or reverse) if both are signed into same iCloud.

### Continuity Camera
Use iPhone as webcam. Works in Zoom, Meet, FaceTime, etc.

### Hot Corners
System Settings → Desktop & Dock → Hot Corners. Put Mission Control, Screen Saver, Lock in corners.

### Sound + menu bar shortcuts
- `⌥` click menu bar items — reveals more options (Wi-Fi details, Bluetooth signal, etc.)
- `⌥ ⌃ ⇧ S` — screenshot just selection to clipboard (configurable)

### Spotlight math + conversions
- Type `1234 * 5.67` in Spotlight → result
- `30 usd in eur` → conversion
- `215 km to mi` → conversion

### Quick Look power
- Spacebar on any file in Finder
- Press `Y` to open in Photos (for images)
- Multiple files selected — Space previews all with arrow navigation

## `defaults write` tweaks

```bash
# Dock: disable the bounce animation
defaults write com.apple.dock no-bouncing -bool true

# Finder: show path bar
defaults write com.apple.finder ShowPathbar -bool true

# Finder: show status bar
defaults write com.apple.finder ShowStatusBar -bool true

# Finder: default to list view
defaults write com.apple.finder FXPreferredViewStyle -string "Nlsv"

# Screenshots location
defaults write com.apple.screencapture location ~/Screenshots

# Disable disk image verification on downloaded dmgs (speeds up install)
defaults write com.apple.frameworks.diskimages skip-verify -bool true

# Expand save dialog by default
defaults write NSGlobalDomain NSNavPanelExpandedStateForSaveMode -bool true

# Disable annoying "are you sure you want to open" for downloaded apps
defaults write com.apple.LaunchServices LSQuarantine -bool false

# Faster key repeat (requires logout)
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# After changing defaults, kill affected processes to apply
killall Dock Finder SystemUIServer
```

## Apps worth knowing (native)

- **Migration Assistant** — transfer from old Mac / Time Machine
- **Disk Utility** — format drives, partition, First Aid
- **Activity Monitor** — see `/mac/diagnostics`
- **Console** — system logs, unified log viewer
- **System Information** — `⌥ Apple menu` — About This Mac → More Info
- **TextEdit** — `⌘ ⇧ T` toggles plain vs rich text
- **Preview** — edit PDFs, sign documents, crop images
- **Script Editor** — write + run AppleScript / JXA
- **Automator** — older macro tool, mostly replaced by Shortcuts
- **Digital Color Meter** — pick color from anywhere on screen
- **Grapher** — plot functions (math / stats)
- **Activity Monitor → View → GPU History** — graphs GPU use

## Shell + terminal power

### Built-in shell features
- `⌃ R` in zsh/bash — reverse search history
- `⌃ A / ⌃ E` — line start/end
- `⌃ U` — clear line
- `⌃ L` — clear screen
- `⌃ W` — delete word back
- `⌃ Z` — suspend → `fg` to resume
- `!!` — repeat last command
- `!$` — last arg of last command
- `^foo^bar` — repeat last command, replace foo with bar

### zsh globbing
- `ls **/*.py` — recursive glob
- `ls *(m-1)` — files modified in last day
- `ls *(L+1048576)` — files bigger than 1MB

## Productivity patterns

- **Window grouping with Stage Manager** (⌃ ⌘ F) — per-project window groups
- **Multiple Desktops (Spaces)** — one per project; ⌃ ←/→ to switch
- **Focus modes** — per-app / per-time quiet mode (Do Not Disturb on steroids)
- **Menu Bar Extras Control** — `⌥` drag items to rearrange

## Obscure but useful

- `pbcopy` / `pbpaste` — clipboard from terminal. `echo "hi" | pbcopy`
- `say "hello"` — speaks text
- `caffeinate` — prevents sleep. `caffeinate -u -t 3600` (1 hour)
- `open .` — open current dir in Finder
- `open -a "Visual Studio Code" file.py` — open with specific app
- `mdfind "query"` — Spotlight from terminal
- `screencapture out.png` — screenshot from terminal
- `networkQuality` — built-in speed test

## Examples

- "What macOS shortcuts should I know?"
- "How do I paste clipboard via a shortcut?"
- "defaults write tweaks for productivity"
- "Built-in features I'm probably missing on my Mac"
