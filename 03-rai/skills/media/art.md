# Art

Generate visual content using AI image models. All generated images are saved
to `~/Downloads/` before any other action.

## Models

Image generation goes through a Google subscription, never a pay-per-use route. agy (the Antigravity CLI) and pi's `generate_image` tool both sign in to the Google account and run the Gemini image models.

## Content types

- **Illustrations:** concept art, editorial, explainer visuals.
- **Diagrams:** flowcharts and concept sketches. For flowcharts, consider D2 or ASCII in code first. An architecture or tech stack diagram goes to `/media → diagram`.
- **Thumbnails:** YouTube, blog, social media thumbnails.
- **Comics:** multi-panel strips, character-driven narratives.
- **Icons/Logos:** simple iconography, brand marks.
- **Backgrounds:** wallpapers, presentation backgrounds.

## Process

1. **Clarify the vision:** subject, style, mood, dimensions, model preference.
2. **Write the prompt:** detailed, specific, with style modifiers.
3. **Generate:** call the selected model.
4. **Save to ~/Downloads/:** always save before presenting.
5. **Present and iterate:** show result, refine prompt if needed.

## Prompt guidelines

- Be specific about composition, lighting, color palette.
- Include style references: "in the style of watercolor", "flat design".
- Specify what to exclude with negative prompts.
- State aspect ratio: square (1:1), landscape (16:9), portrait (9:16).

## Output format

- Image saved to: `~/Downloads/[descriptive-name].png`.
- Prompt used (for reproducibility).
- Model used.
- Offer refinement options.

## Examples

- "Create a thumbnail for a video about Python data pipelines"
- "Generate an illustration of a castle in watercolor style"
- "Make a 4-panel comic about debugging code"
- "Design a minimalist icon for a security tool"
