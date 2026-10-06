# Vale prose gate

`~/helm/.vale.ini` runs two styles on every `*.md`. Run `vale sync` once from the vault root after cloning: it downloads the `ai-tells` package into `styles/` (the kit ships only the hand-written `Rai` style).

- `Rai` (this folder, hand-written): the hard rules from `03-rai/identity/response-format.md` and `03-rai/skills/writing/references/voice.md`. Em dashes, AI-corporate connectors, vague quantities, sentences over 25 words, emoji.
- `ai-tells` (synced from tbhb/vale-ai-tells v1.34.0): 130 AI-fingerprint rules. Advisory. Rules that contradict voice.md are switched off in `.vale.ini` (ColonUsage, EmDashUsage, ParallelStaccato).

Run from anywhere inside the vault:

```
vale draft.md                                   # everything
vale --filter='.Name matches "^Rai"' draft.md   # the blocking set: must be empty before delivery
vale --output=03-rai/config/vale/styles/config/templates/ai-tells-agent.tmpl draft.md   # compact agent output (after vale sync)
```

Code fences and inline code are skipped. Frontmatter is scanned. Arabic text passes through untouched.

Refresh the package: `vale sync` (from the vault root). The `Rai` style is tracked in git; the `ai-tells` package is downloaded per machine and gitignored.
