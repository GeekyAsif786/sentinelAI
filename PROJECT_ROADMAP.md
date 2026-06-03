# Project Roadmap

## Scope

This roadmap turns the AI Network Mapper brief into an implementation sequence. The current repository has no application source code, so the roadmap starts at architecture and scaffolding rather than refactoring existing modules.

The roadmap intentionally avoids production code in this documentation phase.

## Delivery Principles

- Build the smallest correct vertical slice before expanding providers or AI features.
- Keep PostgreSQL as the source of truth and Neo4j as a derived projection.
- Make all background jobs idempotent from the first implementation.
- Add scan policy governance before exposing scan execution.
- Treat AI as optional explanation, not authority.
- Avoid offensive capabilities by design.

## Phase 0: Project Foundation

Goal: Create a maintainable project skeleton and development workflow.

Deliverables:

- Repository layout for backend, frontend, docs, infrastructure, and tests.
- Docker Compose for local PostgreSQL, Neo4j, Redis, API, worker, frontend, Prometheus, and Grafana.
- Backend dependency management.
- Frontend dependency management.
- Linting and formatting configuration.
- Environment configuration template.
- Initial README with local setup.
- CI workflow for linting and tests.

Acceptance criteria:

- A new developer can start all local services with documented commands.
- API service boots and exposes `/health`.
- PostgreSQL, Neo4j, and Redis health checks are available.
- No secrets are committed.

Risks:

- Overbuilding infrastructure before the first data flow exists.
- Introducing dependencies before the codebase proves it needs them.

## Phase 1: Authenticated API and Core Persistence

Goal: Establish the application boundary and core database schema.

Deliverables:

- FastAPI application structure.
- SQLAlchemy 2.0 models.
- Alembic migrations.
- JWT authentication.
- RBAC roles: `admin`, `analyst`, `viewer`, `auditor`.
- Request logging.
- Audit event table and write path.
- Scan policy and scanner profile tables.
- Scan run, target, artifact, host, service, vulnerability, finding, risk model, and risk score tables.
- Asset tag and host asset tag tables.
- Basic API tests.

Acceptance criteria:

- Authenticated users can call protected endpoints.
- Unauthorized requests are rejected.
- Database migrations run from a clean database.
- Audit events are written for authentication and scan creation actions.
- Scan creation cannot bypass scan policy validation.

Risks:

- Weak auth or RBAC design can become expensive to repair later.
- Missing indexes in the first migrations can hide performance issues until later.

## Phase 2: Nmap Ingestion Vertical Slice

Goal: Convert Nmap output into normalized inventory.

Deliverables:

- `DiscoveryProvider` interface.
- Nmap provider implementation for XML output.
- Scanner profile selection for reusable Nmap configurations.
- Scan policy validation before target validation.
- Scan target validation.
- Background scan job with Celery.
- Raw scan artifact storage metadata.
- Normalized scan observations.
- Idempotent host and service upserts.
- Scan lifecycle statuses: `queued`, `running`, `completed`, `failed`, `partial`.
- Unit tests for Nmap parsing.
- Integration tests for scan ingestion.

Acceptance criteria:

- A scan can be queued through `POST /scan`.
- A scan cannot be queued without an enabled scan policy and scanner profile.
- Worker processes the scan and persists hosts and services.
- Re-running a scan updates `last_seen_at` rather than duplicating assets.
- Empty scan results are handled as successful scans with zero discovered assets.
- Provider failures are visible in scan status with sanitized errors.

Risks:

- Nmap output varies by flags and environment.
- Scan policy and target validation must prevent accidental out-of-scope scans.
- Scanner execution should never happen directly in request handlers.
- MVP scope is Nmap XML only; Masscan, RustScan, OpenVAS, and Nessus are explicitly excluded from MVP.

## Phase 3: Vulnerability Intelligence and Risk Scoring

Goal: Enrich inventory with vulnerability context and deterministic risk scores.

Deliverables:

