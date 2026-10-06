---
name: arabic
description: >
  Arabic prose drafting. USE WHEN the user needs to write Arabic content
  for the region business correspondence, Arabic LinkedIn posts, internal Arabic
  docs, formal letters to organizations, or Arabic-first
  communication with peers. Defaults to MSA; switches to your chosen dialect
  when the audience is peers or informal.
---

# Arabic

Draft Arabic prose that reads written, not translated. Most AI Arabic output reads like a stiff newspaper headline. Avoid that.

## Voice mandate

Read `references/voice.md` first. The English voice rules carry over: short sentences, lead with the answer, no fluff, concrete numbers. The Arabic-specific layer below is on top.

**Then read `references/arabic-dictionary.md`.** That file is the working dictionary for Arabic drafting. Default behavior: terms on the list **stay in English** inside Arabic prose — no translation, no transliteration, no `الـ` prefix. Some entries carry context-dependent notes (e.g., `code` can be "البرمجة" when the discipline is meant; `AI` accepts `الـ AI` but never "الذكاء الاصطناعي" in tech prose; `abstraction` and `data orchestrator` have forbidden translations). Read the note before deciding. The list grows over time — append when you encounter a new term that reads wrong in Arabic.

**Note**: John's default global rule is "English only, never Arabic" for AI responses to him. This skill is the explicit exception: the OUTPUT is Arabic, addressed to a non-John audience.

## North star: Lumen (لومن)

**Lumen (`example.com/articles`) is the golden standard for Arabic prose.** Every formal Arabic draft tries to match its voice — pace, register, sentence length, the way claims are made, the way humor and seriousness sit together. The other style models below are *secondary niche references*, used only when the domain demands a flavor Lumen's house voice doesn't cover.

