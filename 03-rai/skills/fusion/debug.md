---
name: debug
description: >
  Panel debug. Each voice ranks root-cause hypotheses with the fastest test
  for each, then kills the others' weak ones in round 2. The coordinator
  converges on the most likely cause and the first test. USE WHEN /fusion
  debug, or a bug survived a first fix and wider eyes would help.
---

# /fusion debug

Debugging follows [[04-debugging]]. The panel is a tool inside it: it widens
the hypothesis list. It never replaces reproducing the bug yourself.

## The ask (`$RUN/ask.md`)

- The symptom: the exact error or wrong output, pasted.
- How to reproduce it, and how often it happens.
- What was tried and what each attempt showed.
- The suspect code paths (the voices can read them in `--cwd`).
- Facts already ruled out, so no voice re-proposes them.

## Rounds

- **Round 1:** ranked hypotheses, each with the fastest way to confirm or kill it.
- **Between the rounds:** run the cheapest tests that tell the top
  hypotheses apart. Each command, its output and the commit go under FACTS
  ESTABLISHED in `ask-r2.md`. The ledger is the hypothesis list. Skip round 2
  when the first test confirms the top hypothesis.
- **Round 2:** every hypothesis judged against the tests and the code; the
  ones the evidence rules out are killed, with the reason.

## Synthesis

1. The most likely cause, and the one test that confirms it. Rank by
   evidence, not votes: a hypothesis round 2 killed with a fact is out,
   whatever the head count.
2. The runners-up, in order, each with its test.
3. Hypotheses killed, one line each.
4. Then run the next test yourself. The panel's ranking is a guess until the
   test runs. The work goes on at [[04-debugging]] step 4, Diagnose.

## Examples

- `/fusion debug the coordinator alarm fires STALE after a clean run`
- `/fusion debug why openkit join hangs 30s on a fresh hub`
