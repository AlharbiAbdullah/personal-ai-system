# talk: from a request to an approvable spec

Talk turns what the human wants into scenarios and a change folder that a human can approve. It runs in two places:
- a **feat** change, right after `mise run change -- <slug> --lane feat`;
- the **constitution** (`mission.md`, `tech-stack.md`, `roadmap.md`), at setup or in a pivot on a `plan/` branch.

Talk writes specs only. No production code and no tests until the spec is approved.

## 1. Evidence before questions

Read before you ask. Never ask a question the repo already answers.
- `specs/mission.md`, `specs/tech-stack.md` (standing rules S-n, never-use) and `specs/roadmap.md`.
- The capabilities this change touches, in `specs/capabilities/`.
- A backlog file whose `roadmap:` names this slug. Starting scheduled work moves its content into `requirements.md` and deletes the file, on this branch.
- The code paths, the tests, recent `git log`, `project_memory/lessons.md` and the active ADRs in `project_memory/decisions/`.

Then state your understanding in 3 to 6 bullets before the first question.

When the sources are thin, as in a brand-new project, open with one free-text prompt:

> Tell me about it: who is it for, what hurts today, what does done look like?

Translate the answer into the checklist below. Then ask decision rounds for what is still open.

## 2. Decision rounds

- At most 3 questions per round, 4 in a feat change's first round. Resolve upstream questions first: who and why, then behaviour and interfaces, then data and errors, then tests.
- Each question offers 2 or 3 options. Exactly one is marked **(Recommended)**, with a one-clause reason.
- In Claude Code, use the AskUserQuestion tool. Elsewhere, ask numbered options in chat. Then stop and wait.
- A feat change covers four topics, one question each in the first round:
  - **Scope:** what is in and what is out.
  - **Decisions:** the choices that shape the behaviour, each with the option rejected.
  - **Context:** constraints, patterns to follow, rules that apply.
  - **Rollback:** if this goes wrong after merge, how is it undone? The options are `revert: <why>`, `flag: <ENV_NAME>` and `one-way: <what>`. Recommend `flag:` when the Distribution in `specs/tech-stack.md` is `service` and a file the change touches is trunk, since spec-check refuses `revert:` there. Recommend `one-way:` when the change migrates data, publishes an interface, sends a message or deletes data. Otherwise recommend `revert:`.
- Cap: 4 rounds. Anything still open becomes `[NEEDS CLARIFICATION: <question>]` in the file where it belongs. Approve and merge refuse while one remains.
- In a run with no human to ask, write the markers directly.

## 3. The constitution checklist

The talk ends only when every item is filled or marked `[NEEDS CLARIFICATION: ...]`. Fill each item from the sources first, then ask only about the gaps.

| File | Items |
|---|---|
| `specs/mission.md` | who it is for, the problem, why now, scope in and out, the success signal, the one-liner |
| `specs/tech-stack.md` | runtime, distribution, standing rules S-n, the Trunk section (`- <glob>: <why>` per entry, or empty) |
| `specs/roadmap.md` | at least 2 phases of feature-sized items, the first one concrete |

