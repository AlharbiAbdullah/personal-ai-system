---
name: diagnostics
description: >
  macOS hardware + software diagnostics. USE WHEN the Mac is slow, hot,
  losing Wi-Fi, running out of memory, crashing, or behaving weird.
  Covers thermal, memory, CPU, disk, network, USB/Thunderbolt.
---

# Mac Diagnostics

Mac is misbehaving. Isolate the problem systematically.

## When to use

- System feels slow; fan is loud
- Apps crash or hang
- Wi-Fi drops or is slow
- External displays / USB devices acting up
- Battery drains fast
- Disk full or slow

## When NOT to use

- A specific app is broken — reinstall it or file a bug
- General preferences / settings — use System Settings

## Triage

Start here, in order:

### 1. Activity Monitor
`⌘ Space → Activity Monitor`. Sort by CPU, Memory, Energy, Disk, Network in turn.

- **CPU tab**: any process > 80%? Click for details.
- **Memory tab**: pressure graph — green/yellow/red. Red = real issue.
- **Energy tab**: high energy impact processes — battery drain
- **Disk tab**: processes with high write rate
- **Network tab**: bandwidth hogs

### 2. System info
```bash
# Quick snapshot
system_profiler SPHardwareDataType | head
vm_stat | head
top -l 1 -n 10 -o cpu
df -h
```

### 3. Temperature + fans
```bash
# Built-in
pmset -g thermlog | tail -20  # thermal pressure log

# Third-party (if installed)
sudo powermetrics --samplers smc -n 1  # CPU + GPU temp, fan RPM
```

High temps: check dust in vents, thermal paste (on older Intel Macs), workload, ambient temp.

## Memory pressure

```bash
# Summary
vm_stat

# Top memory users
top -l 1 -o mem -n 20
```

- **Green pressure**: all good
- **Yellow**: memory tight but managing
- **Red**: swapping aggressively; performance tanks; save work + quit apps

Reduce: quit Chrome tabs, quit heavyweight apps (Xcode, Docker Desktop), restart.

## Disk space + health

```bash
# Space by directory
du -sh ~/Library/* | sort -h | tail -20
du -sh /Applications/* | sort -h | tail -20
df -h

# Files over 1GB
find ~ -type f -size +1G 2>/dev/null

# APFS health
diskutil apfs list
diskutil verifyVolume /
```

Common space hogs:
- `~/Library/Caches/` — safe to delete (apps regenerate)
- `~/Library/Developer/Xcode/DerivedData/` — rebuild cache
- `~/Library/Containers/com.docker.docker/` — Docker VM disk
- `node_modules/` in old projects
- Downloads folder

## Network

```bash
# Wi-Fi signal + rate
/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I

# DNS resolution
dig google.com
scutil --dns | head -30

# Ping + traceroute
ping -c 5 1.1.1.1
traceroute google.com

# Active connections
nettop -P -J bytes_in,bytes_out
```

Wi-Fi dropping: check channel, 2.4 vs 5GHz, router firmware, distance, interference.

## Process audit

```bash
# Everything running for current user
ps -u $USER

# Launch agents / daemons
ls ~/Library/LaunchAgents
ls /Library/LaunchAgents
ls /Library/LaunchDaemons
launchctl list | grep -v "^-"
```

Suspicious process? Look it up — don't kill blindly.

## Logs

```bash
# Last 10 min of system logs
log show --last 10m | less

# Filter by process
log show --last 1h --predicate 'process == "WindowServer"'

# Live tail
log stream --predicate 'eventMessage contains "error"'
```

## Crash reports
```bash
# App crash diagnostics
ls ~/Library/Logs/DiagnosticReports/
# Open the .ips file (newer) or .crash (older)
```

## External devices

### USB / Thunderbolt
```bash
system_profiler SPUSBDataType
system_profiler SPThunderboltDataType
```

Flaky device: try different port, different cable, another Mac.

### Displays
```bash
system_profiler SPDisplaysDataType
```

External display not detected: unplug/replug, check cable, reset NVRAM (Intel) / System Settings.

## Resets

Try in order (least → most invasive):

1. **Quit the misbehaving app**
2. **Logout + login**
3. **Restart**
4. **Reset NVRAM** (Intel): hold Option-Command-P-R at startup
5. **Reset SMC** (Intel, specific per model): various key combos
6. **Safe Mode boot**: hold Shift at startup (Intel) or power + ⏎ (Apple Silicon)
7. **Reinstall macOS** (keeps data): Recovery mode
8. **Nuke + pave**: see `/mac/dotfiles-bootstrap` for restoring

## Specific common issues

### "Beachball" on app open
- App is unresponsive. Wait 30s. If still stuck, Force Quit (`⌥⌘⎋`).
- Check Console for crashes.

### Fan always loud
- High CPU process (Activity Monitor)
- Thermal throttling (powermetrics)
- Dust in vents (physical cleaning)

### Wi-Fi drops every few minutes
- Router issue most likely
- `sudo pkill -HUP mDNSResponder` to reset DNS
- System Settings → Network → Wi-Fi → Forget + rejoin
- On macOS Sequoia: check network location settings

### External display doesn't wake
- Unplug + replug power + video cables
- Try different port (USB-C vs HDMI)
- Reset monitor firmware if available

### Battery drops quickly
- Activity Monitor → Energy tab
- Background apps (music, torrents, mail sync)
- Bluetooth / Wi-Fi searching
- Battery Health in System Settings — if capacity < 80%, consider replacement

## Anti-patterns

- "Restart" as the first move — often masks the real issue
- Installing "cleaners" (CleanMyMac, etc.) — mostly snake oil
- Killing random processes without understanding them
- Assuming hardware failure before checking software
- Running Disk First Aid unnecessarily (it's fine, modern APFS is robust)

## Examples

- "Mac is slow — diagnose"
- "Why is my battery draining so fast?"
- "Wi-Fi keeps dropping"
- "External monitor not detected after sleep"
