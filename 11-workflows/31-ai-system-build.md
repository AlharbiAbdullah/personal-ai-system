# AI System Build

**Use when:** building or changing an AI feature or product: a document chat, an agent, an MCP or context server, an expert set. Choosing a model or a serving stack runs step 2 alone. Evaluating an AI system runs step 4 alone. Checking one before a demo or a release runs step 7.
**Not for:** a tool with no AI build behind it goes to 07 evaluate a technology. The pipeline that feeds the model goes to 27 data pipeline. A design choice that needs a paper goes to 30 architecture decision. Shipping into a sealed network goes to 29 air-gapped delivery. Rai's own skills, hooks and memory go to 24 changing Rai. The engagement around the build is 32 work engagement.
**Done when:** the model decision and its benchmark are written in the repo. The eval report exists, with arms reported apart, plus a sealed holdout when anything is claimed publicly. The prod-mimic checklist passed. The change merged through 21's G3 or launch, or through 02. A step 2 run alone ends at the logged decision; a step 4 run alone ends at the report and its baseline.

This is how John builds AI: the model decides only what a model must, on his own data, in the user's language, and evals come before claims. As a method workflow, it fills the slots of [[21-project-init]] in a repo with `.project.toml`, and runs through [[02-task]] elsewhere.

```d2
direction: right

frame: "1 Frame"
model: "2 Model and serving"
harness: "3 Harness, tools,\nretrieval"
evals: "4 Evals"
build: "5 Build\n21 or 02"
proof: "6 Prod-mimic proof"
gate: "7 Release or\ndemo gate"
modelq: "A model question" {shape: oval}
evalq: "An eval request" {shape: oval}

frame -> model -> harness -> evals -> build -> proof -> gate
modelq -> model: "runs alone" {style.stroke-dash: 3}
evalq -> evals: "runs alone" {style.stroke-dash: 3}
```

---

## Steps

### 1. Frame

- [ ] The product's decisions are AI-driven, not if-then rules. Fixed code supplies the facts: numbers from real compute, lookups from tables, charts from a deterministic engine.
- [ ] The model chooses and explains; code computes. Keep a model step that adds value. When its output breaks, validate it and fall back to a deterministic version, never bypass the model.
- [ ] Answers come from our data only, never from the model's own knowledge or the web. Write this rule once, in the shared base every agent loads.
- [ ] When the data holds no answer, the agent says so. A count over a retrieved sample says "at least N"; an exact count comes from a query.
- [ ] Each service owns its data, and no side route bypasses the retrieval path. Chat cites its sources, from the warehouse and the documents alike.
- [ ] The user's language first. Questions and answers work in it, and the output follows the language of the question. Technical terms stay in Latin script.
- [ ] RTL is a layout problem, not a translation problem. Translate queries only when a measured result on this corpus says it helps.
- [ ] Write the production profile before any model talk: the hardware, the network, the air gap, the users. Design for it, never for the laptop.
- [ ] Stub locally what cannot run on a dev machine, and keep the prod path intact. Model only what prod data holds.
- [ ] Keep one OpenAI-compatible code path from dev to prod, with one setting that picks the provider. The client's infrastructure is a deployment target, never a build dependency.
- [ ] Product defaults:
  - Chat is the entry point, never a wizard or a menu.
  - Every answer offers numbered follow-up questions.
  - Sources show in a full, spreadsheet-like table.
  - A result shows the chart and a short analysis, nothing more.
- [ ] Learn a harness before adapting it. Take the idea, never the whole stack. Get one operating system working before the others.
- [ ] Brainstorm features with no filter first. Then he runs a keep-or-kill pass over the list.
- [ ] Test a big idea on a panel of models with `/fusion → brainstorm` before building it.
- [ ] Where the frame goes: 21's talk writes it into `specs/tech-stack.md` in a repo with `.project.toml`. Elsewhere `/grill` writes it in 02's Define step.

> **Decision Point**: is the production profile known?
> - Yes: write it down, then step 2.
> - No: it is an open question for the owner. Inside an engagement, [[32-work-engagement]] step 1 names who answers it. Hold the model talk until then.

### 2. Model and serving

A model question starts here and ends at the logged decision.

