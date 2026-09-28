# Web Assessment

Authorization required — penetration testing is active. Confirm scope with owner before starting.

Assess web application security through structured testing. Covers
threat modeling, vulnerability scanning, and manual testing techniques.
Integrates with the Recon skill for initial reconnaissance.

Flow: Start with /investigation/recon for infrastructure mapping, then return here for application-layer testing.

## Assessment Phases

### 1. Threat Modeling
Map the application's attack surface before testing.
- Identify entry points (APIs, forms, uploads, auth flows)
- Map data flows and trust boundaries
- Enumerate potential threats using STRIDE
- Prioritize threats by risk (likelihood x impact)

### 2. Penetration Testing
Authorized testing of identified attack vectors.
- Authentication/authorization bypass
- Injection testing (SQL, XSS, SSRF, command)
- Business logic flaws
- Session management weaknesses
- API security (rate limiting, input validation, IDOR)

### 3. Fuzzing
Automated input mutation to find edge cases.
- Parameter fuzzing (forms, query strings, headers)
- File upload testing (type bypass, path traversal)
- API endpoint fuzzing (unexpected methods, payloads)

### 4. OSINT
Open-source intelligence about the target.
Scope: tech-stack OSINT (GitHub, job postings, documented stack). For broader entity/personnel OSINT, use /investigation/osint instead.
- Exposed credentials in public repos
- Leaked API keys or tokens
- Indexed admin panels or debug endpoints
- Historical vulnerabilities in the tech stack

### 5. Bug Bounty Mode
Structured approach for bug bounty programs.
- Read program scope and rules first
- Focus on high-impact, in-scope targets
- Document findings with clear reproduction steps
- Follow responsible disclosure timelines
- If program scope is ambiguous, ask: "Can I test [endpoint]?" Get explicit "yes" before probing.

## Integration

Uses /Recon for initial infrastructure mapping.
Uses /PromptInjection for LLM-specific testing if applicable.

## Output

- Vulnerability report with severity ratings (CVSS)
- Reproduction steps for each finding
- Remediation recommendations
- Executive summary for non-technical stakeholders

## Examples

- "Assess our web application's security"
- "Threat model our new API endpoints"
- "Test our login flow for auth bypass"
- "Run a bug bounty-style assessment on [target]"
