---
name: competitor
description: >
  Structured competitor teardown. USE WHEN the user wants a head-to-head
  analysis of a competing product or company — positioning, pricing,
  weaknesses, how to differentiate. Not generic web research.
---

# Competitor

Take a competitor apart systematically. Find the weak points, the moats,
the narrative gaps.

## When to use

- Evaluating a specific competitor ahead of a product decision
- Preparing a battlecard for sales
- Positioning a launch against a known alternative
- Due diligence on acquirability

## When NOT to use

- Generic market scan → `/research/market`
- "What's new in AI" → `/research/web-research` or `/news-digest`
- Academic or scholarly lit → `/research/literature`

## Teardown sections

1. **Identity** — name, tagline, founded, team size, HQ, funding
2. **Positioning** — who they say they're for (target customer + JTBD in their words)
3. **Product** — core capabilities, pricing structure, tiers, integration surface
4. **Differentiation claims** — their top 3 "why us" statements
5. **Evidence** — case studies, customers, growth signals (hiring, news, traffic proxy)
6. **Weaknesses** — gaps, scaling limits, areas they don't cover, user complaints
7. **Pricing** — plans, anchors, contract terms, published or "contact us" opaque
8. **Go-to-market** — sales-led vs. PLG vs. partner-led; paid media footprint; conferences
9. **Technical stack inference** — BuiltWith / Wappalyzer signal; what they build on
10. **Narrative gaps** — what a buyer asks that they don't answer well

## Sources

- Website: pricing, product pages, blog, case studies, jobs board
- LinkedIn: company page, employee count trends, key hires, exits
- Crunchbase: funding, founders, investors
- G2 / Capterra / Gartner Peer Insights: user reviews (honest pain signal)
- Reddit / HN / product Slack: unsolicited user opinion
- Archive.org: positioning changes over time
- Ahrefs / SimilarWeb: traffic proxy (if accessible)
- Twitter / X: founder + team commentary, product updates

## Output

A structured teardown document:

```
# Competitor Teardown: [Company]
Date: YYYY-MM-DD | Analyst: [Name]

## TL;DR (3 bullets)
- Positioning: ...
- Moat: ...
- Weakness to exploit: ...

## 1. Identity
...

## 10. Narrative gaps
...

## Recommended counter-positioning
...

## Sources
- [URL 1]
- [URL 2]
```

## Battlecard (derivative output)

After teardown, generate a 1-page battlecard for sales:
- When a prospect asks about [competitor], say X
- Top 3 objections + responses
- Features we have that they don't
- Features they have that we don't (and what to say)
- Who to target if they're already using [competitor]

## Anti-patterns

- Reading only marketing pages — you need review sites + Reddit
- Taking their self-described weaknesses at face value — real weaknesses aren't published
- Counter-positioning on feature parity — you lose because they got there first
- Ignoring pricing + contract terms — often the real differentiator

## Examples

- "Competitor teardown: Collibra for Matchbox positioning"
- "Battlecard against Alation for data governance sales"
- "How does Databricks position vs Snowflake for Taskflow use case?"
- "Investigate the local compliance tooling landscape against OpenKit"
