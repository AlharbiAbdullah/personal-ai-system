# BrightData

Progressive scraping strategy with automatic escalation through four tiers.
Start simple, escalate only when needed.

## Four-tier escalation

### Tier 1: WebFetch
First attempt. Fast, simple, no overhead.

- Use the WebFetch tool directly.
- Works for most static pages and simple sites.
- If blocked or content is missing, move to Tier 2.

### Tier 2: curl with headers
Add browser-like headers to bypass basic blocks.

- Set User-Agent, Accept, Accept-Language headers.
- Add Referer header matching the target domain.
- Works for sites that block bare requests.
- If still blocked, move to Tier 3.

### Tier 3: Browser automation
Full browser rendering for JavaScript-heavy sites.

- Use the Browser skill to navigate and extract.
- Handles SPAs, dynamic content, lazy loading.
- Can interact with the page (scroll, click "load more").
- If blocked by anti-bot (Cloudflare, CAPTCHA), move to Tier 4.

### Tier 4: Bright Data MCP
Tier 4: Bright Data residential/datacenter proxies. Requires: Bright Data account + API key + MCP configuration. Slowest and paid — use only when Tiers 1-3 fail.

- Route through Bright Data residential/datacenter proxies.
- Handles geo-restricted content.
- Bypasses sophisticated anti-bot systems.
- Use only when Tiers 1-3 fail.

## Process

1. **Start at Tier 1.** Attempt WebFetch.
2. **Evaluate result.** Check if content is complete and valid.
3. **Escalate if needed.** Move to next tier on failure.
4. **Report tier used.** Tell the user which method succeeded.

## Output format

- Extracted content (cleaned and formatted).
- Tier used and why escalation was needed (if applicable).
- Any data quality notes (partial content, missing elements).

## Cost/performance

- Tier 1 (WebFetch): fast, free.
- Tier 2 (curl+headers): fast, free.
- Tier 3 (browser): slower, free compute.
- Tier 4 (BrightData proxy): slowest, paid.

## Examples

- "Scrape this article URL" (starts at Tier 1).
- "Get pricing data from this site" (may need Tier 2-3).
- "Extract data from this geo-restricted page" (likely Tier 4).
