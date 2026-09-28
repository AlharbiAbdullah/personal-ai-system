# Remotion

Create professional videos programmatically using React components. Remotion
turns React code into MP4 video files. No video editing software needed.

## What it does

- Write video scenes as React components.
- Compose scenes into a timeline with transitions.
- Add text animations, charts, data visualizations.
- Render to MP4, WebM, or GIF.
- Parameterize videos for batch generation.

Output: MP4 for web/sharing, WebM for browser embedding, GIF for looping animations. 1920x1080 at 30fps is the default.

## Workflow: ContentToAnimation

Transform static content into animated video.

### Process

1. **Analyze:** review the source content (slides, text, data).
2. **Storyboard:** plan scenes, transitions, timing.
3. **Component design:** create React components for each scene.
4. **Composition:** assemble scenes into a Remotion composition.
5. **Style:** add animations, transitions, typography.
6. **Render:** export to MP4.

### Scene types

- **Title:** animated text with background.
- **Bullet Points:** sequential reveal of items.
- **Code:** syntax-highlighted code with line-by-line reveal.
- **Data:** animated charts and graphs.
- **Comparison:** side-by-side with highlight transitions.
- **Outro:** call-to-action or closing card.

## Technical notes

Remotion is a React framework where scenes are components that receive `frame` and `fps`. Animations interpolate values over time.

- Each scene is a React component receiving `frame` and `fps`.
- Use `useCurrentFrame()` and `interpolate()` for animations.
- `<Sequence>` controls timing within compositions.
- Spring animations via `spring()` for natural motion.

Rendering time: ~1s of video per 30fps of composition. A 5-minute video typically takes 5–10 minutes to render.

## Examples

- "Create a video explaining our API architecture"
- "Turn these bullet points into an animated presentation"
- "Build a data visualization video from this dataset"
- "Generate a code walkthrough video for this function"
