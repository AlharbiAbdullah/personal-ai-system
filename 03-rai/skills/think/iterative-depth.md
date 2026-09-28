# Iterative Depth

Run 2-8 structured passes through the same problem, each from a different
analytical lens. Each pass builds on and challenges previous findings.

## Lenses (select 2-8 based on complexity)

1. **Technical**: How does it work? What are the constraints?
2. **User**: Who benefits? What's the experience?
3. **Economic**: What does it cost? What's the ROI?
4. **Risk**: What can go wrong? What are the edge cases?
5. **Historical**: What's been tried before? What failed and why?
6. **Contrarian**: What if the opposite is true? Devil's advocate.
7. **Systems**: How does it interact with everything else?
8. **Future**: Where does this lead in 1, 3, 5 years?

### Lens Selection by Problem Type

- Feature design → user + technical + economic lenses
- System failure → risk + historical + systems
- Strategic decision → time + competitive + resource
- Code review → correctness + security + maintainability

## Process

1. **Select lenses** based on the problem (minimum 2)
2. **First pass**: Apply lens 1, document findings
3. **Challenge pass**: Apply lens 2, challenge findings from pass 1
4. **Synthesis**: What did multiple lenses reveal that one alone missed?
5. **Repeat** with additional lenses if needed
6. **Output**: Integrated analysis with confidence levels

## Modes

**Quick** = 2 lenses. Fast exploration. Use when time-constrained.
**Standard** = 3-4 lenses. Good balance. Default for most requests.
**Deep** = 5+ lenses. Full exploration. Use for major decisions. Don't exceed 8 — diminishing returns.

## Output

Each pass produces:
- New insights not visible from previous angles
- Challenges to previous conclusions
- Refined understanding with confidence levels

Final synthesis highlights:
- Points of agreement across lenses
- Unresolved tensions
- Recommended path with supporting reasoning

## Confidence Assessment

For each finding, track how many lenses independently surfaced it.
- 1 lens = exploratory
- 2-3 lenses = worth attention
- 4+ lenses = high-confidence

## Stopping Rule

Stop when new lenses confirm prior findings (diminishing returns) or when confidence is sufficient for the decision at hand.

## Examples

- "Explore our database migration decision with iterative depth"
- "Deep analysis: should we build or buy this feature?"
- "Multi-angle review of our API design"
