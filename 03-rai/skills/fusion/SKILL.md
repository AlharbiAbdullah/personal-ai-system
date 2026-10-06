---
name: fusion
description: >
  Multi-model panel router on John's subscriptions, no pay-per-call API.
  Six voices, one per model, each a separate read-only session in its own tmux window:
  Gemini 3.1 Pro through agy, MiniMax M3 and GLM-5.3 through opencode, DeepSeek V4 Pro
  and GPT-6.1 Sol at xhigh effort through pi, and Opus 5.5 at max effort through Claude
  Code. The voices answer alone, then check each other's points on evidence; the
  session that triggered /fusion coordinates and writes one answer. Sub-skills: review, brainstorm,
  plan, debug, decide, ask, write-english, write-arabic. USE WHEN the user types
  /fusion, asks for an adversarial or external review, a second opinion, "ask
  gemini" (or minimax, glm, deepseek, sol), "panel this", "brainstorm with everyone",
  "let them all weigh in", a translation by other models, or a multi-model
  draft in English or Arabic. Never spawns Agent or Workflow subagents.
---

# /fusion

Six models on one problem. Six voices, each a separate session pairing one
harness with one model, answer the same brief. Then each one checks the
others' answers against the evidence. The session John triggered /fusion from is the
coordinator: it writes the brief, runs the rounds, checks the claims and gives
him one organized answer. From Claude Code that is Claude; from pi, pi does it.

## The panel

| Voice | Harness | Model | Effort | Paid by |
|-------|---------|-------|--------|---------|
| `gemini` | agy | Gemini 3.1 Pro | high | Google AI Pro |
| `minimax`, `glm` | opencode | MiniMax M3, GLM-5.3 | high | Ollama Pro |
| `deepseek` | pi | DeepSeek V4 Pro | high | Ollama Pro |
| `sol` | pi | GPT-6.1 Sol | xhigh | ChatGPT Plus |
| `opus` | Claude Code | Opus 5.5 | max | Claude Max |

`scripts/voices.conf` is the single source: change a model or effort there.
Each model runs once. The same model on a second harness is a resample, not
a new view, and it would count twice toward the majority. The models are
split across opencode and pi, so a broken harness costs two voices, not all.
Every voice runs read-only in the target directory: it reads files to check
claims, and cannot edit or run commands. opencode, pi and Claude Code get read
tools only, and agy an empty command allow list. Every harness also runs inside
`bwrap`. There the filesystem is read-only, the environment is cleared, and
his home folder, `/tmp`, his runtime folder and `/var/log` are empty. Only the target directory, the harness install and its own login come
back, so a voice can read nothing outside `--cwd`. Without `bwrap` a voice fails rather
than run unjailed. No voice sees his identity files, memory, global
`AGENTS.md`, skills, hooks or MCP tools. No voice's transcript reaches Rai's
capture. agy still loads the working folder's own `AGENTS.md`. Ollama Pro runs
3 requests at once, and the three Ollama voices fill those 3 slots together.
The `sol` voice runs on ChatGPT Plus through pi's Sign in with ChatGPT.

## Routing