- Vulnerability import/update workflow for CVE metadata.
- CVSS field normalization.
- EPSS field normalization.
- Finding creation from vulnerability evidence.
- Composite risk score v1.
- Immutable risk model definitions.
- Risk score versioning linked to a specific risk model.
- Top-risk API endpoint.
- Tests for risk score edge cases.

Acceptance criteria:

- Findings can reference vulnerabilities by CVE ID.
- Risk score combines CVSS, EPSS, exposure, and asset criticality.
- Missing CVSS or EPSS data does not crash scoring.
- Score output includes deterministic explanation.
- Risk scores are reproducible for the same inputs and referenced risk model.
- Future risk model changes do not alter historical scores.

Risks:

- Product/version matching can create false positives.
- CVSS-only prioritization would not meet project goals.
- Risk scores without explanation will be hard to trust.

## Phase 4: Neo4j Graph Projection

Goal: Project inventory and findings into Neo4j for traversal and visualization.

Deliverables:

- Neo4j connection management.
- Graph projection service.
- Constraints and indexes.
- Host, Service, Vulnerability, Finding, NetworkSegment, and Technique nodes.
- `RUNS`, `HAS_FINDING`, `HAS_VULNERABILITY`, `REFERENCES`, `MEMBER_OF`, and `MAPS_TO` relationships.
- Projection job triggered after scan ingestion.
- Projection status tracking through `graph_projection_jobs`.
- Graph neighborhood API.
- Graph tests with seeded data.

Acceptance criteria:

- Graph projection can be retried without duplicate nodes.
- PostgreSQL UUIDs are present on corresponding Neo4j nodes.
- Failed projection does not roll back persisted scan results.
- Graph API returns bounded results.
- Stale projection status is visible to API consumers.
- Projection retries are idempotent.

Risks:

- Graph drift if projection is not idempotent.
- Full graph fetches can overload the UI.
- Missing constraints can cause duplicate graph nodes.

## Phase 5: Graph Analytics Foundation

Goal: Prove graph quality, freshness, and relationship confidence before generating attack paths.

Deliverables:

- Graph neighborhood queries.
- Shortest path queries.
- Critical asset identification.
- Graph health metrics.
- Relationship confidence modeling.
- Asset tag filtering for graph queries.
- Graph freshness metadata in API responses.
- Tests for empty graphs, disconnected graphs, stale projections, and low-confidence relationships.

Acceptance criteria:

- Analysts can request bounded graph neighborhoods around hosts and critical assets.
- Shortest path queries work without persisting attack paths.
- Critical assets can be identified using criticality, tags, and findings.
- Graph health metrics expose node counts, relationship counts, projection freshness, and confidence coverage.
- Low-confidence relationships are visible and filterable.

Risks:

- Graph analytics can produce misleading conclusions if projection freshness is hidden.
- Relationship confidence must be modeled before path scoring is trusted.
- Full graph traversal can become expensive without strict bounds.

## Phase 6: Attack Path Engine

Goal: Add defensive attack path analysis after graph quality and confidence are established.

Deliverables:

- BFS shortest path analysis.
- DFS bounded exploration.
- Weighted path analysis using Dijkstra or Neo4j equivalent.
- Attack path persistence.
- Critical node analysis.
- Path scoring.
- Critical node and choke point detection.
- Attack path API.
- Tests for disconnected graphs, cycles, stale projections, and empty graphs.

Acceptance criteria:

- Shortest path can be calculated between two hosts.
- Weighted path uses versioned edge costs.
- Disconnected graphs return no path without error.
- Cycles do not cause unbounded traversal.
- Output includes path nodes, relationships, risk score, confidence, and critical nodes.

Risks:

- Path results can be misleading if relationship confidence is ignored.
- Advanced algorithms should run as jobs for large graphs.
- The engine must not produce offensive execution steps.

## Phase 7: MITRE ATT&CK Mapping

Goal: Map findings and attack paths to ATT&CK tactics and techniques.

Deliverables:

- MITRE tactic and technique tables.
- Seed/import workflow for ATT&CK metadata.
- Rule-based finding mappings.
- Path-level mappings.
- Confidence and evidence fields.
- API fields for ATT&CK context.
- Tests for mapping rules.

