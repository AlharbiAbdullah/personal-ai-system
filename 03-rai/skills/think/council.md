# Council

Structured multi-agent debate. Three rounds of collaborative-adversarial
discussion producing a transcript and final synthesis.

## Workflows

### DEBATE (Full)
Three-round structured discussion with 3-5 agents.

**Round 1 -- Opening Positions**
Each agent states their position with supporting reasoning.
No rebuttals yet. Pure position establishment.

**Round 2 -- Challenge and Response**
Agents challenge each other's positions directly.
Point out weaknesses, ask hard questions, present counter-evidence.

**Round 3 -- Synthesis**
Agents acknowledge valid points from others.
Refine positions based on the debate. Find common ground where it exists.

### QUICK
Each agent states its position once (parallel synthesis, no debate).
Moderator synthesizes immediately.
Use when time matters more than depth.

**Full vs Quick:** Quick = each agent states its position once (parallel synthesis, no debate). Full = three rounds with challenges and refinement.

## Agent Selection

Agents are chosen based on the topic. Default panel:

- **Advocate**: Argues for the strongest option
- **Critic**: Finds flaws, risks, and blind spots
- **Pragmatist**: Focuses on feasibility and implementation

Other available roles on request: Security Expert, Cost Analyst, User Advocate, Technical Lead, Historian. Request by role name.

For domain-specific debates, swap in relevant experts
(e.g., Security Expert, Cost Analyst, User Advocate).

## Process

1. **Frame the question**: State the decision or topic clearly
2. **Select agents**: Pick 3-5 with diverse viewpoints
3. **Run rounds**: Execute the chosen workflow
4. **Produce transcript**: Full record of all positions and exchanges
5. **Synthesize**: Moderator summary with recommendation

## Tiebreaker

If the council ties, moderator presents both views, notes areas of disagreement, and recommends either "proceed with mitigation X" or "defer pending more information on Y".

## Output Format

```
COUNCIL: [Topic]  |  AGENTS: [List]
--- Round 1: Positions ---
[Agent]: [Position] ...
--- Round 2: Challenge ---
[Agent] -> [Agent]: [Challenge] ...
--- Round 3: Synthesis ---
[Agent]: [Refined position] ...
--- VERDICT ---
[Moderator synthesis and recommendation]
```

## Examples

- "Council: should we use PostgreSQL or DynamoDB for this project?"
- "Quick debate: monorepo vs polyrepo"
- "Run a council on whether to build or buy our auth system"
