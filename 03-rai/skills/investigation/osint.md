# OSINT

Open source intelligence from publicly available data. All lookups use legal,
public sources only. Requires user authorization before any investigation
begins.

## Authorization required

Before starting any OSINT task, confirm with the user:
1. What entity is being investigated.
2. Why (legitimate purpose).
3. Explicit "go ahead" confirmation.

Never proceed without all three.

## Investigation types

Choose investigation type based on target:
- Person → PeopleSearch (see private-investigator.md).
- Company/org → CompanyIntel.
- Domain/IP → delegate to recon.md.
- Threat entity → ThreatIntel.

### CompanyIntel
Corporate filings, leadership team, news coverage, technology stack (from job postings, public repos), financial reports (public companies).

### Investment due diligence
Funding history, market position, team track record, product reviews, red flags (lawsuits, regulatory issues, negative press).

### ThreatIntel
Domain/IP ownership (WHOIS), infrastructure mapping, data breach history, dark web mentions via public aggregators (Shodan, HaveIBeenPwned, IntelX). No direct dark web forum access. Indicators of compromise.

## Process

1. **Authorize:** get explicit user permission.
2. **Scope:** define what information is needed and boundaries.
3. **Collect:** gather from public sources systematically.
4. **Verify:** cross-reference findings across sources.
5. **Analyze:** identify patterns, connections, red flags.
6. **Report:** structured findings with source attribution.

## Output format

- Executive summary (3-5 sentences).
- Findings organized by category.
- Each finding cites its source.
- Confidence level per finding (high/medium/low).
- Red flags section (if any). Red flags: regulatory actions, documented breaches, consistent negative reporting from multiple independent credible sources, criminal proceedings. Not a red flag: single negative review, competitor-sponsored commentary, unverified social posts.
- Information gaps (what could not be found).

## Examples

- "Look up this person's professional background"
- "Research this company before our meeting"
- "Due diligence on this startup before investing"
- "Threat intel: investigate this domain"
