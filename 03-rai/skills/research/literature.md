---
name: literature
description: >
  Academic and peer-reviewed paper survey. USE WHEN the user wants a
  systematic literature review: key papers on a topic, citation graph,
  methodology comparison. For scholarly depth, not quick web scans.
---

# Literature Review

Survey academic literature on a topic with methodology, citation tracing, and critical synthesis.

## When to use

- Rigorous background before a research project or thesis
- Technical due diligence where academic basis matters (AI, crypto, medicine)
- Locating seminal papers + their intellectual descendants
- Comparing methodologies across a research area

## When NOT to use

- Quick answer to a factual question → `/research/web-research`
- Industry trend scanning → `/research/market`
- Building a business case → `/research/competitor`

## Sources

- Google Scholar — citation counts + full-text search
- Semantic Scholar — citation graph + AI-suggested related work
- arXiv — preprints (CS, physics, math, stats, econ)
- PubMed — biomedical
- ACM Digital Library / IEEE Xplore — CS/engineering
- Connected Papers — visual citation graph around a seed paper
- DBLP — CS publication database

## Process

1. **Define the question precisely** — one sentence. "What is the state of X" is too broad. "Which retrieval strategies minimize hallucination in domain-specific RAG?" is scoped.

2. **Seed papers** — find 3–5 highly-cited or recent key papers. Start with Google Scholar sort by citation count + recency.

3. **Forward + backward citation trace**:
   - Backward: read seeds' references; pick the most-cited ones
   - Forward: find papers that cite the seeds (Google Scholar "cited by")
   - Stop when you hit papers you've already seen (saturation)

4. **Extract** for each paper:
   - Problem statement
   - Methodology
   - Dataset / experimental setup
   - Key findings
   - Limitations (stated + inferred)
   - Citations in/out

5. **Cluster** — group papers by approach, not by chronology. "Dense retrieval approaches", "sparse approaches", "hybrid" — then trace each cluster.

6. **Synthesize** — what's the consensus? Where do experts disagree? What's unanswered?

7. **Critical assessment** — which papers replicate, which don't; which authors have retractions; sample sizes, p-hacking signals.

## Output

```
# Literature Review: [Topic]
Date: YYYY-MM-DD

## Question
[One sentence]

## Search protocol
- Databases: [list]
- Keywords: [list]
- Inclusion criteria: [list]
- Exclusion criteria: [list]
- Papers reviewed: [N]

## Clusters
### Cluster 1: [Approach name]
- [Seminal paper] (Author, Year)
- [Key followup] (Author, Year)
- Findings: ...
- Limitations: ...

## Synthesis
- Consensus: ...
- Disagreements: ...
- Gaps: ...

## Recommended reading (ranked)
1. [Paper] — why it matters
...

## Citations
[Formatted bibliography]
```

## Anti-patterns

- Counting citations without reading — citation count ≠ quality
- Cherry-picking papers that support a preferred conclusion
- Ignoring non-English literature where relevant (medicine, materials science)
- Skipping the limitations sections — that's where the truth hides
- Conflating correlation findings with causal claims

## Examples

- "Literature review on RAG hallucination mitigation"
- "Survey papers on federated learning in healthcare"
- "What does the academic literature say about prompt injection defenses?"
- "Key papers on medallion architecture + data quality"
