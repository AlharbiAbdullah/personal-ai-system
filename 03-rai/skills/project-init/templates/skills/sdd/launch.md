# launch: the whole feature, then the flag comes off

Each change passed its own review at merge. Launch reviews a roadmap item as one feature: every change that built it, read together. Then the human uses it end to end, and the flag comes off. Launch never merges.

## When

- `mise run status` on the default branch lists the merged roadmap items not launched yet, those with a live flag first, and names the next `/sdd launch <slug>`.
- Run it on the default branch with no change open. The audit writes only the launch file. Each fix it needs is a lane of its own, one at a time.

## 1. Collect

- **The item:** `- [x] <slug>: ...` in `specs/roadmap.md`, without `(launched ...)`. An item not ticked has not merged yet: stop.
- **Its change folders:** `grep -lE '^roadmap: "?<slug>"?' specs/changes/*/requirements.md`. The Rollback line of each says whether a flag guards it: `flag: <ENV_NAME>`, with its row in `.env.example`.
- **Its squash commits:** `git log --first-parent --format='%h %as %s' <default> -E --grep='^Branch: [a-z]+/<slug>$' --grep='^Change: specs/changes/<folder>$'`, one `--grep` per change folder. A fast lane on the roadmap slug lands as `Branch: chg/<slug>` or `fix/<slug>`.
- **The audited diff:** the oldest of those commits is `<first>`. The files are what the commits touched (`git show --name-only --format= <sha>` for each). The diff is `git diff <first>^ <default> -- <files>`, so later fixes to the same files count too.
- **The launch file:** `specs/backlog/<date>-launch-<slug>.md`. Merge wrote it for a `flag:` change. With none, run `mise run backlog -- launch-<slug>`.

## 2. Lenses

**Inputs for every lens:** the roadmap line and `specs/mission.md`, each change's `requirements.md` and `validation.md`, the scenarios the squash bodies name (`Scenarios added:`, `modified:`), the audited diff, the tests, and each change's `proof/<date>-<slug>/README.md`.

**How to run them.** In Claude Code, run each lens as its own subagent with the same inputs, told only its lens. In other harnesses, run them one after another. Each lens reports findings as `file:line`, what is wrong, and the evidence.

1. **Performance:** hot paths, N+1 queries, unbounded reads, startup cost.
2. **Security:** which input is trusted, secrets, injection, what files and hosts the code can reach.
3. **Conformance:** the feature as a whole against its scenarios, the mission and the roadmap wording, not one change at a time.
4. **Simplicity:** dead code, duplicate helpers, names, and the leftovers of work done in broad strokes.

## 3. Every finding gets one outcome

1. **Fix now:** a lane of its own, by the classifier in `SKILL.md`: `fix` when the code breaks a scenario, `chg` when behaviour moves, `refactor` when the tests stay as they are. Start one at a time, run it to its handover, and stop: the human merges it. Then `/sdd launch <slug>` again resumes at the next open finding.
2. **Later:** `mise run backlog -- <topic>`.
3. **Dismissed:** `Dismissed: <file:line or finding>: <reason>`.

Write each finding with its outcome under `## Findings` in the launch file, and a lane's merge as `merged` beside it. On the default branch the file stays uncommitted: `mise run change` takes a backlog file along, new or edited. On a lane branch, commit it alone first, as the backlog row of `SKILL.md` says.

## 4. The launch checklist

Write `## Launch checklist` into the launch file, for the human. Taste is theirs:

```markdown
## Launch checklist   (tick each line; write what felt wrong under it)
- [ ] Use <slug> end to end as a user would, with <ENV_NAME>=1 set where a flag guards it.
- [ ] Open each change's proof: proof/<date>-<slug>/README.md, or .agent/proof/<date>-<slug>.html where validate left it.
- [ ] Read each finding above and its outcome.
- [ ] Nothing felt wrong, or each thing that did has a line below with its outcome.
```

What the human lists gets an outcome the same way. Then stop, and wait for the human's ticks.

## 5. The launch lane

When every finding has its outcome and every checklist line is ticked, open the last change of the launch. Its slug is `launch-<slug>`, and its merge marks the item launched.

- **With a flag:** `mise run change -- launch-<slug> --lane chg`. One commit, as the chg recipe in `SKILL.md` says: the scenarios of the new behaviour drop `GIVEN <ENV_NAME>=1` and their tests stop setting it; the seam's flag check, the `.env.example` row and the `[flag-off: <ENV_NAME>]` scenarios go, with their tests. Trailers: `Spec: <the scenarios that changed>`, `Spec-Removed: <the flag-off IDs>`. It stays chg whatever its scenario count: it removes the flag's scaffolding and turns on behaviour already specified and proven, so Q7 does not apply (`specs/README.md#lanes`).
- **Without a flag:** `mise run change -- launch-<slug> --lane chore`, and one commit `chore(launch): <slug>`.

The same commit deletes the launch file: `git rm -f` when it is tracked (it may carry edits from the default branch), `rm` when it never was (then the chore commit needs `--allow-empty`). Its body holds the launch record: the audited range, each finding with its outcome, and the checklist as the human left it. The squash keeps the body of the commit its subject comes from, so the record lands on the default branch.

Then follow `validate.md` for the lane. Its preview's `close` step says `roadmap marked <slug> launched`. Hand over with its closing line: merge appends ` (launched <date>)` to the item, and `mise run status` stops listing it.

Then stop.
