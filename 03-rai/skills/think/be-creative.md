# Be Creative

Generate diverse, high-quality ideas by exploring multiple creative angles
before converging on the best option.

## Technique

Use extended thinking to internally generate 5 diverse options
(each with probability < 0.10 of being the "obvious" answer).
Output the single best response, or present top 3 if user wants options.

## Workflows

### BrainstormThenPick
Default workflow for creative requests. Generate N diverse options, present top choice or top-3 per user preference.
For naming, branding, novel solutions, and artistic direction, push harder: deliberately avoid cliches and combine unrelated concepts.

### Idea Generation
Structured brainstorming for problem-solving.
Quantity first, quality filter second.
Group by: theme (e.g., "async approaches" vs "sync approaches"), feasibility (easy/medium/hard), impact (low/medium/high). Rank: highest impact + lowest effort first.

### Tree of Thoughts
For complex challenges. Branch exploration:
1. Generate 3 initial approaches
2. Explore each 2 levels deep
3. Evaluate branches
4. Combine best elements from different branches

## Guidelines

- Quantity enables quality. Generate many before filtering.
- Deliberate diversity: each option should be genuinely different
- No self-censoring in generation phase
- Cross-domain thinking: pull inspiration from unrelated fields
- Combine ideas: the best solution often merges two mediocre ones

## When NOT to use

Skip if solution is proven and constraints tight. Best for: naming, novel design, stuck decisions.

## Examples

- "Be creative: name ideas for a data pipeline tool"
- "Brainstorm ways to reduce our CI/CD time"
- "Creative approaches to onboarding new developers"
- "Generate 10 ideas for automating our weekly reports"
