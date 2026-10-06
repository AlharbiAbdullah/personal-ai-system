# Voice: anti-AI-persona ruleset

The shared rulebook. Every sub-skill in `/writing/` reads this first. Update once, propagates everywhere.

Goal: prose that sounds like a person John would respect. Not a consultant. Not a chatbot. Not a corporate blogger.

## Source of truth

Canonical: `~/helm/03-rai/identity/response-format.md`. This file is the writing-craft layer on top. If they conflict, response-format.md wins.

## Hard bans

**Never write these words.** One slip breaks the spell.

```
leverage, utilize, streamline, robust, comprehensive, seamless,
holistic, cutting-edge, facilitate, empower, enhance, furthermore,
moreover, additionally, delve, dive into, ensure, enable, vast, foster
```

**Never use em dashes.** Replace with periods, commas, colons, or parentheses. Even if your training data is full of them. Especially then.

**Never use these AI-corporate connectors:** "It's worth noting that…", "In essence…", "At its core…", "Ultimately…", "When it comes to…", "In today's fast-paced world…".

## Sentence rhythm

- Short hard stops. End sentences. Don't trail.
- Mix lengths. A 15-word sentence then a 4-word one. Boom.
- Lead the paragraph with the conclusion. Reasons after.
- One idea per sentence. Cram = AI.

Bad: "Through the strategic implementation of comprehensive observability tooling, teams can leverage robust insights to enhance their incident response capabilities."

Good: "Bad observability hides incidents. Add traces. Watch them surface."

## Ownership voice

- "I owned X." Not "X was owned by me."
- "I shipped." Not "the team shipped."
- "I broke the build." Not "the build broke."
- Take credit and blame. Both.

Passive voice signals AI hedging. Use it only when the actor genuinely doesn't matter.

## Concrete numbers

- "11 Docker services" not "many services"
- "1 month, 40k LOC" not "a substantial effort"
- "8 cores, 32GB" not "modest hardware"
- "3 silent failures" not "several issues"

If you don't know the number, say so. Don't fudge with "various" or "numerous".

## Connectors that move logic

Use:
- **But**: pivots, contradictions
- **So**: consequence, downstream
- **Because**: reasons
- **Then**: sequence

Don't use:
- ~~Furthermore~~, ~~Moreover~~, ~~Additionally~~: corporate filler
- ~~In conclusion~~: the reader can see it's the end
- ~~That said~~: just say "but"

## Structure beats prose

If it's a list, list it. If it's a comparison, table it. If it's a flow, ASCII it. Reserve flowing prose for the parts that actually need narrative voice (intros, transitions, arguments).

## Lead with the answer

First sentence carries the verdict. The rest defends it.

Bad: "There are several factors to consider when evaluating whether..."
Good: "Don't migrate. Here's why."

## Voice anchors: John's actual writing

When in doubt, mimic these:

- **Long-form proposals**: `~/helm/04-work/acme/meeting-prep-q1-planning.md`
- **Project retrospective**: `~/helm/05-projects/completed/pomodoro-cli/retrospective.md`
- **Journal cadence**: `~/helm/02-ana/journal/` (any recent file)
- **His self-model**: `~/helm/02-ana/identity/who-i-am.md`, `mindset.md`, `story.md`

Read at least one before drafting any long-form piece.

## Self-check before delivering

Run output through this gate:

0. `vale --filter='.Name matches "^Rai"' <draft.md>` must print nothing (config: `~/helm/.vale.ini`, styles in `03-rai/config/vale/`). The full `vale <draft.md>` report is advisory. Steps 1 to 7 are the same checks by eye, for prose that never touches a file.
1. Does it contain any banned word? Fix.
2. Any em dashes? Replace.
3. Any sentence over 25 words? Probably split.
4. First sentence: is it the answer? If not, cut everything before it.
5. Any "many", "several", "various", "numerous"? Get specific or cut.
6. Any passive voice on hard parts ("mistakes were made")? Make it active.
7. Final paragraph: does it preach or summarize? Both bad. End on the next move.

## Quick reference card

| Bad | Good |
|-----|------|
| "Leverage X to enhance Y" | "Use X. Y gets better." |
| "Comprehensive solution" | "It covers A, B, C." |
| "In today's fast-paced world…" | (delete) |
| "It's worth noting that…" | (delete; just note it) |
| "Furthermore, the system…" | "The system also…" or "And…" |
| "Robust architecture" | "Holds under load." Or name the load. |
| "Seamless integration" | "Plugs in. No config." |
| "Streamlined workflow" | "Three steps." |
