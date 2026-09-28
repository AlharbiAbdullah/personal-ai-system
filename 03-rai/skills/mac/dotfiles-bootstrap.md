---
name: dotfiles-bootstrap
description: >
  The "spilled coffee" skill: restore a full development environment from
  scratch in under 2 hours. USE WHEN setting up a new Mac, recovering from
  disaster, or establishing a reproducible dev environment.
---

# Dotfiles Bootstrap

Assume the current Mac is gone. Rebuild in under 2 hours, nothing forgotten.

## When to use

- New Mac (work or personal)
- Nuked + paved the current Mac
- Starting a fresh dev environment (Docker container, cloud VM)
- Teaching someone to set up their machine

## When NOT to use

- Daily-use machine config tweaks — just change System Settings
- Quick installs of 1-2 tools — just run `brew install`

## Philosophy

- **Declarative** — one file describes the whole machine
- **Idempotent** — running it twice does no harm
- **Version-controlled** — dotfiles in git, restorable to any point
- **Modular** — split by concern (zsh, git, brew, apps, secrets)
- **Secrets separate** — never commit keys + tokens + SSH identities

## The layout

```
~/dotfiles/
├── README.md
├── bootstrap.sh               # entry point
├── brew/
│   └── Brewfile              # all brew packages + casks
├── zsh/
│   ├── .zshrc
│   └── .zprofile
├── git/
│   ├── .gitconfig
│   └── .gitignore_global
├── ssh/
│   └── config                 # SSH aliases (no keys!)
├── starship.toml
├── wezterm.lua
├── vscode/
│   └── settings.json
├── macos/
│   └── defaults.sh            # `defaults write` commands
└── secrets/                   # gitignored — symlink target
    └── README.md              # documents what goes here manually
```

## bootstrap.sh structure

```bash
#!/usr/bin/env bash
set -euo pipefail

DOTFILES="$HOME/dotfiles"

# 1. Prerequisites
which brew >/dev/null || /bin/bash -c "$(curl -fsSL \
  https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. Install packages
brew bundle --file="$DOTFILES/brew/Brewfile"

# 3. Link dotfiles (stow or manual)
for f in .zshrc .zprofile .gitconfig; do
    ln -sf "$DOTFILES/zsh/$f" "$HOME/$f" 2>/dev/null || \
    ln -sf "$DOTFILES/git/$f" "$HOME/$f" 2>/dev/null || true
done

# 4. macOS defaults
bash "$DOTFILES/macos/defaults.sh"

# 5. Shell (zsh default)
chsh -s /bin/zsh

# 6. Per-tool config
mkdir -p "$HOME/.config"
ln -sf "$DOTFILES/starship.toml" "$HOME/.config/starship.toml"
ln -sf "$DOTFILES/wezterm.lua" "$HOME/.wezterm.lua"

# 7. Manual steps prompt
cat <<EOF

=== DONE ===
Manual steps:
1. Copy SSH keys + GPG keys from secure backup to ~/.ssh/ and import to GPG
2. Sign into: iCloud, GitHub, 1Password, Slack, Linear
3. Install App Store apps (Xcode if needed)
4. Claude Code: re-link ~/.claude/ to ~/helm/03-rai/ per vault layout
5. Restart + verify

EOF
```

## Brewfile example

```ruby
# Terminal
brew "wezterm"
brew "starship"
brew "zsh"
brew "git"
brew "tmux"
brew "neovim"
brew "fzf"
brew "ripgrep"
brew "fd"
brew "eza"
brew "bat"
brew "delta"
brew "jq"
brew "yq"
brew "direnv"

# Languages + tooling
brew "python@3.12"
brew "uv"
brew "node"
brew "pnpm"
brew "go"
brew "rustup"

# Containers + infra
brew "docker"
brew "docker-compose"
brew "kubectl"
brew "helm"
brew "terraform"
brew "awscli"

# Data
brew "duckdb"
brew "sqlite"
brew "postgresql@16"

# Apps (casks)
cask "cursor"
cask "wezterm"
cask "raycast"
cask "1password"
cask "obsidian"
cask "orbstack"
cask "zed"

# Fonts
tap "homebrew/cask-fonts"
cask "font-jetbrains-mono-nerd-font"
cask "font-fira-code-nerd-font"
```

## macOS defaults.sh

Common useful defaults:
```bash
# Show hidden files in Finder
defaults write com.apple.finder AppleShowAllFiles -bool true

# Dock: auto-hide, minimal
defaults write com.apple.dock autohide -bool true
defaults write com.apple.dock autohide-delay -float 0
defaults write com.apple.dock autohide-time-modifier -float 0.15

# Screenshots: PNG, not to Desktop
defaults write com.apple.screencapture type -string "png"
mkdir -p "$HOME/Screenshots"
defaults write com.apple.screencapture location "$HOME/Screenshots"

# Tap-to-click
defaults write com.apple.AppleMultitouchTrackpad Clicking -bool true

# Key repeat (for vim/coding)
defaults write NSGlobalDomain KeyRepeat -int 2
defaults write NSGlobalDomain InitialKeyRepeat -int 15

# Restart affected processes
killall Dock Finder SystemUIServer
```

## What to keep separate (NOT in dotfiles repo)

- SSH private keys → backup to encrypted external drive + 1Password
- GPG private keys → same
- API tokens / passwords → 1Password
- Specific work configs with client identifiers → private repo
- Browser profile data → use profile sync (Arc, Chrome, Firefox all sync)

## Verification checklist

After running bootstrap:
- [ ] Shell prompt renders correctly (Starship)
- [ ] Git commits work (name + email set)
- [ ] SSH can push to GitHub
- [ ] Brew apps all installed
- [ ] Python + Node + etc. versions correct
- [ ] Claude Code reads vault correctly
- [ ] Obsidian opens vault
- [ ] 1Password unlocks
- [ ] Screenshot saves to expected folder
- [ ] Key repeat feels right

## Anti-patterns

- Putting secrets in the dotfiles repo
- One 500-line `bootstrap.sh` without functions — hard to maintain
- Not testing on a fresh machine — config rots
- Editing live configs instead of dotfiles source — changes not version-controlled
- Overly clever stow layouts for a single-user setup — simpler is better

## John-specific notes

- Vault at `~/helm/` with symlinks: `~/.claude/CLAUDE.md` → `~/helm/03-rai/AGENTS.md`
- `~/.claude/skills` → `~/helm/03-rai/skills`
- ChromaDB lives at `~/helm/03-rai/semantic-memory/chromadb/`
- `py-chroma.sh` wrapper for Python env

Document every symlink in `bootstrap.sh` so restore doesn't miss any.

## Examples

- "Write me a bootstrap script for my Mac"
- "Add Rust + Cargo to my Brewfile"
- "Set up new work Mac following my dotfiles"
- "What's missing from my bootstrap compared to my current Mac?"
