# Security Updates

Aggregate security news from multiple sources in parallel. Categorize,
prioritize, and present findings in a structured briefing.

## Sources

- tldrsec newsletter (https://tldrsec.com/)
- CISA advisories (https://www.cisa.gov/news-events/cybersecurity-advisories)
- NVD — National Vulnerability Database (https://nvd.nist.gov/)
- Security vendor blogs — CrowdStrike (https://www.crowdstrike.com/blog/), Mandiant (https://cloud.google.com/blog/topics/threat-intelligence), Palo Alto Unit 42 (https://unit42.paloaltonetworks.com/)
- Hacker News security threads (https://news.ycombinator.com/)
- GitHub Security Advisories (https://github.com/advisories)

## Three Categories

### News
Active incidents and breach reports.
- Who was breached, when, what was exposed
- Impact scope and response status
- Relevance to our tech stack

### Research
CVEs, vulnerability disclosures, and technical findings.
- CVE ID, severity (CVSS), affected software
- Exploit availability and active exploitation status
- Patch/mitigation availability

### Ideas
Emerging trends, new tools, and strategic shifts.
- New attack techniques and defense approaches
- Tool releases and framework updates
- Regulatory changes and compliance impacts

## Process

1. **Fetch**: Pull from all sources in parallel. Fetch mechanism: RSS feeds where available (https://<source>/feed); WebFetch for those without RSS. Parse the last N hours of posts based on the requested window.
2. **Deduplicate**: Same story from multiple sources gets merged
3. **Categorize**: Assign to News, Research, or Ideas
4. **Prioritize**: Rank by relevance to user's tech stack
5. **Brief**: Present in structured format

## Relevance

Cross-reference each finding with the user's tech stack (from `~/helm/02-ana/identity/tech-stack.md`). Flag items that touch the user's stack as high priority.

## Update frequency

Default window: last 7 days. User can specify: "last 24 hours", "this week", "this month".

## Output Format

Each item includes:
- Category tag (News/Research/Ideas)
- Priority (critical/high/medium/low)
- One-line summary
- Source link
- Relevance note (why it matters to us)

## Examples

- "Security briefing for this week"
- "Any critical CVEs in the last 48 hours?"
- "What's trending in cybersecurity this month?"
- "Check for vulnerabilities affecting Python or Node.js"
