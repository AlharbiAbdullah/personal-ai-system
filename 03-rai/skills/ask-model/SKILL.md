---
name: ask-model
description: >
  Call an external frontier LLM via OpenRouter for a specific task. Two
  models available: «Gemini 3.1 Pro Preview» and «GPT-5.5». Task types:
  write, translate, judge, critique, summarize, freeform. USE WHEN the user
  asks to "ask gpt", "ask gemini", "use gpt 5.5", "use gemini", or wants a
  second-opinion model output, a translation, or an external critique.
  Reusable across writing, translation, judging, and freeform tasks.
---

# /ask-model

Single-purpose tool. Routes a task to a chosen frontier model via OpenRouter, returns the response.

## Models

| Alias | Model ID | Role |
|------|----------|------|
| `gemini` | `google/gemini-3.1-pro-preview` | Drafter A. Broad Arabic, structured prose, long context. |
| `gpt` | `openai/gpt-5.5` | Drafter B. Punchier, Lumen-rhythmic, three-beat sentences. |
| `sol` | `openai/gpt-5.6-sol` | Adversarial code reviewer (used by /adversarial-review with `REASONING_EFFORT=high`). |
| `grok` | `x-ai/grok-4.5` | Adversarial code reviewer fallback (used by /adversarial-review when `sol` fails). |
| `claude` | `anthropic/claude-opus-4.7` | Synthesizer / Judge. Nuanced editorial reasoning. |

User-facing invocations the skill should recognize:
- "use gpt 5.5", "ask gpt", "via gpt" → alias `gpt`
- "use gemini", "ask gemini", "gemini 3.1" → alias `gemini`
- "use claude", "ask claude" → alias `claude`
- "compare", "compare all", "side by side" → all three in parallel via `compare.sh`
- "trio", "synthesize", "let them collaborate", "talk together" → 3-stage trio-synth flow (see below)

## Task types

| Task | When | System prompt prelude |
|------|------|----------------------|
| `write` | Drafting Arabic prose. Default for Arabic writing handoff. | `preludes/write-arabic.md` |
| `translate` | Arabic↔English translation. | `preludes/translate.md` |
| `judge` | Rubric-scored evaluation of a draft. | `preludes/judge.md` |
| `critique` | Editorial critique, free-form margin notes. | `preludes/critique.md` |
| `summarize` | 5–8 bullet summary. | `preludes/summarize.md` |
| `freeform` | No prelude. Pass-through. | none |

### How preludes stay in sync with the writing skill

Prelude files contain `INCLUDE: <path>` directives. At call time, `scripts/call.sh` expands each directive by reading the referenced file and substituting its contents into the system prompt. The Arabic-related preludes (`write-arabic`, `translate`, `judge`, `critique`) include:

- `~/helm/03-rai/skills/writing/arabic.md` — the full Arabic writing skill spec (registers, process, anti-patterns, voice anchors table).
- `~/helm/03-rai/skills/writing/references/voice.md` — shared voice mandate (banned words, em-dash ban, sentence-rhythm gate).
- `~/helm/03-rai/skills/writing/references/arabic-dictionary.md` — the complete dictionary (~293 entries across 13 categories with context-dependent notes and forbidden-translation flags).
- `~/helm/02-ana/voice-samples/arabic/formal--lumen-sports-column-promotion.md` — a concrete Lumen voice anchor.

Editing any of those files immediately propagates to the next `/ask-model` call. No drift. The assembled system prompt is roughly 10K tokens for Arabic tasks — well within both Gemini 3.1 Pro Preview (1M context) and GPT-5.5 (256K+).

## How to invoke (from inside Claude Code)

1. **Pick the alias** from the user's request: `gemini` or `gpt`. If both, use compare mode.
2. **Pick the task**. If unstated, infer: Arabic content + draft request → `write`; "translate" → `translate`; "review/score" → `judge`; "critique/feedback" → `critique`; "summarize" → `summarize`; anything else → `freeform`.
3. **Build the prompt** — write the user's content to a temp file. If you have any context the model needs (source draft, target audience, format), include it in the prompt file.
4. **Resolve the system prelude** — for non-`freeform` tasks, point the script at `preludes/<task>.md`. For `freeform`, omit.
5. **Call the script** (one model) or `compare.sh` (both models).
6. **Stream the output back to the user**. Don't post-process unless asked.

## Trio collaborative writing workflow (recommended for serious Arabic prose)

This is the workflow John uses for high-stakes Arabic writing — homepage copy, about-page sections, blog openers. Three models collaborate to produce ONE final output, not three for picking.

### The flow

**Stage 0 — Context.** Before any drafting, establish shared context. The context block answers:
- **Target**: what piece, what section, what file?
- **Audience**: who reads it, what register do they expect?
- **Purpose**: what should the reader walk away thinking/feeling/doing?
- **Current state**: what's there now (if anything)?
- **Constraints**: length, format markup (`<strong>`, `<highlight>`), formality, references to existing site copy?
- **Locked-in phrasings**: anything John has explicitly approved that must be preserved.

Write the context block to a prompt file. All three models receive it.

**Stage 1 — Independent drafts (parallel).** Gemini and GPT each draft, fully independent. Both have:
- Full corpus (12 Lumen anchors)
- Full writing rules (`arabic.md` + `voice.md`)
- Full dictionary
- The shared context block

