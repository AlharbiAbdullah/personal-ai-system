# Bawaba Weekly — House Style

Loaded by the `/news week` job **before writing** and enforced by a self-review pass **before publish**.
The point: the voice that "clicked" in W24 stops being re-invented every Saturday and stops sounding
auto-generated. Born from the 50-agent redesign (2026-06-13).

---

## Keep (the voice that works — protect)
- Lead with the verdict, then defend it. First sentence carries the claim.
- Concrete numbers over adjectives. Named human subjects ground every abstraction.
- Active voice. Tables and data where they beat prose.

## Rationed devices (allowed, but capped per issue)
| Device | Budget |
|---|---|
| Full antithesis / rule-of-three closer | Cover, Lesson, Closing **only** — one each, max |
| "frontier-vs-floor" paired frame | **exactly twice**: Editor's Letter open + Closing last line |
| Aphoristic fragment-closer | one genuinely earned per issue |
| Em-dash | fine in prose; don't pile 3+ in a sentence |

## Banned / overused-words ledger (cut on sight)
- Self-awarded superlatives: "the most important paragraph of the week", "the best thing anyone said"
- Filler connectives: "rhymes with", "worth noting", "one more", "it's worth"
- Hollow-profundity lines that the very next sentence contradicts
- Staccato fragment pile-ups ("X. Y. Z. The work is in between.") more than once per issue
- Banned vocab (carried from voice.md): furthermore, moreover, robust, comprehensive, seamless, leverage, delve, empower

## One idea, one home
- "cost-per-task, not cost-per-call" → **The Stack** only (other departments may reference the shape)
- The multi-source convergence reveal → stated in full **only** in The Lesson
- A claim's full table of numbers → one home; cross-reference, don't restate

## Tag notation (define once in The Fold legend)
- **Shelf life:** `[durable]` (mechanism that holds) vs `[perishable]` / `[shelf ~Mon DD]` (ages out)
- **Evidence tier:** `[primary]` `[vendor-claim]` `[1-practitioner]` `[projection]` — hedge proportional to evidence
- Tag every price, ship-date bet, engagement count, projection, and every load-bearing claim.

## Structure contract (per issue)
- Masthead (wordmark · No. · dates · cover line · creed) + **The Fold** (≤90-sec scan, anchor jumps, tag legend, previously/next-watch from `story-arcs.md`).
- Every department: kicker label · one-sentence **italic deck** (its single falsifiable claim this issue) · a fixed **decision footer** (`BUILD-NOW` / `DECIDE` / `WATCH` / `AVOID`) — which replaces any literal "How it applies to your stack:" header.
- Stable kebab anchors on every H2 (`#cover`, `#model-state`, `#lesson`, `#stack`, `#workshop`, `#shelf`, `#closing`).
- Model State opens with the diffable register (same columns weekly + Δ + trajectory arrow).
- Closing carries the reference diagram (D2/ASCII), each node labeled by the department that argued it.
- **No word floor.** Per-department ceilings + a cut-line rule. Surface one visible line above the footer: *"Cut this week: [X], because [Y]."*
- Two-altitude reading: any passage with 3+ hard numbers keeps one headline number in prose, pushes the rest into a labeled `<details>` drawer.

## Self-review pass (run before publish)
```
grep -nE "most important|best thing|rhymes with|worth noting|furthermore|moreover|seamless|leverage" file   # → expect ~0
grep -c "frontier" file        # frame paired ~2; plain descriptors ok but watch the count
grep -c "cost-per-task" file   # → 1 home (The Stack)
grep -c "CLAUDE_FILL\|<concept>\|TODO" file   # → 0
```
Then eyeball: does each department have a deck + a decision footer? Does The Fold scan in 90 seconds? Is every perishable number tagged? Did the cut-line name what was dropped?
