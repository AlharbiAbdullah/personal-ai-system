# First Principles

Break problems down to fundamental truths and rebuild from there.
Based on physics-based reasoning: only hard constraints are immutable.

## Core Methodology

### 1. Deconstruct
- List every assumption about the problem
- Identify what is actually known vs assumed
- Separate facts from conventions

### 2. Challenge
- Classify each constraint:
  - **Hard** (physics, math, laws): immutable, work within these
  - **Soft** (policy, convention, habit): challenge these
  - **Assumption** (unvalidated beliefs): test these first
- Ask "Why?" at each level until you hit bedrock

### 3. Reconstruct
- Build solution from only the hard constraints
- Ignore "how it's always been done"
- Consider cross-domain solutions (what would another field do?)

## Three Principles

1. **Physics First (Function Over Form)**: Only physical/mathematical limits are real constraints. Focus on what something needs to DO, not what it has historically looked like.
2. **Question Everything**: "Industry standard" is not a reason. Challenge conventions until you hit bedrock.
3. **Cross-Domain Synthesis & Rebuild**: Borrow solutions from unrelated fields. When patching stops working, rebuild from the hard constraints.

## Scope

Apply first-principles to the subsystem causing the actual constraint, not every system. Deconstructing everything wastes effort.

## Anti-Patterns to Avoid

- Reasoning by analogy ("Company X does it this way"). Analogies can be useful for exploration — but validate every analogy against first-principles reasoning before acting on it.
- Accepting market prices as fixed ("That's what it costs")
- Form fixation ("A database must be relational")
- Soft constraint worship ("We've always deployed on Fridays")

## Examples

- "First principles: should we use microservices or a monolith?"
- "Break down our deployment process from first principles"
- "Why does our data pipeline take 4 hours? Challenge assumptions."
