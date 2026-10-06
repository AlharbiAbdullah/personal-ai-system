# Incident on a Machine

**Use when:** something on a machine broke or stopped. A job or a timer, sync, the disk, the network, an app or the desktop, or a hook that blocks Claude. Also when he asks to investigate a failure.
**Not for:** the news digest failing, which is 10 news recovery. A sanity alarm, which is 17 brain healthcheck. A bug in code, which is 04 debugging. A planned change to a machine, which is 16 machines.
**Done when:** the cause is named with evidence, and the fix is proven and live. A guard stops it coming back, and a memory ruling holds the lesson. An external cause ends with the recheck command written down. "Investigate only" ends with the findings and nothing changed.

His way with a broken machine: find the real cause before touching anything. Then fix it at the source, one change at a time, and make sure it cannot happen again.

```d2
direction: down

route: "1. Route it" {shape: diamond}
w10: "10 news recovery"
w17: "17 brain healthcheck"
w04: "04 debugging"
checks: "2. First checks\nwhen it began, what changed"
look: "3. Look where\nthe evidence is"
traps: "4. Harness traps\nwhen Claude itself fails"
data: "5. Protect data first"
fix: "6. Fix at the source\none change at a time"
guard: "7. Guard and record"
external: "External cause:\nwait, recheck, ticket"

route -> w10: "the news run"
route -> w17: "a sanity alarm"
route -> w04: "a code bug"
route -> checks: "a machine"
checks -> look -> data -> fix -> guard
look -> traps: "Claude's tools fail" {style.stroke-dash: 3}
look -> external: "outside his machines" {style.stroke-dash: 3}
```

---

## Steps

### 1. Route it

> **Decision Point**: what broke?
> - The news digest, or a news abort marker: [[10-news-digest-recovery]] step 1.
> - A sanity alarm, or a BROKEN or STALE banner: [[17-brain-healthcheck]] step 1.
> - A bug in code that a test can reproduce: [[04-debugging]] step 1.
> - Anything else on a machine: this workflow.

- [ ] He reports the symptom, and Rai diagnoses it. Inspect the machine, and never answer from speculation.
- [ ] "Investigate only" means change nothing. Report the findings, offer tests he can approve, and stop.
- [ ] Every system-level change waits for his go.

### 2. First checks

- [ ] Find when it began, and what changed at that moment: an update, an extension, a config edit, a reboot. The start of a failure streak points at the cause.
- [ ] Look for an unclean boot near that date. Run `journalctl --list-boots`, then read about 40 lines from the end of each boot. An app that held an open database may have left it truncated.

- [ ] A stale green file proves nothing. Check the status file's modified time and the service state itself.
- [ ] The maintenance service exits 1 with every step at rc=0: that is the sanity alarm, not a crash. Go to [[17-brain-healthcheck]] step 1.
- [ ] A step reports rc=0, but nothing drains: suspect a background child that the `claude -p` turn exit killed.
- [ ] Claude drops prompts: grep the transcripts for "blocked by hook". The message names the hook.
- [ ] Tools fail with no clear cause: grep the live config for stale `/Users` paths from the Mac.

### 3. Look where the evidence is

- [ ] Logs live outside the repo. The coordinator writes to `~/.local/state/rai-maintenance/logs/`.
- [ ] Ask the live app, not its config files. A missing config file proves nothing.
- [ ] A bind or a script that does nothing: run its command by hand and read the error.
- [ ] A window that cuts its content: compare the window rule's size with the content before touching a renderer.
- [ ] A headless display: check it with `xwininfo -root -tree`, not by whether the process lives.
- [ ] A Chromium or Electron SIGTRAP with SI_KERNEL is a deliberate fatal check. Read the log line before it.
- [ ] Wi-Fi lost its 5 GHz networks: check `iw reg get` first.
- [ ] A crash: `/omarchy → diagnose-crash`. Heat, memory, disk, network or USB: `/ubuntu → diagnostics`.
- [ ] A failing job, timer or sync path goes to the `sre` agent: inputs the symptom, the unit names and the log paths. It returns a timeline and the likely cause with evidence, and changes nothing.
- [ ] A failing script goes to the `debugger` agent: inputs the script and the failing run. It returns a reproduction and the proven cause, and writes only in scratch.
- [ ] Rai re-checks the cause either agent names before any fix rests on it.

