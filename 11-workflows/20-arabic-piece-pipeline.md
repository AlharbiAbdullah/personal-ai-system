# Arabic Writing

**Use when:** serious Arabic prose, for any destination: a letter, a memo, a brief, a decision paper, an intro document or a LinkedIn post. That includes the Arabic version of an English source, written natively.
**Not for:** English pieces, including anything for his site, which is English only: 33 career. A quick informal reply, such as WhatsApp, Slack or a peer note: `/writing → arabic` alone, with no panel.
**Done when:** he approved the final, and it went out only on his explicit go. Every steering signal from his edits is written into the rule files.

The Arabic system is locked in, approved on 2026-05-16. This workflow sequences it and never re-opens the rules mid-piece. The two gates that get skipped carry the value: the context brief at the front, and the steering capture at the back.

```
Context brief → Anchor read → (research) → Panel → Voice check → He reads the final → Steering capture → Deliver on his go → Sync
```

> **Locked system, north star Lumen.** Lumen is the golden standard, and serious prose runs the panel. The rules live in `/writing → arabic`, its `references/voice.md` and its dictionary.

---

## Steps

### 1. Context brief first

- [ ] No drafting until the brief exists. Write it: the audience, the intent and the key references.
- [ ] Add the target file or section, its current state, the English source if any, the length and markup limits, and any locked phrasing.
- [ ] The English source is intent, not text. Express the idea natively in Arabic, never word for word.
- [ ] Pick the register: formal for serious prose. Unsure: ask him.
- [ ] List what must not appear, such as a sensitive capability he rules out.
- [ ] Output for `04-work/`: no AI mentions, a formal tone, and every name, amount and date checked with him.

> **Decision Point**: is the brief missing or vague?
> - Stop. A piece written without context drifts off his voice and burns the run.
> - "It is a short post" never excuses skipping it. The brief is the cheapest gate.

### 2. Anchor read

- [ ] Read at least one local Lumen anchor, a `formal--lumen-*.md` file in `02-ana/voice-samples/arabic/`, before any words get written.
- [ ] Match its shape: sentence length, paragraph length, how the opener works and how the close lands. Never copy its lines.
- [ ] Add a second-tier anchor only when the piece sits in its niche. The niches: politics, a tech executive's voice, a personal reflection, a literary essay.
- [ ] A technical domain: open the dictionary, `03-rai/skills/writing/references/arabic-dictionary.md`.

### 3. Research, only for facts

- [ ] The piece needs facts or sources: run `/research → web-research` first.
- [ ] Skip it for an opinion or a reflective piece.

### 4. The panel: parallel drafts, one synthesis

- [ ] Put the brief into the run's ask file. Frame the task as a tech writer at Lumen telling the story in Arabic for the first time. The English is source notes, never text to translate.
- [ ] `/fusion → write-arabic`: every panel voice drafts from the same brief, then scores the others' drafts against the Arabic rules, and the coordinator synthesizes one version.
- [ ] Hand the panel run, the synthesis and the voice check to the `writer` agent. Inputs: the brief. It runs `/fusion → write-arabic` as the coordinator, fixes the synthesis until step 5 passes, and returns one final with its checklist. It writes the final draft file only.
- [ ] Rai re-checks the checklist and every fact in the final against the brief.
- [ ] Never ship a model's raw draft. The value is the synthesis.

> **Decision Point**: the panel cannot run, for example because a harness is signed out or the Ollama credits ran out?
> - Tell him. He signs in, or picks the voices that still work.

### 5. Voice check: the gate

- [ ] The anti-AI voice rules pass: `03-rai/skills/writing/references/voice.md`.
- [ ] Inline English tokens sit in «guillemets», at most 2 or 3 in a short clause.
- [ ] The Arabic definite article goes before a definite or categorical English noun.
- [ ] Hedging qualifiers and diacritics are gone.
- [ ] It reads as meaning, not translation: no word-for-word seams.

> **Decision Point**: does any rule fail?
> - Fix the synthesis and check again. Never hand him a half-checked draft: it wastes his read and pollutes the steering signal.

### 6. He reads only the final

- [ ] Show him the one final piece. Never the Gemini or GPT drafts: he judges the final only.
- [ ] Write it to a file and give him the path. He opens it himself: the terminal cannot shape Arabic, and Rai never opens a window.

### 7. Steering capture: the gate

- [ ] Capture every signal from his edits. A forbidden translation goes to `arabic-dictionary.md`. A preferred pattern goes to `voice.md`. A preference about him goes to memory.
- [ ] A one-off phrasing: leave it. A repeatable preference: write the rule. Rai curates the rule files, and he never edits them by hand.

> **Decision Point**: did he edit something, and Rai moved on without capturing it?
> - That is the failure mode. Every signal left uncaptured is a rule the system relearns next time.

### 8. Deliver on his go

- [ ] Approving the words is not a go to publish or send. Nothing goes out without his explicit go.
- [ ] Rai prepares; he publishes or sends it himself, whether a post, a letter or a memo.
- [ ] A piece that lives in a code repo commits through that repo's own flow: 21's gates in a repo with `.project.toml`, `/git → commit` elsewhere. A push waits for his go.

### 9. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Voice rules and the synthesis: `/writing → arabic`. Parallel drafts: `/fusion → write-arabic`.
- Facts: `/research → web-research`. A repo commit: `/git → commit`.
- Agents: `writer` (steps 4 and 5).
- Sent here by [[30-architecture-decision]] step 7 and [[32-work-engagement]] step 2, for an Arabic paper. English public pieces go to [[33-career]].