**Stage 2 — Synthesis.** Claude reads the context + both drafts. Synthesizes ONE final by:
- Picking the strongest opening (whichever draft nailed it)
- Picking the strongest argument/middle
- Picking the strongest close
- Locking in phrasings where both agreed
- Breaking ties using Lumen voice
- Fixing issues that appear in both
- Light rewrites where neither draft is best

**Stage 3 — Judge.** John reads ONLY the final. Approves, applies, or steers.

### Steering signals (what to capture when John pushes back)

- **"X always reads wrong"** → update `arabic-dictionary.md` (new forbidden translation, new context-dependent note).
- **"I prefer X over Y consistently"** → update `voice.md` or `arabic.md` (preferred patterns section).
- **"For THIS piece specifically, avoid Z"** → in-conversation prompt update for this iteration, plus a note in memory if the pattern recurs.
- **"This phrasing is locked in"** → mark in the file's context block so future trio runs don't touch it.

The agent (Claude Code) curates these signals. The user doesn't manage the rule files manually.

### Bash invocation

Trio synthesis (recommended):
```bash
~/helm/03-rai/skills/ask-model/scripts/trio-synth.sh write <prompt-file> ~/helm/03-rai/skills/ask-model/preludes/write-arabic.md
```

Output:
- DRAFT A (Gemini) — for audit
- DRAFT B (GPT) — for audit
- FINAL (Claude synthesis) — what John reads

Compare-only (three drafts, no synthesis — for cases where John explicitly wants to read all three):
```bash
~/helm/03-rai/skills/ask-model/scripts/compare.sh <task> <prompt-file> [system-file]
```

Single model (when John explicitly says "ask gemini" / "ask gpt" / "ask claude"):
```bash
~/helm/03-rai/skills/ask-model/scripts/call.sh <gemini|gpt|claude> <task> <prompt-file> [system-file]
```

Example — trio synthesis for a homepage section:
```bash
cat > /tmp/p.txt <<'EOF'
# CONTEXT
- Target: messages/ar.json → about.section1Body (Arabic locale)
- Audience: local/Arab tech readers visiting johndoe.dev
- Purpose: open the "about me" page; establish background + thread
- Current state: <paste current Arabic>
- English source (semantic truth): <paste current English>
- Constraints: ≤80 words; preserve <highlight>...</highlight> tags

# TASK
Rewrite section1Body in Lumen voice. Output Arabic only.
EOF
~/helm/03-rai/skills/ask-model/scripts/trio-synth.sh write /tmp/p.txt ~/helm/03-rai/skills/ask-model/preludes/write-arabic.md
```

Example — single model translation:
```bash
echo "ترجم للإنجليزي: السلام عليكم" > /tmp/p.txt
~/helm/03-rai/skills/ask-model/scripts/call.sh gemini translate /tmp/p.txt ~/helm/03-rai/skills/ask-model/preludes/translate.md
```

Example — single model judge:
```bash
cat draft.md > /tmp/p.txt
~/helm/03-rai/skills/ask-model/scripts/call.sh claude judge /tmp/p.txt ~/helm/03-rai/skills/ask-model/preludes/judge.md
```

## Auth

Requires `OPENROUTER_API_KEY` in the environment. The script fails fast with a helpful error if it's missing. Every secret lives in 1Password, never a plaintext rc export. `~/.bashrc.local` (mode 0600, sourced by `~/.bashrc`) resolves it via the `__op_env` helper (`dev-env/mac/.zshrc.local.example` is the template for both machines):

```bash
__op_env OPENROUTER_API_KEY 'op://Private/OpenRouter API key/credential'
```

Get the key from <https://openrouter.ai/keys> if it ever needs rotating in 1Password.

## Hook into other skills

- **`/writing/arabic`** — see step 5 of its process. After drafting locally, optionally call `/ask-model` with `gemini` or `gpt` for a parallel Arabic draft, or with `claude`/`gpt` task=`judge` for an external critique. Compare-mode is the right tool for "which voice is more Lumen".
- **Translation tasks** — prefer `/ask-model task=translate model=gemini` over translating in Claude. Output is then checked against the Arabic dictionary.
- **Judging code or prose** — `/ask-model task=judge` gets an independent second opinion. Useful when Claude wants to gut-check its own work.
- **General Q&A from another model** — when the user explicitly says "ask gpt" or "ask gemini", route through here, never call a different vendor's API directly.

## When NOT to use

- The user wants Claude's own opinion or output — answer directly, don't proxy.
- The user wants to BUILD an LLM-powered system (RAG, agents, eval harness) — that's `/ai`.
- The user wants Anthropic SDK code — that's the `claude-api` skill.

## Adding a new model later

To add a model (e.g., Claude, Qwen, DeepSeek), edit `scripts/call.sh`:
1. Add a new `case` branch under `ALIAS`.
2. Add an entry to the user-facing aliases table at the top of this file.
3. If the model has different behavior for compare-mode, update `scripts/compare.sh`.

To add a new task type, write a new file under `preludes/` and add a row to the task table above.

## Files in this folder

```
ask-model/
├── SKILL.md              # this file
├── scripts/
│   ├── call.sh           # single-model call
│   └── compare.sh        # call both models in parallel
└── preludes/
    ├── write-arabic.md   # Arabic writing system prompt (Lumen voice)
    ├── translate.md      # Arabic↔English translation rules
    ├── judge.md          # rubric-scored evaluation
    ├── critique.md       # free-form editorial critique
    └── summarize.md      # 5–8 bullet summary
```
