# System Design

## Scope

This document describes the target architecture for **AI Network Mapper**, a defensive security analytics platform that converts network scan data into asset inventory, vulnerability intelligence, attack-path analysis, MITRE ATT&CK mapping, and AI-assisted explanations.

The current repository contains no application source code at the time this document was created. This design is therefore derived from the project brief, not from an existing implementation.

## Goals

- Discover and normalize network assets from scan providers such as Nmap.
- Store authoritative inventory, scan history, vulnerability data, and audit records in PostgreSQL.
- Store topology, trust, exposure, and attack-path relationships in Neo4j.
- Calculate risk using CVSS, EPSS, exposure, exploitability context, and asset criticality.
- Map findings and paths to MITRE ATT&CK tactics and techniques.
- Provide AI-generated explanations without allowing AI output to make final security decisions.
- Support scheduled scans, delta analysis, alerting, and interactive visualization.
- Remain defensive and analytical; do not generate exploits, payloads, or automated offensive actions.

## Non-Goals

- Exploit generation.
- Automated exploitation.
- Payload creation.
- Credential theft or credential harvesting.
- Direct offensive attack execution.
- Treating AI output as authoritative security policy.

## High-Level Architecture

```text
              +----------------------+
              |      React UI        |
              |  Vite + TypeScript   |
              +----------+-----------+
                         |
                         | HTTPS / JSON API
                         v
              +----------------------+
              |      FastAPI API     |
              | auth, RBAC, REST     |
              +----+------------+----+
                   |            |
                   |            | enqueue jobs
                   |            v
                   |   +------------------+
                   |   | Celery Workers   |
                   |   | scans, imports,  |
                   |   | graph builds, AI |
                   |   +----+--------+----+
                   |        |        |
                   v        v        v
       +--------------+ +--------+ +----------------+
       | PostgreSQL   | | Redis  | | External Scan  |
       | source of    | | cache, | | Providers      |
       | record       | | queue  | | Nmap first     |
       +------+-------+ +--------+ +----------------+
              |
              | graph projection events
              v
       +--------------+        +------------------+
       | Neo4j        |<-------| Graph Engine     |
       | topology and |        | projection, path |
       | attack graph |        | algorithms       |
       +------+-------+        +------------------+
              |
              v
       +--------------+
       | Prometheus   |
       | Grafana      |
       +--------------+
```

## Core Components

### API Service

The API service is the public application boundary. It should be implemented with FastAPI and should own:

- Authentication and authorization.
- Request validation.
- API rate limiting.
- Request logging and audit trails.
- Asset, vulnerability, graph, scan, and analysis endpoints.
- Job submission and job status APIs.
- Health checks.

The API service should not run scan engines directly in request handlers. Scan requests should validate intent, authorize the user, persist a scan record, and enqueue a background job.

### Scan Governance

Scan creation must always pass through policy validation before target validation and queue submission. This prevents accidental or unauthorized scanning and makes scan scope auditable.

Required flow:

```text
User
  |
  v
Scan Request
  |
  v
Policy Validation
  |
  v
Target Validation
  |
  v
Queue Scan
```

The platform should model scan governance with `scan_policies`. A policy defines allowed CIDR ranges, blocked CIDR ranges, maximum target count, maximum scan rate, provider restrictions, and enabled state. Scanning must never bypass policy validation, including scheduled scans and API-triggered scans.

Users should also select a `scanner_profile` rather than supplying raw scanner arguments. Profiles centralize provider-specific configuration such as quick discovery, service detection, safe internal scanning, and full inventory scanning. The API may expose controlled profile selection, but raw scanner flags should remain internal to trusted configuration.

### Discovery Engine

The discovery engine normalizes output from external scanners into internal domain models.

The first provider should be Nmap. The design should expose a provider interface named `DiscoveryProvider` so future providers can be added without rewriting ingestion:

- Masscan.
- RustScan.
- Shodan.
- Nessus.
- OpenVAS.

The MVP is explicitly limited to Nmap XML ingestion. Masscan, RustScan, OpenVAS, and Nessus are not part of the MVP, although the `DiscoveryProvider` abstraction should preserve a future extension path.

Provider output should be converted into a common scan result format before persistence. Raw provider output should be retained for traceability, but downstream systems should consume normalized entities.

Failure handling requirements:

- Missing or disabled scan policy must reject scan creation before target validation.
- Scanner profile provider must be allowed by the selected scan policy.
- Invalid targets must fail validation before a job is queued.
- Provider execution errors must mark the scan as failed with a structured error.
- Partial results must be persisted with explicit scan status, not silently treated as complete.
- Provider timeouts must be configurable and observable.

### Asset Inventory

PostgreSQL is the system of record for inventory data:

- Hosts.
- Services.
- Vulnerabilities.
- Scan runs.
- Findings.
- MITRE mappings.
- AI explanations.
- Users, roles, audit logs, and alerts.
- Scan policies and scanner profiles.

