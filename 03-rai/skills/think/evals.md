# Evals

Build and run evaluations for AI agents and model outputs.
Two grader types: code-based (deterministic) and model-based (subjective).

## Grader Types

**Selection:** Use code-based graders for objective criteria (exact match, JSON schema, format validation). Use model-based graders for subjective criteria (quality, tone, appropriateness).

### Code-Based Graders
Deterministic checks with binary pass/fail results.

| Grader | Use Case |
|--------|----------|
| String Match | Exact expected output |
| Regex Match | Pattern-based validation |
| Contains | Substring presence check |
| JSON Schema | Structural validation |
| Binary Test | Custom pass/fail function |

### Model-Based Graders
LLM judges output quality against criteria.

| Grader | Use Case |
|--------|----------|
| Rubric | Score against defined criteria (1-5 scale) |
| Pairwise | Compare two outputs, pick the better one |
| Reference | Compare against gold-standard answer |
| Multi-Aspect | Score on multiple dimensions separately |

## Metrics

- **pass@k**: Probability of at least one correct answer in k attempts. Use for generation tasks with multiple valid outputs.
- **Accuracy**: Percentage of passing test cases. Use for binary pass/fail.
- **Mean Score**: Average rubric score across test cases. Use for rubric-based scoring (1-5).
- **Win Rate**: Pairwise comparison wins percentage. Use for comparing two models pairwise.

## Partial Credit

For each test case, decide upfront: pass/fail OR rubric (0-5). Partial credit lives in the rubric. Binary tests cannot have partial credit.

## Process

1. **Define test cases**: Input-output pairs or input-criteria pairs
2. **Select graders**: Code-based for objective, model-based for subjective
3. **Configure scoring**: Thresholds, weights, aggregation method
4. **Run evaluation**: Execute test cases against the target
5. **Analyze results**: Scores, failure patterns, edge cases
6. **Report**: Summary table with pass rates and breakdowns

## Output Format

```
EVAL: [Name]
Target: [Model/Agent]
Test Cases: [N]
Pass Rate: [X%]

| Test Case | Score | Grader | Notes |
|-----------|-------|--------|-------|
| ...       | ...   | ...    | ...   |

Failure Analysis: [Common patterns in failures]
```

## Examples

- "Create an eval for our RAG pipeline's answer accuracy"
- "Compare GPT-4o vs Claude on these 20 test cases"
- "Build a rubric grader for code review quality"
- "Run pass@5 evaluation on the agent's tool use"
