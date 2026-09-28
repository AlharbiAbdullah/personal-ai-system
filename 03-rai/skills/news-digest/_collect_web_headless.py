#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["websocket-client>=1.6"]
# ///
"""Headless-Chrome Substack + Medium collector via CDP.

Sibling of _collect_x_headless.py, born 2026-08-24 after the claude-in-chrome
extension auto-update (1.0.85, night of Aug 18) broke MCP pairing at 03:00 for
seven straight nights and killed every digest at the preflight. X had already
been MCP-free since v5.6; this script moves the last two browser sources off
the paired desktop Chrome the same way:

    ~/helm/03-rai/skills/news-digest/_collect_web_headless.py --date 2026-08-24

  - Pure google-chrome --headless=new + raw CDP. No extension, no pairing, no
    45s javascript_tool cap.
  - Throwaway profile cloned from the real cookie jar, PRUNED to substack.com +
    medium.com only (Google/YouTube auth must never ride along — see memory
    news-digest-cookie-clone-google-signout; Medium's session cookies live on
    medium.com even though login is Google SSO, so the prune keeps auth intact).
  - Reuses the committed observers: substack_observer.js (Load-more click loop
    on /inbox) and medium_observer.js (one More click on /me/following-feed/all).
  - merge_write accumulates into substack.json / medium.json keyed by url, so
    re-runs and recovery passes are additive, mirroring the X pool.
  - Login failure FAILS LOUD per source ({source}_LOGIN_FAILED.json) and the
    other source still runs; these are partial-ok sources, not dealbreakers.

The CDP plumbing is duplicated from _collect_x_headless.py on purpose: X is the
dealbreaker spine and stays untouched; ~100 shared lines are cheaper than
destabilizing it with a refactor.

Exit codes: 0 at least one source collected · 2 chrome/devtools failure ·
3 both sources login-failed.
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
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36")

SUBSTACK_URL = "https://substack.com/inbox"
MEDIUM_URL = "https://medium.com/me/following-feed/all"

COOKIE_DOMAINS = ("substack.com", "medium.com")


def observer(name):
    return open(os.path.join(BASE, "chrome_snippets", name)).read()


# --- status -------------------------------------------------------------------

def make_status_writer(path):
    def st(**kw):
        kw["ts"] = time.strftime("%H:%M:%S")
        with open(path, "w") as f:
            json.dump(kw, f)
        print(kw, flush=True)
    return st


# --- chrome lifecycle (duplicated from _collect_x_headless.py) ----------------

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
    _prune_cookies(os.path.join(profile, "Default", "Cookies"))


def _prune_cookies(db):
    if not os.path.exists(db):
        return
    con = sqlite3.connect(db)
    try:
        where = " OR ".join(["host_key = ? OR host_key LIKE ?"] * len(COOKIE_DOMAINS))
        params = [v for d in COOKIE_DOMAINS for v in (d, f"%.{d}")]
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


def new_page(port, url):
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/json/new?{url}", method="PUT")
    info = json.loads(urllib.request.urlopen(req, timeout=10).read())
    c = CDP(info["webSocketDebuggerUrl"])
    c.cmd("Page.enable")
    c.cmd("Runtime.enable")
    c.cmd("Page.addScriptToEvaluateOnNewDocument",
          source="Object.defineProperty(navigator,'webdriver',{get:()=>undefined});")
    return c


def merge_write(path, new_items):
    """Accumulate new_items into any existing dump at path, deduped by url."""
    pool = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                for it in json.load(f):
                    k = it.get("url")
                    if k:
                        pool[k] = it
        except Exception:
            pass  # corrupt/partial prior dump — start from this pass's items
    for it in new_items:
        k = it.get("url")
        if k:
            pool[k] = it
    with open(path, "w") as f:
        json.dump(list(pool.values()), f, ensure_ascii=False)
    return len(pool)


def login_marker(run_dir, source, fix):
    marker = os.path.join(run_dir, f"{source}_LOGIN_FAILED.json")
    with open(marker, "w") as f:
        json.dump({"source": source, "reason": "not_logged_in", "fix": fix,
                   "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}, f)
    return marker


def wait_for(c, expr, tries=20, pause=2):
    for _ in range(tries):
        try:
            if c.js(expr):
                return True
        except Exception:
            pass
        time.sleep(pause)
    return False


def gentle_scrolls(c, n):
    for _ in range(n):
        c.js(f"window.scrollBy(0,{900 * (1 + random.uniform(-0.2, 0.2)):.0f})")
        time.sleep(random.uniform(0.5, 0.8))


# --- sources ------------------------------------------------------------------

def collect_substack(port, run_dir, st, target, max_clicks):
    st(phase="substack_navigate")
    c = new_page(port, SUBSTACK_URL)
    time.sleep(8)
    # Logged-in signal: inbox feed cards present (/p/ or /p- anchors).
    if not wait_for(c, "document.querySelectorAll('a[href*=\"/p/\"], a[href*=\"/p-\"]').length > 0"):
        m = login_marker(run_dir, "substack",
                         "open Chrome, log into substack.com, retry")
        st(phase="substack", error="not_logged_in", marker=m)
        return None
    c.js(observer("substack_observer.js"))
    st(phase="substack_loadmore", size=c.js("window.__substack_size()"))
    # The loop is a Promise that self-terminates on target/plateau/no_button;
    # js() awaits it. Worst case ~ max_clicks * (3s interval + 1.5s wait) + margin.
    reason = c.js(
        f"window.__substack_loadmore_loop({{target:{target}, max_clicks:{max_clicks}}})",
        timeout=max_clicks * 6 + 60)
    raw = c.js("window.__substack_dump()", timeout=60)
    items = json.loads(raw) if isinstance(raw, str) else (raw or [])
    pool = merge_write(os.path.join(run_dir, "substack.json"), items)
    st(phase="substack_done", got=len(items), pool=pool, reason=reason)
    return len(items)


def collect_medium(port, run_dir, st, target):
    st(phase="medium_navigate")
    c = new_page(port, MEDIUM_URL)
    time.sleep(8)
    # Logged out = redirect to /m/signin (or no feed articles ever render).
    if not wait_for(c, "!location.pathname.startsWith('/m/signin') && document.querySelectorAll('article h2').length > 0"):
        m = login_marker(run_dir, "medium",
                         "open Chrome, log into medium.com (Google SSO), retry")
        st(phase="medium", error="not_logged_in", marker=m)
        return None
    c.js(observer("medium_observer.js"))
    gentle_scrolls(c, random.randint(6, 9))  # render recycled cards for the sweep
    st(phase="medium_more_click", size=c.js("window.__medium_size()"))
    reason = c.js("window.__medium_click_more_once()", timeout=30)
    gentle_scrolls(c, random.randint(3, 5))
    time.sleep(2)  # let the 1.5s periodic sweep catch the last cards
    raw = c.js("window.__medium_dump()", timeout=60)
    items = json.loads(raw) if isinstance(raw, str) else (raw or [])
    pool = merge_write(os.path.join(run_dir, "medium.json"), items)
    st(phase="medium_done", got=len(items), pool=pool, reason=reason,
       target=target)
    return len(items)


# --- main ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--sources", default="substack,medium",
                    help="comma list: substack,medium")
    ap.add_argument("--substack-target", type=int, default=200)
    ap.add_argument("--substack-max-clicks", type=int, default=20)
    ap.add_argument("--medium-target", type=int, default=30)
    ap.add_argument("--profile", default="/tmp/news-web-profile")
    ap.add_argument("--port", type=int, default=9224)
    args = ap.parse_args()

    sources = [s.strip() for s in args.sources.split(",") if s.strip()]
    run_dir = os.path.join(BASE, ".runs", args.date)
    os.makedirs(run_dir, exist_ok=True)
    st = make_status_writer(os.path.join(run_dir, "web_headless_status.json"))

    st(phase="setup", sources=sources)
    setup_profile(args.profile)
    proc = launch(args.profile, args.port)
    results = {}
    try:
        if "substack" in sources:
            try:
                results["substack"] = collect_substack(
                    args.port, run_dir, st, args.substack_target,
                    args.substack_max_clicks)
            except Exception as e:
                st(phase="substack", error=f"exception:{str(e)[:200]}")
                results["substack"] = None
        if "medium" in sources:
            try:
                results["medium"] = collect_medium(
                    args.port, run_dir, st, args.medium_target)
            except Exception as e:
                st(phase="medium", error=f"exception:{str(e)[:200]}")
                results["medium"] = None
        st(phase="all_done", results=results)
        if all(v is None for v in results.values()):
            return 3
        return 0
    finally:
        proc.send_signal(signal.SIGTERM)
        time.sleep(2)
        try:
            proc.kill()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
