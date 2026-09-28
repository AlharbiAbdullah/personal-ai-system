# Browser

Single-page browser automation with built-in debugging. Console and network
monitoring are always active. Sessions auto-start when no active tab exists.

For large-scale data extraction across many pages, use `/scraping` (Apify
for social/business platforms, BrightData for general URLs). Browser is
for interactive single-page tasks: form fills, clicks, screenshots, JS
debugging.

## Capabilities

- **Screenshot**: Capture current page state
- **Navigate**: Go to URL, back, forward
- **Click**: Left, right, double click by coordinates or element ref
- **Fill**: Set form input values by element ref
- **Extract**: Read page text, accessibility tree, find elements
- **Scroll**: Directional scrolling, scroll-to-element
- **Console**: Read browser console logs (errors, warnings, info)
- **Network**: Monitor XHR/Fetch requests and responses

## Process

1. **Get context**: Call `tabs_context_mcp` to find existing tabs
2. **Create tab if needed**: Use `tabs_create_mcp` for new sessions
3. **Navigate**: Go to the target URL
4. **Screenshot first**: Always screenshot before interacting
5. **Act**: Click, fill, scroll, extract as needed
6. **Verify**: Screenshot after actions to confirm result

## Debug-First Approach

Always monitor console and network alongside actions:

- Before debugging: `read_console_messages` with error filter
- After form submit: `read_network_requests` to check API calls
- On page errors: Check console for JavaScript exceptions
- On missing data: Check network for failed requests

## Key Rules

- Always screenshot before clicking. Coordinates must be visually confirmed.
- Click center of elements, not edges.
- Use `find` for locating elements by description.
- Use `read_page` with `filter: "interactive"` for form elements.
- Large pages: use `ref_id` to focus on specific sections.

## Examples

- "Go to example.com and screenshot it"
- "Fill out the contact form on this page"
- "Check the console for errors on this page"
- "Extract the prices from *this* page" (single page — for multi-page extraction, use /scraping)
