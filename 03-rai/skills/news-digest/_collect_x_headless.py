#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client>=1.6"]
# ///
"""Headless-Chrome X collector via CDP — the /news-digest X spine.

Promoted from the orphaned .runs/2026-06-12/_x_headless.py experiment that pulled
2003 For You tweets fully headless. The shebang resolves the websocket dep into
a cached uv env, so system python is never involved:

    ~/helm/03-rai/skills/news-digest/_collect_x_headless.py --date 2026-06-14

Why headless-CDP instead of claude-in-chrome MCP:
  - No MCP extension pairing (the #1 cause of 3am-run hangs — see memory
    news-digest-chrome-pairing). Pure google-chrome --headless=new + raw CDP.
  - No 45s javascript_tool CDP cap: the scroll loop is driven from Python, so
    it can run for as long as collection needs.
  - Throwaway profile cloned from the user's real cookies → never disturbs the
    live Chrome session, runs while it's open.

Hardening over the original experiment:
  - Login preflight FAILS LOUD (writes x_LOGIN_FAILED.json, exit 3) instead of
    silently shipping zero — X is a dealbreaker source.
  - Reload-cycle recovery: under the per-account pagination-starve throttle a
    fresh page load still serves ~10-19 tweets even when scroll pagination is
    dead (observed 2026-06-13). When the main scroll plateaus short of target we
    reload + re-inject + harvest the initial batch, accumulating across cycles.
  - Items tagged with source_tier (foryou_algo / following) so present_v5.py can
    keep the x_foryou affinity boost.
  - Gentle Premium-era defaults: target ~1200, well under the ~10k/day Premium
    read cap, to avoid the burst pattern that soft-flagged the account on 06-12.
  - ACCUMULATES across passes (merge_write): the writes union into the day's
    x_foryou.json / x_following.json by tweet id instead of overwriting. The
    scheduled pipeline runs THREE gentle passes per digest — 21:00 + 00:00
    (news-x-collect.timer, deterministic) then 03:00 (inside the digest run) —
    each --target 700 --following-target 50. Premium lifts the daily READ cap but
    NOT X's per-session timeline-injection throttle (the feed freezes ~200 deep
    after ~2 min of scroll); three fresh sessions hours apart each get a fresh
    batch as the feed refills, which is how the pool reaches ~1k where one
    session plateaus at ~350.

Exit codes: 0 ok · 2 chrome/devtools failure · 3 not logged in.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import random
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request

import websocket  # provided by uv (--with websocket-client)
import shutil
CHROME_BIN = next((b for b in ("google-chrome", "google-chrome-stable") if shutil.which(b)), "google-chrome")

BASE = os.path.expanduser("~/helm/03-rai/skills/news-digest")
OBSERVER = open(os.path.join(BASE, "chrome_snippets", "x_observer.js")).read()
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")


# --- status -------------------------------------------------------------------

def make_status_writer(path):
    def st(**kw):
        kw["ts"] = time.strftime("%H:%M:%S")
        with open(path, "w") as f:
            json.dump(kw, f)
        print(kw, flush=True)
    return st


# --- chrome lifecycle ---------------------------------------------------------

def setup_profile(profile):
    src = os.path.expanduser("~/.config/google-chrome")
    if os.path.exists(profile):
        shutil.rmtree(profile)
    os.makedirs(os.path.join(profile, "Default"))
    # Local State holds the cookie-encryption key reference; copy it so the
    # cloned Cookies DB decrypts against this user's keyring.
    shutil.copy(os.path.join(src, "Local State"),
                os.path.join(profile, "Local State"))
    for f in ["Cookies", "Cookies-journal"]:
        p = os.path.join(src, "Default", f)
        if os.path.exists(p):
            shutil.copy(p, os.path.join(profile, "Default", f))
    # Strip every cookie that isn't X. The headless browser must NEVER carry
    # Google/YouTube (or any other) auth: Google's anti-abuse reads a session
    # replayed from a headless, webdriver-spoofed context as a hijack and
    # rotates it server-side, which signs the real browser out too. The
    # collector only needs x.com/twitter.com (+ twimg media).
    _prune_cookies_to_x(os.path.join(profile, "Default", "Cookies"))


# Domains the X collector legitimately needs; everything else is deleted from
# the cloned cookie jar before the headless browser ever launches.
X_COOKIE_DOMAINS = ("x.com", "twitter.com", "twimg.com")


def _prune_cookies_to_x(db):
    if not os.path.exists(db):
        return
    con = sqlite3.connect(db)
    try:
        where = " OR ".join(["host_key = ? OR host_key LIKE ?"] * len(X_COOKIE_DOMAINS))
        params = [v for d in X_COOKIE_DOMAINS for v in (d, f"%.{d}")]
        con.execute(f"DELETE FROM cookies WHERE NOT ({where})", params)
        con.commit()
    finally:
        con.close()


def launch(profile, port):
    # Free the port if a prior headless instance is lingering. By-PORT, never by
    # cmdline pattern (pkill -f self-matches our own wrapper shell in some envs).
    try:
        subprocess.run(["fuser", "-k", f"{port}/tcp"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10)
        time.sleep(1)
    except Exception:
        pass
    proc = subprocess.Popen([
        CHROME_BIN, "--headless=new", f"--user-data-dir={profile}",
        f"--remote-debugging-port={port}", "--window-size=1400,1600",
        "--disable-gpu", "--no-first-run", "--mute-audio",
        f"--user-agent={UA}", "about:blank",
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(60):
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/json/version", timeout=1)
            return proc
        except Exception:
            time.sleep(0.5)
    raise RuntimeError("chrome devtools port never came up")


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=120, suppress_origin=True)
        self.mid = 0

    def cmd(self, method, **params):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})

    def js(self, expr, timeout=60):
        r = self.cmd("Runtime.evaluate", expression=expr, returnByValue=True,
                     awaitPromise=True, timeout=timeout * 1000)
        if r.get("exceptionDetails"):
            raise RuntimeError(str(r["exceptionDetails"])[:500])
        return r.get("result", {}).get("value")

    def navigate(self, url):
        self.cmd("Page.navigate", url=url)


def new_page(port, url):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{url}", method="PUT")
    info = json.loads(urllib.request.urlopen(req, timeout=10).read())
    c = CDP(info["webSocketDebuggerUrl"])
    c.cmd("Page.enable")
    c.cmd("Runtime.enable")
    c.cmd("Page.addScriptToEvaluateOnNewDocument",
          source="Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    return c, info["id"]


def wait_logged_in(c, st, phase, tries=30):
    for _ in range(tries):
        try:
            ok = c.js("!!document.querySelector('[data-testid=\"SideNav_NewTweet_Button\"]')")
            n = c.js("document.querySelectorAll('article[data-testid=\"tweet\"]').length") or 0
        except Exception:
            ok, n = False, 0
        if ok and n > 0:
            return True
        time.sleep(2)
    st(phase=phase, error="login_or_feed_never_appeared")
    return False


# --- collection ---------------------------------------------------------------

def _merge_dump(c, acc, tier):
    """Pull window.__tweets, merge into acc keyed by id, tag with source_tier."""
    raw = c.js("window.__tweets ? window.__tweets_dump() : '[]'", timeout=120)
    items = json.loads(raw) if isinstance(raw, str) else (raw or [])
    new = 0
    for it in items:
        tid = it.get("id") or it.get("url")
        if not tid or tid in acc:
            continue
        it["source_tier"] = tier
        acc[tid] = it
        new += 1
    return new


def merge_write(path, new_items):
    """Accumulate new_items into any existing dump at path, deduped by tweet id
    (falls back to url). This makes the collector idempotent and ADDITIVE so the
    21:00 / 00:00 / 03:00 passes union into one pool instead of overwriting each
    other. Returns the resulting pool size."""
    pool = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                for it in json.load(f):
                    k = it.get("id") or it.get("url")
                    if k:
                        pool[k] = it
        except Exception:
            pass  # corrupt/partial prior dump — start from this pass's items
    for it in new_items:
        k = it.get("id") or it.get("url")
        if k:
            pool[k] = it
    with open(path, "w") as f:
        json.dump(list(pool.values()), f, ensure_ascii=False)
    return len(pool)


def scroll_collect(c, st, phase, acc, tier, target, scroll_delta=800,
                   plateau_s=120, max_s=1500):
    """Humanized Python-driven scroll. Merges into acc; returns reason string."""
    start = time.time()
    last_size = len(acc)
    last_growth = time.time()
    ticks = 0
    while True:
        dist = scroll_delta * (1 + random.uniform(-0.2, 0.2))
        try:
            c.js(f"window.scrollBy(0,{dist:.0f})")
        except Exception as e:
            st(phase=phase, error=f"scroll_err:{str(e)[:120]}", size=len(acc))
            time.sleep(3)
            continue
        ticks += 1
        time.sleep(random.uniform(0.6, 0.9))
        if ticks % random.randint(15, 25) == 0:
            time.sleep(random.uniform(2, 5))  # dwell — humanize
        if ticks % 10 == 0:
            _merge_dump(c, acc, tier)
            size = len(acc)
            if size > last_size:
                last_size = size
                last_growth = time.time()
            st(phase=phase, size=size, ticks=ticks,
               elapsed=int(time.time() - start),
               stall=int(time.time() - last_growth))
            if size >= target:
                _merge_dump(c, acc, tier)
                return "target"
            if time.time() - last_growth > plateau_s:
                _merge_dump(c, acc, tier)
                return "plateau"
            if time.time() - start > max_s:
                _merge_dump(c, acc, tier)
                return "time_cap"


def reload_recovery(c, st, port, page_url, phase, acc, tier, target,
                    max_reloads, prep=None):
    """Throttle recovery: a fresh load serves the initial batch even when scroll
    pagination is starved (observed 2026-06-13). Reload + re-inject + short
    scroll, accumulating each load's batch, until target hit or dry."""
    dry = 0
    for i in range(max_reloads):
        if len(acc) >= target:
            return "target"
        c.navigate(page_url)
        time.sleep(random.uniform(6, 9))
        if not wait_logged_in(c, st, f"{phase}_reload{i}", tries=15):
            dry += 1
            if dry >= 2:
                return "reload_login_lost"
            continue
        c.js(OBSERVER)
        if prep:
            prep(c)
        before = len(acc)
        # short scroll to trigger the initial pagination batch
        for _ in range(random.randint(8, 14)):
            c.js(f"window.scrollBy(0,{800 * (1 + random.uniform(-0.2, 0.2)):.0f})")
            time.sleep(random.uniform(0.6, 0.9))
        gained = _merge_dump(c, acc, tier)
        st(phase=f"{phase}_reload{i}", size=len(acc), gained=gained,
           before=before)
        dry = 0 if gained > 0 else dry + 1
        if dry >= 2:
            return "reload_dry"
        time.sleep(random.uniform(2, 4))
    return "reload_exhausted"


