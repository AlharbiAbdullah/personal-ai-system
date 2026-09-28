---
name: monitoring
description: >
  Observability: metrics, logs, traces, alerting. Grafana, Prometheus,
  OpenTelemetry, Loki. USE WHEN the user needs to instrument a service,
  debug production, or set up alerts.
---

# Monitoring

Observability = the three pillars (metrics, logs, traces) + alerting on top.

## When to use

- New service going to production
- Existing service has "works on my machine" problems in prod
- Oncall is firefighting blind — adding visibility
- SLO definition + measurement

## When NOT to use

- Pure local dev — `console.log` is fine
- Obsessing over dashboards for a service no one uses

## The three pillars

### Metrics
- Numeric time series (counters, gauges, histograms)
- Cheap, aggregatable, great for trend + alerting
- Bad for high-cardinality (per-user metrics blow up storage)
- **Prometheus** = default: pull-based scrape + PromQL + alertmanager
- **Grafana Mimir, VictoriaMetrics, Thanos** = scalable Prometheus backends
- **Datadog, New Relic, Honeycomb** = managed SaaS

Metrics to track for any HTTP service (USE/RED):
- **RED**: Rate (req/s), Errors (err/s), Duration (latency)
- **USE**: Utilization, Saturation, Errors (for resources — CPU, memory, disk, network)

### Logs
- Structured JSON > free-text
- Include request-id / trace-id for correlation
- Volume grows fast; retention cost matters
- **Loki** = Grafana's log store (indexed labels only — cheap)
- **Elasticsearch / OpenSearch** = full-text indexing
- **CloudWatch, Datadog Logs, Splunk** = managed

### Traces
- End-to-end request flow across services
- Spans with parent-child relationships
- **OpenTelemetry (OTel)** = standard SDK + protocol
- **Tempo, Jaeger, Zipkin** = open-source backends
- **Honeycomb, Lightstep, Datadog APM** = managed

## Alerting principles

- **Alert on symptoms, not causes** — "site is slow for users" not "CPU >80%"
- **SLO-based alerts** — burn rate of your error budget (3× per 1h OR 1× per 6h)
- **Runbook per alert** — what to check, how to fix, who to escalate to
- **Silence during maintenance** — alertmanager silences or schedules
- **Tune aggressively** — alert fatigue is real; if an alert fires twice without action, fix or delete

## Instrumentation

### OpenTelemetry — unified approach
Use the OTel SDK for your language. It emits metrics, logs, and traces via one API, exported to a Collector that fans out to backends.

```python
# Python example
from opentelemetry import trace, metrics
tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)

request_counter = meter.create_counter("http_requests_total")

with tracer.start_as_current_span("handle_request") as span:
    span.set_attribute("user.id", user_id)
    request_counter.add(1, {"route": "/api/v1/foo", "status": "200"})
```

### Prometheus client (if not using OTel)
```python
from prometheus_client import Counter, Histogram
REQUESTS = Counter("http_requests_total", "HTTP requests", ["route", "status"])
LATENCY = Histogram("http_request_duration_seconds", "Request latency", ["route"])
```

## Dashboards

One dashboard per service with:
- **Overview row**: RED metrics, error budget consumption, recent deploys
- **Latency row**: p50, p95, p99 per endpoint
- **Saturation row**: CPU, memory, connection pool, queue depth
- **Dependency row**: latency + error rate per downstream dep
- **Deploy annotations**: mark each release on graphs

Keep dashboards focused. If you have 40 panels, it's a data graveyard, not a tool.

## Logs — structured fields

Always include:
- `timestamp` (ISO 8601)
- `level` (DEBUG, INFO, WARN, ERROR)
- `service` name
- `trace_id` + `span_id` (from OTel)
- `user_id` or request-identifying field when relevant
- `message` human-readable summary
- Any extra context as typed fields (not interpolated into message)

## PromQL cheatsheet

```promql
# Rate of requests in the last 5 minutes
sum(rate(http_requests_total[5m])) by (route)

# p95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, route))

# Error rate as % of total
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))

# Alert: 5xx rate over 5% for 5 min
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
```

## Cost management

- Metrics cardinality explodes cost. Don't add high-cardinality labels (user-id, request-id).
- Logs: tier retention (hot 7d, warm 30d, cold 1y). Keep debug logs off by default in prod.
- Traces: head sampling (1-10%) + tail sampling for errors (retain all errors, sample success).

## Anti-patterns

- Silent services — no logs, no metrics, no traces
- Per-user labels on Prometheus metrics — blows up series count
- Alerts on every anomaly — fatigue → ignored alerts
- No runbooks — oncall spends 20 min figuring out what the alert means
- Logs without trace-id — can't correlate across services
- 40-panel dashboards that no one reads
- Polling health endpoints too aggressively — adds load

## Examples

- "Instrument the OpenKit API with OpenTelemetry"
- "Set up SLO alerts for 99.9% availability on Helios chat"
- "Why is latency high — what to look at?"
- "Create Grafana dashboard for Matchbox compliance pipelines"
