---
name: ask
description: >
  A quick answer from one or a few named voices, in one round: a second
  opinion, a fact check, a summary or a translation. Defaults to gemini.
  USE WHEN /fusion ask, "ask gemini" (or minimax, glm, deepseek, sol, opus), "get a
  second opinion", or "translate this" with another model.
---

# /fusion ask

The light path: one round, few voices, no feedback round unless he asks.

## Voices

He names them, by voice id or loosely: "gemini", "the pi voices", "everyone".
Each model is one voice: `gemini`, `minimax`, `glm`, `deepseek`, `sol`, `opus`.
Nothing named: `gemini`.

## The ask (`$RUN/ask.md`)

The question and the content it is about, pasted. Point `--cwd` at the folder
the question is about so the voices can read around it.

- **Translation:** `$P new ask --prelude translate-ar --cwd <dir>` into Arabic,
  `--prelude translate-en` into English. The ask holds the source text.
- **Summary or fact check:** the default prelude.

## Run

`$P start $RUN 1 <voices>`, wait, show. Add round 2 only when he asks for the
voices to compare notes.

## Answer

- One voice: its answer, then one line on whether you agree, and why.
- Two or more voices: the answer they converge on, then any real split.
- A translation: the best one, with any line where the voices differ and
  your call on it.

Save the answer you gave in `$RUN/synthesis.md`.

A contested claim from research goes on at [[18-deep-research-to-home]] step 3,
Verify the load-bearing claims.

## Examples

- `/fusion ask gemini: is the 3-concurrent limit on Ollama Pro per account?`
- `/fusion ask translate this paragraph to Arabic, gemini and minimax`
- `/fusion ask opus: is this regex catastrophic on long input?`