Inventory writes should be idempotent. Repeated scans of the same target should update `last_seen_at`, create scan observations, and preserve history rather than duplicating canonical assets.

Asset tagging should be supported through reusable asset tags such as `Production`, `Development`, `Database`, `PCI`, `Critical`, `DMZ`, and `DomainController`. Tags support filtering, risk prioritization, reporting, and attack path prioritization without overloading host naming or network segment membership.

### Graph Engine

Neo4j stores derived graph state optimized for topology queries and path analysis. It should not be the only copy of canonical asset data.

The graph engine is responsible for:

- Projecting PostgreSQL inventory into Neo4j nodes and relationships.
- Maintaining graph consistency after scan ingestion.
- Running shortest-path and weighted-path analysis.
- Returning graph slices for visualization.
- Marking path results with risk and MITRE context.

Graph writes should be deterministic and idempotent. Every Neo4j node that maps to PostgreSQL data should carry a stable external identifier.

Graph projection must be tracked as a first-class job. Projection failures must never invalidate PostgreSQL inventory, retries must be idempotent, and graph freshness must be visible through API responses and operational metrics.

### Vulnerability Intelligence

The vulnerability intelligence module enriches services and findings with:

- CVE metadata.
- CVSS scores.
- EPSS probability.
- Severity.
- Reference URLs.
- Known affected products and versions where available.

Risk scoring must not rely on CVSS alone. The platform should calculate a composite score using at least:

- CVSS severity.
- EPSS probability.
- Network exposure.
- Asset criticality.
- Service sensitivity.
- Known exploit availability as metadata only, not as exploit execution support.

Risk models should be versioned explicitly. Each stored risk score must reference a specific risk model definition containing the scoring version, name, description, and formula summary. Historical scores must remain reproducible, and future scoring changes must not rewrite prior calculations.

### MITRE ATT&CK Mapping

The MITRE module maps findings and graph paths to tactics and techniques. The mapping should be evidence-based and explainable.

Examples:

- SMBv1 exposure may map to lateral movement and credential access depending on context.
- Weak authentication findings may map to credential access.
- Exposed remote administration services may map to initial access or lateral movement depending on network segment and trust relationships.

Mappings should store both ATT&CK IDs and the local evidence used to justify the mapping.

### Attack Path Engine

The attack path engine runs graph algorithms against Neo4j data:

- BFS for unweighted shortest paths.
- DFS for bounded exploration and graph traversal.
- Dijkstra or equivalent weighted traversal for lowest-risk or lowest-cost path analysis.

The engine should support:

- Attack chain discovery.
- Choke point identification.
- Critical asset analysis.
- Path scoring.
- Path explanation.

The engine should not execute attacks. It models plausible exposure and trust relationships for defensive analysis.

### AI Security Analyst

The AI security analyst is an optional enhancement layer for explaining findings, paths, and risk scores. AI must be disabled by default, and the system must function fully without AI using inventory, deterministic risk scores, MITRE mapping, and graph analysis.

When enabled, it should be implemented behind an `AISecurityAnalyst` abstraction with provider adapters for:

- Ollama.
- OpenAI-compatible APIs.

AI output must be treated as generated explanation, not ground truth. The application should preserve the evidence that was sent to the model and should distinguish model-generated text from deterministic findings. Provider failure must not affect scan ingestion, inventory, risk scoring, MITRE mapping, graph projection, or alerting.

Safety requirements:

- Do not ask the model to generate exploit code, payloads, or offensive commands.
- Restrict prompts to defensive explanation and remediation guidance.
- Log provider errors and latency.
- Store model name, provider, prompt version, and source evidence references.

### Continuous Monitoring

Continuous monitoring should schedule recurring scans and compare results over time.

Delta detection should identify:

- New hosts.
- Missing hosts.
- New services.
- Closed services.
- New vulnerabilities.
- Resolved vulnerabilities.
- Changed topology.
- Changed risk score.

Alert generation should be rule-based and auditable. AI may summarize alerts, but alert creation should not depend solely on AI output.

### Dashboard

The frontend should provide operational views, not a marketing landing page:

- Asset inventory.
- Graph visualization with Cytoscape.js.
- Risk dashboard.
- Vulnerability detail.
- Attack path explorer.
- Scan history and timeline.
- Alerts.
- AI explanation panel.

The graph UI should request bounded graph slices from the API rather than loading the entire graph for large environments.

## Primary Data Flow

```text
1. User submits authorized scan request with scan policy and scanner profile.
2. API validates the selected scan policy.
3. API validates targets against allowed and blocked policy scope.
4. API creates scan_run and enqueues discovery job in Redis.
5. Celery worker runs the selected DiscoveryProvider using the scanner profile.
6. Worker stores raw scan artifact and normalized observations.
7. Inventory service upserts hosts, services, and findings.
8. Vulnerability intelligence enriches findings.
9. Risk engine calculates composite risk with a specific risk model.
10. Graph projection job projects changes into Neo4j.
11. Graph analytics and attack path jobs use only fresh or explicitly marked stale graph state.
12. MITRE module maps findings and paths to tactics and techniques.
13. API serves inventory, risk, graph, and analysis views to the dashboard.
```

