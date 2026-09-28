# replan: roadmap, backlog and process, between changes

A replan changes what comes next, never what is already merged. It runs on its own `plan/` branch and ends at the human merge gate like any other lane.

## When

- `mise run status` reminds you: the answer to "still right?" was no, 5 or more backlog items are open, or 3 features merged since the last replan.
- A feature showed that the roadmap, a standing rule or the process itself is wrong.
- The human asks for a replan or a pivot.

## Precondition: a clean break

- No change is open. Merge or abandon it first. Both are human gates.
- The tree is clean and the default branch is up to date.
- Then run `mise run change -- <date>-replan --lane plan`. A pivot uses `<date>-pivot`.

## Inputs

- `specs/roadmap.md`: done items, what is next, the Gates section.
- Open backlog items in `specs/backlog/`, including deferred validate findings.
- Lessons added since the last replan: `git log -p -- project_memory/lessons.md`.
- Open `[gap: <slug>]` scenarios in `specs/capabilities/`.
- `mise run status`.

Summarize them in 3 to 6 bullets. Then ask decision rounds by the rules in `talk.md`: at most 3 questions per round, each with one Recommended option.

## What a replan may change

- **Roadmap.** Reorder, merge or split phases, and add items. Slugs are permanent: never rename or reuse one. A split keeps the old slug for the first part and gives the rest new slugs. A merge keeps one slug, and the reason for each dropped line goes in the commit body. Open questions that block a phase go under Gates.
- **Backlog.** Schedule an item: set `status: scheduled` and `roadmap: <slug>`, and add that slug to the roadmap. Drop an item: delete its file, with the reason in the commit body.
- **Standing rules.** Add or edit rules S-n in `specs/tech-stack.md`. Numbers are never reused.
- **A cross-cutting constraint**, such as accessibility or security. Write it once: a standing rule S-n here, and an "apply S-n" phase on the roadmap. The feat change that builds that phase adds one cross-cutting capability with its tests. Never edit every feature's spec.
- **The process.** When the loop itself hurt, fix it on this branch. That covers a lane threshold that is wrong, a template missing a field, or a gate that is too slow. Edit `specs/README.md` or the files of this skill. The next project-init run sees a customized file and asks before touching it.
- **ADRs.** A phase dropped for a reason worth keeping, or a new rule later changes must respect, gets one file in `project_memory/decisions/`.

## What a replan never does

- It writes no code and edits no tests or scenarios. Removing merged behaviour is scheduled as a later chg change.
- `specs/mission.md` changes only in a pivot (who, why, scope), or for a constraint that is a product promise. A pivot runs the constitution checklist in `talk.md`, rewrites the roadmap and re-triages every backlog item.

## Close

1. Commit with a `spec(replan): <what changed>` subject.
2. Run `mise run verify`, then `mise run status -- --merge`.
3. Hand over as step 4 of the Close in `validate.md` says. That is the command on the preview's last line, plus `--title` when the preview lands a parked `spec(backlog)` subject. Name the first item of the new roadmap, to start after the merge with `/sdd`. Then stop.
