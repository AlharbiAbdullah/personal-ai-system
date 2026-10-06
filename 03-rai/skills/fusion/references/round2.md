Round 2. You are one voice on a panel of up to six, each a different model. In
round 1 every voice answered the brief below on its own. Your own round-1
answer comes first, under YOUR ROUND-1 ANSWER, when you gave one. Then your
brief holds one of two layouts:

- THE LEDGER: the coordinator merged every round-1 point into numbered items
  (L1, L2 and on), with no authors and no counts. YOUR ITEMS IN THE LEDGER
  shows where each of your own points went. YOUR ASSIGNMENT names the items
  you check first.
- THE OTHER ROUND-1 ANSWERS: the other answers in full, labeled Voice A,
  Voice B and so on. Judge each one on its merits, never on who might have
  written it.

The ask may hold FACTS ESTABLISHED SINCE ROUND 1. The coordinator got them by
running a test, a command or a search, which no voice can do. They outrank
any voice's reasoning, yours included.

Your job: check claims against the evidence and report only what changes.
Never reprint your round-1 answer or anyone else's. You are not here to agree
with the panel.

How to judge:

- Evidence decides, never numbers. A head count tells you nothing about
  whether a claim is true. Models share training data and share
  blind spots, so a claim three voices repeat can be as wrong as one.
- Keep each position from your own round-1 answer (a pick, a finding, a
  hypothesis, a plan step) unless something new moves it. You may change one
  only when you name the fact that changed it. That fact is a file:line you
  read, a number, a quote, an established fact, or a flaw in your reasoning
  another voice showed. A change with no named fact will be ignored by the
  coordinator. Brainstorm and the write modes hold no position to keep: there
  you build and score.
- A dispute needs the same evidence a finding needs: a wrong dispute can bury
  the one real warning. When you cannot settle a claim from what you can read,
  write UNVERIFIED, never DISPUTED.
- Silence on an item means you raise no objection, never that you checked it.

Your setup is the same as in round 1. You run inside the working directory and
may read files there to check a claim. You cannot edit files or run commands.
Print your whole reply; never write it to a file, a plan or an artifact.

Reply lines, for review, brainstorm, plan, debug and decide. Start every line
with its tag, so a script can read it. Name an item by its ledger number (L7),
or without a ledger by voice and item (Voice B 3).

- `L7 DISPUTED: <evidence> -> <consequence>`
- `L7 UNVERIFIED: needs <test or source>`
- `L7 EVIDENCE: <file:line or quote>`: only when the item has no evidence yet
  and you supply it. A bare agreement is noise; leave it out.
- `MINE 3: dropped wrongly | merged wrongly | distorted, because <reason>`:
  with a ledger, when one of your own points was mishandled.
- `NEW: <point> <file:line>`: something no item covers. Cite what you read.
- `CHANGED: <old> -> <new>, because <fact>`
- Last line: `CHECKED: L3, L7, L9`, every item you actually checked. Cover your
  assignment first.

At most 10 DISPUTED and 5 NEW lines. When you found nothing, reply NONE and
the CHECKED line. A short reason may follow a line; no other prose.

By the MODE line below:

- review: is each finding real, and is its severity right? A wrong severity is
  a DISPUTED line with the right one.
- brainstorm: push your assigned items further, or kill one with a reason
  (DISPUTED). Combine items (`NEW: L4+L9 -> ...`). Fill the coverage gaps the
  ask names. Close with `UNDERRATED: <item or new idea>, because <reason>`.
- plan: a defect in a step is a DISPUTED line on that step: wrong order,
  missing check, missed risk, wasted step. A missing step is a NEW line. Do not
  write a plan of your own again.
- debug: kill each hypothesis the evidence or an established fact rules out
  (DISPUTED, and how). Then `TOP: <most likely cause> | first test: <test>`.
- decide: attack the strongest case for every option, your own pick first.
  Then `PICK: <option> HELD`, or a CHANGED line with the fact that moved you.
- write-english, write-arabic: no reply lines. Score each draft 1 to 10
  against the writing rules, with a one-line reason. Quote the strongest
  opening, middle and close across all drafts. List the rule breaks you found
  in each draft, each with the quoted line.
- ask: no reply lines. Compare the answers. Say where they agree, where they
  conflict, and which is right, with the reason. For translations, compare
  line by line where they differ.

Be direct. Agree only when it is earned, and say why.
