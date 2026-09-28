# News Digest Recovery

**Triggered by:** "news didn't fire" / "digest is placeholders" / "no news today"
**Cadence:** Ad-hoc: when the 03:00 local time Omarchy-hub run failed or shipped a partial/placeholder digest.
**Done when:** a real, complete digest for the date exists in `08-bawaba/daily/{date}.md` AND the root cause is fixed-forward so the next scheduled run succeeds.

The news spine runs unattended on the Linux hub. When it misses or ships
placeholders, this playbook is the triage order + the hard-rule gate: the actual
collection is the `news-digest` skill (`/news`). This runs on the hub; from a
laptop, drive it over SSH.

```
Triage unit → Identify failed source → Manual recovery run → HARD-RULE gate → Verify real → Fix-forward → Coordinator commits
```

> **Hard-rule frame (non-negotiable):** X is REQUIRED: no X, abort, never ship
> without it. All 6 sources are mandatory; the AI does not decide to skip. Fully
> autonomous (zero prompts). Scheduled runs collect X, Substack and Medium
> through headless CDP collectors, never a Chrome tab (see step 2). These
> override every other consideration.

---

## Steps

### 1. Triage: timer, run, or source?

- [ ] All work happens on the hub. From a laptop, reach it over keyless
      **SSH**. Never run the collection locally on the laptop.
- [ ] Run **`/ubuntu → diagnostics`** to inspect the units:
      `systemctl --user status news-daily.timer news-x-collect.timer` (did they fire?),
      `journalctl --user -u news-daily` / `-u news-x-collect` (did the run start / how did it exit?).
- [ ] Read the run logs in `~/.local/state/news-digest/logs/` for the date.
- [ ] `news-x-collect.timer` fires twice (21:00 and 00:00 local), each time doing
      a gentle headless X pre-pass into that day's `.runs/` dumps.
      `news-daily.timer` (03:00 local) runs the final X pass plus Substack, Medium,
      HN, Reddit, GitHub, and synthesis. A recovery may need to check either or both.

> **Decision Point**: where did it break?
> - **A timer never fired** (inactive/masked, missing graphical session) → unit problem, jump to step 6 after the recovery run.
> - **Run started but exited non-zero** → a source failed → step 2.
> - **Run "succeeded" but digest is placeholders** → silent source failure → step 2.

### 2. Identify the failed source

- [ ] The 6 mandatory sources: **HN, Reddit, X, Substack, Medium, GitHub Trending**.
- [ ] From the logs, find which source(s) returned empty or errored. Common culprits:
      a stale or logged-out X/Substack/Medium cookie jar (`x_LOGIN_FAILED.json`,
      `substack_LOGIN_FAILED.json`, `medium_LOGIN_FAILED.json`). Also common: Reddit
      JSON 403, which needs the RSS fallback, or a headless Chrome port (9223/9224)
      left stuck from a prior run.

> **Decision Point**: was **X** the failure?
> - X failed → the whole run is invalid. Do not patch around it. Fix X access (re-login `@johndoe` in the desktop Chrome so the cookie jar is fresh), then re-run.
> - A non-X source failed → still mandatory; recovery must collect all 6, not 5.

### 3. Manual recovery run

- [ ] Re-run the scheduled runner with the recovery flag:
      `RECOVERY=1 03-rai/skills/news-digest/scheduled/run-news-ubuntu.sh daily`.
- [ ] Or, for full manual control, invoke the **news-digest** skill directly (`/news day`) on the hub.
- [ ] There is no browser tab to babysit in scheduled/recovery mode. The headless
      collectors clone Chrome's on-disk cookies and drive their own throwaway
      profile. The desktop Chrome only needs to stay logged into x.com,
      substack.com and medium.com. It does not need to be running.

### 4. HARD-RULE gate (the one that bites)

- [ ] **X present?** No X → ABORT the run. Never ship a digest without X.
- [ ] **All 6 sources collected?** Missing one → not done. The AI does not skip sources.
- [ ] **Fully autonomous?** Zero permission prompts during collection.
- [ ] **Headless collectors, not the Chrome-MCP ladder, in scheduled/recovery mode.** The
      10-attempt Chrome/Playwright ladder is the interactive fallback only (see
      `news-digest` SKILL.md rule 11); it should not fire during a scheduled recovery run.

### 5. Verify the digest is genuinely real

- [ ] Open `08-bawaba/daily/{date}.md`. Confirm it is **populated, not placeholder**:
      no empty sections, no "TODO"/scaffold text, gems in feed style with real items.
- [ ] Spot-check that For You covers the full identity (max 2 items per topic) and that
      X content is present and text-only.

> **Decision Point**: still placeholders or thin after recovery?
> - Yes → a source is still failing silently → back to step 2; do not accept a partial.
> - No, real + complete → done with collection; proceed to fix-forward.

### 6. Fix-forward the root cause

- [ ] If the break was the **systemd unit/env** (timer not firing, missing PATH/uv
      deps, no graphical session), fix the unit forward via `/ubuntu → diagnostics`.
      That keeps the NEXT scheduled run succeeding unattended.
- [ ] Archiving of the prior digest to `13-archive/news/` is handled by the news skill: no manual move.

### 7. Sync (leave for the coordinator)

- [ ] The digest is written + **committed by the coordinator's** maintenance run
      (04/10/16/22:00 local): not from the Mac. Vault edits stay **local**.
- [ ] **Do not `git push` from the Mac**: single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Gating facts (verified, sourced)

| Fact | Value | Source |
|------|-------|--------|
| X pre-pass timer | 21:00 and 00:00 local time | `news-x-collect.timer` |
| Daily timer | 03:00 local time | `news-daily.timer` |
| Weekly timer | Sat 07:00 local | `news-weekly.timer` |
| Runner | `run-news-ubuntu.sh [daily\|weekly]`, env `RECOVERY=1` | `03-rai/skills/news-digest/scheduled/` |
| Logs | `~/.local/state/news-digest/logs/` | live |
| Output | `08-bawaba/daily/{date}.md` | live |
| Mandatory sources | HN, Reddit, X, Substack, Medium, GitHub Trending | hard rule |
| X | required: no X, abort | hard rule |
| Collection method (scheduled) | Headless CDP collectors (`_collect_x_headless.py`, `_collect_web_headless.py`), no paired browser, no claude-in-chrome MCP | hard rule |

---

## Connections

- Collection engine: `news-digest` skill (`/news`)
- Unit / timer / env diagnostics: `/ubuntu → diagnostics`
- Generic system triage: [[04-debugging]]
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