## API Surface

Initial endpoints:

- `POST /scan`
- `GET /scan/{id}`
- `GET /assets`
- `GET /assets/{id}`
- `GET /vulnerabilities`
- `GET /attack-paths`
- `GET /graph`
- `POST /analyze`
- `GET /health`
- `GET /health/db`
- `GET /health/neo4j`
- `GET /health/cache`

Recommended additions:

- `GET /scans`
- `GET /findings`
- `GET /findings/{id}`
- `GET /alerts`
- `POST /scan-schedules`
- `GET /scan-schedules`
- `PATCH /scan-schedules/{id}`
- `GET /audit-events`

## Security Model

Minimum controls:

- JWT authentication.
- RBAC for administrative, analyst, and read-only users.
- Rate limiting on public API endpoints.
- Mandatory scan policy validation before any scan job is queued.
- Strict target validation before scan scheduling.
- Audit trail for scan creation, configuration changes, AI analysis requests, and user management.
- Request logging with sensitive values redacted.
- No direct exposure of scanner execution primitives to users.
- No secrets stored in source code or committed configuration.

Open-source contribution boundaries:

- No offensive automation.
- No exploit generation.
- No payload generation.
- No credential abuse features.
- Project functionality must remain defensive and analytical.

Future open-source readiness documents:

- `SECURITY_BOUNDARIES.md`.
- `THREAT_MODEL.md`.
- `RESPONSIBLE_DISCLOSURE.md`.

Recommended roles:

- `admin`: user management, settings, integrations, all scans.
- `analyst`: run scans, view assets, view risks, request AI analysis.
- `viewer`: read-only access to dashboards and reports.
- `auditor`: read-only access to audit records and reports.

## Observability

Structured logging should use `structlog`. Logs should include:

- Request ID.
- User ID where available.
- Scan ID where available.
- Job ID where available.
- Provider name.
- Duration.
- Status.
- Error code.

Prometheus metrics should include:

- API latency.
- API error count.
- Scan duration.
- Scan success/failure count.
- Queue depth.
- Graph node count.
- Graph relationship count.
- Graph projection duration.
- Graph projection failure count.
- Graph freshness age.
- AI provider latency.
- AI provider error count.

Grafana dashboards should cover:

- API health.
- Worker health.
- Queue health.
- Scan throughput.
- Graph size.
- AI latency and failures.

## Deployment Topology

Local development should use Docker Compose:

- FastAPI API.
- Celery worker.
- Celery beat or scheduler.
- PostgreSQL.
- Neo4j.
- Redis.
- Frontend dev server.
- Prometheus.
- Grafana.

Production deployment should separate:

- API replicas.
- Worker replicas.
- Scheduler singleton.
- PostgreSQL managed service or hardened cluster.
- Neo4j managed service or hardened cluster.
- Redis managed service or hardened instance.
- Frontend static hosting.
- Observability stack.

## Scaling Targets

The design target is:

- 10,000 hosts.
- 100,000 services.
- 500,000 graph relationships.

Design implications:

- Use database indexes from the first migration.
- Use bounded pagination for list APIs.
- Avoid full graph responses in the UI.
- Cache expensive read models in Redis where appropriate.
- Use idempotent background jobs so retries are safe.
- Keep graph projections incremental where possible.

## Consistency Model

PostgreSQL should be treated as the authoritative source. Neo4j should be treated as a derived projection.

If graph projection fails after inventory persistence:

- The scan should remain persisted.
- The projection failure should be visible in `graph_projection_jobs`.
- A retry should be possible without duplicating graph nodes.
- API graph endpoints should surface stale projection status when relevant.

## Key Risks

- Scanner output variability can corrupt inventory if normalization is too loose.
- Graph projection can drift from PostgreSQL if idempotency is not enforced.
- AI responses can overstate certainty unless evidence boundaries are explicit.
- Large graph responses can overwhelm the frontend.
- Poor target validation can create legal and operational risk.
- CVE/product matching can create false positives if version evidence is weak.

## Minimum Correct First Implementation

The first implementation should be intentionally narrow:

1. Authenticated API.
2. Nmap XML ingestion only.
3. Scan policies and scanner profiles.
4. PostgreSQL inventory for hosts, services, scans, findings, asset tags, and risk models.
5. Neo4j projection for hosts, services, vulnerabilities, and `RUNS` / `HAS_VULNERABILITY`.
6. Deterministic risk score v1.
7. Basic graph API.
8. Read-only dashboard views.

This avoids building provider plugins, complex AI workflows, and advanced attack path scoring before the core data model is proven. Masscan, RustScan, OpenVAS, and Nessus remain future provider integrations, not MVP deliverables.
