# Apify

Run Apify actors for social media scraping and business data extraction. Uses
token-efficient file-based filtering to handle large datasets.

## Supported platforms

| Platform | Data Types |
|----------|-----------|
| Instagram | Profiles, posts, reels, hashtags, comments |
| LinkedIn | Company profiles, job listings, people search |
| TikTok | Videos, profiles, hashtags, comments |
| YouTube | Videos, channels, comments, search results |
| Google Maps | Business listings, reviews, contact info |
| Amazon | Product data, reviews, pricing, sellers |

## Process

1. **Identify the actor.** Match the platform and data type to the right Apify actor.
2. **Configure input.** Set search terms, URLs, limits, and filters.
3. **Run the actor.** Execute via Apify API with the configured input.
4. **Retrieve results.** Pull dataset from Apify storage.
5. **Filter and format.** Write results to file, apply filters, present summary.

## File-based filtering

For large datasets (100+ items), write raw results to a JSON file first.
Then filter in-memory to avoid blowing the context window.

```
Raw data -> ~/Downloads/apify_[actor]_[timestamp].json
Filtered -> Present summary + key metrics in response
```

## Output format

- Summary statistics (total items, date range, key metrics).
- Top results table (5-10 items).
- Full dataset path for user reference.
- Note any rate limits or incomplete data.

## Examples

- "Scrape the top 50 Instagram posts for #datascience"
- "Get business listings for coffee shops in Austin from Google Maps"
- "Pull the latest 100 videos from this YouTube channel"
- "Scrape Amazon reviews for this product URL"

## Actor discovery

Browse https://apify.com/store or ask 'which Apify actor extracts [data] from [platform]?' Rai can search actor descriptions.

## Rate limits and cost

Apify runs consume credits per actor invocation. Check plan limits before scraping >1000 items. For datasets >100K items, use pagination via the Apify API directly.
