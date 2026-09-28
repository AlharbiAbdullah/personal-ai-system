<!-- capability: what is true now for one area, as scenarios with stable IDs. Living; no design prose. Cap 300 lines, split beyond. -->
# Capability: config

## Requirement: No crash on a bad env knob
The CLI SHALL never end with a Python traceback because of the value of TIPCALC_DEFAULT_PERCENT.

### Scenario: config.percent-empty [gap: entrypoint-hardening]
- GIVEN TIPCALC_DEFAULT_PERCENT is set to an empty string
- WHEN the user runs `tipcalc 100`
- THEN stderr holds no traceback

### Scenario: config.percent-invalid [gap: entrypoint-hardening]
- GIVEN TIPCALC_DEFAULT_PERCENT is `abc`
- WHEN the user runs `tipcalc 100`
- THEN stderr holds no traceback and the exit code is not 0
