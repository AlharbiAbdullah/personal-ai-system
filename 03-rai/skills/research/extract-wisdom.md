# ExtractWisdom

Extract wisdom from any content. Adapts output sections dynamically based on
what the content actually contains. No filler sections.

## Depth levels

| Level | Time | When |
|-------|------|------|
| Instant | <10s | Quick summary, 3-5 bullet points |
| Quick | <30s | Key ideas + quotes + takeaways |
| Standard | <2min | Full extraction, all relevant sections |
| Deep | <5min | Standard + connections to existing knowledge |
| Comprehensive | <15min | Deep + research verification + follow-ups |

Default is Standard unless specified.

User can specify depth: `instant`, `quick`, `standard`, `deep`, `comprehensive`. Default is `standard`.

## Adaptive sections

Include only sections that have real content. Skip empty sections.

| Section | Include When |
|---------|-------------|
| Summary | Always |
| Key Ideas | Content has distinct ideas or arguments |
| Insights | Content reveals non-obvious patterns |
| Quotes | Content has memorable exact quotes |
| Habits/Practices | Content describes actionable behaviors |
| Facts/Data | Content contains statistics or data points |
| References | Content mentions books, papers, people |
| Recommendations | Content suggests tools, resources, actions |
| Takeaways/Reflection | Include personal takeaways when the content is actionable; use neutral 'reflection' for non-actionable content. |

## Tone rules

- Write as if explaining to a smart friend over coffee.
- Use "you" and "your", not "one" or "the reader".
- Short sentences. No filler. No hedging.
- State opinions directly: "This is wrong because..." not "It could be argued..."
- Preserve the speaker's voice in quotes (exact words).

## Process

1. **Assess content type:** transcript, article, book chapter, etc.
2. **Set depth level:** based on user request or default to Standard.
3. **Extract raw material:** ideas, quotes, data, references.
4. **Select sections:** include only sections with real content.
5. **Write conversationally:** apply tone rules.
6. **Add takeaways:** personal, actionable, specific.

## Examples

- "Extract wisdom from this podcast transcript"
- "Deep extraction on this article about distributed systems"
- "Quick wisdom from this YouTube video summary"
- "Comprehensive extraction of this book chapter"
