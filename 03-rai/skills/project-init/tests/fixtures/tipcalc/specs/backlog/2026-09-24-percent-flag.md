---
status: scheduled                               # open | scheduled
roadmap: percent-flag                           # the roadmap slug, once scheduled
---
<!-- backlog item: an idea, spike finding or abandoned change that is not being built now. Deleted when its work starts or a replan drops it. No line cap. -->
# `--percent` overrides the default

## What
A `--percent` flag that sets the tip percent for one run.

## Why
Today the percent comes only from TIPCALC_DEFAULT_PERCENT, which is clumsy for a one-off tip.

## Notes
Scheduled as roadmap Phase 2. Its open question is under Gates in `specs/roadmap.md`: when both are set, does `--percent` win over TIPCALC_DEFAULT_PERCENT?
