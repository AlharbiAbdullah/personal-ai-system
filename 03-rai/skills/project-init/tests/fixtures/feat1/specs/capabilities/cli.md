<!-- capability: what is true now for one area, as scenarios with stable IDs. Living; no design prose. Cap 300 lines, split beyond. -->
# Capability: cli

## Requirement: Tip output
The CLI SHALL print the tip for the bill given as the first argument.

### Scenario: cli.tip-default
- GIVEN TIPCALC_DEFAULT_PERCENT is unset
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0

## Requirement: Usage help
The CLI SHALL print its usage when run with `--help`.

### Scenario: cli.help
- WHEN the user runs `tipcalc --help`
- THEN stdout starts with `usage: tipcalc`, stderr is empty and the exit code is 0

## Requirement: No crash on bad input
The CLI SHALL answer bad input with exit code 2 and one `error:` line on stderr, never a Python traceback.

### Scenario: cli.no-args
- WHEN the user runs `tipcalc` with no arguments
- THEN stderr holds one `error:` line and no traceback, and the exit code is 2

### Scenario: cli.bad-amount
- WHEN the user runs `tipcalc abc`
- THEN stderr holds one `error:` line and no traceback, and the exit code is 2

### Scenario: cli.negative-amount
- WHEN the user runs `tipcalc -5`
- THEN stderr holds one `error:` line and no traceback, and the exit code is 2