> **Decision Point**: the cause is outside his machines, such as an ISP route, a CDN or a vendor outage.
> - Prove where it stops first: a TCP probe to the host, the route, and the provider's status page.
> - Waiting is a valid fix: last time he chose a day's wait over a workaround. Write down the recheck command and when to run it.
> - Still blocked after a day: a ticket to the ISP that names the blocked range.

### 4. Harness traps

When Claude's own tools fail, these come first.

- [ ] Every Bash call exits 1 with no output: the /tmp quota is full, and Claude cannot recover by itself. Diagnose with a Read of `/proc/mounts` and a tiny Write probe. He cleans up in a plain terminal.
- [ ] The disk is full: he recovers in a plain terminal. `sudo tune2fs -m 1` on the root device frees the reserve, then `du -x` finds what filled it.
- [ ] A truncated `.claude.json` comes back from the newest valid copy in `~/.claude/backups/`.
- [ ] The `!` prefix runs through the same broken path, so recovery commands go to his own terminal.
- [ ] Never `pkill -f` or `pgrep -f`, since the pattern matches the harness's own shell. Kill by port or by PID.
- [ ] Waiting on a oneshot service: poll `systemctl --user show <svc> -p ActiveState`, never `is-active`.

### 5. Protect data before touching anything

- [ ] Before a re-pair or a restore that can bring files back, commit a git baseline. Verify each resurrected file before deleting it.
- [ ] An autostash can hold the only copy of a record. Diff it against the tree before dropping it.
- [ ] Secrets arrived in a merge: he blocks the push first, since only he can. A script he runs then rebuilds the unpushed history.
- [ ] A live credential turns up: leave it in place. He revokes it at the source first.

### 6. Fix it at the source

- [ ] One change at a time.
- [ ] Fix the cause where it lives, such as the generator, the installer or the hook. Never patch the symptom.
- [ ] Prove the fix in a scratch repo or a throwaway first, then live.
- [ ] Fix forward, so the job heals itself next time. Never add a "needs a human" exit for a recoverable state.
- [ ] When a scheduled job owns the pending work, let the scheduler pick it up instead of a run by hand.
- [ ] Sudo, passwords and restarts are his. Hand him the exact command.
- [ ] A `settings.json` edit, or any step the classifier denies Rai, goes to him the way [[24-changing-rai]] step 9 says.
- [ ] A fix that changes Rai follows the build rules in [[24-changing-rai]] step 5. A fix on a machine is declared in dev-env as [[16-machines]] step 6 says.

### 7. Guard and record

- [ ] He wants it never to happen again, so add a guard at the source. Past guards: fail-open hooks with an honest alarm, and a shutdown guard with a pairing watch.
- [ ] He declines extra machinery. Offer each guard as 2 or 3 options with one Recommended, and wait for his pick.
- [ ] A declined guard is recorded and not re-pitched. He may reopen it himself, as he did after the third Obsidian Sync failure.
- [ ] Write the lesson as a memory ruling in Claude Code's auto-memory (or `03-rai/auto-memory/` if you mount it there), indexed in its `MEMORY.md`. It holds the symptom, the cause, the check that found it, and how to apply it.

### 8. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Skills: `/omarchy → diagnose-crash` (crashes and core dumps), `/ubuntu → diagnostics` (heat, memory, disk, network, USB).
- Agents: the `sre` agent (jobs, timers, sync, the coordinator), the `debugger` agent (a failing script).
- Workflows: [[10-news-digest-recovery]], [[17-brain-healthcheck]] and [[04-debugging]] take their own failures. [[24-changing-rai]] owns a fix that changes Rai. [[16-machines]] owns a fix declared in dev-env.