What makes Lumen the north star:
- **MSA that reads spoken**: written-grade Arabic that still sounds like a person, not a press release.
- **Lead with the claim**: the opening line tells you what the piece is about. No throat-clearing, no "في عالمنا اليوم".
- **Short sentences, hard breaks**: long sentences are broken into two. Paragraphs rarely exceed five lines.
- **Concrete numbers, named people, real places**: "35 سنة", "الجولة 25", "اسم النادي" — not "بعض اللاعبين" or "إحدى الجولات".
- **Light dialect code-switch in dialogue and asides** — never in the body. Inside quoted speech and parenthetical asides, dialect is welcome.
- **Light English code-switch for technical terms only**: brand names, software, foreign titles. Never as a crutch.
- **One controlled comma per clause**: no four-comma sprawl.
- **Sub-headings (##) for long-form**: thesis → evidence → counterpoint → close.
- **No religious flourishes, no diacritics (تشكيل) unless the audience needs them.**

Read at least one Lumen anchor file before drafting any formal Arabic. Match the *shape* of the prose. Don't copy lines.

## Register decision (do this first)

Two registers. Pick one before drafting:

| Register | When | Vibe |
|----------|------|------|
| **formal** | Columns, opinion pieces, formal letters, white papers, business emails, LinkedIn posts, considered Twitter threads | MSA, punchy, written. Short sentences. No classical flourishes. Concrete numbers. Lead with the claim. |
| **informal** | WhatsApp/Slack replies, casual tweets, peer notes, voice-style asides | Your dialect or relaxed MSA. Conversational markers ("اللي", "لما"). Code-switch English tech terms where natural. Short and reactive. |

If unsure, ask. Picking wrong is worse than asking.

## Process

1. **Confirm register**: explicit pick from the table above.
2. **Identify the audience**: name them. Ministry? Coworker? Twitter audience? The recipient changes everything.
3. **Read the north star**: open at least one `formal--lumen-*.md` anchor and skim its shape — sentence length, paragraph length, how the opener works, how the close lands. For formal Arabic this step is non-negotiable.
4. **Layer a niche reference only if needed**: deep political analysis → columnist-a. Tech-executive → columnist-b. Personal-reflective life-stage → columnist-c. Literary/philosophical → columnist-d. Otherwise stop at Lumen.
5. **Open the dictionary** (`references/arabic-dictionary.md`) if the domain is technical. Terms on the list stay English by default; honor any context-dependent notes attached to specific entries.
6. **Draft in target register**: don't translate from English. Think in the register first.
7. **Trim**: Arabic AI output tends to inflate. Cut 30%. Long Arabic sentences feel formal even when not intended. Break them.
8. **Self-check** against the Arabic anti-patterns below + the Lumen signature checklist above.
9. **For serious Arabic prose, use the `/fusion → write-arabic` panel.** Six voices collaborate to produce ONE final output, not six for picking. The steps are written once, in [[20-arabic-piece-pipeline]]: follow it from the context brief to the steering capture.
   - Every voice drafts, then scores the others' drafts; the coordinating session synthesizes.
   - Quick second opinions and translations: `/fusion → ask`. A critique of a finished draft: `/fusion → review` with the `review-prose-ar` rules.

## Arabic-specific anti-patterns (avoid)

- **Newspaper Arabic**: "تعتبر التكنولوجيا واحدة من أهم العوامل التي…". This is the AI default. Stiff, hollow, formulaic. Cut it.
- **Over-formal address**: Don't open every email with "تحية طيبة وبعد" unless the audience expects it. For peer notes, just say "السلام عليكم" or skip the salutation.
- **Translated idioms**: English idioms translated literally read alien. "في نهاية اليوم" is fine, but "ضرب عصفورين بحجر واحد" works only when natural.
- **Mixed register**: pick MSA or dialect. Don't drift mid-paragraph.
- **Unnecessary religious framing**: "بتوفيق من الله" is fine when it's natural and the audience expects it. Sprinkled artificially, it reads pandering.
- **Vowelization (تشكيل)**: don't add diacritics. Aggressively strip what AI defaults sprinkle in. `أحول` not `أُحوّل`. `المعقدة` not `المعقّدة`. Shadda, damma, kasra on body prose — all out. Only keep diacritics when the audience genuinely needs them (children, learners, religious text, ambiguous proper noun).
- **Hedging qualifiers when the verb already implies them**: `أحول البيانات إلى قرارات` beats `أحول البيانات الخام إلى قرارات`. The verb "transform" already implies the source was unprocessed; "raw" is filler. Trim qualifiers like `الخام`, `الأولية`, `المبدئية`, `الحقيقية`, `الفعلية` when the surrounding sentence makes them redundant.
- **Diplomatic-news Arabic in tech-leader prose**: certain words read as press-release / wire-service Arabic, not lived speech. They're grammatically correct but tonally wrong for a local tech writer's voice. Swap them out:
  - `نظير / نظيرة` (peer) → `أخرى` (other), or `مماثلة` (similar). `شركة نظيرة` reads diplomatic-Arabic; `شركة أخرى` reads natural.
  - `أصلب / تجعلها أصلب` (harder, sturdier — for software hardening) → `تقوّي`, `تصقل`, `تنضّج`, `تحسّن`. `أصلب` is a literal-translation shape that no Arab tech speaker uses for software maturity.
  - `يصمد` (withstands) → `يعمل تحت الحمل`, `لا يسقط`. `يصمد` evokes battlefield, not infrastructure.
  - `يحمل العبء / يحمل الحمل` (carries the burden) → `يواجه التحديات`, `يواجه نفس المشكلة`. Carrying-burden is an English-translation reflex; local tech voice says "faces" challenges, not "carries" burdens.
  - `يستقر` (resides, settles — for inanimate things like data, tables, files) → drop the verb entirely and ask the question directly. `أين يستقر كل جدول؟` → `أين كل جدول؟`. The verb is filler; the question word already does the work.
  - `يوجد / موجود / الموجودة` (exists, is present) → almost always filler in Arabic prose. `ما قواعد البيانات الموجودة لدينا؟` → `ما قواعد البيانات لدينا؟`. The preposition (`في`, `لدى`, `عند`) already conveys existence. Drop the verb/participle unless the sentence is genuinely about existence-vs-non-existence as the claim.
  - `المسبق / مسبقًا` (prior, previously, upstream — as a modifier) → drop or rephrase. `المصدر المسبق محدث؟` → `مصدر البيانات محدث؟`. `المرتبطين مسبقًا` → `المرتبطين` (the perfect-aspect verb already implies the past state). `مسبقًا` is filler that translation-mind adds for completeness; Arabic rarely needs it.
  - `المستهلكين` (consumers — for downstream data/system users) → `المستفيدين` (beneficiaries). In Arabic, `المستهلكين` carries a commercial / retail-goods sense; it doesn't read right for downstream data consumers or system users. `المستفيدين` is the natural local tech-gov term for "the parties that use the output downstream".
  - `بأسره / برمته / قاطبة` (entire, whole — classical wholeness modifiers) → `كاملاً`, or drop entirely. `مشروع المكتب بأسره` → `مشروع المكتب كاملاً` or just `مشروع المكتب`. The classical forms read literary, not lived speech.
  - `نطاق / النطاقات / مدير نطاق` (domain, scope, domain-owner — when the real referent is an organizational department) → `إدارة`, `الإدارات`, `مدير إدارة`. In an organization, `إدارة` is the lived word for an organizational department; `نطاق` reads abstract / English-org-chart-translated. Keep `نطاق` only when the meaning is genuinely "scope" or "area of responsibility" rather than a named department.
  - `نهضوي / تنموي / استشرافي` (developmental / forward-looking) → describe what changed concretely. These are official-speech filler.
  - **Test**: would a local tech leader say this word aloud in a meeting? If no, it's wire-service Arabic. Cut.

## Meaning over translation (CRITICAL — read before every Arabic draft)

When an English source is provided alongside the Arabic target, **the English is the source of intent, not the source of text**. Do NOT translate sentence-by-sentence. Do NOT preserve English structure, idioms, or metaphors that don't have native resonance in Arabic.

The job: read the English, understand what John wants the reader to come away thinking. Then write Arabic that lands that idea natively — even if the surface form looks unrelated to the English.

### Unit of translation: paragraph, never word, never sentence

Work **chunk by chunk**. A chunk is one paragraph, or one logically self-contained block (a list item, a table row, a blockquote line). Never word-by-word. Never sentence-by-sentence.

For each chunk, run this four-step rubric before writing a single Arabic word:

1. **Context.** Where does this chunk sit in the document? What came before it? Who is reading right now?
2. **What is being said.** What is the one idea, the one claim, the one beat of this chunk? Strip it down to the core.
3. **The goal.** What should the reader walk away thinking after this chunk? What's the next move it's setting up?
4. **Natural Arabic.** How would a local tech writer at «لومن» say exactly that, fresh, in Arabic, today — if they had never seen the English at all?

Then write that. Within a chunk, English sentences may collapse, reorder, split, or expand. Two English sentences may become one Arabic sentence. One English sentence may become three Arabic sentences. Two English paragraphs may merge if the ideas belong together. Trust the four-step rubric over the source structure.

**Anti-pattern**: opening the English chunk and walking line-by-line, producing one Arabic sentence per English sentence. This is the AI-default that produces stiff translated prose. The result reads competent but lifeless — the rhythm is wrong, the openings are wrong, the closes don't land. Avoid.

**Pace yourself.** For serious Arabic prose (formal letters, memos, columns, op-eds), translate **slowly**. One chunk at a time. Don't speed-run the whole document in a single pass — that's how chunk-by-chunk degrades into sentence-by-sentence at the seams. Pause after each chunk, re-read the Arabic aloud, make sure it stands on its own as Arabic prose before moving to the next chunk.

**Two failure modes to avoid:**

1. **Word-for-word translation.** AI default. Reads like a Google-translated press release. "Infrastructure that serves at scale" → `«infrastructure» تصمد تحت الحمل، ولا تطلب الانتباه` — the "doesn't ask for attention" metaphor doesn't carry in Arabic. No Arabic reader has that idiom for infrastructure. Drop the metaphor or find a native Arabic image.

2. **Metaphor preservation across languages.** English metaphors that work English-only:
   - "doesn't ask for attention" / "flies under the radar" / "behind the scenes" → in Arabic, find a different image or drop entirely.
   - "the plumbing" → `السباكة` happens to work because Arabic uses the same metaphor for foundational systems. Rare lucky case.
   - "the heavy lifting" → no clean Arabic equivalent; just say what it lifts.
   - "moving the needle" → no Arabic equivalent; say what changed.

**How to test if a metaphor carries:**

- Read the Arabic translation aloud. Does an Arabic-native ear naturally use this image for this concept? If unsure, the answer is no.
- Check: does any Lumen anchor use this image for this concept? If not, drop it.
- Default: prefer a concrete description over an English metaphor in Arabic. "بنية تحتية متينة" beats forcing "لا تطلب الانتباه" into a sentence where it doesn't belong.

**The right mode:**

For each English string, ask the SEMANTIC question:
- What does John want the Arabic reader to walk away thinking?
- What's the ONE thing this sentence conveys?
- What's the most natural Arabic way to convey THAT?

Then write that Arabic. The English source becomes a reference for intent, never a template for surface form.

**The framing that produces the best output:**

When dispatching the panel, frame the task as: *"You are a local tech writer at «لومن» telling this story in Arabic for the first time. The English below is the writer's source notes — not text to translate, just intent to convey."* This framing produces bolder rewrites: re-structured paragraphs, native Arabic openings, dropped metaphors that don't carry. Verified on the agentic-coding-revolution rewrite — the version that locked in started with: *"في 2025، تغيّرت البرمجة من سؤال تقني إلى سؤال ذهني: هل تعرف ماذا تريد؟"* The English had no such opener — it was written fresh because the trio was told to write, not translate.

## English code-switch density (don't pile up `«»` tokens)

The `«word»` convention is a punctuation tool for marking foreign tokens — not a license to chain four of them in a single short clause.

**Hard limit:** if a sentence has 4+ `«English»` tokens packed in 10 words, you've gone too far. Examples of overload:
- `بدأت من «data engineering»: «pipelines»، و«warehouses»، و«lakehouses»` — 4 tokens in 8 words. Reads like a tag cloud, not Arabic prose.

**Three fixes when you hit the density limit:**

1. **Compress the list to 2 strongest items.** Drop the rest. `بدأت من «data engineering»: «pipelines» و«warehouses»` — still names the discipline, still gives examples, half the tokens.
2. **Use Arabic equivalents for the generic items.** Specific tools/products stay English (`«Dagster»`, `«dbt»`). Generic categories can go Arabic (`pipelines` → `أنابيب البيانات` rarely, OR just drop the list and lean on the discipline name).
3. **Restructure the sentence to space tokens out.** Split one dense clause into two breath-clauses with the tokens distributed.

**Rule of thumb:** before keeping a `«»` token, ask: is this term industry-standard English (where the Arabic translation would be wrong / stiff), OR could the sentence work without naming this specific noun? If the second — drop or rephrase.

## Arabic micro-moves (Lumen patterns we've locked in)

These are small, specific patterns that emerged from real edits. They're stricter than the anti-patterns above — apply consistently in formal Arabic prose.

- **Parallel pluralization across paired clauses.** When two clauses are syntactically parallel (`أحول X إلى Y، والZ إلى W`), match grammatical number. Plural-plural beats singular-plural even when both work grammatically. Example: `أحول البيانات إلى قرارات، والأنظمة المعقدة إلى أنظمة بسيطة` — both targets are plural for rhythm. Singular `قرار` against plural `أنظمة` breaks the beat.
- **Ellipsis (`...`) on identity-statement closes.** Bio openers, mission statements, "about me" intros — close with `...` not a period. Signals "this is the start of a conversation, not the end of a pitch." Example: `... وسهلة التعامل...` at the end of a homepage `bioMission`. Don't overuse — this is for statements that should feel open, not for every paragraph.
- **`X، لا Y` three-beat negation.** Lumen signature: state the positive then negate the obvious wrong reading. `الصورة الكاملة، لا القطعة`. `التحوّل الذي يحدث تحت السطح، لا الـ «hype»`. Punchy, parallel, characteristic.
  - **STRICT TEST — apply before using this pattern.** The Y must be a concept Arabic readers already recognize as the cultural/semantic opposite of X. Not invented. Not translated from English. Y must pass two checks:
    1. **Would Y stand alone as a recognizable idea in an Arabic conversation?** `القطعة` does. `الـ «hype»` does (loan-word, but recognized). `مغامرة كل مرة` does NOT — it's an English-derived hypothetical, not an Arabic idea.
    2. **Does any Lumen anchor use Y as a similar opposite?** If you can't point to a precedent, the pattern isn't ready.
  - **Failure mode**: forcing the pattern with an invented Y. If Y has to be conjured to make the negation work, **drop the pattern entirely**. End with a clean positive declarative instead. The X، لا Y is a tool, not a quota.
  - Examples of WRONG uses (do not produce):
    - `نشر قابل للإعادة، لا مغامرة كل مرة` — `مغامرة كل مرة` is invented English-rhythmic Arabic. No Arabic reader has "deployment-as-adventure" as a frame.
    - `كود نظيف، لا فوضى كل صباح` — `فوضى كل صباح` is invented.
  - When in doubt: state the positive cleanly and stop. `نشر يعمل بنفس الطريقة في كل مرة.` lands. Don't add a negation just to hit the pattern.
- **Rephrase forbidden translations descriptively when possible.** `abstraction` → `أنظمة بسيطة وسهلة التعامل` (descriptive) beats `«abstraction»` (English fallback) beats `تجريد` (forbidden). The dictionary entry has the priority order. Same pattern applies to any term with a forbidden literal translation: try descriptive rephrase first, English fallback second, never the literal Arabic.
- **Drop filler trailing clauses.** If a final clause adds no information the verb didn't already imply, cut it. Example: `بنيت مستودعات البيانات، ومسارات الـ «ETL»، والـ «pipelines»، يعتمد عليها الفريق كل يوم.` → drop `يعتمد عليها الفريق كل يوم` — it's filler that translation-mind adds for completeness. The list of artifacts already conveys "things that exist and are used." Test: does the trailing clause introduce a new claim, or just restate what's implicit? If implicit, cut.
- **Section/heading labels: translate to Arabic by default.** When in an Arabic locale page, section headings like `Data Engineering:`, `System Design:`, `AI Engineering:` translate to Arabic equivalents (`هندسة البيانات:`, `تصميم الأنظمة:`, `هندسة الذكاء الاصطناعي:`). **Exception**: `«DevOps»` stays English (no clean Arabic). Acronym-only labels (e.g., `«CI/CD»`) stay English. Tell: if the heading has a clean idiomatic Arabic form, use Arabic; if it's an acronym or English-only term of art, stay English.
- **Post title and Part 1 H2 must not duplicate.** The post title (from `blog-posts.ts` metadata) appears as the page H1 at the top. Part 1's `<h2>` appears mid-page. If they say the same thing, the reader sees the line twice. When changing one, check the other.
- **Verb form `نُجرّد` vs. noun `التجريد`.** The verb works in Arabic prose ("نُجرّد «code» منذ ثمانين سنة" lands as an action). The abstract noun `التجريد` reads stiff and academic — forbidden. Use the verb for "to abstract / we abstract"; rephrase or keep English `«abstraction»` for the noun.
- **Drop the `الـ` before `Athletics`-style English label tokens in compact phrases.** When the English token is a tight compound that doesn't need a definite article in context, drop `الـ`. `«CI/CD»، أتمتة، «infrastructure as code»` — the list-of-tokens shape doesn't take articles. The `الـ` rule applies to definite/categorical subjects, not to bare list items.
- **Never start an Arabic paragraph, sentence, heading, or bullet with an LTR token.** Even with `dir="rtl"` set on the container, the Unicode BiDi algorithm uses the first strong character of each line/paragraph to drive its local direction. A paragraph that opens with `«open-kit»` or `` `code` `` will render visually scrambled — the LTR token jumps to a wrong position and the punctuation around it follows. Rewrite to lead with an Arabic word.
  - `«open-kit» تطبيق يعمل من الـ «terminal»` → `تطبيق «open-kit» يعمل من الـ «terminal»` (move an Arabic head-noun in front)
  - `**«open-kit» يعرف السياق.**` → `**يعرف «open-kit» السياق.**` (verb-subject inversion is natural in Arabic; the verb leads)
  - `«Dagster» هو المنسق` → `هو «Dagster» المنسق` (lead with the pronoun)
  - When no graceful Arabic lead exists, restructure the sentence so the LTR token sits in the middle. Never as the absolute first character.
  - **Tell**: if the first non-whitespace, non-markdown-marker character of a line is an LTR character (`«`, an English letter, a backtick + English), the line WILL render wrong on most viewers. Lead with Arabic.

## Output specs

- **Email**: subject line in target register, body 80-200 words for formal, can be shorter for informal.
- **LinkedIn post**: 100-300 words formal. Strong opener. Concrete example. Soft close (no CTA spam).
- **Formal letter to an executive**: formal register, header (date, recipient, subject), greeting, body (problem → ask → next step), closing (الاسم، الصفة، التاريخ).
- **Notes / Slack / WhatsApp**: informal, as concise as English. Dialect is fine.

## Voice anchors

Anchor files live in `~/helm/02-ana/voice-samples/arabic/`. Tiered by priority.

### Tier 1 — North star (read first, every time)

**لومن** (Lumen, `example.com/articles`) — the golden standard. local editorial collective: newsletters, podcasts, documentaries. House voice is the target.

| File | What it anchors |
|------|-----------------|
| `formal--lumen-essay-1.md` | Analytical column — section-headed long-form, concrete numbers, structured argument (a columnist, a news newsletter) |
| `formal--lumen-essay-2.md` | Cultural/critical essay — تمهيد → النتيجة structure, embedded thinker reference, casual-but-precise MSA (a columnist, a culture newsletter) |
| `formal--lumen-essay-3.md` | Humorous personal essay — MSA narration with dialect dialogue, parenthetical asides to reader, punchline close (a columnist, a personal newsletter) |

### Tier 2 — Secondary niche references (layer only when domain demands)

- **كاتب سياسي** (columnist-a) — `@columnist-a`. Deep political/diplomatic analysis. Use when the piece is geopolitical and Lumen's range doesn't cover it.
- **كاتب تقني** (columnist-b) — `@columnist-b`. Tech-executive voice, heavy English term code-switching. Use for AI/CS pieces with programmer slang.
- **كاتب مقالات شخصية** (columnist-c) — `example.substack.com`. Personal life-stage essays (retirement, career arcs). Use when the topic is autobiographical and the audience is general.
- **كاتب أدبي** (columnist-d) — `example.me`. Literary/philosophical op-ed with embedded novelist quotations. Use for dense reflective pieces.

| Register | File | What it anchors |
|----------|------|-----------------|
| formal | `formal--columnist-a-1.md` | Long-form analytical column |
| formal | `formal--columnist-a-2.md` | Narrative-driven column with a historical frame |
| formal | `formal--columnist-a-3.md` | Short-form punchy opinion thread (Twitter, three-beat structure) |
| formal | `formal--columnist-a-4.md` | Reflective retrospective voice (Medium year-end piece) |
| formal | `formal--columnist-b-1.md` | Tech-executive MSA, English term code-switching |
| formal | `formal--columnist-c-1.md` | Personal reflective essay — narrative MSA, light dialect in dialogue |
| formal | `formal--columnist-d-1.md` | Literary/philosophical op-ed — dense MSA, embedded quotations |
| informal | `informal--columnist-a-1.md` | Conversational reflection, dialect markers ("اللي", "لما"), peer voice |
| informal | `informal--columnist-b-1.md` | Programmer informal voice — MSA + dialect + English tech terms |

**Default: Lumen only.** Layer a Tier-2 reference *only* when the piece sits clearly inside that niche. When in doubt, stop at Tier 1.

**How to use**: Read the anchor(s). Match cadence, sentence length, idiom density, and how claims are introduced. Don't copy lines — copy the *shape* of the prose.

Background context (optional, not voice anchors):
- `~/helm/02-ana/identity/who-i-am.md` — persona, useful for self-references
- `~/helm/02-ana/identity/story.md` — story, useful for first-person narrative

To add or rotate anchors, see `~/helm/02-ana/voice-samples/arabic/README.md`.

## Examples

- "اكتب إيميل لفريق الهندسة في شركة شريكة عن Matchbox" → formal email
- "بوست لينكدإن بالعربي عن مشروع هيليوس بدون فلسفة" → formal LinkedIn post
- "خطاب رسمي لمدير عام في شركة لطلب اجتماع" → formal letter
- "رد سريع لأخوي على الواتساب عن تأخير الديبلوي" → informal note
- "ترجم هذا البوست الإنجليزي للعربي مع الحفاظ على نبرتي" → translate-and-adapt (English source → formal)
