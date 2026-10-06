# Air-Gapped Delivery

**Use when:** shipping a product into a sealed or offline network. That covers a first install, an update to a running box, building or refreshing the bundle, and a failure on site.
**Not for:** 06 shipping, for a public product or any target with a network: offline-first there is a hack. 32 work engagement, for the engagement around the delivery. 16 machines, for his own boxes. 25 incident, for something broken on a machine of his own.
**Done when:** the target runs the new commit with zero outbound traffic. The layered verification passed and is signed. Integrity was checked after every hop. A dated runbook and the lessons are in the repo.

John's way to ship into a network with no internet. Air-gap is a packaging problem, not a code problem, so the build is most of the work. Nothing installs at runtime, and every step carries the command that proves it.

> **Entry.** [[06-shipping]] step 4, [[21-project-init]] Phase E and [[32-work-engagement]] step 7 send a sealed target here. 32 also runs step 0 during its build and step 3 as its proof on a copy of prod. Step 0 runs once per target. Every delivery runs steps 1 to 6, then returns to the workflow that sent it.

```d2
direction: right

build: "Build machine, online\n1 offline-true stack\n2 one bundle, checksums"
lab: "Sealed lab\n3 prove the cut,\nlayered checks"
media: "Media\n4 read back,\nchecksum every hop"
target: "Sealed target\n5 deploy\n6 verify, hand off"

build -> lab: "rehearse"
lab -> build: "a red check" {style.stroke-dash: 3}
build -> media: "Gate C green"
media -> target: "carried by hand"
target -> lab: "7 failed on site:\nsame errors first" {style.stroke-dash: 3}
```

---

## Steps

### 0. Frame the target

Once per target.

- [ ] Design for the production profile, never the laptop. Stub what cannot run locally. Dev limits never shape the design.
- [ ] Draw the topology on tenant boundaries. A shared model server is an endpoint the app calls, never a host to touch.
- [ ] The host is provisioned by hand, once. Runners check the prerequisites and fail fast. They never install anything or change the host.
- [ ] Write the prerequisite list with exact versions the target's IT can paste, in install order. It is a one-time ask, so ask for everything that might be needed.
- [ ] One switch, such as `DEPLOY_ENV`, pins the environment. Going to production is a config swap. Name each exception to "no code change".
- [ ] Once real data is on the box, it never goes online, not even briefly.
- [ ] **Gate A.** The prerequisite list, the one switch and the named exceptions are written.

> **Decision Point**: a vendor product rather than his own stack?
> - Yes: the vendor's installer is the bundle, so skip steps 1 and 2. Check the vendor's version compatibility table. The step 3 lab is a VM matched to the server's config. Activation is offline: carry the request file out and the response file back.
> - No: step 1.

### 1. Make the stack offline-true

- [ ] Exact version pins everywhere, never `:latest`. Only host drivers get a floor.
- [ ] No runtime network: local defaults, telemetry off, the offline env vars set. All traffic stays on localhost or internal names.
- [ ] Anything fetched at runtime is baked in at build time, behind a gate. A missing piece fails the build on the online machine, never silently on the target.
- [ ] One control folder, one env file, three modes: resume, fresh, nuke.
- [ ] All runtime data sits under one bind-mount root: one tar to back up, one unit to remove.
- [ ] Optional pieces fail soft. When the assistant is down, nothing else breaks.
- [ ] The base compose file is Linux-first. A dev machine's adjustments live only in a local override.
- [ ] Containers run as non-root by default. In a sealed deployment inside one trust boundary, a container may run as root when its Dockerfile says why.
- [ ] **Gate B.** The built image runs with `--network none`.

### 2. Build the bundle

On the online build machine.

- [ ] One archive, no mirrors.
- [ ] A must-ship table and a must-not-ship table, each row with its reason. No model weights. No internal content: session memory, internal notes, dev tooling.
- [ ] Nothing ships unless it earns its place. Audit the bundle for content that must not ship, and run `/security → security-review` over its secrets.
- [ ] Ship the build kitchen when work will continue on the sealed box: the base images, the package caches and the wheelhouse.
- [ ] Choose restart, rebuild or rebundle from the repo's matrix, never by guess.
- [ ] Generate the offline compose file. It has no `build:` sections, and the packager asserts the image count.
- [ ] Checksum manifests cover the bundle and the source tree. Code fails hard. Files the operator edits only warn.
- [ ] Write the dated runbook for this delivery, and ship it with the bundle. His shape: what this run is not, before you touch anything, the steps, verify, do not, rollback, known and deferred on purpose.
- [ ] Every ops doc is human-runnable and short: no placeholders, no `$(date)`, no backslash continuations, no inline Python.
- [ ] Hand the runbook draft to the `sre` agent. Inputs: the commit range since the last delivery, the repo's rebundle matrix and the prerequisite list. Returns: a draft in his shape. It writes that draft file only.
- [ ] Rai checks every command in the draft against the repo. John reads the runbook before the carry.
- [ ] The preflight passes. Then verify locally, the way the target will run it.
- [ ] Tag every shipped bundle with a dated tag, and name the tag in the runbook.
- [ ] Secrets: the private work repo keeps its plug-and-play env file with dev values. Real secrets are rotated at a fresh install and never committed. His own systems keep every secret in 1Password.

