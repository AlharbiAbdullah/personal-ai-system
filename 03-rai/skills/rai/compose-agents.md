---
name: compose-agents
description: >
  Custom agent composition and orchestration.
  USE WHEN the user wants to create a specialized agent with unique expertise,
  list available agents, or spawn multiple agents to work in parallel on
  different aspects of a problem.
---

# Agents

Create, manage, and deploy specialized agents with focused expertise.
Each agent gets a name, role, expertise area, and behavioral instructions.

Agents are stored in `~/helm/03-rai/agents/`, registered in `~/helm/03-rai/agents/MANIFEST.md`. Tier and orchestration rules live in that manifest.

## Workflows

### CREATE
Define a new agent with specialized knowledge and behavior.

1. Gather agent spec: name, role, expertise domain, behavioral rules
2. Write the agent definition (system prompt, tool access, constraints)
3. Store in agent registry for reuse
4. Confirm agent is ready with a summary of capabilities

### LIST
Show all available agents with their roles and expertise areas.

1. Read agent registry
2. Display: name, role, domain, last used
3. Flag any agents that may be outdated

### SPAWN PARALLEL
Run multiple agents simultaneously on different parts of a problem using Claude Code's built-in `Agent` tool with multiple parallel tool calls in one message.

1. Decompose the problem into independent sub-tasks
2. Assign each sub-task to the best-fit agent
3. Issue one assistant message with N parallel `Agent(...)` tool calls
4. Collect each agent's return value
5. Merge: deduplicate findings; for genuinely conflicting outputs, present both views and recommend a tiebreaker

### UPDATE
Modify an existing agent's spec.

1. Read the agent file in `~/helm/03-rai/agents/`
2. Apply the requested changes to expertise, tools, or rules
3. If the agent's name or scope changed, update `~/helm/03-rai/agents/MANIFEST.md`

### DELETE
Remove an agent that is no longer used.

1. Confirm with the user
2. Delete the agent file in `~/helm/03-rai/agents/`
3. Remove the row from `~/helm/03-rai/agents/MANIFEST.md`
4. Delete (do not archive) per the "delete over archive" preference

## Output Format

Agent definitions follow this structure:

```
Agent: [Name]
Role: [One-line role description]
Expertise: [Domain areas]
Tools: [Allowed tool set]
Rules: [Behavioral constraints]
```

Parallel results are merged into a single coherent response with
attribution to each agent's contribution.

## Concrete agent example

```
Agent: db-migration-expert
Role: Schema change reviewer for production databases
Expertise: PostgreSQL, MySQL, online migrations, locking, rollback strategies
Tools: Read, Bash, Grep
Rules:
  - Never propose a migration without an explicit rollback plan
  - Flag any locking change on tables >10M rows
  - Require a backfill estimate for new NOT NULL columns
```

## Examples

- "Create an agent that specializes in security code review"
- "List my agents"
- "Spawn three agents: one for frontend, one for backend, one for infra"
- "Create a data pipeline expert agent"
- "Delete the unused mobile-design-reviewer agent"
