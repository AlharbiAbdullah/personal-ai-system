# Arabic dictionary

Working dictionary for Arabic drafting. Each entry has guidance for whether the term stays English, switches to Arabic, or is context-dependent.

Some terms have notes — context-dependent renderings, forbidden translations, acceptable inline forms. Read the note before deciding.

Rule of thumb: if the term has a stable industry meaning in English and Arab tech-speakers say it in English when speaking Arabic, keep it English in writing too. Translating `data engineering` to `هندسة البيانات` reads stiff; native bilingual tech speech keeps it `data engineering`.

## Typographic convention: wrap English in « »

When an English word, phrase, brand, or acronym appears inline in Arabic prose, wrap it in Arabic guillemets `«word»` (same style as Lumen uses for named entities and quoted titles). Examples:
- `«Dagster»`, `«dbt»`, `«DuckDB»` (brand/tool names)
- `«data orchestrator»`, `«asset-based orchestration»`, `«medallion architecture»` (technical compounds)
- `«AI»`, `«ML»`, `«API»`, `«UI»` (acronyms in prose)
- `«abstraction»`, `«lineage»`, `«idempotent»` (concept terms)

Do NOT wrap in « »:
- English inside `<code>` inline tags (already visually distinct)
- English inside ``` code blocks / `<HighlightedCode>` (it's code, not prose)
- English in `<h2>` / `<h3>` headings (heading style is visually distinct)
- File paths in technical contexts (`data/raw/`, `path/to/file.py`)

Do wrap:
- English inside `<p>` body text, `<li>` bullets, `<strong>`/`<highlight>` spans (these are prose).

## Definite article `الـ` before English words

Native bilingual Arabic prose freely prepends `الـ` to English nouns when they're definite/categorical subjects in flowing prose. Use `الـ` when:
- The English word is the subject of a categorical statement: `الـ «infrastructure» تصمد تحت الحمل` (infrastructure holds under load).
- The reference is definite ("the X" in English): `الـ «resource» يلفّ DuckDB`, `الـ «schedule» يبدأ متوقفًا`.
- Generic/categorical mention in prose flow: `الـ «data orchestration» اليوم لا تحتاج بنية تحتية ضخمة`.

Don't use `الـ` when:
- First indefinite introduction ("a X" in English): `بنيت «data orchestrator»` (built a data orchestrator).
- Proper noun (brand/tool): `«Dagster»`, `«DuckDB»` — never `الـ «Dagster»`.
- List/enumeration of bare labels: `«pipelines»، «warehouses»، «lakehouses»`.
- Predicate adjectives: `يجعل العملية «idempotent»`, `يعمل «embedded»`.

Spacing: write `الـ «word»` with a space between `الـ` and the « » — the article is Arabic grammar, the « » wraps the foreign token.

## How to use this list
- Read before drafting Arabic content for `johndoe.dev` or any tech-domain Arabic prose.
- If you hit a term that you considered translating and it's on this list, leave it English (unless a note says otherwise) and wrap in « ».
- If you encounter a new term that should be added, ask John, then append it to the right section below. New terms with context-dependent rendering go under their entry as an italicized note.

---

## Programming / coding

- **code** — *Default: English. Exception: when the sentence is about programming as a discipline/practice in a non-tech rhetorical context, "البرمجة" works. The artifact stays English ("اكتب code يقرأ من dbt"), the discipline can be Arabic ("تعلَّم البرمجة من الصفر"). Never write "الكود" or "كتابة الكود".*
- **coding** — *Same rule as `code`. Default English. "البرمجة" only when the sentence treats programming as a discipline, not as the act of producing code in a tech workflow.*
- **agentic coding**
- **vibe coding**
- pair programming
- refactor
- refactoring
- pull request / PR
- code review
- commit
- merge
- rebase
- diff
- bug
- patch
- hotfix
- changelog

## AI / ML

- **AI** — *Context-dependent. Three rules — pick by where the term sits:*
  - *English `«AI»` (or `الـ «AI»`) — when it's a tight tech-jargon compound or a category heading: `«AI agents»`, `«AI models»`, `«AI Engineering»` as a section title, `«AI tooling»`.*
  - *Arabic `الذكاء الاصطناعي` — when it sits inside natural Arabic prose flow as a subject/object: "يغيّر الذكاء الاصطناعي طريقة البناء"، "تطبيقات على الذكاء الاصطناعي".*
  - *Arabic `ذكاء اصطناعي` (indefinite) — in first-person bio contexts where John introduces himself in Arabic-first prose: "مهندس بيانات وذكاء اصطناعي من أوستن". The Arabic-first identity register wins over the "label/heading" rule because the audience is reading Arabic about a person, not browsing a tech section.*
  - *Tell: tech-jargon compound or section heading → English. Sentence subject/object → Arabic definite. Bio-title for John → Arabic indefinite.*
- **ML**
- **LLM / LLMs**
- RAG
- agent / agents
- sub-agents
- autonomous agents
- agentic workflows
- prompt
- prompting
- fine-tuning
- embedding / embeddings
- inference
- training
- hallucination
- context window
- tokens
- token

## Data engineering

- **data** — *Context-dependent. Default Arabic `البيانات` when the word stands alone as a noun in Arabic prose ("البيانات الخام"، "تحويل البيانات"، "جودة البيانات"). Stays English only inside compound tech tokens: `data engineering`, `data pipeline`, `data lake`, `data lakehouse`, `data warehouse`, `data orchestrator`, `data orchestration`, `data mesh`. Rule of thumb: if the next or previous token is English and forms a known industry compound, keep `data` English; otherwise it's `البيانات`.*
- data engineering
- data lake / data lakes
- lakehouse / data lakehouse
- warehouse / data warehouse
- pipeline / data pipeline
- ETL / ELT
- ingestion
- staging
- intermediate
- marts
- medallion (architecture)
- bronze / silver / gold (layers)
- schema
- transformation / transformations
- orchestration
- **data orchestration** — *Keep English `«data orchestration»` — the term is a load-bearing compound. NEVER `«تنسيق البيانات»` or `«منسق البيانات»` (both read like product-manual translation). Rephrase only if the sentence can lose the noun entirely (e.g., "أدير سير البيانات من المصدر إلى الـ «warehouse»").*
- **data orchestration tool** — *Keep English `«data orchestration tool»`. NEVER `«أداة منسق بيانات»`.*
- **data orchestrator** — *Keep English `«data orchestrator»`. NEVER `«منسق بيانات»`. Same rephrase exception as above if the sentence can drop the noun.*
- observability
- lineage
- dbt
- DuckDB
- Dagster
- Airflow
- Snowflake
- BigQuery
- Databricks
- Parquet
- Iceberg

## DevOps / infra

- DevOps
- CI/CD
- **infrastructure** — *Keep English `«infrastructure»` (wrap in « » in prose). NEVER `«البنية التحتية»` — AI-default and overused. Even better when the sentence allows: drop the abstract noun and describe what it is or what it does. "هذا يغطي بنية الـ «LLM»" → "هذا يكفي لتشغيل الـ «LLM»". "قائد البنية التحتية" → "مدير الـ «infrastructure»" or descriptive "المسؤول عن الشبكة والخوادم". Test: does the sentence still land if you drop the word entirely? Usually yes.*
- infrastructure as code
- IaC
- **hardware** — *Keep English `«hardware»`. NEVER translate to `«عتاد»` — reads archaic and military in Arabic, doesn't carry the computing-hardware sense. When the sentence references definite/categorical hardware, use `الـ «hardware»`; with prepositions, `بالـ «hardware»` / `للـ «hardware»`.*
- container / containers
- containerization
- deployment / deploy
- rollback
- monitoring
- logging
- alerting
- uptime
- SLA / SLO / SLI
- scale
- scaling
- horizontal / vertical scaling
- load balancing
- Docker
- Docker Compose
- Kubernetes / k8s
- Terraform
- Ansible
- AWS
- GCP
- Azure
- Cloudflare
- Vercel

## System design

- **system design** — *Context-dependent.*
  - *English `«system design»` — when it's a category title, a section heading, a labeled discipline name in a list of disciplines, or a CV/resume-style descriptor.*
  - *Arabic `تصميم الأنظمة` (or `بناء الأنظمة`) — when speaking about the practice in flowing Arabic prose: "أعمل في تصميم الأنظمة"، "بناء الأنظمة الموزّعة يحتاج إلى...".*
  - *Arabic `تصميم الأنظمة` (also) — in first-person bio contexts where John introduces himself in Arabic-first prose: "أبني عند تقاطع البيانات وتصميم الأنظمة...". The Arabic-first identity register wins over the "label/heading" rule.*
  - *Tell: section heading or CV descriptor → English. Sentence subject or bio listing in Arabic prose → Arabic.*
- **architecture** — *Context-dependent. Avoid `«المعمارية»` AND `«البنية»` in tech prose — both read stiff and AI-default. Three valid renderings in priority order:*
  - ***Preferred — describe concretely** when context allows: section heading "كيف يعمل", body phrasing "ثلاث طبقات", "كيف بُني". Native local tech voice describes rather than names abstract structure.*
  - *Fallback — keep English `«architecture»` wrapped: "هذا يغير «architecture» النظام كاملًا".*
  - *NEVER `«المعمارية»` or `«البنية»` for the noun "architecture" of a software system. Both read translated.*
- platform architecture
- **abstraction** — *Noun vs. verb form matters here. Three valid renderings, in priority order:*
  - ***Preferred — rephrase descriptively** in natural Arabic when context allows: "أنظمة بسيطة وسهلة التعامل", "بنية تخفي التعقيد", "طبقة تختصر التفاصيل". When the sentence is about the *effect* of an abstraction (not the noun itself), this lands cleaner than keeping the English term.*
  - *Fallback — keep English `«abstraction»` when the rephrase would lose specificity or break sentence rhythm: "حوّل التعقيد إلى «abstraction» واحدة".*
  - *NEVER translate the NOUN to `«التجريد»` — reads stiff and academic. Same for "abstract" used as adjective in a technical sense.*
  - ***Verb form `نُجرّد` / `جرّد` IS acceptable** when the sentence uses abstraction as an action: "نُجرّد «code» منذ ثمانين سنة". The verb carries the "we are abstracting away" sense naturally in Arabic, even though the abstract noun `التجريد` is forbidden. Tell: if the sentence describes an ongoing action ("we abstract X"), the verb works. If it names the abstraction as a thing ("an abstraction"), use rephrase or English.*
- monolith
- microservices
- service
- API
- API key / API keys
- REST
- GraphQL
- gRPC
- webhook
- queue
- broker
- pub/sub
- event-driven
- idempotent / idempotency
- caching
- cache
- consistency
- latency
- throughput
- backpressure
- embedded

## Auth & security

- auth
- authentication
- authorization
- SSO
- OAuth
- JWT
- token (auth)
- session
- secret / secrets

## Tooling / IDE / CLI

- terminal
- CLI
- shell
- prompt (CLI)
- IDE
- VS Code
- Cursor
- Claude Code
- Windsurf
- Copilot
- GitHub Copilot
- ChatGPT
- Claude
- Gemini
- Replit

## Languages / frameworks

- Python
- TypeScript
- JavaScript
- Go
- Rust
- Java
- C
- C++
- SQL
- YAML
- JSON
- Bash
- HTML
- CSS
- React
- Next.js
- Vue
- Svelte
- Express
- FastAPI
- Django
- Flask
- Prisma
- Tailwind
- Tailwind CSS
- Pydantic
- npm
- pip
- uv
- bun
- pnpm

## Concepts (Claude Code-specific)

- hooks
- skills
- sub-agents
- MCP / MCP servers
- plugins
- slash commands
- agents
- assets
- tool calls
- dependency injection
- dependencies
- resources

## Files / formats

- markdown
- MDX
- CSV
- TSV
- PDF
- PNG
- JPG
- SVG
- woff2

## Networking

- HTTP / HTTPS
- URL
- DNS
- TCP
- WebSocket
- CDN
- proxy
- reverse proxy
- gateway

## Misc

- production
- staging (env)
- dev / development
- testing
- unit test / integration test / e2e
- linter
- formatter
- prettier
- ESLint
- git
- GitHub
- GitLab
- Bitbucket
- pull (git)
- push (git)
- branch
- main
- master

---

## How notes work

Entries with `**bold**` formatting carry a context-dependent note in italics. The italic note overrides the default "always English" rule. Four patterns appear:

1. **Discipline vs. artifact** (e.g., `code`, `coding`) — Arabic acceptable when the noun is a discipline/practice; English when it's the artifact in a tech workflow.
2. **Label vs. prose flow** (e.g., `AI`, `system design`) — English when the term is a label, heading, category title, or part of a tight tech compound. Arabic when the term is the subject/object the sentence is naturally discussing in Arabic flow.
3. **Compound vs. standalone** (e.g., `data`) — Stays English inside known industry compounds (`data pipeline`, `data engineering`). Defaults Arabic when standing alone as a noun in Arabic prose.
4. **Forbidden translation** (e.g., `data orchestrator`, `abstraction`) — a specific Arabic translation that AI defaults produce, flagged as wrong. Keep English.

When adding a new context-dependent entry, follow one of the four patterns and keep the note tight.

---

## Add-as-you-go

Terms encountered in review that need a decision. Move to the right section once confirmed.

- (empty)
