---
name: scraping
description: >
  Web and platform scraping router. USE WHEN the user wants to extract data
  from websites, social platforms, or business listings. Routes between Apify
  (social media + business data) and BrightData (progressive escalation for
  hard-to-reach URLs).
---

# Scraping

Two scraping approaches live in this category. Pick by the shape of the task,
then `Read` the matching sub-skill file in this directory and follow it.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Instagram, LinkedIn, TikTok, YouTube data | Apify | `apify.md` |
| Google Maps business listings, reviews | Apify | `apify.md` |
| Amazon product data, reviews, sellers | Apify | `apify.md` |
| Lead generation from social platforms | Apify | `apify.md` |
| Any URL not covered by Apify | BrightData | `brightdata.md` |
| URL blocked by anti-bot, Cloudflare, CAPTCHA | BrightData | `brightdata.md` |
| JS-heavy SPA, lazy-loaded content | BrightData | `brightdata.md` |
| Geo-restricted page | BrightData | `brightdata.md` |

## How to use

1. Identify which sub-skill matches the task using the table above.
2. `Read` the file in this directory (`apify.md` or `brightdata.md`).
3. Follow that file's instructions.

If the URL is on an Apify-supported platform (Instagram, LinkedIn, TikTok, YouTube, Google Maps, Amazon, etc.), prefer Apify — it's faster and cheaper. If the platform isn't on the Apify list, or you're not sure, start with BrightData Tier 1 (WebFetch).

If unsure which platform tool the user wants, ask once before scraping.
