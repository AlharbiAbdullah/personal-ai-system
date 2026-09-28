# Red Team

Attack ideas before reality does. Run parallel adversarial agents
that decompose, challenge, and reconstruct arguments to find blind
spots and failure modes.

## Five-Phase Protocol

### 1. Decomposition
Break the target (idea, plan, argument) into its core claims,
assumptions, and dependencies.

### 2. Parallel Analysis
Use extended thinking to internally generate 3-5 parallel adversarial perspectives (Logical, Empirical, Adversarial, Systemic, Temporal). Present findings as one unified report — no multi-agent harness needed.

- **Logical**: Find contradictions, fallacies, circular reasoning
- **Empirical**: Challenge with data, counterexamples, base rates
- **Adversarial**: What would a motivated opponent exploit?
- **Systemic**: Second-order effects, unintended consequences
- **Temporal**: What breaks in 6 months? 2 years? 5 years?

### 3. Synthesis
Merge findings. Deduplicate. Rank vulnerabilities by severity
and likelihood.

### 4. Steelman
Before delivering criticism, strengthen the original argument.
Present the best possible version of the idea. This prevents
shallow or unfair attacks.

### 5. Counter-Argument
Present findings as: vulnerability, severity, evidence, and
suggested mitigation. Always pair criticism with a path forward.

## Workflows

### ParallelAnalysis
Full five-phase protocol. For important decisions and plans.

### AdversarialValidation
Quick red team: 2-3 attack angles, no steelman phase.
For fast sanity checks on ideas.

## Output

- Steelmanned version of the original argument
- Ranked vulnerability list (critical, high, medium, low)
- Each vulnerability: description, evidence, mitigation
- Overall assessment: proceed, proceed with caution, reconsider

## Examples

- "Red team our migration plan to Kubernetes"
- "Attack this business proposal: [description]"
- "Find weaknesses in my argument for [position]"
- "Adversarial validation: should we open-source this tool?"

## When NOT to use

Skip RedTeam when: the idea is already stress-tested, the downside is trivial/reversible, or timeline is too tight for careful critique. Best for: decisions with large reversible downside, novel strategies, high-impact bets.