def click_following(c):
    c.js("""
      (() => {
        const tabs = [...document.querySelectorAll('[role="tab"]')];
        const f = tabs.find(t => /following/i.test(t.textContent));
        if (f) f.click();
        return tabs.map(t=>t.textContent).join('|');
      })()
    """)
    time.sleep(6)
    c.js("window.__tweets_reset && window.__tweets_reset()")
    c.js("window.scrollTo(0,0)")
    time.sleep(2)


# --- main ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--target", type=int, default=2000, help="For You target")
    ap.add_argument("--following-target", type=int, default=500)
    ap.add_argument("--phase", choices=["both", "foryou", "following"], default="both")
    ap.add_argument("--max-reloads", type=int, default=8)
    ap.add_argument("--profile", default="/tmp/news-x-profile")
    ap.add_argument("--port", type=int, default=9223)
    ap.add_argument("--max-scroll-s", type=int, default=2100)  # ~2000 tweets @ ~1.4/s ≈ 1430s; margin for plateaus. Still inside the scheduled-mode 85-min collection window.
    args = ap.parse_args()

    run_dir = os.path.join(BASE, ".runs", args.date)
    os.makedirs(run_dir, exist_ok=True)
    st = make_status_writer(os.path.join(run_dir, "x_headless_status.json"))

    st(phase="setup")
    setup_profile(args.profile)
    proc = launch(args.profile, args.port)
    rc = 0
    try:
        # ---- For You ----
        if args.phase in ("both", "foryou"):
            st(phase="navigate_foryou")
            c, _ = new_page(args.port, "https://x.com/home")
            time.sleep(8)
            if not wait_logged_in(c, st, "foryou"):
                marker = os.path.join(run_dir, "x_LOGIN_FAILED.json")
                with open(marker, "w") as f:
                    json.dump({"phase": "foryou", "reason": "not_logged_in",
                               "fix": "open Chrome, log into x.com as @johndoe, retry",
                               "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
                st(phase="foryou", fatal="not_logged_in", marker=marker)
                return 3
            c.js(OBSERVER)
            acc = {}
            st(phase="foryou_scrolling")
            reason = scroll_collect(c, st, "foryou", acc, "foryou_algo",
                                    args.target, max_s=args.max_scroll_s)
            if len(acc) < args.target and reason != "target":
                st(phase="foryou_recovery", size=len(acc), after=reason)
                reason = reload_recovery(c, st, args.port, "https://x.com/home",
                                         "foryou", acc, "foryou_algo",
                                         args.target, args.max_reloads)
            pool = merge_write(os.path.join(run_dir, "x_foryou.json"),
                               list(acc.values()))
            st(phase="foryou_done", got=len(acc), pool=pool, reason=reason)

        # ---- Following ----
        if args.phase in ("both", "following"):
            st(phase="navigate_following")
            c2, _ = new_page(args.port, "https://x.com/home")
            time.sleep(8)
            if not wait_logged_in(c2, st, "following"):
                st(phase="following", error="not_logged_in_following")
            else:
                c2.js(OBSERVER)
                click_following(c2)
                accf = {}
                st(phase="following_scrolling")
                reason = scroll_collect(c2, st, "following", accf, "following",
                                        args.following_target, plateau_s=90,
                                        max_s=min(600, args.max_scroll_s))
                if len(accf) < args.following_target and reason != "target":
                    reason = reload_recovery(
                        c2, st, args.port, "https://x.com/home", "following",
                        accf, "following", args.following_target,
                        max(2, args.max_reloads // 2), prep=click_following)
                pool = merge_write(os.path.join(run_dir, "x_following.json"),
                                   list(accf.values()))
                st(phase="following_done", got=len(accf), pool=pool, reason=reason)

        st(phase="all_done")
        return rc
    finally:
        proc.send_signal(signal.SIGTERM)
        time.sleep(2)
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