- An entrypoint that crashes today becomes a `[gap: <roadmap-slug>]` scenario, and that slug becomes the Phase 1 roadmap item.
- The Trunk section names the paths every run goes through: the entrypoint, shared settings, the schema. Setup's probe proposes candidates, each with its why. Ask one question: keep all (Recommended), edit, or start empty. A trunk path's diff is read at merge, and the rest is skimmed ([`specs/README.md#formats`](../../../specs/README.md#formats)).
- Never copy personal paths, private note links or secret values into specs. The leak rules block them anyway.

## 4. Write the feature spec

Formats and size caps are in [`specs/README.md#formats`](../../../specs/README.md#formats). Follow them exactly.

**Capabilities first.** Add or edit scenarios in `specs/capabilities/<cap>.md`:
- one SHALL sentence per requirement; GIVEN, WHEN and THEN bullets per scenario;
- IDs are `<cap>.<slug>`, unique, and never reused;
- literal inputs and outputs, no design prose;
- WHEN runs the real entrypoint wherever a user would.

A change that fixes a `[gap]` rewrites that scenario as an exact contract and drops the tag.

**Then the change folder** that `mise run change` created:
- `requirements.md`. `title:` is a conventional commit subject that becomes the squash commit and the CHANGELOG line. `feat` adds, `change` alters, `fix` repairs, and a `!` after the type marks a removal. Then Why, Scope (In, Out), Decisions (each with what was rejected and why), Context (file pointers, the standing rules that apply) and Rollback: exactly one line, the answer to round 1's fourth question.
- `plan.md`. Groups ordered by dependency, each small enough for one red-green pass: its scenario IDs plus the files they touch. Mark `risk: high` on anything hard to undo: data migrations, security, money, public interfaces. A group whose files match an entry of `## Trunk` in `specs/tech-stack.md` is `risk: high` too, and spec-check refuses it otherwise (I17). Keep trunk edits to the seam: new behaviour goes into leaf modules, and the trunk file gets the one call that reaches them. Mark `parallel: yes` only for groups with disjoint files.
- `validation.md`:
  - **Review focus:** up to 5 inputs the spec never named. Think empty, missing, malformed, huge, negative, an empty env value. Each row points at a scenario ID or says `none: <reason>`.
  - **Run it:** only what tests cannot reach, such as a real server. Merge runs each row.
  - **Proof:** what a human looks at instead of reading leaf code, at most 6 rows of `| <scenario ID or G<n>> | <kind> | <what it shows> |`. One row per case, in the one kind that fits what the case changes:
    - `run`: what a command prints or exits with (`run --before` when the old output matters);
    - `screenshot`: a page's look; `video`: a flow across clicks or pages;
    - `terminal`: an interactive terminal session; `http`: an API response;
    - `log`: a background job or a service; `attach`: anything captured another way.

    Never every kind: a second row for the same case fails. A case whose tests show enough gets no row, since the test proof is automatic. In a repo with a UI, a change whose look or flow changes gets a screenshot, video or terminal row.
  - **Human checks:** at most 3, and only for judgment a test cannot make, such as whether an error message reads clearly.

**A `flag:` change** puts its row into `.env.example`, `# <ENV_NAME> | flag | bool | no | 0 | <what it turns on>`; approve lints it there, and the first compile commit carries it. The scenarios for the new behaviour say `GIVEN <ENV_NAME>=1`. At least one scenario tagged `[flag-off: <ENV_NAME>]` pins the old behaviour with the flag off: it is the control that must not change. Plan one seam in the trunk that reads the flag, with the new behaviour in leaf modules the seam calls. **A `one-way:` change** puts the one-way work in a `risk: high` group.

**Also on this branch:** a new runtime dependency, service or standing rule edits `specs/tech-stack.md`. A choice later changes must respect gets one ADR in `project_memory/decisions/`. Out-of-scope ideas go to `mise run backlog -- <topic>`, never into the roadmap.

## 5. Check the spec before handing it over

- **Under-specified?** Could two people build incompatible things from it? Add the missing scenario.
- **Over-specified?** Does a scenario name a class, a library or an algorithm? Move that to Decisions or Context. Scenarios state behaviour.
- **Outcomes, not mechanisms.** "exits 2 with one `error:` line", not "uses argparse".
- **Nothing deferred** that evidence can settle now. Compile must not have to guess.
- **Every Review focus row** maps to a scenario ID or a reason.
- **Size caps hold.** Split or cut. Never raise a cap.

## 6. Hand off

**A feat change:**
- Leave the spec uncommitted. `approve` lints it, stamps its hash and commits it.
- Run `mise run status`. It must say `ready for approve`. Fix whatever it lists.
- Show the human the scenario diff (`mise run status -- --change`) and the three files. Approving `validation.md` approves the test list and the proof list.
- Say: "run `! mise run approve`, then start a fresh context (`/clear`) before `/sdd compile`." Then stop.

**The constitution** (a `plan/` branch, no change folder): commit it with a `spec:` subject, run `mise run verify`, then `mise run status -- --merge`. Say: "run `! mise run merge`." Then stop.