| Ask | Rounds | Default voices (round 2 skips the coordinator's model) | Sub-skill |
|-----|--------|----------------|-----------|
| Review finished pipeline work, or any code, doc, plan or prose on request | 2 | all 6 | `review.md` |
| Explore a thought; collect every idea and angle | 2 | all 6 | `brainstorm.md` |
| Build a plan | 2 | all 6 | `plan.md` |
| Find a root cause | 2 | all 6 | `debug.md` |
| Pick between options | 2 | all 6 | `decide.md` |
| A quick second opinion, a fact, a translation | 1 | `gemini` | `ask.md` |
| Draft English prose | 2 | all 6 | `write-english.md` |
| Draft Arabic prose | 2 | all 6 | `write-arabic.md` |

Read the chosen file and follow it. John can name a subset at any time
("just gemini and opus", "skip opus", "only the pi voices").

## A run

`P=~/helm/03-rai/skills/fusion/scripts/panel.sh`

1. **Frame.** State the ask in one sentence and name the sub-skill. Ask him
   first if the ask is unclear: a run is not cheap.
2. **Cost.** Before the first round, say what the run spends (below).
3. **New run.** `RUN=$($P new <mode> --cwd <dir>)`. From a coordinator that
   is not Claude Code, add `--coordinator <voice>` for the voice on your own
   model, or `--coordinator none` when no voice is. `<dir>` is where the voices
   run and read: the repo under review, or the folder the ask is about. Leave
   `--cwd` out when the ask has no folder: the voices then get an empty one.
   Never his home folder: the voices would read everything in it.
4. **The ask.** Write `$RUN/ask.md`: the exact question, then everything the
   voices need. Paste real content (the diff, the error, the draft, the
   decisions so far, what was tried). Point to files they can read in `<dir>`.
   They cannot see this session.
5. **Round 1.** `$P start $RUN 1`, then `$P wait $RUN 1` until it exits 0.
   In Claude Code, run the wait in the background with a long limit, such as
   `$P wait $RUN 1 3600`, and you are called back when it ends. A voice that
   fails is skipped; the round never blocks on one. A call that fails fast is
   retried once on its own; agy retries any failure short of a timeout. One call may run up to `FUSION_TIMEOUT` (30 min),
   plus as long again waiting for an Ollama slot. `wait` covers one call by
   default, so call it again while it returns 3. To re-run a failed voice, use
   `$P start $RUN 1 <voice>`. It works while the rest of the round runs.
6. **Between the rounds.** Round 2 can only move on a fact no voice had. You
   are the one participant who can run commands, so bring the facts in:
   - Read round 1: it is the vote. `$P cites $RUN 1` checks that every file:line
     exists; a made-up citation dies here.
   - Run what settles claims. The sub-skill names it: the first test in debug,
     the flip-facts in decide, the cited code and quick tests in review.
   - Write `$RUN/ask-r2.md`. Round 2 gets it in place of `ask.md`. It holds
     the question and the ask's non-negotiables, quoted: criteria order,
     declined options, locked wording, the source to match. Then `# FACTS
     ESTABLISHED SINCE ROUND 1`, each with the command, its result and the
     commit or file it ran on. In brainstorm, add the coverage gaps.
   - Review, brainstorm, plan, debug and decide: write `$RUN/ledger.md`, every
     round-1 point once, numbered. One line per item:
     `L7 | gemini:3 sol:1 | open | <claim> | <evidence>`. The second field is
     who raised it, by round-1 item number. Status: `open`, `open!` (high
     stakes, checked by 3), `verified: <how>`, `dropped: <why>`. Show no
     recommendation in it: a draft answer would anchor the voices. The write
     modes and ask take no ledger: round 2 reads the drafts.
   - Skip round 2 when the facts settled it, and say so. Debug and decide
     name their cases.
7. **Round 2.** Run `$P start $RUN 2` and wait the same way. Round 2 skips
   your own model, set by `--coordinator` on `new` (default `opus`). Your synthesis
   is already an Opus pass, so a second one is the most correlated check on
   the panel. Name voices to change that (`$P start $RUN 2 opus`). With a
   ledger, each voice gets its own round-1 answer and where each of its points
   went. It also gets the ledger with its sources stripped, and an assignment.
   Each open item goes to 2 voices that did not raise it, an `open!` item to 3.
   A voice that failed round 1 still checks. Without a ledger, each voice gets its own
   answer and the others under fixed labels (Voice A, B and on). Either way it
   replies in tagged lines (`references/round2.md`), keeps its position unless
   it names the fact that changed it (`CHANGED: old -> new, because ...`), and
   ends with `CHECKED:`.
8. **Read.** `$P digest $RUN` first: the reply lines by item, the new points,
   assigned items a voice never named, answers with no reply line, and items
   nobody could check. Open a full answer with `$P show $RUN 2 <voice>` only
   where the digest shows a split or an unparsed answer. Every line read stays
   in your context.
9. **Merge.** Follow the sub-skill's synthesis. You own the result: the panel
   is advisory. Verify by consequence: every claim the answer rests on, every
   lone claim that would change it, every dispute that would remove a finding.
   An item nobody could check, you verify yourself. Write `$RUN/synthesis.md`:
   the answer exactly as you gave it, then every item with its L-number and
   disposition. With a ledger, `$P check $RUN` then confirms the chain: every
   numbered round-1 item is in the ledger, every ledger item is in the
   synthesis.
10. **Close.** `$P close $RUN` stops any voice still running, and warns when
   `synthesis.md` is missing. Answers stay in `$RUN` for the record. The work
   goes on in the workflow the sub-skill names at its end.

He can watch any round live: `tmux attach -t fusion-<run name>-r<round>`.

## The coordinator's answer

- Two layers. In the chat: the answer, the reasons it rests on, the one
  check before acting, and the path to `synthesis.md`. In the file: everything.
- Lead with the answer or recommendation, never a roll call.
- Round 1 is the vote: six independent answers, one per model. Consensus and
  splits are counted there ("four voices held X; gemini and opus disputed it").
- Round 2 is the check. Count a dispute or added evidence only when it
  carries evidence. Count a new point. Count a changed position only when it
  names the fact that moved it. A change with no named fact is ignored, since
  that is the voice following the majority.
- A claim is weighed by its evidence, never by its head count. A lone claim
  with proof beats a majority without it.
- Standouts: the sharpest point only one voice raised.
- Your own call last, including where you overrule the majority, and why.
  When your call sides with your own model's voice against the majority, cite
  evidence that did not come from that voice.
- Name any voice that failed.

## Cost

Round 1 costs 6 calls. Gemini takes 1 from Google AI Pro. The Ollama
voices take 3 from the monthly credit. Sol takes 1 xhigh call from the
ChatGPT Plus weekly allowance. Opus takes 1 max-effort call from
the Claude Max quota. Round 2 costs 5 more, without opus: a two-round run is
11 calls, 1 of them Opus max. Opus max is the scarce part: drop `opus` from
round 1 too when quota is tight.

## Rules

- Never use the Agent or Workflow tools. The voices are tmux sessions.
- Work content (`04-work/`) goes to the panel only on John's explicit go.
  Confidentiality comes first there.
- When a harness is missing on this machine, run without its voices and say so.

## Examples

- `/fusion review` after `/compile` validate: the full panel on the branch.
- `/fusion brainstorm what could a local-first recipe app become?`
- `/fusion decide Postgres vs ClickHouse for the event store, skip opus`
- `/fusion ask gemini: is this claim right?` or `/fusion ask translate this to Arabic`
- `/fusion write-arabic the about-page opener`

## Files

```
fusion/
├── SKILL.md                 # this router
├── review.md  brainstorm.md  plan.md  debug.md  decide.md
├── ask.md  write-english.md  write-arabic.md
├── scripts/
│   ├── panel.sh             # new, start, wait, status, show, cites, digest, check, close
│   ├── ledger.sh            # ledger round 2, cites, digest, check (sourced by panel.sh)
│   ├── voice.sh             # one voice, one round, jailed (launched by panel.sh)
│   ├── voices.conf          # the panel: voice, harness, model, effort
│   └── test_panel.sh        # offline tests: mock harnesses, no model calls
└── references/
    ├── panel.md             # round-1 brief: the voice's role, shaped by mode
    ├── round2.md            # round-2 brief: tagged reply lines, by mode
    ├── review-code.md       # code review rules
    ├── review-prose.md      # English prose review rules
    ├── review-prose-ar.md   # Arabic prose and translation review rules
    ├── write-english.md     # English writing rules
    ├── write-arabic.md      # Arabic writing rules
    ├── translate-ar.md      # English to Arabic translation rules
    ├── translate-en.md      # Arabic to English translation rules
    └── arabic-corpus.md     # the Lumen corpus, round 1 only (INCLUDE-R1)
```