- [ ] Shortlist from the newest model family only. Discount vendor scores: a score earned on the vendor's own scaffold may not hold on our harness.
- [ ] Hand the shortlist to the `researcher` agent. Inputs: the production profile, the tasks, the constraints. It returns candidates with size, license, tool-call reliability and a dated source each. It writes nothing. Rai re-checks every load-bearing claim it returns.
- [ ] Benchmark each candidate on the app's own tasks, split by task. Use real records, the production prompt, and prompts in each of the users' languages. An LLM judges.
- [ ] The output is a score table per task, with latency. A small sample shows direction, not size: ten rows is enough.
- [ ] Run the benchmark on our own harness, never the model's native scaffold. For an agent loop, measure prefill and tool-call reliability first. Decode speed matters least for one user.
- [ ] Hand the benchmark run to the `engineer` agent. Inputs: the candidates, ten real records, the production prompt, the judge. It builds a throwaway harness in a scratch folder and returns the table per task. It writes only in scratch. Rai re-checks the table against the raw outputs.
- [ ] Pick as few models as possible: one family behind one setting, with dev on the same family as prod. The product offers a cloud default and one local fallback.
- [ ] Take the cheapest model that is reliable at tool calling.
- [ ] A cloud-backed model is fine for a demo. Scale the serving only for a real scale problem: Ollama for dev and single users, vLLM for a multi-user server.
- [ ] Remove a model that is slow or returns nothing. Switch the default when a measured number says so.
- [ ] Keep a cloud escape hatch for the hardest tasks.
- [ ] His own machines hold no model weights. Benchmark local candidates on cloud tags or rented hardware. Local serving happens inside the client's network only.
- [ ] Write the decision in the repo: a status table (DECIDED, SHORTLIST, LEANING, REQUIRED), a ruled-out list with reasons, and a dated decision log. In a repo with `.project.toml`, a choice later changes must respect is an ADR in `project_memory/decisions/`.
- [ ] The landscape moves monthly. Re-check it before any default changes. A deep landscape study runs `/deep-research`, and its findings go into the repo's model doc.
- [ ] Second opinions come from `/fusion → ask`; the record from `/architecture → adr-writer`; fast facts from `/research → web-research`.
- [ ] Before a default model changes, benchmark on his own tasks, with real records and the production prompt. This binds every AI build, work or personal.
- [ ] A default model retires on measured behaviour on his tasks: latency, empty or broken output, or a failed demo question.
- [ ] For a client deployment, the canonical model registry lives in the product repo: the model decision doc plus the one config switch.

### 3. Harness, tools, retrieval

- [ ] Control flow is readable and auditable. Add an agent framework only when its explicit states make the flow easier to audit. Otherwise keep the layer small enough to read in an afternoon.
- [ ] Where `/ai → agent-design` or `/ai → rag-design` suggests a default framework or a cloud embedder, the rules in this step win.
- [ ] Forking a harness: learn it first, fork a minimal one, and keep a ledger of every change to an upstream file. Keep the upstream license and attribution notices; drop only its telemetry.
- [ ] Agents start in ask mode and act only after an explicit switch to act mode. Destructive actions get an extra gate. Capability grows in stages behind tiers, never capped.
- [ ] No agent works in the background. Awareness loads into context at prompt time, the way a `CLAUDE.md` does.
- [ ] Product operations are skills the agent can call from a prompt. Reads run freely. Writes still pass the product's own gates, never around them.
- [ ] YAML for config, markdown only for skills. Product concepts never reuse the host harness's own names.
- [ ] He keeps control of skill authoring for now: agents never author their own skills.
- [ ] Runtime policy: a tool error goes back to the model once, and a second failure stops the turn. Cap the iterations per turn: 20 in the reference build.
- [ ] Freeze the prompt prefix so caching works. Harden tool-call parsing. Keep the context lean.
- [ ] An MCP or context surface exposes few tools: four, not eighteen. Tool choice gets worse past 30 to 50 tools. Read-only tools carry the hint. Call budgets and disclaimers go inside the tool descriptions.
- [ ] Any served text is a prompt-injection channel. Threat-model the surface with `/security → prompt-injection`.
- [ ] Never commit an LLM key: the agents read the repo tree, and a committed key leaves through a prompt. Keys come from the environment.
- [ ] Retrieval, when the product searches documents:
  - One embedding model, with a separate chunk table per service.
  - Keep the embedder proven on this data until real prod queries exist.
  - Search quality in the corpus language is not negotiable: keep the engine with the best analyzer for it.
  - No duplicated vectors, and no second vector store when a join answers the question.
  - Retrieve 20, rerank, drop near-duplicates, keep 6 to 10.
  - At scale nobody reads the corpus, so the pipeline reports its own quality signals.
