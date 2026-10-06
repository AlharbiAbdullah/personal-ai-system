# News Digest Recovery

**Use when:** the scheduled news digest failed or came out thin. It shows as the NEWS DIGEST FAILED banner at session start, or the "News digest (daily) FAILED" desktop alert. A missing short digest shows as the "Bawaba digest FAILED" alert. Or an abort marker sits in `08-bawaba/`, a source is silent, or he says no news came.
**Not for:** 25 incident, for anything else broken on the hub. 17 brain healthcheck, for a sanity alarm.
**Done when:** the date's digest sits in `08-bawaba/daily/`, or the week's issue in `08-bawaba/weekly/`, with X in it and no placeholders. A daily has its short digest in `08-bawaba/digest/`. Every other source is collected or marked partial with its note. The cause is fixed forward, so the next scheduled run succeeds unattended.

The news runs unattended on the hub. When a run fails or ships thin, this is the triage order and the rule that governs the recovery. The collection itself is the `/news-digest` skill.

```d2
direction: right

alarm: "Banner, alert\nor no news"
triage: "1-2 Triage\ntimer, run, source"
run: "3 Recovery run\nattempt 3"
gate: "4 X gate"
verify: "5 Verify real"
fix: "6 Fix forward"

alarm -> triage -> run -> gate -> verify -> fix
verify -> triage: "still thin" {style.stroke-dash: 3}
```

> **The X rule.** No X, no digest, in every run: the 03:00 run, its retry and a recovery (his ruling, 2026-09-29). Partial X ships, with its note in the source-notes table. Zero X in the merged pool stops the run: no digest, and `08-bawaba/.news-failed-<date>.md` says why. Every other source is still attempted, and the AI never decides to skip one. Zero prompts, and headless collectors only.

> **Runner facts.** A failed 03:00 run already retried once, 10 minutes later, with the budget-protecting prompt. X's read budget is per account and does not reset within the same day. So a manual recovery is attempt 3, and it reuses the day's dumps.

---

## Steps

### 1. Triage: timer, run or source

- [ ] Work on the hub. From another machine, drive it over Tailscale SSH. Never run the collection anywhere else.
- [ ] Did the timers fire? `systemctl --user list-timers` shows `news-x-collect.timer` (21:00 and 00:00) and `news-daily.timer` (03:00).
- [ ] How did the runs exit? Read `journalctl --user -u news-daily` and `journalctl --user -u news-x-collect`.
- [ ] Read the day's logs in `~/.local/state/news-digest/logs/`. The daily log ends in a `RESULT:` line, and the x-passes log holds the two pre-passes.
- [ ] The 21:00 and 00:00 pre-passes each add a gentle headless X pass to the next digest's run dir. That dir is `03-rai/skills/news-digest/.runs/<date>/`, named for the digest's date.
- [ ] The 03:00 run does the final X pass, then Substack, Medium, HN, Reddit and GitHub, then the synthesis.
- [ ] Hand the triage to the `sre` agent. Inputs: the date, the three news timers, the log folder and the run dir. Returns: which timers fired, how each run exited, the failing phase and the failing sources, each with its log line. It writes nothing.
- [ ] Rai re-checks every log line the agent cites before acting on it.

> **Decision Point**: where did it break?
> - A timer never fired, or its unit failed before the run: a unit problem. Run the recovery at step 3, then fix the unit at step 6.
> - The run started and failed: the log names the phase. Step 2 finds which sources still need collecting.
> - The digest exists, but a source is empty with no note: a silent source failure. Step 2.

### 2. Find the failed source

- [ ] The six sources: HN, Reddit, X, Substack, Medium and GitHub Trending.
- [ ] Look in the run dir for login markers: `x_LOGIN_FAILED.json`, `substack_LOGIN_FAILED.json`, `medium_LOGIN_FAILED.json`.
- [ ] Compare each dump with its target in the skill's `config.yaml`. X counts the merged pool of all three passes: at least 700 For You and 110 Following.
- [ ] Other causes: Reddit's JSON API answering 403, which the RSS fallback covers. Or a headless Chrome still holds port 9223 (X) or 9224 (Substack and Medium).
- [ ] An API Usage Policy block on security news can kill a run mid-flight. It is a false positive, and a later attempt usually passes.
- [ ] The `sre` agent's report from step 1 names the source. Rai re-checks it against the run dir.

> **Decision Point**: what does the failure look like?
> - A login marker: he logs in again by hand, in the desktop Chrome, as `@johndoe` for X. The runner never logs in. The collectors copy that profile's cookies, so Chrome need not be running.
> - X trickles with no login marker: look first for the `login_or_feed_never_appeared` error, the sign of a weak headless login. Then try a gentler scroll.
> - X trickles right after a change to the collection-time enrichment: disable `expandPass()` in `chrome_snippets/x_observer.js` first. Its "Show more" clicks add an anti-bot signal.
> - X trickles night after night with a good login, so Premium no longer lifts the cap: the agreed next step is the twitterapi.io fallback. It costs money, so it waits for his go.
> - A stuck port: find the holder with `ss -ltnp`, then kill it by port (`fuser -k 9223/tcp`) or by PID. Never `pkill -f` or `pgrep -f`: in the harness they match their own shell.

- [ ] Never clone the full cookie jar. Each collector prunes its copy to its own sites. A full copy once let Google rotate his session and sign the real browser out.
- [ ] A Google or YouTube sign-out he reports: the fix is a re-login. It is not a breach, and no password reset is needed.

### 3. The recovery run: attempt 3

