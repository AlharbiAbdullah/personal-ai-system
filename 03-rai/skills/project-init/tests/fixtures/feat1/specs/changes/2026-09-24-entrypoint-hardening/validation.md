<!-- validation.md: what gets checked beyond the tests. Review focus at most 5 rows, Human checks at most 3. Cap 60 lines. -->
## Review focus   (implied inputs the spec never named; each -> a scenario, or "none: <reason>")
- no args -> cli.no-args
- --help -> cli.help
- non-numeric bill -> cli.bad-amount
- negative bill -> cli.negative-amount
- env knob empty / non-numeric -> config.percent-empty, config.percent-invalid
## Run it   (optional, feat only: what tests cannot reach, e.g. a real server; merge executes each row)
| command | exit | stdout contains | stderr contains |
|---|---|---|---|
## Human checks   (<=3; merge asks with a TTY, or records your --attest)
- The error messages read clearly to a first-time user.
