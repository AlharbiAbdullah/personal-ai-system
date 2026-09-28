---
name: load-test
description: >
  Load, stress, soak, and performance testing. USE WHEN the user needs to
  verify a system handles target traffic — k6, Locust, Artillery, Gatling.
---

# Load Test

Prove the system can handle the traffic you expect + a safety margin.

## When to use

- Pre-launch validation for a new service
- Before a known traffic surge (product launch, Black Friday, marketing push)
- Regression testing after performance-critical changes
- Capacity planning — how much headroom do we have?

## When NOT to use

- Feature correctness — that's integration / e2e
- One-shot ops scripts
- Very low traffic services where load isn't the constraint

## Types

| Type | Goal | Duration | Load profile |
|---|---|---|---|
| **Smoke** | Baseline works | 1–5 min | Low (1–10 VUs) |
| **Load** | Validate expected traffic | 10–30 min | Target steady |
| **Stress** | Find breaking point | 15–30 min | Ramp up until failure |
| **Spike** | Survive traffic surge | 5–10 min | Sudden jump to 10× |
| **Soak** | Catch leaks + degradation | 4–24 hours | Target steady |

## Tool choice

- **k6** — JavaScript-driven, clean syntax, great cloud + local. Preferred default.
- **Locust** — Python-driven. Good if your team is Python-heavy.
- **Gatling** — Scala. Great reports. Steeper learning curve.
- **Artillery** — Node.js. Lightweight, good YAML config.
- **JMeter** — Java. Mature, heavy, GUI-oriented (can be scripted).

## k6 skeleton

```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },   // ramp to 100 VUs
    { duration: '5m', target: 100 },   // stay at 100
    { duration: '2m', target: 0 },     // ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% under 500ms
    http_req_failed: ['rate<0.01'],    // <1% errors
  },
};

export default function() {
  const res = http.get('https://api.example.com/v1/users');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'body not empty': (r) => r.body.length > 0,
  });
  sleep(1);
}
```

## Process

1. **Define target profile**
   - Peak RPS you expect
   - Latency SLO (p50, p95, p99)
   - Acceptable error rate
   - Duration of peak

2. **Warm up the test environment**
   - Caches primed
   - JIT-compiled code warm
   - Connection pools established

3. **Run in stages**
   - Smoke → Load → Stress → Soak
   - Each stage informs the next

4. **Measure + alert**
   - Latency percentiles (not averages)
   - Error rate
   - Throughput
   - Resource saturation (CPU, memory, DB connections, queue depth)

5. **Find bottlenecks**
   - Where does latency grow first?
   - Where do errors start?
   - What resource saturates?
   - Profile the slowest component

6. **Fix + re-test**
   - Single variable per run
   - Document the change + result

## Where to run tests

- **Local** — smoke + small load
- **Staging env with prod-like data** — load + stress + spike
- **Prod during off-peak** — soak (with feature flags to contain blast radius)
- **Cloud load generators** (k6 Cloud, BlazeMeter) — distributed load from multiple regions

## Metrics to collect

- Throughput (RPS, TPS)
- Latency percentiles (p50, p95, p99, max)
- Error rate by endpoint + status code
- Resource metrics (CPU, memory, IOPS, connections)
- Downstream dep metrics (DB queries, cache hit rate, external API latency)

## Anti-patterns

- Testing against prod traffic accidentally (hitting real users)
- Averaging latency — hides tail problems
- Testing only the happy path — failure modes matter more
- Ignoring think time — real users aren't in a loop
- Running from one location — misses regional issues
- No baseline — you can't detect regression without one

## Examples

- "Load test the Helios chat API at 500 RPS"
- "Find the breaking point for the Matchbox scan endpoint"
- "Soak test the Taskflow ingestion pipeline over 24h"
- "Spike test: can we handle 10× traffic at launch?"
