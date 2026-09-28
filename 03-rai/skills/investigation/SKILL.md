---
name: investigation
description: >
  Investigation router. USE WHEN the user needs to look up a person, research
  a company, conduct due diligence, investigate infrastructure, or gather
  threat intelligence from public sources only. Routes between OSINT
  (broad investigation), PrivateInvestigator (people-finding), and Recon
  (infrastructure mapping). Public data only. Some workflows require
  explicit user authorization before starting.
---

# Investigation

Three skills with overlapping but distinct scope. Public data only. Pick by
the target type.

## Routing table

| Target | Sub-skill | File to Read |
|--------|-----------|--------------|
| Person — professional / company / threat-intel context | OSINT | `osint.md` |
| Company — corporate filings, leadership, due diligence | OSINT | `osint.md` |
| Investment due diligence | OSINT | `osint.md` |
| Domain / IP / threat-intel entity | OSINT or Recon (see below) | `osint.md` or `recon.md` |
| Person — pure people-finding (verify identity, public records) | PrivateInvestigator | `private-investigator.md` |
| Reverse lookup (phone, email, username → identity) | PrivateInvestigator | `private-investigator.md` |
| Infrastructure mapping (DNS, subdomains, services, ASN) | Recon | `recon.md` |
| Network range or netblock analysis | Recon | `recon.md` |
| Target is BOTH a person AND their infrastructure (e.g. "look up John Doe who runs this domain") | Combo | `combo.md` |

## OSINT vs Recon — when both could fit

- **OSINT** is the broader investigation framing — gathers context, news, breaches, business signal.
- **Recon** is the technical scan — DNS, certs, ports, services. Active recon needs target authorization.

Use OSINT first if the question is "who/what is this entity." Use Recon when the question is "what does its infrastructure look like."

## OSINT vs Recon

OSINT answers "who/what is this entity". Recon answers "what does its infrastructure look like". Use OSINT first if the target is a person or company; use Recon first if the target is a domain, IP, or network.

## How to use

1. Pick the sub-skill that matches the target.
2. **Authorization gate:** Authorization required for: OSINT (all types) and active Recon (port scans, service detection, direct probes). Passive Recon (WHOIS, DNS, cert transparency, Shodan lookups) does NOT require authorization. Confirm: what entity, why, "go ahead". Never proceed without all three.
3. `Read` the appropriate file in this directory.
4. Follow that file's instructions.

## Hard rules (apply to all three)

- Public data sources only.
- No paid databases unless the user provides access.
- No impersonation, pretexting, or social engineering.
- No unauthorized access to private systems.
- Report findings factually; cite sources; flag confidence.
