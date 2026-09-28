# Art

Generate visual content using AI image models. All generated images are saved
to `~/Downloads/` before any other action.

## Models

| Model | Best For |
|-------|----------|
| FLUX | Photorealistic images, detailed scenes, portraits |
| GPT-Image-1 | Illustrations, diagrams, text-in-image, stylized art |

FLUX is preferred for photorealistic output; GPT-Image-1 is more reliable when the image must contain readable text.

## Content types

- **Illustrations:** concept art, editorial, explainer visuals.
- **Diagrams:** architecture diagrams, flowcharts, system maps. For flowcharts, consider D2/ASCII in code first — image is a fallback when the diagram must be visually polished.
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
- For text in images, use GPT-Image-1.
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
