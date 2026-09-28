# Prompting

Design, refine, and optimize prompts for language models.
Applies prompt engineering best practices and token efficiency techniques.

## Core Principles

1. **Clarity over cleverness**: Simple, direct instructions beat complex ones
2. **Structure matters**: Use XML tags, numbered steps, clear sections
3. **Examples teach**: Few-shot examples outperform lengthy explanations. 2-5 is usually optimal. Fewer than 2 may not establish the pattern; more than 5 risks confusing the model with too many variations.
4. **Constraints guide**: Tell the model what NOT to do as well
5. **Test and iterate**: A prompt is never done on the first draft

## Workflows

### Write
Create a new prompt from a task description.
Steps: understand goal, define output format, add constraints, include
examples, optimize token usage.

### Improve
Take an existing prompt and make it better.
Steps: identify weaknesses, test edge cases, tighten language,
add missing constraints, reduce ambiguity.

### Template
Build a reusable prompt template with variable slots.
Steps: identify fixed vs variable parts, create slots with types,
add validation rules, document usage.

Example template: `{name}` (string, 1-50 chars), `{depth}` (enum: quick/standard/deep), `{format}` (enum: markdown/json).

### Refine
Test the prompt on 3-5 realistic examples. If >1 fails the goal, adjust the instructions. Re-test. Repeat until pass rate is acceptable.

### Optimize
Reduce token count while preserving quality.
Steps: remove redundancy, compress instructions, test shortened
version against original, measure quality delta.

## Token Efficiency Tips

- Cut filler words ("please", "I want you to", "could you")
- Use structured formats (XML tags, markdown headers)
- Replace paragraphs with bullet points
- Use role assignment ("You are X") sparingly and only when it helps. Use "You are X" role assignment when: you want a specific persona, expertise that shapes tone, or role-specific knowledge. Skip for generic tasks.
- Prefer short examples over long explanations

## Examples

- "Write a prompt for extracting action items from meeting notes"
- "Improve this prompt: [paste existing prompt]"
- "Create a reusable template for code review"
- "Optimize this prompt to use fewer tokens"
