<!-- capability: what is true now for one area, as scenarios with stable IDs. Living; no design prose. Cap 300 lines, split beyond. -->
# Capability: config

## Requirement: No crash on a bad env knob
The CLI SHALL treat an empty TIPCALC_DEFAULT_PERCENT as unset and answer a non-numeric one with exit code 2, never a Python traceback.

### Scenario: config.percent-empty
- GIVEN TIPCALC_DEFAULT_PERCENT is set to an empty string
- WHEN the user runs `tipcalc 100`
- THEN stdout is `tip: 15.0` and the exit code is 0

### Scenario: config.percent-invalid
- GIVEN TIPCALC_DEFAULT_PERCENT is `abc`
- WHEN the user runs `tipcalc 100`
- THEN stderr holds one `error:` line naming TIPCALC_DEFAULT_PERCENT and no traceback, and the exit code is 2
