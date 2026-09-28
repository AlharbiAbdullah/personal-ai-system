# Deep Research → Home

**Triggered by:** "research {X} properly and write it up" / "deep research on {X}"
**Cadence:** Weekly / ad-hoc
**Done when:** a verified, cited report has landed in a permanent vault home AND been indexed by `/map-updater`.

Every deep-research run today is ephemeral — it fans out, synthesizes, scrolls past,
and dies. This playbook closes the loop: question → verified report → permanent home →
indexed. The harness does the research; the gates here decide whether the question is
worth running and where the output lives.

```
Scope gate → Deep research → Route decision → Land it → Index → Leave for coordinator
```

> **The output is worthless if it dies in the transcript.** A run that ends without
> a routed, indexed home is an incomplete run. The two gates (scope + route) are the
> whole value — everything between them is delegated.

---

## Steps

### 1. Scope gate (before you run anything)

- [ ] Read the question. **Is it specific enough to research directly?**
- [ ] **Underspecified** (e.g. "what laptop to buy", "best vector DB") → STOP. Ask
      **2–3 clarifying questions** first: budget, use-case, region, constraints,
      time horizon — whatever narrows it.
- [ ] Weave the answers back into a single refined question. Do not run on the vague one.

> **Decision Point**: a vague question produces a vague report that earns no home.
> Sharp question in, or no run. If the user resists narrowing, name the tradeoff
> ("broad query → shallow survey") and let them choose.

### 2. Run the deep-research harness

- [ ] Run **`/deep-research`** with the refined question as args. It fans out web
      searches, fetches sources, adversarially verifies claims, and synthesizes a
      cited report.
- [ ] Do not re-implement any of this by hand. The harness owns fan-out, verification,
      and citation — your job is the question in and the routing out.

### 3. Route-decision gate (where does it belong?)

- [ ] The report exists but is still ephemeral. **Pick exactly one permanent home:**

> **Decision Point**: route by what the report *is*, not what it's *about*.
> - **Durable concept / mental model** → **`/knowledge → new-topic-note`**
>   (`10-knowledge/`, Simplicity Theorem note from the `Topic Note.md` template).
> - **Scholarly / literature survey** → **`/research → literature`**.
> - **It sparked an idea, not just a fact** → **`/ideas → start-seed`**
>   (`09-ideas/`, status `seed` in frontmatter — ideas never die).
> - **Work-relevant to a live engagement** → land under `04-work/{engagement}/`.
> - **None fit cleanly?** Default to `/knowledge → new-topic-note` — durable concept
>   is the safest permanent home. Never leave it in the transcript.

### 4. Land the report in its home

- [ ] Run the chosen sub-skill from step 3 to scaffold + write the verified report
      into that location. Carry the citations through — an uncited landing loses the
      whole point of the verification pass.
- [ ] No "archive" verbs for knowledge/ideas text. Git log is the archive; ideas never
      die.

### 5. Index it

- [ ] Run **`/map-updater`** to refresh the vault index
      (`.helm-index/helm-index.md`) so the new report is discoverable. An unindexed
      report is a buried report.

### 6. Sync (leave for the coordinator)

- [ ] Vault edits (the new note/seed/work file, the index) stay **local**. The Linux
      coordinator commits + pushes at its next maintenance run (04/10/16/22:00 local time).
- [ ] **Do not `git push` from the Mac** — single-writer rule, `03-rai/SYNC-ARCHITECTURE.md`.

---

## Connections

- Research harness: `/deep-research`
- Permanent homes: `/knowledge → new-topic-note`, `/research → literature`, `/ideas → start-seed`, `04-work/{engagement}/`
- Indexing: `/map-updater` → `.helm-index/helm-index.md`
- Second-opinion model on a contested claim: `/ask-model`
- Inbound capture that feeds research queues: `/triage → process-inbox`
- Single-writer sync: `03-rai/SYNC-ARCHITECTURE.md`
