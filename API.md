# API

Base URL for local development:

```text
http://localhost:8000
```

Most endpoints require a JWT bearer token with one of the documented roles. Health endpoints are public.

## Health

```http
GET /health
GET /health/db
GET /health/neo4j
GET /health/cache
GET /metrics
```

## Discovery

```http
POST /scan
GET /scan/{scan_id}
```

`POST /scan` accepts a scan policy, scanner profile, provider, scan type, and target list. Scanner execution is not run in the request handler.

## Inventory

```http
GET /assets
GET /assets/{asset_id}
GET /vulnerabilities
```

The current implementation exposes the route structure and typed response models. PostgreSQL-backed list/detail behavior is the next persistence milestone.

## Graph And Attack Paths

```http
GET /graph
GET /attack-paths
```

Graph responses must remain bounded. Attack-path responses are defensive models and do not include execution commands.

## Analysis

```http
POST /analyze
```

AI analysis is disabled by default. The disabled provider returns deterministic evidence summaries so the platform remains usable without model access.