Acceptance criteria:

- Findings can map to ATT&CK techniques with evidence.
- Attack paths can aggregate mapped techniques.
- Mapping confidence is visible.
- Unknown mappings are allowed and do not block finding creation.

Risks:

- Overconfident mappings reduce analyst trust.
- Technique metadata must be versioned or refreshable.

## Phase 8: AI Security Analyst

Goal: Provide optional, safe, evidence-grounded explanations.

Deliverables:

- `AISecurityAnalyst` abstraction.
- Ollama provider.
- OpenAI-compatible provider.
- Disabled-by-default AI configuration.
- Prompt templates for findings, paths, and risk scores.
- Prompt safety constraints.
- AI explanation persistence.
- Provider latency and error metrics.
- Tests for prompt construction and blocked unsafe requests.

Acceptance criteria:

- The full platform works when AI is disabled.
- AI explanations reference deterministic evidence.
- AI output is stored separately from deterministic findings.
- Provider failures do not affect inventory, risk scoring, MITRE mapping, graph analysis, or alerting.
- Unsafe prompt categories are blocked or redacted.
- Users can see model, provider, prompt version, and source evidence.

Risks:

- AI can hallucinate unsupported claims.
- Provider latency can degrade user experience.
- Prompts must not request exploit details or payloads.

## Phase 9: Dashboard

Goal: Build the operational frontend.

Deliverables:

- React + TypeScript + Vite app.
- Authentication flow.
- Asset inventory view.
- Host detail view.
- Vulnerability and findings view.
- Graph view with Cytoscape.js.
- Risk dashboard.
- Scan timeline.
- Alert list.
- Optional AI explanation panel.

Acceptance criteria:

- Dashboard supports the main analyst workflow without using mock-only data.
- Graph view requests bounded graph slices.
- Empty states are explicit.
- API failures are visible to users.
- Large text and graph data do not break layout.

Risks:

- Loading too much graph data into the browser will not scale.
- UI must distinguish evidence, deterministic analysis, and AI text.

## Phase 10: Continuous Monitoring and Alerts

Goal: Add scheduled scans and change detection.

Deliverables:

- Scan schedules.
- Scheduler service.
- Mandatory scan policy validation for scheduled scans.
- Delta analysis.
- Alert rules.
- Alert state transitions.
- Notification integration design.
- Tests for new, changed, resolved, and missing entities.

Acceptance criteria:

- Scheduled scans run without manual API calls.
- New hosts, services, vulnerabilities, and topology changes generate alerts.
- Alerts can be acknowledged and closed.
- Delta analysis handles empty previous scans and empty current scans.

Risks:

- Repeated scans can generate noisy duplicate alerts.
- Missing hosts may be temporary network failures, not true removals.

## Phase 11: Observability, Hardening, and Release Readiness

Goal: Prepare for production deployment and open-source release.

Deliverables:

- Prometheus metrics.
- Grafana dashboards.
- Structured logging with `structlog`.
- Rate limiting.
- Security headers.
- Dependency vulnerability scanning.
- Backup and restore documentation.
- Deployment documentation.
- Security model documentation.
- Security boundaries documentation.
- Threat model documentation.
- Responsible disclosure documentation.
- API documentation.
- Test coverage above 80%.

Acceptance criteria:

- Health checks cover API, PostgreSQL, Neo4j, Redis, and worker dependencies.
- Metrics cover API latency, scan duration, queue depth, graph size, and AI latency.
- Logs include request IDs and job IDs.
- Production deployment guide is complete.
- License and contribution guidance are present.
- Contributor guidance rejects offensive automation, exploit generation, payload generation, and credential abuse features.

Risks:

- Observability added too late may miss critical failure modes.
- Open-source release requires clear safety boundaries and contribution rules.

## Suggested Milestones

### Milestone 1: Local Skeleton

Includes Phase 0 and the minimum `/health` endpoint.

### Milestone 2: Inventory MVP

Includes Phases 1 and 2.

