# Prompt Injection Testing

Test LLM-based applications for prompt injection vulnerabilities.
Requires explicit written authorization from the system owner
before any testing begins.

## Authorization Required

Authorization: Get written approval (email, ticket, or explicit confirmation in chat) from the system owner. Must state: target app, scope (which endpoints/inputs), and explicit "go ahead". Verbal is insufficient.

Before running any test:
1. Confirm the user owns or has written permission to test the target
2. Define scope (which endpoints, which models, what's off-limits)
3. Agree on responsible disclosure process
4. Document authorization

## Workflows

### Reconnaissance
Map the target application's LLM integration points.
Steps: identify input surfaces, map system prompts (if visible),
catalog model behaviors, document guardrails.

### DirectInjection
Test user-facing inputs for injection susceptibility.
Steps: craft payloads (instruction override, role manipulation,
context escape), test each input surface, document results.

### IndirectInjection
Test data sources the LLM processes (documents, emails, web content).
Steps: embed instructions in processable content, test retrieval
paths, check if injected instructions execute.

### MultiStageAttack
Chain multiple small injections across sessions or inputs.
Steps: plant benign-looking fragments, test if fragments combine
into effective attacks, document chain paths.

## Workflow → Attack Categories

| Workflow | Attack categories |
|----|----|
| DirectInjection | Instruction override, prompt leaking, jailbreak |
| IndirectInjection | Data exfiltration, tool abuse |
| MultiStage | Chained payloads, persistent injection |
| Recon | Model identification, prompt extraction |

## Attack Categories

- **Instruction override**: "Ignore previous instructions and..."
- **Role manipulation**: "You are now a different assistant..."
- **Context escape**: Breaking out of structured prompts
- **Encoding bypass**: Base64, Unicode, leetspeak obfuscation
- **Delimiter injection**: Exploiting XML/JSON/markdown boundaries

## Responsible Disclosure

- Report all findings to the system owner
- Provide severity ratings and reproduction steps
- Suggest mitigations for each vulnerability
- Do not publish or share findings without permission

## Examples

- "Test our chatbot for prompt injection (I own the system)"
- "Assess our RAG pipeline for indirect injection risks"
- "Run injection tests against our API endpoints"