- [ ] The knowledge the agents run on:
  - Prompts are markdown files read fresh on each request, written for any model.
  - Each fact appears once in the loaded context. Shared rules sit once, in base files every expert loads.
  - Computed numbers go into the prompt, so the model never guesses them.
  - Each expert ends with three numbered follow-ups. Low router confidence means clarify and suggest the right expert.
  - An expert is a prompt plus a markdown knowledge file. Its required sections are locked by tests that call no model.
  - A knowledge base is a deep slice, not full breadth, with explicit incomplete markers.
  - Safety sits in the content and the data layer. Refusals are enforced where no prompt can override them.
- [ ] In a repo with `.project.toml`, harness and trunk files make a `risk: high` plan group.
- [ ] Hand the design review to the `architect` agent. Inputs: the frame, the model decision, the harness design. It returns each place the design breaks a rule in this step, with the file or section. It writes nothing. Rai re-checks every load-bearing claim it returns.
- [ ] Agent runtime caps default to one retry per tool error and 20 iterations a turn. A build may override them with a written reason.
- [ ] Every MCP surface he ships has few tools, read-only hints, and writes behind a gate.
- [ ] A work AI product keeps traces of its model calls, off by default and switched on by one setting.

### 4. Evals before any claim

An eval request starts here and ends at the report and its baseline.

- [ ] Keep function and quality apart. Tests prove it runs; the eval proves it answers well.
- [ ] Build the golden set from the product's real tasks, with hand-written refusal traps.
- [ ] Report each arm apart. One averaged number hides the weak corpus.
- [ ] Keep a sealed holdout for any public claim. Its numbers are reported apart, never merged into one figure.
- [ ] Report ambiguity instead of hiding it. Disclose thin coverage; never pad it.
- [ ] The bench measures the served shape. The loader and the bench run before any public claim.
- [ ] Prompt and expert files get structural goldens: tests that call no model and check anchors that survive a rephrase.
- [ ] Scenario tests are one paragraph each, so he and Rai can walk them together. They run on machines that copy prod, with the same story in every environment.
- [ ] Deterministic arms run with the tests. Model-judged arms are manual and budgeted: they run when he asks.
- [ ] Run the whole eval set, never a sample. Then tear down whatever the run stood up.
- [ ] Order of work: fix any active data loss first, then take a baseline, then harden, then run again against the baseline.
- [ ] Re-freeze the set after new data loads, then review the diff. A stale row is dropped from the score openly, never silently.
- [ ] A correctness bug takes two tracks: a quick fix now, and the proper fix after, which adds an eval gate in CI.
- [ ] "We cite sources" counts only when an arm measures it.
- [ ] Grader types: `/think → evals`. A working golden set with a judge: `/rai → eval`.
- [ ] A product that makes a public claim gets a bench with a sealed holdout before the claim. An internal product runs on golden sets and structural goldens.
- [ ] Every eval for a multilingual product carries a quality arm per language.

### 5. Build

- [ ] In a repo with `.project.toml`, run [[21-project-init]] Phase C. The "Slots in 21" table below says what goes where.
- [ ] Anywhere else, run [[02-task]]. Steps 1, 2 and 4 feed its Define step, where `/grill` writes the plan. The parts of step 3 become the groups `/compile` builds.
- [ ] A large build gets a master tracker first: logical phases in one progress file. Then each phase runs the loop once.
- [ ] Tests are green at every milestone, not in a final phase. Each feature has a happy case, an edge case and a failure case.
- [ ] `/fusion → review` reads the branch with the panel he chose.
- [ ] Every automated check passes before his manual test.

### 6. Prod-mimic proof

