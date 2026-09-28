# Science

Apply the scientific method to any domain. Works for debugging code,
validating product ideas, making decisions under uncertainty, and
actual research. The cycle runs until confidence is sufficient.

## The Cycle

### 1. Goal
Define what you are trying to learn or prove.
State the question clearly. One question per cycle.

### 2. Observe
Gather existing data and evidence.
What do we already know? What patterns exist?

### 3. Hypothesize
Form a testable prediction based on observations.
"If X, then Y, because Z." Must be falsifiable.

### 4. Experiment
Design the smallest test that could disprove the hypothesis.
Control variables. Define success/failure criteria upfront.
Document upfront: "Success = [specific outcome]. Failure = [different outcome]. We will not change this mid-cycle."

### 5. Measure
Collect results from the experiment.
Quantify when possible. Record everything, including surprises.

### 6. Analyze
Compare results to the hypothesis.
Confirmed, partially confirmed, or refuted? Why?

### 7. Iterate
Update understanding. Form new hypothesis if needed.
Repeat the cycle with refined questions.

Stop the cycle when confidence is sufficient for the decision at hand. Define upfront: "High confidence = 3 supporting sources; low confidence = proceed with caveats; insufficient = defer decision."

## Application Domains

| Domain | Example Cycle |
|--------|--------------|
| Coding | Bug report, reproduce, hypothesize cause, test fix, verify |
| Product | User complaint, observe usage data, hypothesize, A/B test |
| Research | Question, literature review, hypothesis, experiment, publish |
| Decisions | Problem, gather options, predict outcomes, small test, measure |

## Guidelines

- One variable at a time. Changing multiple things invalidates results.
- Negative results are results. Document what did not work.
- Pre-register your success criteria. Do not move goalposts.
- Prefer small, fast experiments over large, slow ones.

## When NOT to use

Skip for low-cost reversible experiments. Best for: high-stakes decisions, product pivots, research questions.

## Examples

- "Scientific method: why is our API latency spiking?"
- "Help me design an experiment to test this product idea"
- "Apply the science cycle to our deployment failures"
- "What experiment would validate this assumption?"
