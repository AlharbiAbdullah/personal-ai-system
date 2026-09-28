<!-- plan.md: task groups for this change, numbered G1, G2 and on. A group is done when every ID in it has a passing test, so no checkboxes; risk: high pauses compile after the group. Cap 100 lines. -->
## G1 usage errors | cli.no-args cli.help cli.bad-amount cli.negative-amount | risk: low | parallel: no
Files: src/tipcalc/__init__.py, tests/test_cli.py
## G2 env knob | config.percent-empty config.percent-invalid | risk: low | parallel: no
Files: src/tipcalc/config.py (NEW), tests/test_config.py (NEW)
