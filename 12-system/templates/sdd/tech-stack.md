<!-- tech-stack.md: runtime, tooling, distribution, standing rules, never-use, environment, trunk. Living; edit it on the branch that adds, removes or swaps a runtime dep or tool (I11). No line cap. -->
# Tech stack: {NAME}

## Runtime
- Language: {LANGUAGE_AND_VERSION}
- Dependencies: {RUNTIME_DEPENDENCIES}

## Tooling
- {TOOL}: {WHAT_IT_OWNS}

## Distribution
{PYPI_OR_GIT_OR_SERVICE_OR_NONE}

## Standing rules
- S-1: {RULE}

## Never use
- {THING}: {REASON}

## Environment
The typed contract is `.env.example` (NAME | kind | type | required | default | notes). An empty value means unset, so the default applies.

## Trunk
<!-- one entry per line, - <glob>: <why>. Globs are gitignore-style from the repo root (** crosses folders). A path no entry matches is leaf, and an empty section is valid. Adding an entry is free; removing or changing one needs merge --gate-change. Replace the placeholder line: spec-check fails it. -->
- {GLOB}: {WHY_IT_IS_TRUNK}
