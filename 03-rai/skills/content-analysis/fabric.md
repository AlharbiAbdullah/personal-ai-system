# Fabric

Execute Fabric prompt patterns natively. 240+ patterns organized by category.
Each pattern defines a specific input-to-output transformation.

See the full Fabric library at https://github.com/danielmiessler/fabric for the complete pattern catalog.

## Categories

### Extraction
Pull specific elements from content.

- `extract_ideas`: Key ideas as bullet points
- `extract_recommendations`: Actionable recommendations
- `extract_references`: Books, papers, tools mentioned
- `extract_patterns`: Recurring patterns in the content

### Summarization
Condense content to essentials.

- `summarize`: General purpose summary
- `summarize_paper`: Academic paper summary (method, results, impact)
- `summarize_meeting`: Meeting notes with decisions and action items
- `create_tldr`: Ultra-short summary (1-3 sentences)

### Analysis
Examine content for deeper understanding.

- `analyze_claims`: Fact-check and assess claim strength
- `analyze_threat`: Security threat analysis
- `analyze_debate`: Map arguments and counter-arguments
- `rate_content`: Score content quality on defined criteria

### Creation
Generate new content from inputs.

- `create_essay`: Structured essay from topic or outline
- `create_quiz`: Quiz questions from source material
- `write_seminar`: Technical seminar outline
- `create_keynote`: Presentation structure and talking points

## Process

1. **Identify pattern:** match user request to a Fabric pattern.
2. **Load pattern:** read the pattern's system prompt and structure.
3. **Apply to input:** run the pattern against the provided content.
4. **Format output:** follow the pattern's specified output structure.
5. **Present results:** clean, structured output matching the pattern.

## Native execution

Patterns run directly in-context. No external Fabric CLI needed. The pattern's
system prompt is applied as behavioral instructions for processing the user's
input content.

## Output format

Each pattern defines its own output structure. Common formats:

- Bullet lists (extraction patterns)
- Structured sections with headers (analysis patterns)
- Prose paragraphs (creation patterns)
- Scored rubrics (rating patterns)

## Examples

- "Run extract_ideas on this article"
- "Fabric: summarize_paper on this PDF"
- "Apply analyze_claims to this blog post"
- "Use create_quiz to make 10 questions from this chapter"

## Pattern discovery — find-pattern workflow

When user intent is unclear or could map to multiple patterns, run this workflow to narrow the search:

1. **Categorize the intent** — is this extraction, summarization, analysis, or creation?
2. **Identify the input type** — article, transcript, code, paper, conversation?
3. **Identify the desired output shape** — bullets, prose, structured data, rubric score, question list?
4. **Propose top 3 patterns** from the matching category that align with input + output shape
5. **Confirm with user** before executing — "I can run `extract_ideas`, `extract_patterns`, or `analyze_debate`. Which fits?"

Example: user says "I want the key takeaways from this talk."
- Intent: extraction
- Input: talk (video/transcript)
- Output: bullets
- Top 3: `extract_ideas`, `extract_recommendations`, `extract_wisdom`
- Ask: "Ideas (what's said), recommendations (what to do), or wisdom (what to remember)?"

Patterns have natural-language names (`extract_ideas`, `summarize_paper`, `create_analogy`). Rai maps intent to pattern name; no need to memorize the 240+ list.
