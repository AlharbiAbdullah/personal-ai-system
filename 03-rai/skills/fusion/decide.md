---
name: decide
description: >
  Panel decision. Each voice weighs 2 to 4 options against the criteria and
  picks one, then attacks the strongest case for every option, its own first,
  and keeps or changes its pick on evidence. The coordinator counts round 1 and recommends. USE WHEN /fusion decide, or
  John weighs options: an architecture choice, a tool, a purchase.
---

# /fusion decide

An architecture decision follows [[30-architecture-decision]] and a purchase
follows [[26-purchase]]. The panel is one step inside them.

## The ask (`$RUN/ask.md`)

- The decision in one sentence, and the options, labeled.
- The criteria in his order of weight. Ask him when he has not given them.
- Facts per option that are already verified (prices, versions, local stock).
- Options he already declined stay out: never re-pitch them.

## Rounds

- **Round 1:** each voice weighs every option, picks one and says what would
  change its mind.
- **Between the rounds:** check the facts each voice said would change its
  mind (price, version, local stock, a benchmark). The results go under FACTS
  ESTABLISHED in `ask-r2.md`. The ledger holds each option's arguments, with
  no pick and no count. Skip round 2 when 5 of 6 picked one option and no
  checked fact flips it.
- **Round 2:** each voice attacks the strongest case for every option, its own
  pick first. Then it gives its final pick: HELD, or CHANGED with the fact
  that moved it. No tally is shown: a head count pulls voices to the majority.

## Synthesis

1. **Recommendation** first, with the deciding reason.
2. **Tally:** the round-1 picks per option, one vote per model: the
   independent vote. Then each round-2 change with the fact that moved it. A
   change with no new fact is ignored.
3. **The best case against** the recommendation, and why it loses.
4. **What would flip it:** the facts to check before he commits.

Present it as numbered options, one marked (Recommended). His pick is recorded
at [[30-architecture-decision]] step 9, Record, or bought through [[26-purchase]]
step 6, He picks.

## Examples

- `/fusion decide Postgres vs ClickHouse for the event store`
- `/fusion decide SQLite vs Postgres for the side project, skip opus`
