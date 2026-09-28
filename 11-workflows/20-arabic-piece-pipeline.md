# Arabic Piece Pipeline

**Triggered by:** "write an Arabic post" / "اكتب مقال بالعربي" / "Arabic piece for the site"
**Cadence:** Per piece
**Done when:** one approved Arabic piece in John's locked-in voice exists in the site repo, and any steering signals from his edits are captured into the rule files.

The Arabic writing spine. The system is LOCKED IN (approved 2026-05-16) — this playbook
SEQUENCES it, it does not re-litigate it. The two gates that quietly get skipped and
carry all the value are **context-first** (front) and **steering-capture** (back).

```
Context gate → Anchor read → (research?) → Trio-synth → Voice-check gate → User reads final → Steering-capture gate → Apply to repo → Leave for coordinator
```

> **Locked system, north star = Lumen.** `example.com/articles` is the golden
> standard; serious prose uses trio-synth. Do NOT re-open the rules mid-piece — sequence
> them. The voice rules live in `/writing → arabic` (`references/voice.md`).

---

## Steps

### 1. Context gate (mandatory — write the brief FIRST)

- [ ] No drafting until the context brief exists. Write it down: **audience**, **intent**,
      **key references**.
- [ ] State explicitly: the English source (if any) is **INTENT, not text** — express the
      idea natively in Arabic, never word-for-word.

> **Decision Point**: brief missing or vague?
> - STOP. A piece written without context drifts off John's voice and burns the run.
> - Do not let "it's a short post" excuse skipping this. The brief is the cheapest gate.

### 2. Re-load the target voice (anchor read)

- [ ] Read the Lumen anchor (`example.com/articles`) to re-load the target cadence
      before any words get written. The north star is a read, not a memory.

### 3. (Optional) research for substance

- [ ] If the piece needs facts/sources, run **`/research → web-research`** first. Skip for
      pure-opinion or reflective pieces.

### 4. Trio-synth (parallel drafts → ONE synthesis)

- [ ] **`/ask-model`** Gemini and **`/ask-model`** GPT draft **in parallel** from the same
      brief — two independent angles, not a relay.
- [ ] Claude synthesizes **ONE final** via **`/writing → arabic`**. Never ship a model's
      raw draft; the value is the synthesis.

### 5. Voice-check gate

- [ ] Anti-AI voice rules pass (`/writing → arabic`, `references/voice.md`).
- [ ] Inline English tokens wrapped in **«guillemets»**; **max 2–3 «English» tokens per
      short clause**.
- [ ] **الـ** prefix on definite/categorical English nouns.
- [ ] Hedging qualifiers dropped; diacritics dropped.
- [ ] Reads as meaning, not translation — no word-for-word seams.

> **Decision Point**: any rule fails?
> - Iterate the synthesis. Do NOT hand a half-checked draft to John — that wastes his
>   read and pollutes the steering signal in step 7.

### 6. John reads ONLY the final

- [ ] Present the single synthesized piece. **Do not show the Gemini/GPT drafts** — he
      judges the final only.

### 7. Steering-capture gate (the back-end value)

- [ ] Capture any edit signals from his feedback. Curate them into the Arabic rule files +
      dictionary via **`/writing → arabic`** so the system **compounds**.
- [ ] One-off phrasing → leave it. A repeatable preference → write the rule.

> **Decision Point**: he edited something and you moved on without capturing it?
> - That is the failure mode. Every uncaptured signal is a rule the system relearns next
>   time. This gate is why the voice keeps improving.

### 8. Apply to the live site repo

- [ ] Place the approved piece into the **johndoe.dev** site repo (code project,
      under `~/projects/`). Commit there via **`/git → commit`** — that is a code repo, not
      the vault.

### 9. Sync (leave the vault churn for the coordinator)

- [ ] Any **vault** edits (rule files, dictionary) stay **local**. The Linux coordinator
      commits + pushes at its next maintenance run (04/10/16/22:00).
- [ ] **Do not `git push` the vault from the Mac** — single-writer rule,
      `03-rai/SYNC-ARCHITECTURE.md`. (The site repo in step 8 is separate and may be pushed
      on its own terms.)

---

## Connections

- Synthesis + voice rules: `/writing → arabic` (`references/voice.md`)
- Parallel external drafts: `/ask-model` (Gemini + GPT)
- Substance gathering: `/research → web-research`
- Site-repo commit: `/git → commit`
- Single-writer vault sync: `03-rai/SYNC-ARCHITECTURE.md`
- Adjacent content playbooks: [[05-code-review]] (for the site repo), [[06-shipping]] (site deploy)
