---
name: news-digest
description: >
  Personalized news digest from HN, Reddit, X, Substack, Medium, GitHub Trending.
  USE WHEN the user wants a news briefing, asks what's happening, or says /news.
  Two modes: "day" (last 24h) and "week" (last 7 days). After each scheduled
  daily, a short digest is written from it (digest_style.md).
---

# news-digest

Collect and surface gems from 6 sources. Gems = things that teach, change
thinking, or reveal new tools. News awareness is secondary.

## Core Principle

The digest is a curated social feed, not a newspaper. The user learns from
social media. The #1 job is surfacing 80–100 gem candidates so the user can
pick their own daily winners. Present raw content: actual tweet text, actual
post titles, actual comments. Never summarize away the thing the user might
want to see.

## Hard Rules (Non-Negotiable)

**They override every other consideration including wall-time. The user reads the digest 10+ hours later — speed is irrelevant.**

1. **TIME / SPEED IS IRRELEVANT.** Never bail early to finish faster. Never shrink a target to wrap up sooner. Don't pick algorithms based on wall time. The user reads 10+ hours later. Spend the time needed.

2. **PER-SOURCE COUNT MATTERS.** Each source has its own target (see `config.yaml → sources`). Hit it or get close. Don't sacrifice one source's volume for another's. All 6 sources contribute distinct signal. Targets are floors, not ceilings — exceeding is fine; falling significantly short triggers retries.

3. **HUMANIZE — BE CAUTIOUS.** Bot-detection avoidance is a hard rule. Scroll with random delays + variance, occasional dwell pauses, jitter, no machine-perfect cadence. Avoid getting the account flagged at all costs. Implementation: scroll interval random in [600-900]ms, distance variance ±20%, dwell pause every 15-25 scrolls for 2-5s.

4. **FULLY AUTOMATED.** Zero user involvement after one-time setup. The user only types `/news`. No prompts, no questions, no confirmations. Self-recover from transient failures. Never pause for permission. (Skill already enforces this; restated here for emphasis.)

5. **QUALITY IS NON-NEGOTIABLE.** Apply the rigorous 6-axis scoring (see Scoring Algorithm section). Filter ruthlessly — drop ads, promos, low-substance posts, off-topic content. A short-but-quality digest beats a long-but-noisy one. Heuristic engagement-only scoring is forbidden. Spam-pattern blacklist is mandatory.

6. **NO OVERLAP — TWO LAYERS:**
   - **Cross-day**: never repeat, ever. Step 1.5 dedup against the persistent seen-URL ledger (`seen_ledger.jsonl`) — every displayed item is recorded forever; anything with a prior-date record is dropped. An old-but-unseen item is allowed ONCE (labeled with its real publish date), then never again. Already implemented in `present_v5.py`; do not skip.
   - **Cross-source within same day**: if the same news appears in HN + Reddit + X + Substack, MERGE into ONE entry that lists all sources OR keep the highest-context version and drop the others. **Never duplicate the same news across multiple gem entries.** Apply BEFORE scoring so a popular story doesn't dominate the gem list as 4 entries.

7. **UNDERSTAND THE USER.** Step 0 (load context) is mandatory: mindset, goals, who-i-am, tech-stack, active projects, ideas, MOCs. Score with weights that reflect actual interests. Tag items by genuine project relevance. Drop items in low-relevance buckets (frontend, mobile, gaming) unless exceptional.

8. **NEVER skip a source.** All 6 sources MUST be collected on every run. The decision to skip is not the AI's to make. (Reinforced by rule 2.)

9. **X is a dealbreaker. No X, no news.** If X For You OR X Following fails after all retry attempts, abort the entire run with a marker file. (Time-irrelevant rule 1 means abort is the LAST resort — exhaust all retries first.)

10. **Retry up to 10 times per source.** Per-source-aware retries precede the generic ladder. The AI does not get to give up. This governs the interactive Chrome-MCP fallback (see rule 11); the headless CDP collectors have their own retry/reload-recovery logic instead.

11. **One Chrome tab per source, Playwright as the last resort — interactive/manual fallback only.** In scheduled runs there is no paired browser and no claude-in-chrome MCP at all: X, Substack and Medium go through the headless CDP collectors (`_collect_x_headless.py`, `_collect_web_headless.py`), never a Chrome tab. If a human runs the skill interactively and the headless collectors are unavailable, the Browser Collection Template's ladder applies: one dedicated Chrome tab per source (no state sharing), claude-in-chrome first, Playwright last.

12. **Partial collection ≥ 90% of target = success. Below = retry.** Per-source targets and 90%-derived thresholds live in `config.yaml → sources.<source>.target` (and `success_threshold` where set explicitly). Scheduled runs judge X on the cumulative merged pool across its 3-pass schedule (see "X 3-pass schedule" below), not a single pass: success = ≥700 For You + ≥110 Following merged.

13. **The AI does not negotiate with itself.** If a step says "do X", do X. No rationalizing skips.

**Failure consequence:** if the AI violates any rule above without explicit user permission, the digest is invalid. The user will reject it. Re-run from scratch.

## Autonomous Mode

Runs fully autonomously. Do NOT ask for confirmation on any tool call.
Accept all browser actions, file writes, curl commands, and screenshots
without prompting. The user invokes `/news` and walks away.

**Autonomous ≠ permitted to skip work.** Autonomous means "don't pause for permission." It does not mean "make judgment calls about scope." Scope is fixed by the Hard Rules above.

## Scheduled Mode — Deadline Contract (v5.2, Non-Negotiable)

