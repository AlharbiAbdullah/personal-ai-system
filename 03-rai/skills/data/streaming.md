---
name: streaming
description: >
  Real-time streaming patterns: Kafka, Kinesis, Flink, CDC. USE WHEN the
  user needs event-driven data flow, sub-minute latency pipelines, or
  change-data-capture integration.
---

# Streaming

Event-time data in motion. Producer → broker → consumer with low latency.

## When to use

- Sub-minute data freshness (dashboards, fraud detection, feature stores)
- Change Data Capture from OLTP to warehouse / search / cache
- Event-driven microservices (see `/architecture/patterns`)
- IoT / telemetry ingestion at scale

## When NOT to use

- Batch is fine — scheduled jobs are simpler + cheaper
- Under 10k events/sec and no latency need — overkill
- Exactly-once semantics required without careful design — streaming makes it hard

## Core vocabulary

- **Producer** — sends events to broker
- **Broker** — durably stores + distributes events (Kafka, Kinesis, NATS JetStream, Pulsar)
- **Topic / stream** — named channel; partitioned for parallelism
- **Partition** — ordered sub-log within a topic; consumer parallelism = partition count
- **Consumer** — reads events; tracks offset of last processed
- **Consumer group** — multiple consumers sharing work across partitions
- **Offset** — position in the partition log
- **Watermark** — stream processor's progress indicator for event-time
- **Exactly-once / at-least-once / at-most-once** — delivery semantics

## Brokers

### Kafka
- De facto standard, open source
- Horizontal scale via partitions + replicas
- Retention configurable per topic (time or size)
- Ecosystem: Kafka Connect (CDC + sinks), Kafka Streams (JVM), Schema Registry (Avro/Protobuf)
- Managed: Confluent Cloud, AWS MSK, Aiven

### Kinesis
- AWS-native streaming
- Shard-based partitioning (capacity per shard)
- Integrates with Firehose (easy sink to S3/Redshift), Lambda, KCL
- Pay for shards (steady cost); on-demand mode for spiky workloads

### Pulsar
- Decouples compute + storage (BookKeeper); tiered storage
- Multi-tenant, geo-replication built in
- Smaller ecosystem than Kafka but growing

### NATS JetStream
- Lightweight, low-latency
- Good for microservice messaging, not analytics scale

## Stream processors

### Flink
- True streaming (not micro-batch)
- Event-time processing with watermarks + windows
- Stateful operations with checkpoints to durable store
- Exactly-once supported end-to-end with Kafka
- SQL API (Flink SQL) or DataStream API

### Spark Structured Streaming
- Micro-batch model; near-real-time (seconds, not ms)
- Same API as Spark batch — easy ramp-up for Spark teams
- Checkpoints for fault tolerance
- Good for jobs already in Spark ecosystem

### Kafka Streams
- JVM library embedded in your app — no separate cluster
- Good for simple transformations + stateful aggregates
- Tightly coupled to Kafka

### ksqlDB
- SQL over Kafka topics; simpler than Streams for SQL-first teams
- Limited to Kafka as source/sink

## CDC (Change Data Capture)

### Debezium
- Reads DB transaction log (Postgres WAL, MySQL binlog, etc.)
- Emits one event per row change to Kafka
- Snapshots on startup for initial load
- Preferred for Postgres → Kafka flows

### Fivetran / Airbyte
- Managed CDC from many sources to warehouses
- Less control but less ops

### DIY polling
- Don't. Use the log. Polling misses deletes + updates-then-deletes.

## Windowing

For aggregations over time:
- **Tumbling** — fixed non-overlapping buckets (every 5 min)
- **Sliding** — overlapping windows (every 5 min, updated every 1 min)
- **Session** — gaps define boundaries (user's session ends after 30 min idle)

Key decision: **event time** (when it happened) vs **processing time** (when we saw it). Event time needs watermarks to handle late arrivals.

## Exactly-once semantics

Hard. Requires:
- Idempotent producer (avoid duplicate writes on retry)
- Transactional writes spanning producer + consumer commit
- Idempotent consumer (handle reprocessing of the same event)
- Exactly-once sink (transactional output to DB/warehouse)

If you don't need exactly-once, **at-least-once + idempotent consumer** is the pragmatic default.

## Schema + evolution

- Use a schema registry (Avro, Protobuf, JSON Schema)
- Backward-compatible changes: add optional fields, never remove
- Forward-compatible: consumer ignores unknown fields
- Versioned topics when breaking changes are unavoidable

## Monitoring

- Producer: throughput, error rate, retries, batch size
- Broker: partition skew, ISR (in-sync replicas), under-replicated partitions, disk
- Consumer: lag (messages behind head of topic — THE key metric), throughput, error rate
- Lag alerting: threshold on lag per consumer group

## Anti-patterns

- Partition key skew — one partition gets all traffic
- Too few partitions — cap on consumer parallelism
- Too many partitions — overhead + balance cost
- Unbounded keyed state without TTL — grows forever
- Synchronous writes in the producer's hot path — blocks under broker slowness
- Consumers doing heavy work per message — use batching or async downstream calls

## Examples

- "Design a CDC pipeline from Helios OLTP to Dremio"
- "Which streaming engine for a local telco real-time fraud system?"
- "Set up Kafka consumer group for event fan-out across 3 microservices"
- "Event-time vs processing-time for analytics dashboard"