- [ ] A sealed target: the lab is [[29-air-gapped-delivery]] step 3. Add the AI checks below to it.
- [ ] Swap only the code under test. The VM, the model server and the data stay the same.
- [ ] Serve a small model under the prod model id, so the prod config stays untouched.
- [ ] The stand-in model server sits inside the gap and rejects any model id it does not serve. A lenient stand-in once hid a prod bug.
- [ ] Write the honest framing: what the numbers are, and what they are not.
- [ ] Run the binary checklist. Every item passes or fails, and any FAIL blocks. Any MISSING line in the preflight blocks the run.
- [ ] Any other target: real VMs that copy the prod machines. Each environment mirrors prod or has a named purpose. Tear it down when the run ends.
- [ ] Hand the checklist run to the `qa-tester` agent. Inputs: the checklist and the lab's address. It returns one PASS or FAIL row per item, with evidence. It writes nothing. Rai re-checks every row the gate rests on.

> **Decision Point**: an item fails in the lab but passed in dev?
> - The lab found a real defect on the install path. Fix it at the source, then run the whole checklist again.
> - Hard to tell: reproduce it in the lab until it shows the same errors, following [[04-debugging]].

### 7. Release or demo gate

- [ ] Put the eval report beside the baseline: arms apart, the holdout apart, ambiguity and thin coverage stated.
- [ ] No public claim before the loader and the bench ran on the served shape.
- [ ] Docs claim only what the eval and the demo show. Fix an overstated doc at once.
- [ ] A live demo: every scripted question runs on today's data first. Inside a work engagement, the demo follows [[32-work-engagement]] step 5.
- [ ] A repo goes public only after a secret sweep of its full history, and only on his word.
- [ ] Launch: [[21-project-init]] Phase F in a repo with `.project.toml`, [[06-shipping]] elsewhere. A sealed target ships through [[29-air-gapped-delivery]].
- [ ] No fixed pass mark. The release waits on his read of the report beside the baseline.
- [ ] Gate: he reads the report and says go.

---

## Slots in 21

In a repo with `.project.toml`, this workflow fills the slots of [[21-project-init]]:

| 21 slot | What this workflow supplies |
|---|---|
| Talk, round 1 | Step 1's frame and production profile, step 2's model decision, and step 4's eval plan |
| Trunk | The model endpoint config and the shared base every agent loads. A plan group that touches them is `risk: high` |
| Plan groups | The parts of step 3 the change touches: harness and tools, retrieval, the knowledge files |
| `## Proof` rows | Step 4's eval arms and step 6's sealed A/B. The bench row is captured after the group that serves it |
| Rollback line | The provider switch, as `flag: <ENV_NAME>` |
| Launch, Phase F | Step 6's prod-mimic proof and step 7's report, before the flag comes off |

---

## Working examples

Copy these shapes before inventing new ones.

| What | Where |
|---|---|
| Model decision doc: status table, ruled-out list, decision log | `docs/models.md` in the product repo |
| Bench with arms apart, refusal traps and a sealed holdout | the product repo's `bench/` |
| Structural goldens for prompt and expert files | a unit test that pins their structure |
| Sealed A/B with honest framing | a dated benchmark doc in the repo's `docs/` |
| Binary offline checklist with a preflight | `docs/offline-checklist.md` |
| Harness runtime policy | the repo's `.agent/decisions.md` |
| MCP surface and threat model | `docs/THREAT_MODEL.md` |
| Golden set with a judge | `/rai → eval` |

---

## Connections

- Delivery: [[21-project-init]] Phase C and Phase F in a repo with `.project.toml`; [[02-task]] elsewhere; [[06-shipping]] for a release.
- Neighbours: [[27-data-pipeline]] for the data under the model, [[29-air-gapped-delivery]] for a sealed target.
- A choice that needs a paper: [[30-architecture-decision]].
- From outside: [[07-learning-tech]] hands a model question to step 2.
- Around the build: [[32-work-engagement]] for the engagement, [[04-debugging]] for a lab failure.
- Skills: `/grill`, `/compile`, `/fusion`, `/deep-research`, `/research → web-research`, `/architecture → adr-writer`, `/ai → agent-design`, `/ai → rag-design`, `/security → prompt-injection`, `/think → evals`, `/rai → eval`.
- Agents: the `researcher` agent and the `engineer` agent at step 2, the `architect` agent at step 3, the `qa-tester` agent at step 6.
