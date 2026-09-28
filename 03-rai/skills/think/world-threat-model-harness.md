# World Threat Model Harness

Maintain a persistent world model spanning 11 time horizons.
Test ideas against this model. Update it as conditions change.
Orchestrates RedTeam, FirstPrinciples, and Council skills for
deep analysis.

## Time Horizons

6 months, 1 year, 2 years, 3 years, 5 years, 7 years, 10 years,
15 years, 20 years, 30 years, 50 years.

Each horizon tracks: geopolitical shifts, technology trajectories,
economic conditions, social trends, climate/resource pressures.

## Storage

Model state: in-session only. For persistent world-model tracking across sessions, store summaries in `~/helm/10-knowledge/` or project memory.

## Three Tiers

### Fast
Lookup only, no new analysis (<5 min). Use for simple queries.

### Standard
Update relevant horizons with current data (~15 min). Use for most requests.

### Deep
Full refresh + RedTeam on assumptions + Council on tradeoffs (~45 min).
Orchestrates RedTeam for adversarial testing, FirstPrinciples for assumption
checks, and Council for multi-expert perspectives. Use for major decisions.

## Workflows

### TestIdea
Evaluate an idea against current world models.
Steps: identify relevant horizons, check alignment with trends,
stress-test assumptions, report viability per horizon.

### UpdateModels
Refresh world models with new information.
Steps: ingest new data, identify which horizons are affected,
update trend lines, flag model conflicts, reconcile.
When a prediction proves wrong, update the model and document what changed. Don't pretend the prediction never existed.

### ViewModels
Display current state of world models.
Steps: select horizons (all or specific), format current trends,
show confidence levels, highlight recent changes.

## Orchestration

- /RedTeam: Attack the model's assumptions
- /FirstPrinciples: Strip away soft constraints in projections
- /Council: Get multi-expert perspectives on contested trends

## Examples

- "Test this business idea against world trends"
- "Update models with the latest AI developments"
- "View the 5-year and 10-year horizons"
- "Deep analysis: how does [event] change our 2030 outlook?"
