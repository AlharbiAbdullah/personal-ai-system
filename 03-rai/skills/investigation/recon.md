# Recon

Gather intelligence about infrastructure targets using public sources and
standard scanning techniques. Two phases: passive (no target contact) and
active (direct probing).

## Phases

### Passive reconnaissance
No direct contact with the target. Uses third-party data only.
- WHOIS lookups (domain registration, ownership).
- DNS enumeration (records, subdomains, mail servers).
- Certificate transparency logs (SSL/TLS history).
- Search engine dorking (indexed pages, exposed files).
- Public breach databases (credential exposure check).

### Active reconnaissance
Active reconnaissance requires authorization (port scans, service detection, banner grabbing, any direct target contact). Passive recon (WHOIS, DNS, cert transparency, Shodan passive lookup) does NOT require authorization.
- Port scanning (open services, filtered ports).
- Service detection (software versions, banners).
- Technology fingerprinting (web stack, frameworks).
- Directory enumeration (common paths, hidden endpoints).

## Workflows

### PassiveRecon (passive)
Full passive scan of a target. No authorization needed.
Steps: WHOIS, DNS, certs, search engine, compile report.

### IpRecon (hybrid)
Investigate a specific IP address. Starts passive, may escalate.
Steps: reverse DNS, geolocation, ASN lookup, hosting provider, reputation.

### DomainRecon (hybrid)
Deep dive on a domain. Starts passive, may escalate.
Steps: DNS records, subdomains, WHOIS history, web technologies, SSL chain.

### NetblockRecon (hybrid)
Map an organization's network range. Starts passive, may escalate.
Steps: ASN lookup, IP range enumeration, reverse DNS sweep, service map.

## Output

- Target profile with all discovered assets.
- Risk indicators (exposed services, outdated software).
- Visual network map when possible.
- Recommendations for further investigation.

## Examples

- "Passive recon on example.com"
- "What infrastructure does this IP belong to?"
- "Map all subdomains for our domain"
- "Identify the tech stack of this website"
