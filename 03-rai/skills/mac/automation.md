---
name: automation
description: >
  macOS automation: Shortcuts.app, Keyboard Maestro, Raycast, Hammerspoon,
  AppleScript. USE WHEN the user wants to automate a repetitive workflow
  on macOS — clipboard, text expansion, window management, app launching.
---

# Mac Automation

Four main tool families. Pick by need; they compose.

## Tool picker

| Need | Tool |
|---|---|
| Quick launcher + snippets + AI + extensions | **Raycast** |
| Complex multi-app macros, triggers, schedules | **Keyboard Maestro** |
| Cross-device workflows (Mac + iPhone + iPad) | **Shortcuts.app** |
| Programmable Lua-level control (dotfiles-style) | **Hammerspoon** |
| Native automation (app-specific scripting) | **AppleScript / JXA** |

## Raycast

- Replaces Spotlight — much faster, more features
- Extensions: GitHub, Brew, clipboard history, window management, color picker
- AI Chat + Commands (Pro)
- Snippets: `;gm` → your email, `;addr` → your address
- Window manager: `⌃⌥⌘←` → left half, `⌃⌥⌘↑` → maximize
- Quicklinks: URLs with `{Query}` placeholders

Best for: fast single-action triggers, no workflow logic.

## Keyboard Maestro

- Macro engine with triggers, conditions, variables, loops
- Triggers: hotkey, text typed, schedule, app launch, device event, clipboard change
- Actions: anything macOS can do + shell scripts + AppleScript + HTTP requests
- Variables + IF/ELSE/WHILE
- Import/export as .kmmacros files (version-controllable)

Best for: anything with > 2 steps or conditional logic.

### Common macros worth building

- **Clipboard history** — cycle through last N items with Cmd+Shift+V (or just use Raycast)
- **Text replacement with templating** — `eomail` → `john's email + date`
- **Window grid layout** — one keystroke arranges apps for a specific workflow
- **Browser → terminal** — extract URL from Chrome, open in wget/curl
- **Schedule wakeups / reminders** — time-based triggers

## Shortcuts.app

- Cross-device: iOS + macOS + iPadOS + watchOS
- iCloud-synced
- Built-in actions for Apple apps + some third-party
- Can invoke via Siri, widget, share sheet, menu bar

Best for: anything that needs to run on iPhone too, or interacting with Apple apps (Notes, Reminders, Files, Photos).

Limits: less powerful than Keyboard Maestro; fewer conditional primitives.

## Hammerspoon

- Lua-scripted Mac automation
- API to window mgmt, hotkeys, app control, HTTP, filesystem, dialogs
- Config lives in `~/.hammerspoon/init.lua` — version control it
- Steepest learning curve; most power

Best for: developers who treat their OS config as code.

Example (move focused window to left half):
```lua
hs.hotkey.bind({"ctrl", "alt", "cmd"}, "Left", function()
    local win = hs.window.focusedWindow()
    local f = win:frame()
    local screen = win:screen():frame()
    f.x = screen.x
    f.y = screen.y
    f.w = screen.w / 2
    f.h = screen.h
    win:setFrame(f)
end)
```

## AppleScript / JXA

- AppleScript (English-like syntax) — verbose but app-scriptable
- JXA (JavaScript for Automation) — same API, modern syntax
- Target-specific: write an AppleScript for Mail, another for Numbers, etc.

Best for: controlling specific Mac apps programmatically (Mail, Calendar, Numbers, Pages, Keynote, Finder).

Example JXA — create a Calendar event:
```javascript
const Calendar = Application("Calendar");
const cal = Calendar.calendars.byName("Work");
const evt = Calendar.Event({
    summary: "Standup",
    startDate: new Date(),
    endDate: new Date(Date.now() + 30 * 60 * 1000),
});
cal.events.push(evt);
```

## Patterns

### Compose tools
- Raycast script → calls Keyboard Maestro macro → runs shell script → writes to Obsidian
- Shortcuts → calls Siri → triggers Keyboard Maestro
- Hammerspoon URL handler → invoked from Shortcuts

### Version-control your config
- Keyboard Maestro: export macros as .kmmacros, commit to dotfiles
- Raycast: Settings → Advanced → Import/Export
- Hammerspoon: `~/.hammerspoon/` is just files
- Shortcuts: iCloud syncs them; no text format (hardest to version)

### Keep a "new-mac bootstrap" script
See `/mac/dotfiles-bootstrap` — one script to re-install every tool + restore config.

## Anti-patterns

- Overlapping hotkeys between tools — collisions silently break
- Building automation you use once a year — ROI is negative
- Not documenting what macros do — future-you forgets
- Not versioning — one Keyboard Maestro crash and months of macros vanish
- Using AppleScript for things a shell script would do simpler

## Examples

- "Automate my morning routine: open apps, start timer, focus mode"
- "Keyboard Maestro macro to extract URL from Chrome and curl it"
- "Shortcuts for quick-capture to Obsidian from iPhone"
- "Hammerspoon window manager config for my dev workflow"
