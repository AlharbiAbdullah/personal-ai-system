// x_observer.js
// Capture tweets from X's timeline into window.__tweets as they enter the DOM.
// Fixes the DOM-virtualization problem: React drops old tweets from the DOM as
// new ones scroll in, so post-hoc extraction misses 80% of what flew by.
// Installed once per page load via javascript_tool, before any scrolling.
//
// v5.7 (2026-06-15): per-tweet media/article enrichment so the synthesis-step
// Claude can weigh demos, papers, articles and threads — not just text. Adds
// truncated/has_video/has_image/media_count/is_article/link_domain/is_quote,
// and best-effort inline "Show more" expansion to capture full long-post text.

(() => {
  if (window.__x_observer_installed) return 'already_installed';
  window.__x_observer_installed = true;
  window.__tweets = new Map();

  const parseCount = (s) => {
    if (!s) return 0;
    s = String(s).trim().toUpperCase().replace(/,/g, '');
    const n = parseFloat(s);
    if (isNaN(n)) return 0;
    if (s.endsWith('K')) return Math.round(n * 1e3);
    if (s.endsWith('M')) return Math.round(n * 1e6);
    if (s.endsWith('B')) return Math.round(n * 1e9);
    return Math.round(n);
  };

  // X's own hosts — never report these as the tweet's external link.
  const SELF_HOSTS = /(^|\.)(x\.com|twitter\.com|t\.co|pic\.twitter\.com)$/i;

  // The external domain a tweet points out to (arxiv/github/substack/a blog) —
  // the "article" signal in the news sense. X masks the real href behind t.co,
  // but renders the human domain as the anchor's VISIBLE text, so read innerText
  // (the href would just say t.co).
  const linkDomain = (article) => {
    try {
      for (const a of article.querySelectorAll('a')) {
        const txt = (a.innerText || '').trim().toLowerCase();
        const m = txt.match(/^([a-z0-9.-]+\.[a-z]{2,})(\/|\s|$)/);
        if (m && !SELF_HOSTS.test(m[1])) return m[1];
      }
      const card = article.querySelector('[data-testid="card.wrapper"]');
      if (card) {
        const m = (card.innerText || '').toLowerCase()
          .match(/([a-z0-9-]+\.[a-z]{2,}(?:\.[a-z]{2,})?)/);
        if (m && !SELF_HOSTS.test(m[1])) return m[1];
      }
    } catch (_e) {}
    return '';
  };

  const detectMedia = (article) => {
    const m = { has_video: false, has_image: false, media_count: 0,
                is_article: false, is_quote: false };
    try {
      m.has_video = !!article.querySelector(
        '[data-testid="videoComponent"], [data-testid="videoPlayer"], video');
      const photos = article.querySelectorAll('[data-testid="tweetPhoto"]');
      m.media_count = photos.length;
      m.has_image = photos.length > 0;
      m.is_article = !!article.querySelector(
        'a[href*="/i/article/"], [data-testid="article"]');
      // A quoted tweet nests a second author block inside the article.
      m.is_quote = article.querySelectorAll('[data-testid="User-Name"]').length > 1;
    } catch (_e) {}
    return m;
  };

  // The inline "Show more" control on a truncated long post. Detected via the
  // testid first, then a text fallback so a testid rename can't blind us.
  const findShowMore = (article) => {
    const direct = article.querySelector('[data-testid="tweet-text-show-more-link"]');
    if (direct) return direct;
    for (const el of article.querySelectorAll('button, span, div, a')) {
      if ((el.innerText || '').trim().toLowerCase() === 'show more') return el;
    }
    return null;
  };

  const harvest = (article) => {
    try {
      // Find the first /status/<id> link inside the article, which is the permalink
      const statusLink = article.querySelector('a[href*="/status/"]');
      if (!statusLink) return;
      const idMatch = statusLink.href.match(/status\/(\d+)/);
      if (!idMatch) return;
      const id = idMatch[1];
      // Re-harvest only while truncated (to catch expanded text); once the post
      // is full (or never had a Show more), the first capture is final. Cheap —
      // the DOM only holds the visible screenful at any time.
      const existing = window.__tweets.get(id);
      if (existing && !existing.truncated) return;

      const textEl = article.querySelector('[data-testid="tweetText"]');
      const nameEl = article.querySelector('[data-testid="User-Name"]');
      const timeEl = article.querySelector('time');

      const nameText = nameEl?.innerText || '';
      const nameLines = nameText.split('\n').filter(Boolean);
      const author = nameLines[0] || '';
      const handleMatch = nameText.match(/@\w+/);
      const handle = handleMatch ? handleMatch[0] : '';

      // Engagement buttons carry aria-labels like "1,234 replies", "56 reposts",
      // "12K likes", "1.2M views". Scrape them all.
      const metrics = { replies: 0, reposts: 0, likes: 0, views: 0, bookmarks: 0 };
      article.querySelectorAll('[role="group"] [aria-label]').forEach((el) => {
        const label = (el.getAttribute('aria-label') || '').toLowerCase();
        const numMatch = label.match(/([\d.,]+[kmb]?)\s*(repl|repost|like|view|bookmark)/i);
        if (!numMatch) return;
        const count = parseCount(numMatch[1]);
        const kind = numMatch[2].toLowerCase();
        if (kind.startsWith('repl')) metrics.replies = count;
        else if (kind.startsWith('repost')) metrics.reposts = count;
        else if (kind.startsWith('like')) metrics.likes = count;
        else if (kind.startsWith('view')) metrics.views = count;
        else if (kind.startsWith('bookmark')) metrics.bookmarks = count;
      });

      const media = detectMedia(article);

      window.__tweets.set(id, {
        id,
        url: statusLink.href.split('?')[0],
        text: textEl?.innerText || '',
        author,
        handle,
        ts: timeEl?.dateTime || null,
        likes: metrics.likes,
        reposts: metrics.reposts,
        replies: metrics.replies,
        views: metrics.views,
        bookmarks: metrics.bookmarks,
        // v5.7 enrichment
        truncated: !!findShowMore(article),
        has_video: media.has_video,
        has_image: media.has_image,
        media_count: media.media_count,
        is_article: media.is_article,
        is_quote: media.is_quote,
        link_domain: linkDomain(article),
      });
    } catch (_e) {
      // Swallow errors so one malformed tweet can't stop the observer
    }
  };

  // Expand truncated long posts in place. Click ONLY a non-anchor control — an
  // <a> "Show more" navigates to the standalone tweet and would kill the scroll;
  // that case we leave flagged truncated and ship the visible text. Runs on the
  // periodic sweep (not inside the MutationObserver callback) to avoid clicking
  // during a re-entrant mutation; the expanded text is picked up next sweep
  // because truncated entries are allowed to re-harvest.
  const expandPass = () => {
    document.querySelectorAll('article[data-testid="tweet"]').forEach((article) => {
      try {
        const sm = findShowMore(article);
        if (sm && sm.tagName !== 'A') sm.click();
      } catch (_e) {}
    });
  };

  // Seed with whatever articles are already rendered at install time
  document.querySelectorAll('article[data-testid="tweet"]').forEach(harvest);

  // Catch every article that enters the DOM from now on
  const observer = new MutationObserver((mutations) => {
    for (const mut of mutations) {
      for (const node of mut.addedNodes) {
        if (node.nodeType !== 1) continue;
        if (node.matches && node.matches('article[data-testid="tweet"]')) {
          harvest(node);
        }
        if (node.querySelectorAll) {
          node.querySelectorAll('article[data-testid="tweet"]').forEach(harvest);
        }
      }
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
  window.__x_observer_handle = observer;

  // Re-sweep every 1.5s: expand any visible "Show more", then re-harvest in case
  // React swapped nodes without firing addedNodes (it reuses a node and mutates
  // its children in place) and to capture freshly-expanded text.
  window.__x_observer_interval = setInterval(() => {
    expandPass();
    document.querySelectorAll('article[data-testid="tweet"]').forEach(harvest);
  }, 1500);

  // Control surface exposed to javascript_tool polling
  window.__tweets_size = () => window.__tweets.size;
  window.__tweets_dump = () => JSON.stringify([...window.__tweets.values()]);
  window.__tweets_reset = () => {
    window.__tweets = new Map();
    return 0;
  };
  window.__tweets_uninstall = () => {
    try {
      window.__x_observer_handle?.disconnect();
      clearInterval(window.__x_observer_interval);
    } catch (_e) {}
    window.__x_observer_installed = false;
    return 'uninstalled';
  };

  return 'installed';
})();
