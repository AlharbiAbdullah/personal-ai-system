<!-- project-init:quickstart:begin (tool-owned: the next project-init run replaces this region and shows the diff) -->
## Quickstart

```sh
git clone {CLONE_URL} && cd {CLONE_DIR}   # {IF_REMOTE}
curl https://mise.run | sh      # once per machine
mise install                    # tools, dependencies, git hooks
mise run verify                 # green = ready
{START_EXAMPLE}           # {START_EXPECTED}
```

How changes are made: `specs/README.md`. Agents start at `AGENTS.md`.
At merge a human reads the trunk diff and skims the rest against the change's `proof/` folder.
<!-- project-init:quickstart:end -->
