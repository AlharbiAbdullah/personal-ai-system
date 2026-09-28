// substack_observer.js
// Capture Substack home-feed posts into window.__substack as they enter the DOM.
// Mirrors the x_observer.js pattern: MutationObserver + periodic re-sweep so we
// don't miss posts that the feed recycles out of view during scrolling.
// Installed once per page load via javascript_tool, before any scrolling.

(() => {
  if (window.__substack_observer_installed) return 'already_installed';
  window.__substack_observer_installed = true;
  window.__substack = new Map();

  const harvest = (anchor) => {
    try {
      const href = anchor.getAttribute('href');
      if (!href || !(href.includes('/p/') || href.includes('/p-'))) return;
      // 2026-05-06: /inbox uses /home/post/p-{id}?source=queue path, not /p/{slug}.
      // Backport of P2 fix from runtime; verified in f15.

      // Normalize: strip query string + fragment so dedup is reliable
      const url = href.split('?')[0].split('#')[0];
      if (window.__substack.has(url)) return;

      // Title lives in a child with "title" in the class name (obfuscated)
      const title = anchor.querySelector('[class*="title"]')?.textContent?.trim();
      if (!title) return;

      const container = anchor.closest('[class]');
      const author = container?.querySelector('a[href*="substack.com"]')?.textContent?.trim() || '';
      const subtitle = container?.querySelector('[class*="subtitle"]')?.textContent?.trim() || '';
      const date = container?.querySelector('time')?.getAttribute('datetime')
                 || container?.querySelector('time')?.textContent?.trim()
                 || null;

      window.__substack.set(url, {
        url,
        title,
        author,
        subtitle,
        date,
      });
    } catch (_e) {
      // Swallow errors so one malformed card can't stop the observer
    }
  };

  const sweep = () => {
    document.querySelectorAll('a[href*="/p/"], a[href*="/p-"]').forEach(harvest);
  };

  // Seed with whatever is already rendered
  sweep();

  // Catch every new anchor that enters the DOM
  const observer = new MutationObserver((mutations) => {
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches && (node.matches('a[href*="/p/"]') || node.matches('a[href*="/p-"]'))) {
          harvest(node);
        }
        if (node.querySelectorAll) {
          node.querySelectorAll('a[href*="/p/"], a[href*="/p-"]').forEach(harvest);
        }
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  window.__substack_observer_handle = observer;

  // Periodic re-sweep catches the case where the feed swaps nodes in place
  window.__substack_observer_interval = setInterval(sweep, 1500);

  // Control surface exposed to javascript_tool polling
  window.__substack_size = () => window.__substack.size;
  window.__substack_dump = () => JSON.stringify([...window.__substack.values()]);
  window.__substack_reset = () => {
    window.__substack = new Map();
    return 0;
  };
  window.__substack_uninstall = () => {
    try {
      window.__substack_observer_handle?.disconnect();
      clearInterval(window.__substack_observer_interval);
      if (window.__substack_loadmore_handle) {
        clearInterval(window.__substack_loadmore_handle);
        window.__substack_loadmore_handle = null;
      }
    } catch (_e) {}
    window.__substack_observer_installed = false;
    return 'uninstalled';
  };

  // 2026-05-06 (f15): /inbox paginates via "Load more" button. Click-loop adds ~20
  // posts per click, linear, until button vanishes (~250 ceiling for this user).
  // Caller invokes window.__substack_loadmore_loop({ target, max_clicks, click_interval_ms })
  // and polls __substack_size(). Loop self-terminates and resolves to a status string.
  window.__substack_loadmore_loop = (opts = {}) => {
    const target = opts.target || 200;
    const max_clicks = opts.max_clicks || 20;
    const click_interval_ms = opts.click_interval_ms || 3000;
    const post_click_wait_ms = opts.post_click_wait_ms || 1500;
    return new Promise((resolve) => {
      if (window.__substack_loadmore_handle) {
        return resolve('already_running');
      }
      const findBtn = () => Array.from(document.querySelectorAll('button'))
        .find((b) => /^\s*load more\s*$/i.test(b.innerText || ''));
      let clicks = 0;
      let stable = 0;
      let last = window.__substack.size;
      const tick = () => {
        const btn = findBtn();
        if (!btn) {
          clearInterval(window.__substack_loadmore_handle);
          window.__substack_loadmore_handle = null;
          return resolve(`no_button:clicks=${clicks},count=${window.__substack.size}`);
        }
        try { btn.scrollIntoView({ block: 'center' }); btn.click(); } catch (_e) {}
        clicks++;
        setTimeout(() => {
          const cur = window.__substack.size;
          if (cur === last) stable++; else stable = 0;
          last = cur;
          if (cur >= target) {
            clearInterval(window.__substack_loadmore_handle);
            window.__substack_loadmore_handle = null;
            return resolve(`target_met:clicks=${clicks},count=${cur}`);
          }
          if (stable >= 3 || clicks >= max_clicks) {
            clearInterval(window.__substack_loadmore_handle);
            window.__substack_loadmore_handle = null;
            return resolve(`${stable >= 3 ? 'plateau' : 'max_clicks'}:clicks=${clicks},count=${cur}`);
          }
        }, post_click_wait_ms);
      };
      window.__substack_loadmore_handle = setInterval(tick, click_interval_ms);
      tick();
    });
  };

  return 'installed';
})();