### Milestone 3: Risk MVP

Includes Phase 3.

### Milestone 4: Graph MVP

Includes Phase 4.

### Milestone 5: Path Analysis MVP

Includes Phases 5 and 6.

### Milestone 6: Analyst Experience

Includes Phases 7, 8, and 9.

### Milestone 7: Production Readiness

Includes Phases 10 and 11.

## Minimum Viable Product

The MVP should include:

- FastAPI backend.
- PostgreSQL schema and migrations.
- JWT auth and RBAC.
- Scan policies.
- Scanner profiles.
- Celery worker.
- Redis queue.
- Nmap XML ingestion.
- Hosts and services inventory.
- Asset tags.
- Basic vulnerability findings.
- Composite risk score v1.
- Immutable risk model v1.
- Neo4j projection for hosts, services, vulnerabilities, and findings.
- Graph projection job tracking.
- Graph neighborhood API.
- Basic dashboard for assets, findings, and graph view.

The MVP should not include:

- Multiple scan providers.
- Masscan.
- RustScan.
- OpenVAS.
- Nessus.
- Active Directory graph modeling.
- Advanced AI workflows.
- Required AI availability.
- Automated remediation.
- Any offensive execution capability.

## Testing Strategy

Required test categories:

- Unit tests for parsing, normalization, risk scoring, and mapping rules.
- Integration tests for PostgreSQL persistence.
- Integration tests for Neo4j projection.
- API tests for auth, scan lifecycle, inventory, graph, and findings.
- Worker tests for job idempotency and retry behavior.
- Frontend tests for critical dashboard states.

Important edge cases:

- Empty scan output.
- Duplicate scan observations.
- Invalid targets.
- Missing or disabled scan policy.
- Scanner profile blocked by policy.
- Provider timeout.
- Partial provider output.
- Missing CVSS.
- Missing EPSS.
- Historical score after risk model changes.
- Disconnected graph.
- Cyclic graph.
- Failed Neo4j projection after successful PostgreSQL commit.
- Stale graph projection metadata.
- AI provider timeout.

## Documentation Roadmap

Additional documents to create after implementation begins:

- `README.md`.
- `ARCHITECTURE.md`.
- `API.md`.
- `GRAPH_MODEL.md`.
- `ATTACK_PATH_ENGINE.md`.
- `DEPLOYMENT.md`.
- `SECURITY_MODEL.md`.
- `SECURITY_BOUNDARIES.md`.
- `THREAT_MODEL.md`.
- `RESPONSIBLE_DISCLOSURE.md`.
- `CONTRIBUTING.md`.
- `OPERATIONS.md`.

## Decision Log

### PostgreSQL is the source of truth

Reason: relational persistence is better for canonical inventory, auditability, and transactional writes.

Tradeoff: graph projection introduces eventual consistency.

### Neo4j is a derived projection

Reason: graph traversal and visualization are core platform features.

Tradeoff: projection jobs must be idempotent and observable.

### Nmap is the first provider

Reason: it is widely used and matches the project brief.

Tradeoff: provider abstraction should exist, but Masscan, RustScan, OpenVAS, and Nessus should wait until Nmap XML ingestion is stable.

### AI is optional and disabled by default

Reason: deterministic evidence and scoring must remain auditable.

Tradeoff: AI responses require separate storage, prompt versioning, safety controls, and feature flags, while all critical workflows must work without provider availability.

### Scan policies are mandatory

Reason: scan scope governance prevents accidental or unauthorized scanning.

Tradeoff: every scan path, including scheduled scans, must pass through policy validation before target validation and queue submission.

## Open Questions

- Should local scanner execution be allowed only from worker containers, or should the system initially support upload-only Nmap XML ingestion?
- What target validation policy should be enforced for private, public, and reserved address ranges?
- Will authentication be local username/password only, or should OIDC be supported early?
- Where should raw scan artifacts be stored in production?
- What is the expected maximum scan frequency per environment?
- Which CVE and EPSS data sources should be used first?
- Should graph projection be synchronous after ingestion or always queued as a separate job?