Applies ONLY when the launch prompt declares **SCHEDULED MODE** with a hard deadline (the systemd runner's watchdog). Interactive runs (`/news` typed by the user) ignore this section entirely.

**Rule 0 — outranks rules 1 and 9 in scheduled mode: a shipped digest with partial coverage beats no digest. The watchdog kills this session at the deadline; any plan that crosses it ships NOTHING — the only unacceptable outcome.**

(2026-06-06 incident: the run obeyed the burn-recovery ladder, started a 90-min X cooldown inside a 120-min watchdog, and died with all sources collected but no digest written.)

Mechanics (budgets in `config.yaml → scheduled_mode`):

1. **At run start**, record the wall-clock start time and compute
   `collection_deadline = start + run_budget_min − synthesis_reserve_min`.
2. **Before starting ANY cooldown or retry window**: if `now + cooldown + expected_window_time > collection_deadline`, do NOT wait. Write resume state (`x_foryou_state.json`), mark the source `partial` with its actual yield, and continue with the remaining sources, then synthesis.
3. **Rule 9 (X dealbreaker) is relaxed to zero X**: ship with whatever X yield exists and an explicit "reduced X coverage — burned session, resume state saved" note in the source-notes table. Zero X in the merged pool stops the run, whatever else was collected: write the marker file and ship nothing. No X, no digest, in every run, a manual recovery included (John, 2026-09-29).
4. **Rule 12 (≥90% or retry) is capped by the deadline**: retries happen only while they fit before `collection_deadline`.
5. **Synthesis + POST-FILL start no later than `collection_deadline`** and must finish — both `grep -c CLAUDE_FILL` and `grep -c '<!-- raw:'` at 0 — before the watchdog deadline.
6. Everything else (scoring, dedup, quality bar, humanized scrolling) is unchanged — quality rules cost no wall-clock waits.

## Config

Tunable parameters live in `~/helm/03-rai/skills/news-digest/config.yaml`:
subreddits, scroll tuning, retry thresholds, caps, scoring weights,
relevance tiers, cross-helm context files, chat prompts, mental models.

**Workflow stays in THIS file. Inputs live in config.yaml.** Read config
first when in doubt about any number or list below.

## Trigger

- `/news` or `/news day` — daily digest (default, last 24h)
- `/news week` — weekly MAGAZINE (Bawaba Weekly: dump-mined departments, see § Weekly Magazine)
- `/news chat` — companion mode (discuss today's items)

## Sources

| Source | Method | Target | Cap |
|--------|--------|--------|-----|
| X For You | **`_collect_x_headless.py` (headless CDP, PRIMARY)** — Premium acct, **3 gentle passes/night** (700 each), merge-write accumulates | ~900+ pool | uncapped |
| X Following | **`_collect_x_headless.py --phase following`** (same headless run, Following tab) | ~110+ pool (50/pass) | uncapped |
| Substack | **`_collect_web_headless.py` (headless CDP, PRIMARY)** — substack_observer.js + Load-more click loop on `/inbox` | 200 | uncapped |
| Medium | **`_collect_web_headless.py` (same headless run)** — medium_observer.js + 1 "More" click on `/me/following-feed/all` | 30 | **5 daily / 10 weekly** |
| Hacker News | curl/Python | 100 | **10 daily / 15 weekly** |
| Reddit | curl JSON API | ~200 from 18 subs | uncapped |
| GitHub Trending | curl/Python | 20 | uncapped |

**Each browser source gets its own dedicated Chrome tab** — do NOT share a tab between X For You and X Following, or between Substack and Medium. Open a fresh tab for each source. State leakage (cookies, scroll position, observer globals) across sources causes plateau bugs and confounds the retry ladder. curl sources run in parallel as background jobs from the start of Phase 1.

**X 3-pass schedule (throttle mitigation, 2026-06-16).** X's per-session timeline-injection throttle freezes the feed ~200 deep after ~2 min of scroll — Premium lifts the daily read cap (~10k) but NOT this per-session limit, so one session plateaus at ~350 (For You) regardless of tier. Fix: collect X across **three gentle fresh sessions per digest**, each `--target 700 --following-target 50`, accumulating into the day's `x_foryou.json`/`x_following.json` via `merge_write` (dedup by tweet id). The feed refills between passes, so the pool reaches ~900–1500 For You where a single session can't. Schedule: **21:00 + 00:00** run deterministically via `news-x-collect.timer` → `scheduled/collect-x-pass.sh` (no agent, no MCP; the 21:00 pass targets *tomorrow's* date); **03:00** is the final pass inside the digest run. Judge X success on the MERGED pool length, not any single pass.

---

## Process

### 0. Load Context (Before Collection)

Read these at the start of every digest run:

**Project + identity anchors** (globs resolved, file contents loaded):
- `~/helm/.helm-index/helm-index.md` — compact vault navigation
- `~/helm/02-ana/identity/who-i-am.md`
- `~/helm/02-ana/identity/tech-stack.md`
- `~/helm/02-ana/identity/goals.md` — goals (source of truth)
- `~/helm/02-ana/identity/mindset.md` — beliefs, mental models, frames (source of truth)
- `~/helm/05-projects/active/*/*.md` — active project non-code notes (no auto-generated Brief.md exists)
- `~/helm/09-ideas/*.md` — idea pipeline
- `~/helm/10-knowledge/_mocs/*.md` — topic MOCs

`04-work/` is explicitly excluded. Full list in `config.yaml` under `cross_helm_context`.

**Seen-URL ledger for dedup (Step 1.5):**
- `seen_ledger.jsonl` in the skill dir — loaded automatically by `present_v5.py`. Nothing to restore or stage; prior digests are no longer parsed.

### 1. Collect

Two phases run concurrently.

**Phase 1 (sequential, headless)**: run `_collect_x_headless.py` (final X pass) then `_collect_web_headless.py` (Substack + Medium), both as blocking foreground calls. No MCP, no paired browser. The Browser Collection Template below is the manual/interactive FALLBACK only.

```bash
export PATH="$HOME/.local/bin:$PATH"
~/helm/03-rai/skills/news-digest/_collect_web_headless.py --date YYYY-MM-DD
```

It clones the on-disk Chrome cookies (pruned to substack.com + medium.com — never Google, see the sign-out landmine), drives its own `--headless=new` Chrome on port 9224, merge-writes `substack.json` + `medium.json` (dedup by url), streams progress to `web_headless_status.json`, and on a dead login writes `substack_LOGIN_FAILED.json` / `medium_LOGIN_FAILED.json` per source and keeps going (exit 3 only when BOTH fail). Typical full run: under a minute.

**Phase 2 (parallel, curl)**: launch Reddit + HN + GitHub as background jobs at the start of Phase 1. See Per-Source Specs below.

All dumps land in `~/helm/03-rai/skills/news-digest/.runs/YYYY-MM-DD/` as JSON:
`x_foryou.json`, `x_following.json`, `substack.json`, `medium.json`, `reddit.json`, `hn.json`, `github.json`.

**Durable dump archive (2026-06-13)**: `.runs/` is the working scratch dir; at the end of every run the day's files are copied to `~/helm/13-archive/news/dumps/YYYY-MM-DD/` (by `present_v5.py` on success, and by the scheduled runner regardless of outcome). That archive is git-tracked and synced Mac↔Ubuntu — every collected item is kept forever, not just the ~100 displayed. **Scratch pruning (2026-07-03)**: the runner then deletes `.runs/` day dirs older than 3 days after checksum-verifying the archive copy — the archive is the single durable home; `.runs/` holds only the live window (before this, every day stayed in both places forever and 132MB of dumps were double-tracked in git).

### 1.4. Enrich Substack + Medium (MANDATORY — do not skip)

Substack and Medium collection captures only URL + title + (sometimes) subtitle. Without article body and engagement signals, every item scores near-zero in `present_v5.py` and **none of them make it into the digest**. This was the cause of the 2026-05-09 "0 substack / 0 medium in digest" bug. Enrichment is not optional.

Run both scripts immediately after Step 1, before any dedup or scoring:

```bash
cd ~/helm/03-rai/skills/news-digest
./_enrich_substack.py --date YYYY-MM-DD   # ~10–15s for 200 items
./_enrich_medium.py   --date YYYY-MM-DD   # ~5–10s for 75 items
```

(v5.9: both scripts carry uv script headers — plain `python3` fails on missing `httpx`.)

These scripts fetch each article URL in parallel, extract body text + engagement (likes/restacks/comments_count for Substack; claps for Medium), and write the enriched fields back into the existing JSON dumps.

**Validation after enrichment** (verify before proceeding to Step 1.5):
- Substack: `bodies extracted` should be ≥ 90% of collected count.
- Medium: `bodies extracted` should be ≥ 70% (Medium serves paywalls more aggressively; some failures are normal).
- Substack: `engagement signals` should be ≥ 50% of collected count.
- Publish dates (v5.4): `dates extracted` ≥ 90% Substack / ≥ 60% Medium. Dates feed the ledger's old-once labeling — items without dates still ship and still get ledgered, only the label degrades.
- If either source falls below these thresholds, retry once. If it still fails, ship `status: partial` for that source — but ship.

**Why this is mandatory, not optional**: the universal-axis scoring needs body text to detect teaching content, tool discovery, artifacts, postmortems. The identity-axis scoring needs body text to match Helios/OpenKit/local/data-eng/system-design keywords. Without enrichment, substack/medium items score off the title alone (too short) and uniformly lose to HN/Reddit/X items that have selftext + comment context. Yesterday's digest had 31 substack + 8 medium because enrichment ran. Today's first attempt had 0/0 because it didn't.

### 1.5. Dedup Against Seen-URL Ledger (v5.4)

After Collection completes, before Filter + Score, drop anything that has EVER been displayed in a digest. `present_v5.py` does all of this automatically — Claude's job is only to confirm the log line.

**Source of truth**: `seen_ledger.jsonl` in the skill dir. Git-tracked, append-only, never pruned (~25 KB/day). One JSON record per displayed item: `{"u": <normalized url>, "t": <normalized title>, "a": <author>, "src": ..., "first_seen": "YYYY-MM-DD", "published": "YYYY-MM-DD"|null}`. After every successful (non-`--test`) run, the script appends a record for every item shown in News Wire + Top Shelf + Feed.

**Dedup key — two matchers, either one drops the item:**

1. **URL normalized match.** Lowercase host, strip trailing slash, drop fragment + query (covers tracking params).
2. **Exact (normalized title + author) match.** Only when both sides have an author — exact-on-normalized, not fuzzy, so lookups stay O(1) against a ledger that grows forever.

**Same-date re-run safety**: records with `first_seen == today` are ignored by the dedup, so re-running on the same date never suppresses today's own pool. The append step is guarded too — re-runs append 0 duplicate records.

**Old-once rule**: an item the ledger has never seen passes once even if it's months old; if its publish date is older than `dedup.stale_label_days` (3), it renders with a `· *published YYYY-MM-DD*` label so its age is honest. Then it's ledgered and never returns.

**Confirm in the script log**: `Ledger: N prior URLs` with N > 0 (the backfill seeded ~2.6k). If N = 0, the ledger file is missing — stop and investigate before shipping, or the digest will resurface weeks of old items.

**Skip Step 1.5 when**: mode = `week` (inherits dedup from component dailies).

### 1.6. Cross-Source Dedup (v4.5, north-star rule 6)

**Within the same day, never list the same news twice across sources.** If the same story appears in HN + Reddit + X + Substack, merge into ONE entry that lists all sources, OR keep the best-context version. Apply BEFORE scoring so popular stories don't dominate the gem list as 4 entries.

**Matchers (any one triggers a merge):**

1. **URL normalized match** (same as 1.5 — lowercase host, strip tracking params, strip trailing slash, drop fragment).
2. **Title fuzzy match** (Levenshtein ≤10 OR ≥80% substring overlap, lowercased + punctuation stripped). No author-required clause here — different sources legitimately surface the same story under different bylines.
3. **External-link convergence**: if HN, Reddit, X, etc. all point to the same external article URL, merge by that external URL.

**Merge rule:**
- Pick the entry with the most context (longest text + highest engagement) as the "primary."
- Append `(also seen on: HN 234p, r/sub 45c, X @author)` to its source line.
- Drop the secondary entries from the pool.
- Engagement totals add together for the merged entry's score.

**Output of Step 1.6**: pool with no intra-day duplicates + `deduped_cross_source` counter for the digest header.

### 2. Filter, Score, Order

**Noise gate (binary, runs first)**: drop before scoring.
- Pure announcement with no substance ("We're excited to announce…")
- Meme / joke post (unless exceptionally sharp AND relevant)
- Paywalled with no preview
- Rage bait / engagement farming
- "Look at my setup" without transferable technique
- Pure community sentiment / vibes / drama
- Cool-but-irrelevant technical feats outside user's domains

**Score** every surviving item via the Scoring Algorithm (below). Produces a `final` score per item + a hidden comment tag.

**Apply per-source caps** (from config.yaml): HN top 10 daily / 15 weekly; Medium top 5 daily / 10 weekly. All others uncapped within the global 80–100 gem budget.

**Order** by `final` descending across all sources mixed. Top 20–30 → Top Shelf. Next 50–70 → Feed.

### 3. Synthesize (v5.1 — `present_v5.py`)

Run the v5 presentation script:

```bash
cd ~/helm/03-rai/skills/news-digest
./present_v5.py --date YYYY-MM-DD --out YYYY-MM-DD.md
```

**Re-running is safe (v5.4):** dedup reads `seen_ledger.jsonl`, not the daily/ folder, and today's own ledger entries never suppress a same-date re-run. No archive-restore dance needed. The end-of-run archiving (prior dailies → `~/helm/13-archive/news/daily/`) still happens — it's vault hygiene, not dedup state. Confirm the script log shows `Ledger: N prior URLs` with N > 0. For experiments, use `--test`: writes to `.runs/<date>/preview.md`, skips archiving and the ledger append.

Output goes to `~/helm/08-bawaba/daily/YYYY-MM-DD.md`. The script emits a SKELETON with `<CLAUDE_FILL_*>` placeholders + `<!-- raw: ... -->` scaffolding hints + `<!-- CLAUDE INSTRUCTIONS -->` blocks. **Six sections in order**: News Wire (≤15 after trim) → Hot Topics (0–3) → Top Shelf (~20–30) → Feed (~60) → Wisdom (0–3) → Deep Dive (1 + 0–2 alts).

After the script runs, Claude post-fills in this order:
1. News Wire editorial + briefs (trim candidates to tech news, write neutral wire sentences, set NW count — see the in-file instruction block)
2. Hot Topics (read all displayed items, identify themes, write 2–3 paragraphs each with inline citations)
3. Top Shelf hooks (hook craft spec, 1–2 sentences each, use the `<!-- raw: -->` comment as context)
4. Feed hooks (same spec, 1 sentence each, more compact)
5. Wisdom (Model + Insight for each quote)
6. Deep Dive (title + essay; override the script's pick if a more substantive candidate exists)
7. Hook self-review pass (mandatory — see Post-fill workflow)
8. Update `<CLAUDE_FILL_HT_COUNT>` + `<CLAUDE_FILL_NW_COUNT>` in the `**Sections:**` line
9. **Cleanup**: strip ALL `<!-- raw: ... -->` lines AND delete every `<!-- CLAUDE INSTRUCTIONS -->` block. The user must never see scaffolding.

Full spec in the **V5 Presentation Workflow** section below.

### 4. Save

Digest: `~/helm/08-bawaba/daily/YYYY-MM-DD.md` (day) or `~/helm/08-bawaba/weekly/YYYY-WWW.md` (week).
Dumps stay in `.runs/YYYY-MM-DD/` for future scoring calibration.

### 5. Post-Run Cleanup (mandatory — v4.4)

After the digest is written AND on every abort path (X-strict marker, signed-out abort, etc.), close all browser state opened by this run:

1. For each tab opened during the run, call `mcp__claude-in-chrome__tabs_close_mcp(tabId)`.
2. Closing the last MCP tab triggers Chrome's auto-removal of the tab group (verified in f03). The next run starts from a fresh `tabs_context_mcp{createIfEmpty:true}`.
3. If Playwright was used (attempts 7-10 fallback), call `browser.close()` on the Playwright instance.
4. Do NOT close the user's main Chrome browser process — only the MCP-managed and Playwright-managed instances.

**Reason**: leaving tabs alive after a digest run consumes memory, leaves credentialed sessions visible in the user's task switcher, and pollutes the next run's tab context. The user explicitly required cleanup as a mandatory post-run step on 2026-05-06.

**This step runs on every exit path — success, partial, or abort. Never leak tabs.**

A run that ends partial or failed, or leaves an abort marker, goes to [[10-news-digest-recovery]] in the next interactive session.

---

## Browser Collection Template

All three browser sources (X, Substack, Medium) follow this spec. Parameters fill from `config.yaml` + the Per-Source Specs table.

**Parameters:**
- `url` — navigate target
- `target` — item count goal
- `observer_script` — path under `chrome_snippets/`
- `dump_key` — `window.__<key>_*` API + `<key>.json` filename
- `scroll_delta` — pixels per scroll
- `scroll_interval_ms` — delay between scrolls
- `batch_size` — scrolls per batch before size check
- `login_check_cue` — DOM element / text that proves login

**Steps:**

1. **Open Chrome tab** via the 4-step escalation (see Retry Ladder).

2. **Navigate**: `mcp__claude-in-chrome__navigate` to `{url}`.

3. **Verify login**: `mcp__claude-in-chrome__computer` action `screenshot`. Confirm `{login_check_cue}` visible. On failure → login-expired error (triggers retry attempt 2+).

4. **Inject media-blocking CSS** via `javascript_tool` (standard across sources):
```javascript
() => {
  if (document.getElementById('__news_no_media')) return 'already';
  const s = document.createElement('style');
  s.id = '__news_no_media';
  s.textContent = `
    video, [data-testid="videoPlayer"], [data-testid="videoComponent"] { display: none !important; max-height: 0 !important; }
    [data-testid="tweetPhoto"] img, [data-testid="card.layoutLarge.media"] { max-height: 50px !important; overflow: hidden !important; }
    img:not([alt*="avatar"]):not([alt*="Avatar"]) { max-height: 50px !important; overflow: hidden !important; }
  `;
  document.head.appendChild(s);
  return 'installed';
}
```

5. **Inject observer**: read `~/helm/03-rai/skills/news-digest/chrome_snippets/{observer_script}` and pass to `javascript_tool`. All three observers export the same control surface:
   - `window.__{key}_size()` → count
   - `window.__{key}_dump()` → JSON string of captured items
   - `window.__{key}_reset()` → clear the Map (used between X For You / Following)
   - `window.__{key}_uninstall()` → cleanup

6. **Verify observer installed**: `__{key}_size()` returns a number.

7. **Humanized scroll loop — DETACHED, fire-and-forget** (v5.3, north-star rule 3):
   **`javascript_tool` has a hard ~45-second CDP timeout.** A single blocking scroll loop (one long call that scrolls + sleeps *inside* it) is KILLED at ~45s and yields almost nothing — this caps X at ~8–12 tweets and **masquerades as a server throttle**. The 2026-06-06→08 "X early-morning throttle" incidents were this bug, NOT a rate-limit (proven 2026-06-08: a detached scroller pulled 2006 from the same account/session that a blocking loop capped at 17). Never drive scrolling from one long call. Instead:
   - **Inject a detached scroller** as a fire-and-forget `setInterval` that keeps running in the page *after* the `javascript_tool` call returns (return immediately, e.g. `return 'started'`). The observer (step 5) auto-captures tweets as they fly by — the scroller only has to keep the timeline moving. Each tick it writes `window.__x_status = {size: __{key}_size(), ticks, stalls, ts}`.
   - **Humanize inside the scroller** (bot-avoidance is mandatory): interval random in `[scroll_interval_ms-100, scroll_interval_ms+200]` (≈600–900ms); distance `scroll_delta * (1 + random(-0.2,0.2))` (±20%); a **dwell pause** of `random(2000,5000)`ms every 15–25 ticks (re-arm the interval after the dwell). Real randomness, not machine-perfect cadence.
   - **Self-terminate** inside the scroller after 120s of zero size growth (plateau) OR when `size ≥ target`; on stop set `__x_status.scrolling = false`.
   - **Poll from OUTSIDE** with SHORT `javascript_tool` reads (each far under 45s): read `window.__x_status` / `__{key}_size()` every ~15–20s. Keep polling for as many minutes as collection needs — the wall-clock lives in the detached scroller, never in a single call.
   - Stop polling when `__x_status.scrolling = false` (plateau/target) OR size ≥ `target`.

   (Substack/Medium use their own click-based paginators — see Per-Source Specs — and are not subject to this 45s-cap problem.)

8. **Dump**: call `__{key}_dump()`, parse JSON (double-unwrap if `json.loads(json.loads(raw))` is needed), save to `~/helm/03-rai/skills/news-digest/.runs/{date}/{key}.json`.

---

## Per-Source Specs

### Collectors + fallbacks

Every source has a primary script; some have a fallback for when the primary path is blocked. Reach for the fallback by name instead of re-deriving the collection logic from scratch.

| Source | Primary | Fallback (when primary fails) |
|---|---|---|
| X | `_collect_x_headless.py` (headless CDP) | Chrome-MCP detached-scroller ladder, interactive only (below) |
| Substack | `_collect_web_headless.py` (headless CDP) | `_substack_rss.py` — per-subscription RSS feeds (`substack_subscriptions.json`), used when `/inbox` won't paginate |
| Medium | `_collect_web_headless.py` (headless CDP) | `_medium_rss.py` — beat-relevant tag RSS feeds, used when the personalized feed is signed out |
| Hacker News | `_collect_curl.py` (curl + requests, runs HN/Reddit/GitHub concurrently) | — |
| Reddit | `_collect_curl.py` (JSON API, `hot.json`) | `_collect_reddit_rss.py` (parallel Atom RSS) if the JSON API 403s; `_reddit_rss_paced.py` (sequential, jittered) if the parallel RSS fetch itself gets rate-limited |
| GitHub Trending | `_collect_curl.py` (HTML parse) | — |

### X / Twitter

Account: `@johndoe` (Chrome logged in, **X Premium** — read cap ~10k/day).

**PRIMARY METHOD (v5.6) — headless CDP collector. Use this first, every run:**

```bash
export PATH="$HOME/.local/bin:$PATH"
~/helm/03-rai/skills/news-digest/_collect_x_headless.py \
  --date YYYY-MM-DD --target 2000 --following-target 500 --phase both
```

This is a **blocking foreground** call (no background polling needed — ideal under `claude -p`): it collects For You then Following in one headless Chrome and writes `.runs/{date}/x_foryou.json` + `x_following.json`. Watch `.runs/{date}/x_headless_status.json` (or its stdout) for live `size`. **Success = ~2000 For You + Following up to 500 (Following is activity-bounded — ship whatever it plateaus at).** Exit codes: `0` ok · `2` chrome/devtools failure · `3` not logged in (it also writes `x_LOGIN_FAILED.json` — re-login `@johndoe` in Chrome and rerun; do NOT ship a zero-X digest). It self-recovers under throttle via reload-cycles. Why headless-CDP over MCP: no extension pairing (the #1 3am hang), no 45s `javascript_tool` cap, throwaway profile so it never disturbs the live session.

**FALLBACK ONLY (interactive runs, or if the script's chrome won't launch):** the Chrome-MCP detached-scroller ladder documented below. The per-account read-cap "burn ladder" (W1–W6 cooldowns) is **mostly obsolete on Premium** — the ~10k cap means a single gentle window clears the target; keep the ladder only as a degraded-day safety net, and never burst toward the cap.

| Session | URL | target | dump_key | Observer | Login cue |
|---|---|---|---|---|---|
| For You | `https://x.com/home` | 600 | `x_foryou` | `x_observer.js` | Home feed visible, `[data-testid="SideNav_NewTweet_Button"]` present |
| Following | `https://x.com/home` (click "Following" tab) | 180 | `x_following` | `x_observer.js` (reset first) | Following tab `aria-selected="true"` |

Both: `scroll_delta=800`, `scroll_interval_ms=700`, `batch_size=50`.

**For You algorithm (adaptive burn-recovery ladder, target 600):**

Plateau detector tolerance: **120 seconds of zero growth** before declaring plateau (was 60s). Long-running For You scrolls have natural mid-stream lulls — bailing at 60s of stall stops collection prematurely. Validated: 2259 in a single warm-session window (historical, at the old 2000 target — the bar is now 600; a warm session hits it in ~5 min).

The ladder has **6 windows** (W1-W6) with progressively longer cooldowns. The standard 3-window / 15-min cooldown ladder works for warm sessions. The extended W4-W6 windows (45 / 90 / 180-min cooldowns) recover from BURNED sessions where the user has heavily exercised `@johndoe` earlier in the day. **Per user spec (2026-05-08): time is acceptable; correctness > speed.**

**Standard path (warm session):**

1. **W1** (cooldown: 0 min): open fresh tab, navigate to `x.com/home`, inject `x_observer.js`, scroll until plateau (120s of zero growth). Dump to `x_foryou-attempt1.json`. Record yield Y1.
2. If cumulative ≥ 540: **SUCCESS**, write `x_foryou.json`, skip remaining windows.
3. **W2** (cooldown: 15 min): close W1 tab, open fresh tab, navigate (re-navigation required — Map-reset alone won't probe new budget), inject observer, scroll until plateau. Dump `x_foryou-attempt2.json`. Y2.
4. If cumulative (deduped) ≥ 540: **SUCCESS**, skip W3.
5. **W3** (cooldown: 15 min): same flow. Dump `x_foryou-attempt3.json`. Y3.
6. If cumulative ≥ 540: **SUCCESS**.

**Burn-recovery extension (extended path):**

After W3, if cumulative still < 540, do NOT abort. Continue:

7. **W4** (cooldown: 45 min): first long wait. Validated to restore ~60% capacity for moderately-burned sessions. Dump `x_foryou-attempt4.json`. Y4.
8. If cumulative ≥ 540: SUCCESS.
9. **W5** (cooldown: 90 min): second long wait. Allows X's per-account budget to reset for heavier burns. Dump `x_foryou-attempt5.json`. Y5.
10. If cumulative ≥ 540: SUCCESS.
11. **W6** (cooldown: 180 min, fresh Chrome profile): final escape. **Switch to a separate Chrome profile** (e.g., create `~/.cache/news-digest-x-recovery/` profile if not present and prompt the user to re-login on first use). 3-hour cooldown + fresh profile addresses persistent throttling. Dump `x_foryou-attempt6.json`. Y6.
12. Merge all attempts, dedup by tweet id, write `x_foryou.json`.
13. If cumulative ≥ 540: SUCCESS.
14. If still < 540: ship `partial` with explicit burn-status note. **OR** write a resume marker (`.runs/{date}/x_foryou_state.json` with `next_attempt_eta` ~6 hours forward) and let the user resume the next morning when the session is naturally fresh.

**Burn detection — adaptive short-circuits:**

After EACH window, classify session state from the yield:

| Yield (this window) | Classification | Next action |
|---------------------|----------------|-------------|
| ≥ 450 | Healthy / warm | Continue standard ladder |
| 150–449 | Warm | Continue standard ladder |
| 60–149 | Suspected burn | **Skip remaining quick windows; jump to W4** (45-min wait) |
| < 60 | **Burn confirmed** | Escalate next cooldown to ≥ 90 min |
| Yn < 0.5 × Y_{n-1} | Declining (burn confirming) | Escalate next cooldown to ≥ 90 min |

Specifically: **if W1 < 150, skip W2 and W3; jump directly to W4** (45-min cooldown). Hammering a burned session with two more 15-min retries wastes 30 minutes for almost no yield.

**Wall time bounds:**

| Scenario | Wall time |
|----------|-----------|
| Best (W1 hits 540+) | ~5 min |
| Typical warm (W1+W2) | ~25 min |
| Worst standard (W1+W2+W3) | ~40 min |
| Mild burn (W1 → jump to W4) | ~50 min (45 wait + plateau) |
| Heavy burn (W1+W4+W5) | ~150 min (~2.5 hr) |
| Severe burn (full ladder) | ~180 min (3 hr hard cap, config `max_total_wall_min`) |

**State persistence:** after each window, write `.runs/{date}/x_foryou_state.json`:

```json
{
  "windows": [
    {"name": "W1", "yield": 120, "cumulative_after": 120, "burn_classification": "suspected_burn"},
    {"name": "W4", "yield": 380, "cumulative_after": 500, "cooldown_min_used": 45}
  ],
  "next_attempt": "W5",
  "next_attempt_earliest_eta": "2026-05-08T14:30:00Z",
  "total_wall_time_s": 5400,
  "max_wall_min_remaining": 270
}
```

If a run is interrupted during a long cooldown, `/news-digest` can read this state and resume from the right window at the right time.

**Always preserve partials:** every `x_foryou-attemptN.json` is kept on disk so a future run (or the user) can recover collected tweets even if the run ultimately aborts.

**Following algorithm:**
1. **W1**: after For You's last window completes, navigate same flow to `x.com/home`, DOM-click `Following` tab, reset observer, scroll until plateau (per f14: ~135-200 captures, function of recent followed-account activity).
2. If cumulative ≥ 162 (90% × 180): SUCCESS.
3. **W2 fallback**: 15-min cooldown + W2 fresh tab. Per f17, W2 typically adds 10-30 — modest but useful when W1 lands low.
4. Merge attempt1 + attempt2, dedup, write `x_following.json`.

**Performance**: ~1.1 tweets/scroll at 700ms. For You ≈ 10 min best (W1 only) / 25 min typical (W1+W2) / 40 min worst (W1+W2+W3). Following ≈ 3 min (best) / 20 min (with W2 fallback).

### Substack (v5.9: headless via `_collect_web_headless.py`; MCP algorithm below = fallback)

Account: `@johndoe` (Chrome logged in — the headless collector reads its cookie DB).

| URL | target | dump_key | Observer | Login cue |
|---|---|---|---|---|
| `https://substack.com/inbox` | 200 | `substack` | `substack_observer.js` | Avatar top-right OR "Sign out" present |

**Pagination is button-driven, NOT scroll-driven.** `/inbox` renders ~20 cards initially and paginates only via a "Load more" button. Scroll alone won't trigger more loads.

**Algorithm:**
1. Open fresh tab, navigate to `https://substack.com/inbox`.
2. Verify signed-in (login_check_cue).
3. Inject `substack_observer.js` (selector covers `/p/` AND `/p-` per the 2026-05-06 fix).
4. Call `await window.__substack_loadmore_loop({target: 200, max_clicks: 20})`. The observer self-clicks "Load more" every 3s, captures new anchors, stops when target met OR button vanishes OR 3 stable ticks.
5. Call `__substack_dump()`, save to `.runs/{date}/substack.json`.

Expected wall time: ~45-60s for 200 cards (~10 clicks). Reachable ceiling for this account is ~250 (f15).

**Selector note**: the observer matches both `a[href*="/p/"]` and `a[href*="/p-"]` (the `/p-` form is what `/inbox` uses; the `/p/` form is what `/home` and per-publication pages use). Class names for title extraction are obfuscated and drift — `[class*="title"]` is the survival selector; check via `mcp__claude-in-chrome__read_page` if extraction rate drops.

### Medium (v5.9: headless via `_collect_web_headless.py`; MCP algorithm below = fallback)

Account: Google SSO (John's account; email lives in `02-ana/identity/`). The headless collector needs only the medium.com session cookies — it never carries Google auth and can never re-login; if the Medium session dies, log in once in the desktop Chrome.

| URL | target | dump_key | Observer | Login cue |
|---|---|---|---|---|
| `https://medium.com/me/following-feed/all` | 30 | `medium` | `medium_observer.js` | `/me/...` link in nav; no `/m/signin` button |

**The `medium.com/` homepage is NOT the personalized feed** — it's a 3-article hero shelf even when signed in. The actual following feed is `/me/following-feed/all` which renders ~25 articles.

**Algorithm:**
1. Open fresh tab, navigate to `https://medium.com/me/following-feed/all`.
2. Verify signed-in via DOM probe.
3. Inject `medium_observer.js` (selector now uses `h2.closest('a')` + URL resolver per the 2026-05-06 fix; previous selector missed 80% of articles due to relative-URL filtering).
4. Capture initial render (~25 articles).
5. Call `await window.__medium_click_more_once()`. Single click on the "More" button adds ~5 articles, then the button vanishes (this is not a true paginator).
6. Call `__medium_dump()`, save to `.runs/{date}/medium.json`.

Expected wall time: <10s. Realistic ceiling: 30 articles (f16). To go higher requires walking multiple `/me/following-feed/{writers,publications,...}` endpoints — out of scope; deferred.

### Hacker News (curl)

Run via `_collect_curl.py` (see "Collectors + fallbacks" above), which implements:

```bash
# day mode
curl -s "https://hacker-news.firebaseio.com/v0/topstories.json"
# week mode
curl -s "https://hacker-news.firebaseio.com/v0/beststories.json"
```

Fetch top 100 IDs, then each item via `/v0/item/{id}.json` concurrently (asyncio / concurrent.futures). Extract: title, url, score, descendants, by, time. For items with `descendants >= 100`: fetch top 2 comment texts — the comment is often the gem.

### Reddit (curl, with RSS fallbacks)

Subreddit list in `config.yaml` (`reddit_subs.*`, 18 total). Run via `_collect_curl.py`, which implements:

```bash
curl -s -H "User-Agent: Mozilla/5.0 (X11; Linux x86_64) Gecko/20100101 Firefox/129.0" \
  "https://www.reddit.com/r/{sub}/hot.json?limit=50"
```

Fans out across all subs in parallel. Filter posts by age (<48h day mode, <7d week mode). For posts with `num_comments >= 50`: fetch top 2 via `{permalink}.json`. ~18 × 50 = ~900 raw → ~200 after age filter + dedup. If the JSON API 403s (datacenter IP block), fall back to `_collect_reddit_rss.py` (parallel Atom RSS); if that fetch itself gets rate-limited, fall back further to `_reddit_rss_paced.py` (sequential, jittered). RSS fallbacks lose `score`/`num_comments` (engagement goes neutral) but keep volume and content signal.

### GitHub Trending (curl)

Run via `_collect_curl.py`, which implements:

```bash
curl -s "https://github.com/trending?since=daily"   # day mode
curl -s "https://github.com/trending?since=weekly"  # week mode
```

Parse HTML (BeautifulSoup). Extract: repo, description, language, stars-delta, total stars. For top 10: fetch first paragraph of README (description alone is often too vague).

---

## Retry Ladder

**Hard rule (see top of file): every source retries up to 10 attempts. The AI does NOT get to declare "good enough" mid-ladder. The AI does NOT skip Substack/Medium/X-Following because "we have enough from other sources." That decision is reserved for the user.**

Triggered when a source collects **< target × 0.90** (10% shortfall).

**Per-source isolation: each source gets its own dedicated Chrome tab.** Do not share a tab between X For You and X Following — open a fresh tab for each. Same for Substack and Medium. State leakage across sources causes plateau bugs and confounds the retry ladder.

**Attempts 1-3 (claude-in-chrome, same tab):**

| Attempt | Strategy |
|---|---|
| 1 | Primary defaults from `config.yaml`. Fresh tab dedicated to this source. |
| 2 | Close tab + open new tab in same Chrome group. Slower scroll (`scroll_interval_ms × 2`). Scroll up then down once to reset lazy-load state. |
| 3 | Hard page refresh on a fresh tab. Alternate selector set if DOM changed (read page, update observer). Try with media-blocking **OFF** (some feeds gate lazy-load on image visibility). |

**Attempts 4-6 (claude-in-chrome, fresh Chrome session per attempt):**

| Attempt | Strategy |
|---|---|
| 4 | Close all MCP tabs in the group. Recreate the tab group via `tabs_create_mcp`. Re-navigate. Treat as a clean Chrome session for this source. |
| 5 | Same as 4, but with the slower scroll + alternate selectors from attempt 2/3 stacked. |
| 6 | Same as 4, with media-blocking off + observer rewritten against the live DOM (use `mcp__claude-in-chrome__read_page` to inspect what selectors actually match before scrolling). |

**Attempts 7-10 (Playwright MCP, persistent profile):**

| Attempt | Strategy |
|---|---|
| 7 | Playwright with persistent profile at `~/.cache/playwright-newsdigest/` (must have live logins). Default scroll tuning. |
| 8 | Playwright, slower scroll, alternate selectors. |
| 9 | Playwright with a fresh context (new browser instance, same profile). |
| 10 | Playwright with the observer rewritten against the live DOM. Last attempt before abort. |

**At every attempt:** dump whatever has been collected so far to `.runs/YYYY-MM-DD/{source}.partial-attemptN.json`. The dumps accumulate; the highest-count dump becomes the source-of-truth if all 10 attempts fail. **Never lose data on retry.**

**Wall-clock guidance** (informational, NOT a kill switch — the retry ladder runs to 10 regardless):
- X total (For You + Following): expect ~30-40 min worst case across all retries.
- Substack: expect ~20-25 min worst case.
- Medium: expect ~15 min worst case.

If real-time exceeds these by 2x, the AI MAY check in with the user — but only via a status update, never via a "should I skip" question. The user decides; the AI never proposes the skip.

**After attempt 10:**

- **X For You OR X Following still < 90%**: **abort the entire run** (X is dealbreaker). Write a marker file at `~/helm/08-bawaba/.news-failed-YYYY-MM-DD.md` with:
  - Attempt counts per strategy (1-10)
  - Last error per attempt
  - Collected count vs target per attempt
  - Timestamp
  - Suggested remediation (re-login in desktop Chrome, rerun the headless collector and read its exit code, try Playwright manually, check x.com rate-limit status)
  - Highest-count dump location
  
  No digest ships. The marker file is the notification.

- **Substack / Medium / GitHub still < 90%**: ship the digest with `status: partial` in the header AND a `notes` entry explaining the failure mode + which retry attempts were used. **Do NOT silently skip the source.** The user must see the failure attempt count, last error, and the collected/target ratio. The source still appears in the header table; the digest still attempts to use whatever was collected.

- **HN / Reddit (curl) still < 90%**: same as Substack/Medium — partial with status, notes, and the highest-count dump. These sources are usually network-stable; sub-90% is itself a signal worth surfacing.

**Mid-session failures** (browser crash, login expired during scroll):
1. Retry 1: navigate away + back, retry scroll from current position.
2. Retry 2: full tab reopen, restart from scratch (observer re-install).
3. After 2 mid-session failures: treat as current-attempt failure, advance to next attempt level. **Do not advance to the next source.** The current source still owns the next slot in the ladder.

**curl sources (HN, Reddit, GitHub):**
- Single endpoint fail: retry that endpoint up to 3 times with backoff (1s, 2s, 4s). Then skip just that endpoint; the source continues.
- Entire source fails (all endpoints 429/500): retry the whole source up to 3 times across 60s spacing. If still failed, mark `status: failed` in header with notes — but the digest still ships (curl sources are not dealbreakers; only X is).

---

## Scoring Algorithm

Every item that passes the noise gate gets scored.

**Six axes (Claude assigns 0–5 each):**

| Axis | 0 | 5 |
|---|---|---|
| `teaches` | Nothing to apply | Actionable insight you could use tomorrow |
| `tool_discovery` | Already known / irrelevant | Novel tool/framework you'd actually use |
| `artifact` | No code/diagram/config | Code + diagram + context, well-explained |
| `discussion_quality` | No comments / pure agreement | Multiple substantive perspectives |
| `contrarian_evidence` | Consensus take | Challenges wisdom with data |
| `postmortem` | Not experiential | Real failure/lesson with transferable mechanics |

**Weights** (from `config.yaml` → `scoring.weights`):

```
gem_score = teaches * 3.0
          + tool_discovery * 2.0
          + artifact * 2.0
          + discussion_quality * 1.5
          + contrarian_evidence * 1.0
          + postmortem * 2.0
```

Max `gem_score` = 57.5.

**Relevance multiplier** (pick the bucket that best fits the item's topic):

| Mult | Topics |
|---|---|
| 1.0 | data_engineering, system_design, distributed_systems, product_shipping, startup_thinking |
| 0.9 | ai_research, agents, rag, benchmarks, local_news, energy, regional_tech |
| 0.7 | career, culture, interviews, claude_code, ai_tools |
| 0.3 | frontend, mobile, gaming, unrelated |

**Project bonus**: `× 1.2` if item genuinely connects to an active project (Rai, OpenKit, Orca). No bonus for tangential mentions.

**Final**:

```
final = gem_score × relevance_mult × project_mult
```

Theoretical max: 57.5 × 1.0 × 1.2 = 69.

**Hidden score comment** appended to every gem:

```html
<!-- scores: t=5 td=3 a=4 dq=2 ce=1 pm=0 topic=data_eng rel=1.0 proj=Rai pmult=1.2 final=46.2 -->
```

Invisible in Obsidian rendering, greppable for calibration, diffable across runs.

**Calibration loop (feeds issue #21):**

1. Raw dumps + scored gems retained in `~/helm/13-archive/news/dumps/YYYY-MM-DD/` indefinitely (`.runs/` keeps only a 3-day live window).
2. Monthly: read back a sample of digests and the hidden score comments, and check whether the items John actually reads and reacts to (journal mentions, ideas captured, ChromaDB recall hits) line up with high scores. If low-`tool_discovery`-but-high-`postmortem` items keep landing well, bump `postmortem` weight; if items scored 50+ get ignored, there is a weight misalignment.
3. Adjust `scoring.weights` in `config.yaml`. No code change needed.

---

## V5 Presentation Workflow

**Script:** `~/helm/03-rai/skills/news-digest/present_v5.py`

```bash
cd ~/helm/03-rai/skills/news-digest
./present_v5.py --date YYYY-MM-DD --out YYYY-MM-DD.md
```

The script emits a markdown SKELETON to `~/helm/08-bawaba/daily/YYYY-MM-DD.md` with:
- Final structure (header, sections, all gems with score+link+citation)
- `<CLAUDE_FILL_*>` placeholders where Claude must write prose
- `<!-- raw: ... -->` scaffolding next to each gem (selftext excerpt) — context for Claude during post-fill, must be stripped before final delivery

### Header (compact, Obsidian-friendly)

```markdown
---
date: 2026-05-08
---

|               |  x  | sub |  m  |  hn |  r  | gh  |
|---------------|----:|----:|----:|----:|----:|----:|
| **collected** | 2144 | 200 |  50 | 100 | 578 |  12 |
| **in digest** |  15 |   0 |   0 |  11 |  66 |   6 |

**Sections:** news_wire: 12 · hot_topics: 3 · top_shelf: 26 · feed: 60 · wisdom: 3 · deep_dive: 1
```

YAML frontmatter contains ONLY `date` (renders as a single Properties row in Obsidian). Source/section counts go in the body where they render readable. **No nested YAML maps** — they render as ugly JSON in Obsidian Properties.

### Letter grades

Single number 0–100 internally; collapsed to a letter for display. Realistic daily max is ~40.

| Score | Grade | Meaning |
|-------|-------|---------|
| ≥ 35 | **S** | Must-read |
| 25–34 | **A** | Excellent |
| 18–24 | **B** | Good |
| 12–17 | **C** | Okay |
| < 12 | (filtered) | Doesn't make Top Shelf — may appear in Feed |

### Link tags

Topic anchors per item, multi-tag allowed. Display: `` `[Tag]` ``.

- **Identity dimensions**: `[AI]` `[Data Eng]` `[System Design]` `[DevOps]` `[local]`
- **Active projects**: `[Rai]` `[OpenKit]` `[Orca]`
- **Quality signal**: `[Postmortem]`

If no signal hits, link shows `_none_` rather than blank.

### Citation IDs

Every displayed item gets a stable `[<src>-<n>]` tag, counted per source bucket in display order (News Wire → Top Shelf → Feed):

| Source | Prefix |
|--------|--------|
| Hacker News | `hn-` |
| Reddit | `r-` |
| X (For You + Following) | `x-` |
| GitHub | `gh-` |
| Substack | `sub-` |
| Medium | `m-` |

Used by Hot Topics to cite specific items via inline markdown links: `[hn-3](url)`.

### Sections (in order)

1. **News Wire** (≤15 items, v5.4: GENERAL) — the day's tech-world brief, NOT personalized. Trend-ranked (cross-source convergence + engagement) from the same sources, X-majority (~55%+), tech-relevance gate, NO identity scoring, no local/project guarantees. The script overselects ~21 candidates; Claude deletes non-tech junk (viral sports/celebrity/ads; 1–2 genuinely major world events may stay) and writes ONE neutral wire-service sentence per kept item. Old items carry a `· *published YYYY-MM-DD*` label.

2. **Hot Topics** (0–3 themes, **Claude-filled**) — Read all displayed items, then identify themes that ACTUALLY emerged today. **NOT keyword-detected.** A theme qualifies only if ≥5 items converge on the same story / release / incident / pattern. Skip the section entirely on quiet days. Each topic: title + 2–3 paragraph synthesis + inline `[r-15](url)` markdown-link citations. **No trailing `**sources:**` line** — inline citations suffice.

3. **Top Shelf** (~20–30 gems) — cross-source ranked, diversity-enforced (max 4/topic, max 8/source, ≥50% identity-matched, score ≥ 12). Anti-cluster reorder applied (no >2 consecutive items from same source).

4. **Feed** (~60 gems) — pure score order, then flexed by the **X-share rebalance** (v5.5): X is John's primary channel, so the body (Top Shelf + Feed) is pushed toward the **upper end** of `x_share_target` (lean ~55% X) by swapping the Feed's weakest non-X items for the best unused **on-beat** X (`is_on_beat`: AI/DE/SysDesign/DevOps/projects — never regional/finance/viral junk), overriding the per-source soft cap for X. On throttled-X days it stops short of the band rather than padding. Top Shelf and News Wire are not touched.

5. **Wisdom** (0–3 quotes) — curated insights with **Model** + **Insight** filled by Claude.

6. **Deep Dive** (1 essay + 0–2 also-considered) — one substantive item gets a 4–5 paragraph synthesis. Override the script's auto-pick if a more substantive candidate exists today.

### Gem format

**News Wire item:**
```markdown
- **[Title text](url)** `[r-2]` (r/AI_Agents, 131 pts, 83c) · score: **S** · link: `[AI]`
  > Writer-tone hook in 1 sentence — what / why / how-it-relates.
```

**Top Shelf gem:**
```markdown
---
**#1** `[r-5]` | **r/dataengineering** (19 pts, 10c) · score: **S** · link: `[AI]` `[System Design]`
"Title in quotes"
> Writer-tone hook in 1–2 sentences.
[source](url)
```

**Feed gem:**
```markdown
---
**#27** `[r-13]` | **r/Rag** (38 pts, 10c) · score: **A** · link: `[AI]` — "Title"
> 1-sentence writer-tone hook.
[source](url)
```

**X media tags (v5.7).** X gems carry extra meta tags from the collector's per-tweet enrichment — e.g. `[video]` `[article]` `[→arxiv.org]` `[quote]` `[img]` `[truncated]`. Use them when writing the hook and when curating: a `[video]` is a demo (say what it shows), `[→github.com]`/`[→arxiv.org]` points to the real artifact (hook the repo/paper, not the tweet), `[truncated]` means the visible text is partial so lean on the `[source]` link rather than paraphrasing a stub. They are signals, not scores — weigh them, don't just transcribe them.

### Hook craft spec (Top Shelf + Feed) — v5.4

A hook is ONE claim, not a summary. Every hook must pass all four:

1. **LEAD with the non-obvious thing** — the mechanism, number, failure mode, or contrarian claim inside the item. Not its topic.
2. **GROUND it in John's interest areas** — data engineering, DevOps, AI, system design — NOT in project names. A project reference (Helios, Orca, open-kit, Rai) is allowed ONLY for a currently-active project with a genuinely real connection; default to the interest-area angle ("steal this pattern for any agent memory design") over the project angle ("for Rai"). Project name-dropping gets stale and narrow fast. General-but-sharp beats project-shoehorned.
3. **END with a so-what** — what to steal, watch, or decide.
4. **COVER-THE-TITLE TEST** — hide the title; the hook must still add information. If it reads as a paraphrase of the title, rewrite it.

BANNED:
- Restating or paraphrasing the title.
- Openers: "This post/article/thread/repo …", "A look at …", "X discusses/explores/covers …"
- Hedge filler: "might be interesting", "worth a look", "could be useful", "interesting take", "great read".
- Reflexive project name-drops and generic praise carrying no claim.

Contrastive examples:

- BAD: "A look at how DuckDB is replacing Spark for small workloads." *(title restated)*
  GOOD: "Benchmarks in the post put ~90% of real workloads under 100 GB — the takeaway is engine tiering: default to DuckDB, keep Spark for the tail."
- BAD: "This thread discusses agent reliability problems — worth a look."
  GOOD: "Long-horizon agents die near step ~30 when a sub-agent confidently hallucinates a premise; the fix converging across stacks is a separate small checker model — the doer/checker split every agent system ends up needing."
- BAD: "Trace-every-retrieval observability for RAG — useful for Helios." *(project shoehorn)*
  GOOD: "RAG observability keeps getting rebuilt per stack — steal the trace schema (query, chunks, scores, tool calls per hop), ignore the .NET wrapper."

Junk items get an honest "skip — <reason>" instead of a fake interpretation.

### Wire-brief spec (News Wire ONLY — different voice)

One neutral newsroom sentence: the concrete event/claim + why the tech world cares today. No project or interest-area tie-ins, no second person, no advice, no hedging. Wire-service abstract, not a personal note.

### Post-fill workflow

After running `present_v5.py`, Claude works through this list:

1. **News Wire editorial + briefs** — follow the in-file instruction block: DELETE candidate bullets that aren't tech news (viral sports, celebrity, engagement-bait, ads; 1–2 genuinely major world events may stay), keep at most the configured count, then replace each `> <CLAUDE_FILL_WIRE_BRIEF>` per the Wire-brief spec. Do NOT tie wire items to projects or interests.
2. **Hot Topics** — replace `<CLAUDE_FILL_HOT_TOPICS>` with 1–3 themes (or skip entirely on quiet days). Use inline `[r-15](url)` citations referencing the citation IDs printed next to each gem.
3. **Top Shelf hooks** — replace each `> <CLAUDE_FILL_HOOK>` (1–2 sentences) per the Hook craft spec. Use the `<!-- raw: ... -->` comment as context for what the post says.
4. **Feed hooks** — same spec, more compact (1 sentence each).
5. **Wisdom** — fill `**Model:**` (e.g., Compounding, Inversion, First Principles) + `**Insight:**` (2–4 sentences) for each quote.
6. **Deep Dive** — fill `### <CLAUDE_FILL_TITLE>` and `<CLAUDE_FILL_ESSAY>`. Override the script's auto-pick if a stronger candidate exists today.
7. **Hook self-review pass (mandatory)** — re-read EVERY hook (wire briefs + Top Shelf + Feed). Apply the cover-the-title test and the banned list to each. Rewrite every failure in place. Wire briefs are additionally checked for accidental project/interest tie-ins (remove them). Only after this pass, proceed.
8. **Update section counts** — replace `<CLAUDE_FILL_HT_COUNT>` (actual hot-topic count) and `<CLAUDE_FILL_NW_COUNT>` (kept wire items) in the body's `**Sections:**` line.
9. **Mandatory cleanup** — strip ALL `<!-- raw: ... -->` scaffolding lines AND delete every `<!-- CLAUDE INSTRUCTIONS ... -->` block (News Wire, Gems, Hot Topics):
   ```python
   import re
   path = "~/helm/08-bawaba/daily/YYYY-MM-DD.md"
   text = open(path).read()
   text = re.sub(r'^<!--\s*raw:[^\n]*-->\n', '', text, flags=re.MULTILINE)
   open(path, 'w').write(text)
   ```
   (Instruction blocks are multi-line — delete them by editing, the regex above only handles raw lines.) The user must never see scaffolding.

### Verification before declaring done

```bash
grep -c "CLAUDE_FILL" ~/helm/08-bawaba/daily/YYYY-MM-DD.md    # must be 0
grep -c '<!-- raw:' ~/helm/08-bawaba/daily/YYYY-MM-DD.md      # must be 0
grep -c '<!-- CLAUDE' ~/helm/08-bawaba/daily/YYYY-MM-DD.md    # must be 0 (instruction blocks deleted)
```

If any count is non-zero, the post-fill is incomplete.

### Wisdom (up to 3)

- **Up to 3 items. Minimum 0.** If nothing qualifies, skip the section entirely.
- Each quote mapped to a mental model (list in `config.yaml`, mirroring `02-ana/identity/mindset.md` § Mental Models).
- Model mapping must be genuine. If no model fits, don't force one — that item doesn't qualify.
- Insight is 2–3 sentences connecting the quote to the user's actual context (projects, career, goals).

### Deep Dive (exactly 1 written, 2 others listed)

- Claude picks the top candidate and writes it in full.
- Lists 2 additional candidates under "Also considered" with a one-line reason for each.
- Selection criteria (highest-scoring across these):
  - Connects to active learning goals (AI foundations, system design, product shipping)
  - Connects to active projects
  - Concept is non-obvious
  - There's enough depth to teach something meaningful
  - User probably wouldn't go deep on this himself, but should

---

## Rules

- **NO COMPROMISES, NO SKIPPING.** Collect full target from every source. Use the Retry Ladder up to 10 attempts. The AI does NOT decide to skip a source. The AI does NOT decide to stop early. Only the user does.
- **All 6 sources are mandatory:** X For You, X Following, Substack, Medium, Hacker News, Reddit, GitHub Trending. If any source is below 90% of target, the retry ladder runs to completion (10 attempts) before the digest ships.
- **X is a dealbreaker.** No X (For You + Following both ≥ 90%) → no digest. Abort with marker file.
- **One Chrome tab per source.** Fresh tab for each. No state sharing.
- **Preserve raw content**: actual tweet text, actual post titles, actual comment quotes.
- **No tables in the Gems feed.** Feed style only.
- **No numeric scores visible.** Hidden `<!-- scores: ... -->` comment only.
- **80–100 gems, tiered**: Top 20–30 deep, rest brief.
- **Per-source caps**: HN 10, Medium 5 (double for weekly). Others uncapped within global 80–100.
- **Tight hooks**: 2–3 sentences Top Shelf, 1 sentence Feed. No filler.
- **Wisdom 0–3 items**, not fixed 3.
- **Deep Dive 1 full + 2 also-considered.**
- Run autonomously. Never ask permission during collection. Autonomous ≠ "skip when convenient."
- Project tags + mental-model tags only where genuine.
- Every gem gets a link.

---

## Companion Mode (`/news chat`)

After reading a digest, user enters `/news chat` to discuss items.

**At entry, surface these canonical prompts** (from `config.yaml.chat_prompts`) as starters — user picks one or types their own:

1. "What should I pay most attention to and why?"
2. "What am I missing that I'd want to know?"
3. "Connect gem #N to my active projects."
4. "What would this look like in 6 months if the trend holds?"

**In-session behavior:**
- Load the current day's digest into context.
- Answer questions, connect items to goals/projects/mental models.
- Have opinions. Push back. Ask questions back. This is conversation, not lookup.
- Deep-read any linked item on request.

---

## Short Digest (`08-bawaba/digest/`)

The short version of the daily, for a day with no time to read it. A Bottom line, then News Wire, Hot Topics, Gems, Wisdom and Deep Dive as Obsidian callouts. Each item is a topic, an explanation and a takeaway for him, with no sources and no authors.

- The scheduled runner writes it with a second headless run right after a complete daily. `run-news-ubuntu.sh digest` runs it alone and does nothing when today's digest is complete.
- It heals itself: the coordinator runs `digest` mode at each of its runs while today's daily is on disk.
- `digest_style.md` is its whole brief: the shape, the picks, the fact rules and the check.
- Only the runner archives it, to `13-archive/news/digest/`.

## Weekly Magazine (`/news week`) — Bawaba Weekly

**The weekly is a magazine, not a newspaper.** The daily asks "what happened
today?"; the weekly asks "what was this week trying to teach me?" Topical
departments written as flowing educational prose — something still worth
reading a month later. John reads the weekly more than the daily; this is
the most important output of the whole skill. **Design system: v3** (sealed
2026-06-13 from a 50-agent redesign; `2026-W23` and `2026-W24` are the reference
issues — match them). **No word floor.** Per-department ceilings + a cut-line
rule; a thin week ships tight, not padded. The brief: scannable in ~90 seconds,
re-readable in a month, and unmistakably hand-built, not generator-shaped. Load
`weekly_style.md` (house style — device budgets, tag notation, the self-review
checklist) BEFORE writing and enforce it before publish.

**The beat (in scope):** AI, agents and agent engineering, data engineering,
data broadly, system design, and DevOps/infra. That is the lens. Every
department should land somewhere on it. **Out of beat — do not cover as
topics:** security-as-a-subject, regional/local/geopolitics, sports, general world
news. (They may appear only as one-line context inside an in-beat story, never
as their own thread.) The reference issue (`2026-W24`) drifted into an
AI-industry-only weekly and dropped data-eng / DevOps / system-design entirely;
that is the gap this beat exists to close. Reader value is the test: does this
help John build agents, data systems, and infra — or is it industry gossip?

**Two inputs, one new permission:**

1. **Raw dumps** — `~/helm/13-archive/news/dumps/YYYY-MM-DD/` for the most
   recent Sunday→Saturday week. This is the primary source: full Substack
   article text, Reddit selftext + comments, HN top comments, X posts, GitHub
   READMEs — topic gravity over EVERYTHING collected, with no regard for what
   made a daily.
2. **The 7 dailies** — from BOTH `~/helm/08-bawaba/daily/` and
   `~/helm/13-archive/news/daily/` (prefer `daily/` if a date exists in both).
   Used for context: hot-topic framing and the Wisdom quotes.
3. **Web enrichment is ALLOWED in weekly mode** — `WebSearch`/`WebFetch` only
   (headless-safe; the weekly NEVER opens a browser). Cap ~10 fetches
   (`config.yaml → weekly.web_enrichment`). Use it to deepen the chosen
   subjects: official announcements, docs, papers, primary sources. **Spend the
   budget — `W24` used only 3 of ~10 and shipped a probably-fabricated "16-year
   FFmpeg bug."** Fact-hardening is now mandatory, not optional (see § Fact
   protocol). The dumps are Reddit/X/Substack posts — secondhand by nature;
   anything load-bearing gets verified before it goes in print.

**Skip any missing dump days or dailies silently** — never abort, never scrape
sources. A thinner issue from fewer days is fine; note coverage in the footer.

### Pipeline

0. **Load house style + threads.** Read `weekly_style.md` (device budgets,
   banned/rationed list, tag notation, the v3 structure contract) and
   `~/helm/08-bawaba/story-arcs.md` (the multi-week threads feeding The Fold's
   previously/next-watch). Both are mandatory inputs, not optional references.
1. **Mine.** `./weekly_mine.py` (add `--week YYYY-WWW` to pin a week).
   Writes department briefs to `.runs/weekly-YYYY-WWW/`: `brief_cover.md`,
   `brief_models.md`, `brief_lesson.md`, `brief_stack.md` (data-eng / data /
   system-design / DevOps craft — the beat areas), `brief_workshop.md`,
   `brief_shelf.md`, `coverage.md`. Confirm the console summary shows >0 records
   before writing.
2. **Read.** All briefs + the week's dailies (skim for Hot Topics + Wisdom).
   When a brief candidate needs depth, pull the item's full text from the day's
   dump file (match by url, e.g. `jq` over `substack.json`). **`brief_stack.md`
   is not optional** — the beat lives there; if a department has no in-beat
   craft, that is a coverage miss to fix, not a brief to skip.
3. **Pick subjects.** One cover story, one lesson concept (recurred ≥3 days,
   ≥2 sources — pick the one with real teaching depth, not the loudest), the
   week's model releases, the week's data-eng/DevOps/system-design threads,
   workshop tools, 3–5 shelf long-reads.
4. **Enrich + harden (mandatory).** WebSearch/WebFetch toward the ~10-fetch cap.
   First, **fetch every primary source a load-bearing claim is attributed to**
   (vendor announcement pages, the paper, the official post) — never relay a
   "confirmed on [page]" claim without having fetched that page. Then verify the
   numbers/dates/quotes flagged in `coverage.md`'s verify-queue. Log what you
   fetched + the verdict in the run's `coverage.md`. See § Fact protocol.
5. **Write** the issue (template below) to `~/helm/08-bawaba/weekly/YYYY-WWW.md`
   — ISO week of the Saturday it covers (e.g. `2026-W24.md`).
6. **Self-review + archive.** Run the `weekly_style.md` grep-gated checklist
   (banned words → ~0; signature frame paired ~2; `cost-per-task` one home; no
   placeholders). Confirm every department has a deck + decision footer, The Fold
   scans in ~90s, every perishable number is tagged, and the cut-line names what
   was dropped. Confirm each load-bearing fact was fetched or marked a vendor
   claim. **Update `story-arcs.md`** (advance thread statuses + next-watch).
   Rotate any PRIOR weekly from `08-bawaba/weekly/` to `13-archive/news/weekly/`
   (never delete).

### Departments — v3 layout (order fixed)

```markdown
**BAWABA WEEKLY · No. WWW · Sun Mon D → Sat Mon D, YYYY**
> **<cover line: the issue's whole thesis in 1–2 sentences>**
> *Not a recap. The work around the model.*    ← the standing creed

## The Fold        ≤90-sec scan: week-in-one-line · three things w/ #anchor jumps ·
                   number of the week · if-you-read-one-thing · the one decision ·
                   read time · previously/next-watch (from story-arcs.md) · tag legend
## Editor's Letter            *deck*
## Cover Story: <headline>    <a id="cover">      *deck*
## Model State                <a id="model-state"> *deck* — opens with the diffable register + Routing Card
## The Lesson: <concept>      <a id="lesson">      *deck*
## The Stack                  <a id="stack">       *deck* — data-eng / data / system design / DevOps craft
## The Workshop               <a id="workshop">    *deck*
## Reading Shelf              <a id="shelf">       *deck*
## Closing — Wisdom           <a id="closing">     *deck* — carries the reference diagram

*Cut this week: <X>, because <Y>.*
<details> footer: Coverage · Methodology · Revision log </details>
```

**The v3 contract** (full device budgets in `weekly_style.md`):
- **Masthead + The Fold** lead every issue: a wordmark line, a cover line stating
  the thesis, the creed, then a ≤90-second scan block with real `#anchor` jumps.
- **Every department** carries a one-sentence *italic deck* (its single
  falsifiable claim for THIS issue) and ends with a fixed **decision footer**
  (`BUILD-NOW` / `DECIDE` / `WATCH` / `AVOID`) — which REPLACES the old literal
  "how it applies to your stack" header while keeping the concrete tie-in.
- **Tags everywhere:** decay (`[durable]` / `[perishable]` / `[shelf ~Mon DD]`)
  and confidence (`[primary]` / `[vendor-claim]` / `[1-practitioner]` /
  `[projection]`), defined once in The Fold's legend; hedge proportional to evidence.
- **Model State** opens with the diffable register (identical columns every week
  + a Δ-since-last column + a trajectory arrow) and carries a durable Routing Card.
- **The Closing** carries a reference diagram (D2 or ASCII; D2 renders in Obsidian through the D2 plugin, Mermaid is retired) of the week's
  production stack — the one artifact a reader screenshots — under the synthesis.
- **Two-altitude reading:** any passage with 3+ hard numbers keeps ONE headline
  number in prose and pushes the rest into a labeled `<details>` drawer.
- **No word floor; visible restraint:** ship tight, surface one line — *Cut this
  week: X, because Y* — above the footer.
- **Ration the voice:** the issue's signature frame appears exactly twice (Letter
  open + Closing last line); full aphoristic closers only in Cover/Lesson/Closing;
  one idea has one home. (Budgets enforced from `weekly_style.md`.)

- **Editor's Letter** — what this week was *about*, in voice. One page, prose
  only, no bullets. Sets up the issue.
- **Cover Story** — THE story of the week as a real feature: narrative arc,
  background, primary sources (web-enriched — **fetch the announcement page, do
  not relay it secondhand**), quotes from actual posts, implications. ONE story
  deep, not five shallow. Vendor capability claims are written as "Anthropic
  says…", not as confirmed fact, unless independently verified.
- **Model State** — every model released or meaningfully updated this week
  (frontier labs + open weights), written as a guided tour: "Anthropic spent
  the week…", "meanwhile in open weights…". Capabilities, pricing, benchmark
  claims with salt, what's actually worth trying. From `brief_models.md` +
  official announcement pages. **Open it with a model-comparison table**
  (model · capability · access/price · date) before the prose, then give the
  open-weight / local / routing story real room — that floor is the part most
  useful to the reader, not just the frontier ceiling.
- **The Lesson** — the masterclass; the explicit reason this magazine exists.
  Structure: why the concept kept surfacing this week → first-principles
  explanation (define the jargon in one plain sentence before using it) → what
  practitioners said this week (quote real posts from the dumps, linked) →
  web-enriched depth (docs/papers/history) → **how it applies to John's
  stack, concretely** — a decision tree, a checklist, or a minimal template he
  can act on, not just "this matters." Ground in beat areas (data engineering,
  data, DevOps, system design, agents), NOT project names. `W24`'s Lesson is the
  quality bar; its only miss was stopping at the problem instead of shipping the
  how-to.
- **The Stack** — the beat's home: the week's data-engineering, data-systems,
  system-design, and DevOps/operating craft from `brief_stack.md`. Not industry
  news — *patterns and practice*: schema/parse strategy, pipeline/streaming
  shape, orchestration, observability, cost-per-task vs per-call, what it takes
  to run agents in production. Closes by folding into the issue's
  production-architecture synthesis. If the week was thin here, go deeper on one
  pattern rather than dropping the department.
- **The Workshop** — tools and repos of the week from `brief_workshop.md`,
  grouped by the job they do, with honest "who needs this" verdicts. A guided
  tour, not a list.
- **Reading Shelf** — 3–5 long reads from `brief_shelf.md` (full text sits in
  the dumps — read it before recommending). Render as an annotated list: title +
  author, a sentence on why it earns full attention, one pull-quote each. Bias
  selections toward the beat (at least one data-eng / DevOps / system-design
  read when the week offers one), not only AI-economics essays.
- **Closing — Wisdom** — the best quote across the week's dailies, expanded
  into a short reflective essay tied to your goals + mindset.

### Voice

Magazine prose throughout — apply the anti-AI voice rules in
`~/helm/03-rai/skills/writing/references/voice.md`. No hook-format bullets, no
letter grades, no score comments, no section scaffolding. Inline markdown
links to the original posts serve as citations. Every claim about "this week"
must trace to a dump item or daily; every external fact to a fetched source.

**Keep what works (`W24` graded A on voice):** lead with the verdict then defend
it, concrete numbers over adjectives, active voice, named human subjects
(Willison, Reis, the r/ML author) grounding every abstraction.

**Guard against the formula crystallizing.** `W24` (and the disliked `W23`) both
opened on "convergence" (*N things that only look unrelated*) and closed on a
parable. A third would make the template visible. Per issue: **vary the opening
device** (a systems sketch, a single scene, a contrarian claim, a number that
shouldn't be true) and **vary the close**. Cap aphoristic fragment-closers — one
genuinely earned per issue, not one per section. **No hollow profundity**: never
write a deep-sounding line the body then contradicts (`W24`'s "Memory is not a
place you store things" sat right above three paragraphs describing storage).
Trim filler abstractions ("frontier" as a noun appeared 5+ times — name the
company or the capability instead).

### Fact protocol (weekly)

The weekly is meant to hold up a month later, so its facts must be load-bearing.
Before publishing:

- **Fetch primary sources.** Any claim attributed to an announcement/paper/post
  ("confirmed on Anthropic's page", "the study found") requires fetching that
  page. `W24` linked the Anthropic page as its source but never fetched it, and
  shipped a "16-year-old FFmpeg bug" that no source confirms.
- **No false precision.** Don't assert exact figures the source can't back
  ("exactly 152k engagements", "1,900 HN points"). Round, attribute ("~150k"),
  or cut. Engagement counts from the dumps are point-in-time, not authoritative.
- **Mark unverified vendor claims** as "X says / X claims", never as fact.
- **Beat link rot.** ~54% of `W24`'s sources were ephemeral Reddit/X/Substack
  posts. For any claim that carries a section, add a stable fallback (paper,
  docs, official blog) alongside the post; note in the footer that social links
  are archived as of the issue date.

### Design / formatting (weekly)

A 60-minute read needs structure, not walls (`W24` graded C+ here):

- `###` subheads **and** `---` dividers inside long departments (Cover, Model
  State, The Lesson, The Stack) — signal the topic resets.
- Tables for anything enumerated: the Model State roster, an accuracy/benchmark
  comparison, a tool taxonomy (`verb_object` grammar), a routing portfolio.
- 2–3 **pull-quote callouts** across the issue (extract the sharpest line of a
  section as a `>` blockquote) to give skimmers traction.
- A 3–4 bullet **TL;DR** atop the densest departments (The Lesson, The Stack).
- Render Reading Shelf as an annotated list, not stacked prose paragraphs.

Weekly mode never touches the seen ledger and never scrapes sources — dumps +
dailies + capped web fetches only.