### 3. Rehearse in a sealed lab

- [ ] Write a property-to-lab table: each property of the target, and whether the lab reproduces it faithfully, degraded or not at all. Say plainly what the lab does not mimic.
- [ ] Provision online and snapshot the `staged` state. Then cut the network and prove the cut: no default route, dead DNS, the package index and raw IPs unreachable, peers reachable.
- [ ] Model the real network. Block public egress only: a blanket reject is not how a LAN server with the internet blocked behaves.
- [ ] Stubs for what cannot ship are strict and sit inside the gap. A model stub answers only the served model names.
- [ ] The lab mimics prod, so the harness accepts only the prod env file.
- [ ] Run the operator's real steps on capped dummy data.
- [ ] Audit the run logs for download attempts and hostname leaks.
- [ ] Run the lab locally, on the Linux box with the VM tooling.
- [ ] Hand the layered checks to the `qa-tester` agent. Inputs: the lab address and the checklist, from the network layer up to the features. Returns: PASS or FAIL per layer, with the command and its output. It cannot edit files.
- [ ] Rai re-runs every FAIL before acting on it.
- [ ] The lab rehearsal is required for a first install, a new dependency, a rebundle or a failure fix. A code-only update to a known box may skip it when the preflight and the checksums are green.
- [ ] Keep the proven lab snapshots between deploys to one target. Rebuild them from the scripts when the target's profile changes.
- [ ] **Gate C.** Every checkpoint is green and automated before any manual test. A red check is a finding about the install path, not about the document.

### 4. Carry

- [ ] Use exFAT media, because the tarballs pass 4 GB.
- [ ] Hand off safely: sync, unmount, remount, read back, eject.
- [ ] Copy with rsync, never cp.
- [ ] Run `sha256sum -c` after every hop, not only at the end.
- [ ] A copy that finished too fast is proven by the checksums, never trusted.

### 5. Deploy

> **Decision Point**: first install or update in place?
> - First install: the from-scratch path. On a box provisioned online, run on dummy data first, set the config, cut the wire and prove the cut. Then load the real data and run one command. Rotate the dev secrets at the env stage, with a grep gate.
> - Update on a box that holds data: resume only. Never the from-scratch path, never `rsync --delete`, never `down -v`. Secret rotation waits for the next clean install, listed under known and deferred.

- [ ] First, on the box: record what runs now, meaning the commit, the environment switch, health and free disk. Stop on a mismatch.
- [ ] The runbook's first line states the kind of deploy, such as "This is NOT a from-scratch deploy."
- [ ] On a shared host, touch only this project's containers and volumes. Never prune, and never stop the Docker daemon.
- [ ] Archive after stopping, never before. Refuse to adopt an old database silently.
- [ ] Offer `--dry-run`, and ask for a typed `yes` before removing anything.
- [ ] Recreate with `up -d`. Never `restart`, which keeps the old container config.
- [ ] Forbidden offline: `down -v`, `pull`, `build --no-cache`.
- [ ] The preflight prints its pass line before the run.

### 6. Verify and hand off

- [ ] Run the layered checklist from the machine whose reachability matters, and fill its sign-off table.
- [ ] Browser checks run from a remote consumer machine, never the server's own browser.
- [ ] Prove the backup pipeline before anyone relies on it, and restore from it once. A backup nobody has restored is only a hypothesis.
- [ ] Hand off a flat, minimal doc set: guide, architecture, deploy, verification, lab. Every file earns its place, because a pile of files goes unread.
- [ ] Handing the work to another team: [[32-work-engagement]] step 7 holds the hand-over rules.
- [ ] At a partner hand-off, the receiving team's operator signs the verification after their own run. John signs the lab rehearsal.

### 7. It failed on site

- [ ] Follow [[04-debugging]] from step 1. Its rules for handoff docs and for a target he cannot touch govern here. The step 3 lab is the mimic.
- [ ] Hand the reproduction to the `debugger` agent. Inputs: the site's error text, its logs and the lab snapshot. Returns: the same errors side by side, then one fix per wall on a branch. It writes on that branch only.
- [ ] Rai re-checks the same-errors claim before any fix is accepted.
- [ ] The fix ships as a new delivery, steps 1 to 6.
- [ ] Add the failure's signature and its fix to the ops runbook.

### 8. Lessons

- [ ] Write the incident into the repo's docs.
- [ ] Update the project retrospective in [[01-project]] at its close.

### 9. Commit and sync

- [ ] Repo changes commit through the repo's own flow: 21's gates in a repo with `.project.toml`, `/git → commit` elsewhere.
- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Sent here by [[06-shipping]] step 4, [[21-project-init]] Phase E and [[32-work-engagement]] step 7.
- A pipeline's sealed rehearsal: [[27-data-pipeline]] step 11 runs step 3 here.
- A failure on site: [[04-debugging]]. The retrospective: [[01-project]].
- Skills: `/devops → docker`, `/devops → monitoring`, `/testing → e2e`, `/security → security-review`, `/fusion → review`, `/architecture → system-design` for the topology, `/visual → plan`, `/think → systematic-debug`, `/git → commit`.
- Agents: `sre` (step 2), `qa-tester` (step 3), `debugger` (step 7).
