# Architecture

AI Network Mapper is split into five operational layers:

1. FastAPI API boundary for auth, RBAC, validation, audit, health, and read APIs.
2. Background workers for scan ingestion, enrichment, graph projection, and scheduled monitoring.
3. PostgreSQL as the authoritative source of inventory, findings, users, policies, audit records, and risk scores.
4. Neo4j as a derived graph projection for topology, trust, vulnerability, and path analysis.
5. React dashboard for asset inventory, graph slices, risk views, timelines, and optional explanations.

The API must not execute scanner processes directly. Scan requests are policy-validated, persisted, audited, and then queued for workers.

## Design Rules

- PostgreSQL is source of truth.
- Neo4j is retryable derived state.
- AI is optional and disabled by default.
- Risk scoring is deterministic and versioned.
- Scanner providers normalize into internal discovery results.
- Graph queries must be bounded by depth and result size.
- The product is defensive and analytical only.

## First Vertical Slice

The first implemented slice supports:

- Nmap XML parsing.
- Typed asset/service discovery models.
- JWT/RBAC-protected API routes.
- Composite risk score v1.
- Defensive graph algorithms.
- Bounded React dashboard graph visualization.
- Docker Compose local stack.

