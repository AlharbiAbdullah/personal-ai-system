---
name: security
description: >
  Security work router. USE WHEN the user wants security testing, threat
  analysis, security review, or wants security news / report briefings.
  Routes between Web app testing, prompt injection testing, code review,
  and intelligence aggregation.
---

# Security

Five security-focused skills. Pick by the work shape.

## Routing table

| Task | Sub-skill | File to Read |
|------|-----------|--------------|
| Web app pen test / vulnerability assessment | WebAssessment | `web-assessment.md` |
| Test an LLM app for prompt injection | PromptInjection | `prompt-injection.md` |
| Review code for security flaws (auth, input, crypto) | security-review | `security-review.md` |
| Daily security news briefing (CVEs, breaches, trends) | SECUpdates | `sec-updates.md` |
| Search across 570+ annual cybersecurity reports | AnnualReports | `annual-reports.md` |

## How to use

1. Pick the sub-skill that matches the work.
2. **Authorization gate** for any active testing (WebAssessment, PromptInjection): confirm scope, target, and explicit user "go ahead" before starting. Passive work (security-review, SECUpdates, AnnualReports) does not require authorization.
3. `Read` the appropriate file in this directory.
4. Follow that file's instructions.

## When unsure

- Web target → WebAssessment
- LLM/agent target → PromptInjection
- Codebase → security-review
- "What's happening" → SECUpdates
- Historical / multi-year context → AnnualReports

For adversarial stress-testing of ideas/plans/designs (red-team thinking), see `/think/red-team`. That is a thinking mode, not security work.
