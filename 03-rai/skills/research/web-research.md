# Web Research

Generalist web research. Gathers information from multiple sources in parallel,
cross-references findings, and produces verified, cited results.

This is the default specialization in `/research/`. For domain-specific
specializations, see `competitor.md`, `literature.md`, `market.md` and `academic.md` in this router.

## Modes

**Quick:** single focused search. For simple factual lookups.
**Standard:** 3 parallel search angles. For most research requests.
**Deep:** progressive iterative research. Multiple rounds of searching, each informed by previous findings. For complex or nuanced topics.

## Process

1. **Decompose** the question into 2-5 searchable sub-queries.
2. **Search** in parallel using WebSearch for each sub-query.
3. **Cross-reference** findings across sources for accuracy.
4. **Synthesize** into a structured answer with citations.
5. **Verify** key claims have multiple supporting sources.

## Output format

- Lead with the answer, not the process.
- Cite sources inline.
- Flag conflicting information explicitly.
- Note confidence level (high/medium/low) for each claim.
- List sources at the end.
- When the ask is a written, verified answer that lives in the vault, carry the output into [[18-deep-research-to-home]] at step 3. From there it checks the claims and decides the home.

## Examples

- "Research the best Python testing frameworks for 2026"
- "Investigate how Company X handles authentication"
- "Compare Redis vs Valkey for caching"
- "Research what changed in Python 3.13"

## Guidelines

- Prefer primary sources (docs, papers, official blogs) over secondary.
- When sources conflict, present both views with evidence.
- Do not fabricate citations. If unsure, say so.
- For technical topics, include code examples when available.
- Time-bound claims: note when information was published.
