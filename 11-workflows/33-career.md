# Career

**Use when:** publishing a proof piece, or updating the profile: LinkedIn, the resume and the site. Also applying for a role, or answering someone who asks about one of his published offers.
**Not for:** Arabic prose goes to 20 Arabic writing. Paid work, once agreed, is 32 work engagement. A change to the site's code or look is 02 task, then 06 shipping.
**Done when:** the piece, the profile change or the reply went out on his explicit go. LinkedIn, `resume.html` and the site agree on titles and dates. Nothing confidential appears in any of them.

Work comes to John through visible proof, not outreach. This workflow keeps that proof honest, confidential, and his to publish.

```d2
direction: right

rules: "Step 1\nshared rules"
piece: "2 Proof piece"
profile: "3 Profile\nLinkedIn, resume, site"
apply: "4 Application\n(stub)"
consult: "5 Consulting inquiry\n(stub)"
go: "6 His explicit go" {shape: hexagon}
out: "Published or sent"
w32: "32 work engagement"

rules -> piece
rules -> profile
rules -> apply
rules -> consult
piece -> go
profile -> go
apply -> go
consult -> go
go -> out
consult -> w32: "once agreed" {style.stroke-dash: 3}
```

---

## Steps

### 1. Pick the entry and apply the shared rules

> **Decision Point**: which entry?
> - A LinkedIn post, a site post or a project page: step 2.
> - LinkedIn, the resume or the site's facts about him: step 3.
> - A job opening: step 4.
> - Someone asks about one of his published offers: step 5.

The rules below hold for every entry.

- [ ] Inbound only. Work finds him through the site, the profile and the pieces. No cold outreach, and no pleasing people for a goal.
- [ ] Confidentiality:
  - Employers stay "Confidential" on LinkedIn. The resume may name them.
  - Project code names that tie to an employer stay off LinkedIn.
  - Unreleased work gets a thin teaser, never a spec. A teaser holds the problem in his framing, one paragraph on the answer, and a status line.
  - A fork keeps its upstream license and credit, as the license requires.
  - Where a `/writing` skill example names a work project, these rules win.
- [ ] Honest claims only. No invented metric: without an exact number, use a before-and-after contrast. Every listed skill holds up in an interview.
- [ ] Hooks come from his interest areas: data engineering, DevOps, AI and system design. A project name never leads.
- [ ] Every post earns its place. A post that no longer earns it gets deleted, and its URL redirects.
- [ ] A draft in the vault passes `vale --filter='.Name matches "^Rai"'` before he sees it. Every draft follows `03-rai/skills/writing/references/voice.md`.
- [ ] Rai drafts; he publishes. Nothing goes public, and no application or reply is sent, without his explicit go.
- [ ] Rai reads LinkedIn only when he asks, since a browser window takes his focus. Otherwise he pastes the section.

### 2. Publish a proof piece

- [ ] Cadence: one post every two weeks from shipped work, plus two or three comments a week.
- [ ] Pick the proof: one piece of real, shipped work. Write one sentence on what the piece proves.

- [ ] Pick the surface: a LinkedIn post, a site post, or a project page. The site is English only. Arabic goes to [[20-arabic-piece-pipeline]].
- [ ] A long piece goes to the site, and a short LinkedIn post links to it. A short take goes straight to LinkedIn.

- [ ] Draft with `/writing → social-media` for LinkedIn, or `/writing → blog` for the site. A project page for unreleased work follows the teaser rule.
- [ ] Hand the draft to the `writer` agent. Inputs: the one-sentence proof, the source material, the surface. It returns one clean draft in his voice. It writes nothing.
- [ ] Run the confidentiality pass. No employer, no client engagement, no code name tied to an employer. No private repo, and no unreleased detail beyond the teaser.
- [ ] He reads the final draft only.
- [ ] A site post or project page follows the blog file structure and styling in the site repo's `AGENTS.md`.
- [ ] Publish through step 6.

### 3. Update the profile

- [ ] Sources of truth: LinkedIn for titles and dates, and the resume source in the site repo. The resume follows LinkedIn, never the reverse.
- [ ] The resume:
  - one page;
  - skills as bare category labels, with the keywords in the experience bullets;
  - broad terms over single tools;
  - projects say what the project is and what it solves, never the stack.
- [ ] Print the PDF with the site repo's recipe: headless Chrome, a timeout, a throwaway profile. Check it fits one page and shows no yellow placeholder marks.
- [ ] The resume source and every published copy of it change together.
- [ ] LinkedIn:
  - The headline names the areas he claims.
  - The About is a short hook, not a summary, and it links the site.
  - Skills grow toward the cap, and each one holds up in an interview.
  - Before redrafting the About, check whether he approved the last draft.
- [ ] The site stays very simple.
- [ ] A new profile image: render options, and he judges the likeness himself.
- [ ] Every link points at the current domain.
- [ ] After any change, check that the three agree on titles and dates. Employer names differ by design.
- [ ] Publish through step 6.

### 4. Apply for a role (stub)

Qualifying the role is this entry's gate.

- [ ] Qualify the role against the criteria he wrote in `02-ana/identity/goals.md`: location, level, the kind of work, and his salary floor.
- [ ] Tailor one resume per job title from the resume source. Keywords come from the posting's qualifications block. Bullets say what, how and the result.
- [ ] Hand the company and the role to the `researcher` agent. Inputs: the posting and the company name. It returns the team, the real scope of the role and the interview format, each with a source. It writes nothing. Rai re-checks every load-bearing claim it returns.
- [ ] He sends the application himself.
- [ ] A cover note only where the form asks for one: short, and drawn from the tailored resume.
- [ ] Interview prep: confirm the real format, research in parallel, and write one prep guide. After each interview, write a short debrief.
- [ ] Track each application as one file in `04-work/job-applications/`. It closes at an offer, a no, or when he drops it.

### 5. Answer a consulting inquiry (stub)

This entry earns more steps after a few real runs.

- [ ] Qualify: only the offers he publishes. Decline anything outside them.
- [ ] Scope in the published terms. An audit is fixed scope and ends in a written report: what is solid, what breaks at scale, what to fix first.
- [ ] Stack selection maps the options against the client's real constraints. It ends in a decision with reasons, not a vendor pitch.
- [ ] Quote from the pricing targets in `02-ana/identity/goals.md`. He sets the number.
- [ ] Rai drafts the reply, and he sends it.
- [ ] Once agreed, it runs as a [[32-work-engagement]] from step 0. An audit's deliverable is the report from [[23-audit]] in report mode. A stack selection's deliverable is the paper from [[30-architecture-decision]].

### 6. His go, then publish or send

- [ ] Rai prepares; he publishes. He posts on LinkedIn, and he sends applications and replies himself.
- [ ] A push to the site's `main` deploys it live. The site repo commits and pushes only when he says ship.
- [ ] After the site deploys, check the live pages as [[06-shipping]] step 5 says.

### 7. Sync

- [ ] Vault edits follow the commit rule in `11-workflows/AGENTS.md`.

---

## Connections

- Writing: [[20-arabic-piece-pipeline]] for Arabic, `/writing → social-media` and `/writing → blog` for English.
- Paid work: [[32-work-engagement]], with [[23-audit]] report mode or [[30-architecture-decision]] as the deliverable.
- The site: [[06-shipping]] for the deploy, [[02-task]] for code changes.
- Research: `/research → web-research`.
- Agents: the `writer` agent at step 2, the `researcher` agent at step 4.
