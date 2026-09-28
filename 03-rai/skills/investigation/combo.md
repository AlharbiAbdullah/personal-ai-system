---
name: combo
description: >
  Combo investigation. USE WHEN the target is BOTH a person AND their
  infrastructure (e.g. "look up John Doe who runs this domain"). Sequences
  PrivateInvestigator → OSINT → Recon to build a full profile. Public data
  only. Requires authorization.
---

# Combo Investigation

When the target is a person AND has attached infrastructure (a domain,
network, company). Chains three sub-skills so you don't have to run them
separately.

## When to use

- "Look up this person and the domain they own"
- "This profile says they're at ACME — what's ACME's footprint?"
- "I have an email address; who owns it and what do they operate?"

## When NOT to use

- Target is purely a person (no infra attached) → go straight to `/investigation/private-investigator`
- Target is purely infrastructure (no person) → go straight to `/investigation/recon`
- Target is a company with no specific person → use `/investigation/osint` alone

## Authorization gate

This workflow runs both OSINT (requires auth) and active Recon (requires
auth). Confirm **three things** before proceeding:
1. **What target** — the exact person + infrastructure identifiers
2. **Why** — legitimate purpose (due diligence, threat intel, hiring check)
3. **Explicit "go ahead"** in written form (email, ticket, chat message)

If any of the three is missing, stop and ask.

## Workflow

### Stage 1: PrivateInvestigator — identity anchor
1. Run `/investigation/private-investigator` on the person
2. Confirm identity: name, primary email, current role/affiliation
3. Output: a verified identity record (email, LinkedIn, current employer)

### Stage 2: OSINT — context layer
1. Feed the verified identity + claimed infrastructure into `/investigation/osint`
2. Cross-reference: does the person's footprint match the infra ownership?
3. Output: professional context, recent activity, affiliations, any breach signal

### Stage 3: Recon — infrastructure layer
1. Run `/investigation/recon` on the domain/IP/ASN
2. Map DNS, subdomains, certs, exposed services
3. Output: infrastructure map + hosting profile + tech stack inference

### Stage 4: Synthesize
Produce a single combined report:
- Person identity (verified)
- Professional context (OSINT findings)
- Infrastructure footprint (Recon findings)
- Links between person and infra (who registered, who hosts, contact emails)
- Confidence flags per section

## Hard rules (inherit from parent router)

- Public data sources only
- No paid databases unless the user provides access
- No impersonation, pretexting, or social engineering
- No unauthorized access to private systems
- Report findings factually; cite sources; flag confidence
