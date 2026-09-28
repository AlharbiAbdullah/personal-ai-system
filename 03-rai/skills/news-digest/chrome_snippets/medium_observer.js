// medium_observer.js
// Capture Medium "For you" feed articles into window.__medium as they enter the DOM.
// Mirrors x_observer.js + substack_observer.js: MutationObserver + periodic re-sweep.
// Installed once per page load via javascript_tool, before any scrolling.

(() => {
  if (window.__medium_observer_installed) return 'already_installed';
  window.__medium_observer_installed = true;
  window.__medium = new Map();

  // 2026-05-06 (f16): /me/following-feed/all uses RELATIVE URLs like
  // /@author/article-slug?source=following_feed---0. The previous selector
  // a[href*="medium.com"], a[href*=".com/"] required absolute URLs and missed
  // 20 of 25 visible articles. Anchor identification now goes through
  // h2.closest('a') which finds the actual title link reliably across both
  // home (absolute URLs) and following-feed (relative URLs).
  const harvest = (article) => {
    try {
      const h2 = article.querySelector('h2');
      if (!h2) return;

      const titleAnchor = h2.closest('a') || article.querySelector('a:has(h2)');
      const href = titleAnchor?.getAttribute('href');
      if (!href || href.startsWith('#')) return;

      // Normalize: resolve relative → absolute, strip query/fragment.
      // Stripping ?source=... is also required to bypass E01's output filter.
      let url;
      try {
        url = new URL(href, location.origin).toString().split('?')[0].split('#')[0];
      } catch {
        return;
      }
      if (window.__medium.has(url)) return;

      const title = h2.textContent?.trim();
      if (!title) return;

      const author = article.querySelector('a[href*="/@"], a[href*="/u/"]')?.textContent?.trim() || '';
      const subtitle = article.querySelector('h3, p')?.textContent?.trim() || '';
      const readTime = article.querySelector('[class*="readingTime"], [class*="min read"]')?.textContent?.trim() || '';
      const claps = article.querySelector('[class*="clap"]')?.textContent?.trim() || '';

      window.__medium.set(url, {
        url,
        title,
        author,
        subtitle,
        readTime,
        claps,
      });
    } catch (_e) {
      // Swallow errors so one malformed card can't stop the observer
    }
  };

  const sweep = () => {
    document.querySelectorAll('article').forEach(harvest);
  };

  sweep();

  const observer = new MutationObserver((mutations) => {
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches && node.matches('article')) {
          harvest(node);
        }
        if (node.querySelectorAll) {
          node.querySelectorAll('article').forEach(harvest);
        }
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  window.__medium_observer_handle = observer;

  window.__medium_observer_interval = setInterval(sweep, 1500);

  // Control surface
  window.__medium_size = () => window.__medium.size;
  window.__medium_dump = () => JSON.stringify([...window.__medium.values()]);
  window.__medium_reset = () => {
    window.__medium = new Map();
    return 0;
  };
  window.__medium_uninstall = () => {
    try {
      window.__medium_observer_handle?.disconnect();
      clearInterval(window.__medium_observer_interval);
    } catch (_e) {}
    window.__medium_observer_installed = false;
    return 'uninstalled';
  };

  // 2026-05-06 (f16): /me/following-feed/all has a "More" button that adds ~5
  // articles once, then disappears. Not a true paginator — just one click yields
  // the marginal extras. Caller invokes window.__medium_click_more_once() then
  // dumps. Returns whether a click happened.
  window.__medium_click_more_once = () => {
    return new Promise((resolve) => {
      const btn = Array.from(document.querySelectorAll('button'))
        .find((b) => /^\s*(more|show more|load more)\s*$/i.test(b.innerText || ''));
      if (!btn) return resolve('no_button');
      try { btn.scrollIntoView({ block: 'center' }); btn.click(); } catch (_e) {}
      setTimeout(() => resolve(`clicked:count=${window.__medium.size}`), 1500);
    });
  };

  return 'installed';
})();
