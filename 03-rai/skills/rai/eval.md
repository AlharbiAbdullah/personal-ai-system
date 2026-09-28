---
name: eval
description: >
  Memory v3 QUALITY certifier — sanity certifies function (fresh output), eval
  certifies quality (RIGHT output). Six judged/deterministic sections + /recall
  smokes over a 100-question golden set. MANUAL ONLY: John triggers every
  run; never scheduled, never wired into the coordinator. USE WHEN John says
  "/rai eval", "run the eval", "how good is memory", "eval the brain".
allowed-tools: Bash, Read, Edit
---

# /rai eval — Memory Quality Certifier

Decisions: `.agent/decisions.md` (2026-07-03). The eval READS everything and writes ONLY
`semantic-memory/eval/` (reports, history, partials). It never mutates stores, preferences,
or config. Judge = Claude Opus at xhigh effort. Findings are a fix backlog for John —
nothing auto-applies; flagged preferences are demoted only by John.

## Sections

| id | measures | method |
|----|----------|--------|
| a | retrieval: 80 static golden rows + ~20 RUN-TIME freshness probes (last 48h daily logs) | deterministic hit@k |
| b | per-prompt injection relevance (20 real prompts replayed) | judged |
| c | identity adherence (30 outputs: banned-word/em-dash/emoji/Arabic lint + 5 tone) | lint + judged |
| d | daily-bullet fidelity (10 bullet-vs-turn pairs) | judged |
| e | distill fidelity (5 archived sessions vs their rai-semantic rows) | judged |
| f | self-evolve precision (all ACTIVE + 20 probation) — FLAGS ONLY | judged |
| smokes | 5 golden questions through a real `/recall` end-to-end | judged |

## Run protocol (a full run = ALL sections; there is no quick mode)

Pick `RUN=YYYY-MM-DDx`. Run each section as its OWN Bash invocation (sections write
partials to `reports/.partial/$RUN/` — a timeout kills one section, not the run; re-run
only the missing section). Long judged sections (d, e, smokes) may go in background with
polling. Everything runs under py-chroma.sh:

```bash
W=~/helm/03-rai/semantic-memory/scripts/py-chroma.sh
E=~/helm/03-rai/skills/rai/scripts/eval.py
$W $E --run-id $RUN --section a
$W $E --run-id $RUN --section b
$W $E --run-id $RUN --section c
$W $E --run-id $RUN --section d
$W $E --run-id $RUN --section e
$W $E --run-id $RUN --section f
$W $E --run-id $RUN --section smokes
$W $E --run-id $RUN --section assemble          # add --baseline on the first-ever run
```

Then Read the report at `semantic-memory/eval/reports/` (timestamped) and present it:
lead with per-section scores + delta vs baseline, then stale golden rows (offer to
refresh), proposed golden candidates (John accepts/rejects now), and the fix backlog.

## Golden set maintenance

- `semantic-memory/eval/golden.jsonl` = 80 static rows + 1 `freshness-spec` row
  (freshness probes are sampled at RUN TIME so they can never go stale).
- Rows the run flags as `stale` (expected fact superseded/archived): rewrite or retire
  them with John at the next run — they are excluded from the score, never silently.
- Accepted candidate proposals become new rows: `{id, section, question, expected:
  {content_substrings|doc_id|session_id}, tier: semantic|daily|episodic, kind:
  positive|negative, source, added, status: active}`.
- `--draft-golden` regenerates the stratified mining dump (`golden-draft-input.json`)
  when authoring a large refresh.

## History

`semantic-memory/eval/history.jsonl` — one line per assembled run. The baseline is the
line with `"baseline": true`. Trends across runs answer "is memory getting better?".
