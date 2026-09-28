<!-- capability: what is true now for one area, as scenarios with stable IDs. Living; no design prose. Cap 300 lines, split beyond. -->
# Capability: cli

## Requirement: Tip output
The CLI SHALL print the tip for the bill given as the first argument.

### Scenario: cli.tip-default
- GIVEN TIPCALC_DEFAULT_PERCENT is unset
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0

## Requirement: No crash on bad input
The CLI SHALL never end with a Python traceback.

### Scenario: cli.no-args [gap: entrypoint-hardening]
- WHEN the user runs `tipcalc` with no arguments
- THEN stderr holds no traceback and the exit code is not 0

### Scenario: cli.help [gap: entrypoint-hardening]
- WHEN the user runs `tipcalc --help`
- THEN stderr holds no traceback and the exit code is 0

### Scenario: cli.bad-amount [gap: entrypoint-hardening]
- WHEN the user runs `tipcalc abc`
- THEN stderr holds no traceback and the exit code is not 0
