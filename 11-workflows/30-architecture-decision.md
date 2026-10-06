# Architecture Decision

**Use when:** a directive or a question implies an architecture choice: a database, a platform, a topology or a team split. That includes a design question across teams, a decision paper or proposal for leadership, and a client's stack question.
**Not for:** 07 evaluate a technology, for adopting one tool for his own use. 28 data platform, for a warehouse or lakehouse design, which calls step 7 here for its paper. 23 audit, for reviewing an architecture that already runs. 11 meeting follow-through, for the meeting where it is decided. 32 work engagement, for the engagement around it.
**Done when:** the decision is recorded in its home, or the framing questions that block it are, with who must answer them. The record carries the options, one recommended path, the prerequisites and the open questions.

John's way to frame and decide a design, and to write the decision paper. Framing comes before infrastructure, and the architecture follows ownership. Writing the framing down beats winning the meeting.

```d2
direction: down

frame: "1-2 Altitude and ownership"
blocked: "Framing open:\na framing paper,\nthe questions and who answers"
truth: "3-4 Ground truth and numbers"
paths: "5-6 Paths, one recommended"
branch: "Branches:\ncontract, security"
artifact: "7 The paper\nfor the audience"
stress: "8 Stress-test"
record: "9-10 Record and seam"

frame -> truth -> paths -> artifact -> stress -> record
frame -> blocked: "the question sits downstream" {style.stroke-dash: 3}
blocked -> artifact {style.stroke-dash: 3}
paths -> branch {style.stroke-dash: 3}
```

---

## Steps

### 1. Check the altitude

- [ ] Name the real objective behind the ask.
- [ ] Is the question downstream of an open framing question? Picking a shared database before anyone has said what "one solution" means is one. Then reframe, and never answer the infrastructure question first.
- [ ] When a directive mixes objectives, name each one with its cost. Collaboration, integration and unification cost very different amounts.
- [ ] When the real deliverable is a decision, write a proposal, not a project.

> **Decision Point**: is the framing settled?
> - Yes: step 2.
> - No: the output is a framing paper, not a design. It holds the objectives and their costs, the paths, the prerequisites, the questions for the next meeting, and a recommended position. Write it at step 7, and record it at step 9.

### 2. Ownership and authority

- [ ] Who owns the operation? Who holds binding technical authority? Architecture follows ownership: the team that runs it decides its architecture.
- [ ] Across teams, integrate by contract. Each team exposes its services through APIs, and one team owns the frontend.
- [ ] The prerequisites that hold on any path: one accountable owner, one technical authority, the operational meaning of the goal, and what stays separate.
- [ ] Add a migration plan for every architecture that does not survive.
- [ ] Without an owner and an authority, a working session is a committee. Its output is a treaty rather than a design.
- [ ] Stay out of what you do not own. A shared server another team runs is an endpoint to call, not a box to manage.

### 3. Ground truth

- [ ] Read what exists before deciding: the code, the running system, a live recon of the sources.
- [ ] Every decision cites the ground truth behind it.
- [ ] Diagrams show the current state only, traced from the code.

### 4. Constraints and numbers

- [ ] Write the production profile, the real scale, and any sovereignty or offline need.
- [ ] Walk the numbers into a table before any verdict: users, concurrency, hardware, disk. Magnitude by intuition is unreliable.
- [ ] Size by the load that matters, such as concurrent users on a shared model. Nothing speculative.
- [ ] Before adding infrastructure for speed: stop, measure, and expect plain indexed SQL to be the answer.
- [ ] Throughput measured on a dev provider does not carry over to prod. Tuning is a prod exercise.
- [ ] Settle anything fixed at creation, such as a shard count, before a long run.
- [ ] A benchmark is a controlled A/B. Swap only the code, on the same box, model and data. Report medians, and write what the numbers are and are not.
- [ ] Walk the sizing sheet for any design with shared compute. One row at a time: users, concurrency at peak, load per request, then GPU, RAM and disk. Each row carries a number and its source.

### 5. Paths

- [ ] Lay out two or three paths. Each gets its cost, its requirements and a "use when" line.
- [ ] Compare them in a matrix.
- [ ] Default to the simplest path. On a single host, the database is the queue. No extra service unless it must run as its own process.
- [ ] Config beats abstraction. A swap is an env var, not a class hierarchy.
- [ ] A service that wants its own database and disks moves out. It never grows the stack.
- [ ] Event-driven in principle, with a broker only at real scale.
- [ ] Hand the draft paths to the `architect` agent once steps 1 to 4 are written. Inputs: the framing, the owners, the ground truth and the numbers table. Returns: two or three paths with costs, plus the matrix. It writes nothing.
- [ ] Hand the outside facts a path rests on to the `researcher` agent. Returns: cited facts. It cannot run commands or edit files.
- [ ] Rai re-checks every load-bearing claim before the matrix reaches John.

> **Decision Point**: does the decision cross a team boundary, or open a serving surface?
> - A contract across a team boundary: add the contract branch below.
> - A surface that serves untrusted text or takes user input: add the security branch below.
> - Neither: step 6.

### 6. Recommend

