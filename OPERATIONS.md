# Operations

## Health Checks

- `/health`
- `/health/db`
- `/health/neo4j`
- `/health/cache`

## Metrics

Prometheus scrapes `/metrics`.

Important production metrics:

- API latency and errors.
- Scan duration.
- Scan success and failure counts.
- Queue depth.
- Graph node and relationship counts.
- Graph projection freshness.
- AI provider latency and errors.

## Failure Modes

- Database unavailable: API should reject writes and keep health degraded.
- Redis unavailable: scan queueing should fail explicitly.
- Neo4j unavailable: inventory remains valid and projection status is failed.
- AI provider unavailable: deterministic workflows continue.
- Scanner timeout: scan status records a sanitized failure reason.