- [ ] Daily: `RECOVERY=1 ~/helm/03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh daily`. It skips the git pull, runs one attempt with the budget-protecting prompt, and never retries by itself.
- [ ] That prompt reuses every usable dump in the run dir and re-scrapes only the sources that have none. An X timeline dump with more than 50 tweets is never scraped again.
- [ ] Weekly: `RECOVERY=1 ~/helm/03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh weekly` rebuilds the issue from the dumps and the dailies. It scrapes nothing, so it is safe to redo.
- [ ] Short digest only, when the daily is fine: the coordinator writes a missing one at its next run (04, 10, 16 and 22). For it sooner, run `~/helm/03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh digest` outside those minutes. It reads today's daily, scrapes nothing, and does nothing when the digest is already complete. A recovered daily writes its short digest by itself.
- [ ] Watch the day's log for its `RESULT:` line, and `DIGEST:` for the short digest. A run can take up to two hours.
- [ ] There is no browser tab to watch. The headless collectors copy the desktop Chrome's cookies into a throwaway profile. Chrome only has to stay logged into x.com, substack.com and medium.com.
- [ ] An interactive `/news-digest day` run follows the skill's interactive rules instead: rule 9 aborts without X, and the Chrome ladder may fire. Use it only on his word.

### 4. The X gate

- [ ] The digest carries X. Partial X is fine with its note in the source-notes table, and so is a short source with its note.
- [ ] Zero X in the merged pool stopped the run. No digest ships, and `08-bawaba/.news-failed-<date>.md` says why. A dead login goes back to step 2: he logs in again, then attempt 3 runs.
- [ ] Every source was attempted. The AI never skips a source that works.
- [ ] Zero permission prompts during collection.
- [ ] Headless collectors only. The Chrome-MCP ladder in the skill's rule 11 is the interactive fallback, and it never fires in a recovery run.

### 5. Verify the digest is real

- [ ] Open `08-bawaba/daily/<date>.md`. It holds no `CLAUDE_FILL`, no `<!-- raw:` line and no `<!-- CLAUDE` block. The gems are in feed style, with real items.
- [ ] `08-bawaba/digest/<date>.md` holds the six callouts of `digest_style.md`, with no links and no headings.
- [ ] For You covers his full identity, at most 2 items per topic. X content is present and text-only. Every partial source carries its note.
- [ ] Hand the check to the `qa-tester` agent. Inputs: the digest path and this checklist. Returns: PASS or FAIL per item, with the line that proves it. It cannot edit files.
- [ ] Rai re-checks every FAIL before acting on it.

> **Decision Point**: still placeholders, or a source silent without a note?
> - Yes: a source still fails quietly. Back to step 2, and the X budget rule of step 3 still holds.
> - No: the digest is real. Step 6.

### 6. Fix it forward

- [ ] Fix the cause at its source, so the next scheduled run succeeds unattended. A job that needs a human is broken.
- [ ] Hand the fix design to the `sre` agent. Inputs: the confirmed cause, the unit or script involved, and the evidence. Returns: the smallest fix at the source and the check that proves it. It writes nothing.
- [ ] Rai builds the fix. A change to the runner, a collector or a unit is a change to Rai. [[24-changing-rai]] step 5 holds the build rules, and step 7 the proof.
- [ ] Every runner prompt keeps its never-background clause, `$HEADLESS_NOTE`. Under `claude -p`, ending the turn kills the run and its collectors.
- [ ] Archiving the prior digest is the news skill's job. No manual move.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Gating facts

| Fact | Value | Source |
|------|-------|--------|
| X pre-pass timer | 21:00 and 00:00 local (local time) | `news-x-collect.timer` |
| Daily timer | 03:00 local | `news-daily.timer` |
| Weekly timer | Saturday 07:00 local | `news-weekly.timer` |
| Runner | `run-news-ubuntu.sh daily`, `weekly` or `digest`, env `RECOVERY=1` | `03-rai/skills/news-digest/scheduled/` |
| Short digest | written after a complete daily, two attempts; a failure never fails the daily; the coordinator writes a missing one at its next run | `run-news-ubuntu.sh`, `digest_style.md`, `run-maintenance-ubuntu.sh` |
| Automatic retry | once, 10 minutes after a failed attempt 1; never under `RECOVERY=1` | `run-news-ubuntu.sh` |
| X read budget | per account, no reset within the same day | `run-news-ubuntu.sh` |
| Logs | `~/.local/state/news-digest/logs/` | live |
| Last outcome, read by the banner | `~/.local/state/news-digest/last-run.json` | `run-news-ubuntu.sh` |
| Run dir | `03-rai/skills/news-digest/.runs/<date>/` | the skill |
| Output | `08-bawaba/daily/<date>.md`, short `08-bawaba/digest/<date>.md`, weekly `08-bawaba/weekly/<ISO week>.md` | live |
| Abort marker | `08-bawaba/.news-failed-<date>.md` | the runner and the skill |
| Headless ports | 9223 for X, 9224 for Substack and Medium | the collectors |
| Sources | HN, Reddit, X, Substack, Medium, GitHub Trending | the skill |
| X rule | no X, no digest, in every run; partial X ships with its note | his ruling, 2026-09-29; the skill's Rule 0, item 3 |
| Scheduled collection | headless CDP collectors (`_collect_x_headless.py`, `_collect_web_headless.py`), no browser MCP | the skill |

---

## Connections

- Collection engine: `/news-digest`.
- Agents: `sre` (steps 1, 2 and 6), `qa-tester` (step 5).
- Workflows: [[25-incident]] step 1 routes a news failure here and takes every other hub failure. [[17-brain-healthcheck]] takes a sanity alarm. [[24-changing-rai]] builds the fix.