- [ ] Mark one path (Recommended), with a one-clause reason. Two or three options, and John decides.
- [ ] List the prerequisites, the questions to raise at the next meeting, and a fallback position.
- [ ] The fallback when a meeting keeps the wrong scope: the open questions go into its notes, with the dependency flagged. [[11-meeting-to-followthrough]] carries the meeting.

### 7. The paper for the audience

- [ ] Write a context document first. The paper then draws on those sources only.
- [ ] The shape: the framing question, the options, a comparison matrix, one recommended approach, a phased rollout, and the decisions owed.
- [ ] Close with "Decisions for Leadership". Each decision is a question, an options table with the advantage and risk of each, and the recommendation.
- [ ] Phase 1 holds the foundation only.
- [ ] For management: no tool names, diagrams over text, and every section answers "so what?". Show the current state only, never what is retiring. Substance only.
- [ ] For engineers: grounded in the code, current state only.
- [ ] Real artifacts and small diagrams, never marketing copy.
- [ ] Diagrams are traced from the real code: Excalidraw while editable, PDF when final. Slides embed the same diagrams. The architecture and tech stack pair is drawn in [[34-diagrams]].
- [ ] One house PDF style for every paper.
- [ ] The language follows the audience. An Arabic paper is written natively, never translated, through [[20-arabic-piece-pipeline]].
- [ ] In `04-work/`: no AI mentions, a formal tone, and every name, amount and date checked with John.
- [ ] Hand the first draft to the `writer` agent. Inputs: the context document, the paths, the recommendation and the audience. Returns: a draft in this shape. It writes the draft file only.
- [ ] Rai checks every fact in the draft against the context document.
- [ ] John decides when the paper is done. Once he says it is done, Rai stops proposing additions.
- [ ] The paper's shape: the framing log for a decision inside an organization, and the full proposal shape for leadership.

### 8. Stress-test

> **Decision Point**: a small, reversible choice?
> - Yes: skip to step 9.
> - No, a big or one-way choice: stress-test it first.

- [ ] Attack the recommendation with `/think → red-team`, `/fusion → decide` or `/fusion → review`.
- [ ] Precedent: three independent models killed a plan to keep secrets in git.

### 9. Record

- [ ] Dated and append-only. A reconsidered decision gets a new entry. The old one is marked superseded, never edited or deleted.
- [ ] Each entry holds the decision, the reasons, the alternatives considered, the cost, and where it lives.
- [ ] The original spec stays as written. Later decisions are recorded on top of it.
- [ ] The home:
  - a repo with `.project.toml`: an ADR in `project_memory/decisions/`, written in the talk or replan of [[21-project-init]];
  - any other repo: the repo's own decision log;
  - a work engagement: a decision log in `04-work/<engagement>/`;
  - a product before its repo: a standing rule `S-n` in the kitchen's `specs/tech-stack.md`, in [[01-project]].
- [ ] Split a thought by audience. The architectural half goes in the decision log. The personal half goes in his journal.
- [ ] A work engagement keeps two logs. The repo's log holds decisions about the code. `04-work/<engagement>/` holds decisions about the engagement, such as ownership and scope.
- [ ] Every entry carries a "where it lives" pointer to the code or file that holds the decision.

### 10. Leave a seam

- [ ] Make the next move a config change, not a rewrite: Phase 0 now, the split later.

### 11. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Branch: a contract across a team boundary

- [ ] Read the contract off the code, and list the files behind each claim. Any endpoint not listed does not exist.
- [ ] State the conventions, the error envelope and the status codes this backend really uses. Be honest about dead fields.
- [ ] Where the contract and the code disagree, verification follows the code and says so.
- [ ] The partner team owns its frontend. Deliver the APIs, an OpenAPI spec and the streaming contract.
- [ ] One implementation of a core contract serves every surface. No type import crosses the wire between packages.
- [ ] Code-first, always: the contract follows working code, never the other way round.
- [ ] A partner API changes additively. A breaking change gets a new version, and the old one stays until the partner has moved.

## Branch: a security-sensitive surface

- [ ] Name the trust boundaries, and the one boundary you defend.
- [ ] Put one choke point on the path every request takes.
- [ ] Write what the defense does not claim.
- [ ] Set standing review triggers: a new source, a new route, a new transport.
- [ ] Permission checks run server-side. Frontend hiding is UX, never security. Every denial gets a 403 test.
- [ ] Never commit a key value. Reference secrets instead.

---

## Connections

- The meeting, with this paper as its pre-read: [[11-meeting-to-followthrough]].
- Callers: [[28-data-platform]] (steps 1, 7 and 9) and [[32-work-engagement]] (its decision paper).
- A topology decision for a sealed target feeds [[29-air-gapped-delivery]] step 0.
- Homes for the record: [[21-project-init]] and [[01-project]]. An Arabic paper: [[20-arabic-piece-pipeline]].
- Skills: `/architecture → solution-architect`, `/architecture → system-design`, `/architecture → data-architect`, `/architecture → patterns`, `/architecture → adr-writer`, `/think → first-principles`, `/think → red-team`, `/think → council`, `/fusion`, `/visual → compare`, `/business → presentations`, `/writing → proposals` (its voice anchor only: its sales shape is not his paper), `/research → web-research`, `/work → meeting-prep`.
- Agents: `architect` and `researcher` (step 5), `writer` (step 7).
