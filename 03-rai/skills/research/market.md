---
name: market
description: >
  Market research: sizing, segmentation, trend lines, sources. USE WHEN the
  user needs to understand a market — TAM/SAM/SOM, growth rates, segments,
  incumbents, regulatory environment. For strategic + investment decisions.
---

# Market Research

Size a market. Identify segments. Spot trends. Cite sources.

## When to use

- Pitch deck needs TAM/SAM/SOM numbers
- Board asks "is this market growing?"
- Strategic decision: enter a new geography / segment
- Investor diligence — defensible market narrative

## When NOT to use

- Single-competitor analysis → `/research/competitor`
- Academic depth on a research question → `/research/literature`
- Quick factual lookup → `/research/web-research`

## Output artifact

A market research memo:

```
# Market Research: [Market Name]
Date: YYYY-MM-DD | Horizon: [1–5 years]

## TL;DR
- Size today: [$X B]
- Growth: [Y%] CAGR through [year]
- Key segments: [list]
- Incumbents: [list]
- Our entry angle: [one sentence]

## 1. Market definition
[What's in, what's out — scope matters]

## 2. Size
### TAM (Total Addressable)
- $X B in YEAR
- Source: [analyst firm / IBM/ Gartner / Statista / IDC]

### SAM (Serviceable Addressable)
- Filter TAM by geography + segment we can actually reach
- $Y B

### SOM (Serviceable Obtainable)
- Realistic capture given our GTM, in 3–5 years
- $Z B

## 3. Segmentation
- By buyer: [SMB / mid-market / enterprise / government]
- By use case: [...]
- By geography: [...]

## 4. Trends
- [Trend 1] — data point + source
- [Trend 2] — data point + source
- [Trend 3] — data point + source

## 5. Incumbents
[Table: name, market share if known, positioning]

## 6. Regulatory environment
- [Relevant frameworks: the national data authority, GDPR, HIPAA]
- [Pending regulation that could shift dynamics]

## 7. Entry angle
[Where we fit; why now; which segment first]

## Sources
- [URL 1]
- [URL 2]
```

## Sources (ranked by credibility)

1. **Analyst firms** — Gartner, Forrester, IDC, McKinsey, Bain, BCG. Paywalled but often cited for free.
2. **Government statistics** — the national statistics office, BLS for US, Eurostat, OECD
3. **Industry associations** — often publish annual reports with sizing
4. **Company filings** — 10-Ks disclose TAM narratives for public incumbents
5. **Investor reports** — equity research from Morgan Stanley, Goldman, regional banks
6. **Trade publications** — industry-specific (modeled, cited cautiously)
7. **Academic papers** — slower to publish but often more rigorous
8. **LinkedIn + news scrapes** — directional signal, not sizing

## Sizing approaches

- **Top-down** — analyst TAM × filters for SAM × GTM assumptions for SOM
- **Bottom-up** — number of buyers × price per buyer. More rigorous but requires buyer estimates.
- **Value-chain** — what % of adjacent markets' spend is captured by this category

Triangulate at least two approaches. If they disagree wildly, the market definition or assumptions are off.

## Anti-patterns

- One source, uncited or "according to some reports"
- Extrapolating global CAGR to a specific region without adjustment
- Conflating TAM growth with our growth
- "The XYZ market is $100B" without defining what "XYZ market" means
- Ignoring substitutes and adjacent markets that could cannibalize

## Examples

- "Size the developer-tooling market for project scaffolding"
- "Market research on data governance software"
- "TAM for self-hosted BI in mid-market healthcare"
- "What's the addressable market for on-prem AI platforms in regulated industries?"
