<!-- validation.md: what gets checked beyond the tests. Review focus at most 5 rows, Proof at most 6, Human checks at most 3. Cap 60 lines. Proof: one row per case (a scenario ID or G<n>), in the one kind that shows it best: run (--before when the old output matters), log, http, screenshot, video, terminal or attach. A case whose tests show enough gets no row. -->
## Review focus   (implied inputs the spec never named; each -> a scenario, or "none: <reason>")
- {IMPLIED_INPUT} -> {SCENARIO_ID}
## Run it   (optional, feat only: what tests cannot reach, e.g. a real server; merge executes each row)
| command | exit | stdout contains | stderr contains |
|---|---|---|---|
## Proof   (what a human looks at instead of reading leaf code; test proof is automatic; mise run proof captures each row, merge checks it)
| for | kind | shows |
|---|---|---|
## Human checks   (<=3; merge asks with a TTY, or records your --attest)
- {HUMAN_CHECK}
