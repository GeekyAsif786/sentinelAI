# Neo4j Graph Model

## Scope

This document describes the target Neo4j model for AI Network Mapper. Neo4j stores a derived graph projection used for topology visualization, risk traversal, and attack-path analysis.

PostgreSQL remains the system of record. Neo4j nodes and relationships must carry stable external identifiers that point back to PostgreSQL rows where applicable.

## Graph Design Principles

- Use Neo4j for relationships and traversal, not as the canonical inventory database.
- Keep graph writes idempotent.
- Store enough evidence on relationships to explain why an edge exists.
- Preserve room for future Active Directory modeling.
- Avoid storing secrets, credentials, payloads, or exploit instructions.
- Keep visualization queries bounded by depth, node count, and relationship count.
- Expose graph freshness so stale projections are visible to API consumers and operators.

## Node Labels

### Host

Represents a discovered system.

Required properties:

- `id`: PostgreSQL host UUID.
- `primary_ip`.
- `hostname`.
- `os_name`.
- `asset_criticality`.
- `first_seen_at`.
- `last_seen_at`.

Recommended derived properties:

- `risk_score`.
- `open_service_count`.
- `critical_finding_count`.
- `segment_names`.
- `tag_names`.

### Service

Represents a network service on a host.

Required properties:

- `id`: PostgreSQL service UUID.
- `host_id`: PostgreSQL host UUID.
- `port`.
- `protocol`.
- `service_name`.
- `product`.
- `version`.
- `state`.
- `exposure`.
- `first_seen_at`.
- `last_seen_at`.

Recommended derived properties:

- `risk_score`.
- `is_remote_access`.
- `is_sensitive`.

### Vulnerability

Represents a normalized vulnerability.

Required properties:

- `id`: PostgreSQL vulnerability UUID.
- `cve_id`.
- `title`.
- `severity`.
- `cvss_score`.
- `epss_probability`.

Recommended derived properties:

- `published_at`.
- `known_exploited`: boolean metadata only.

### Finding

Represents an observed issue in context.

Required properties:

- `id`: PostgreSQL finding UUID.
- `finding_type`.
- `title`.
- `status`.
- `risk_score`.
- `first_seen_at`.
- `last_seen_at`.

### NetworkSegment

Represents a logical or CIDR-based network segment.

Required properties:

- `id`: PostgreSQL network segment UUID.
- `name`.
- `cidr`.
- `criticality`.

### AssetTag

Represents a reusable asset classification used for filtering, reporting, risk prioritization, and attack path prioritization.

Required properties:

- `id`: PostgreSQL asset tag UUID.
- `name`.
- `description`.

### User

Reserved for future Active Directory or identity integration.

Required properties when implemented:

- `id`: PostgreSQL or external identity UUID.
- `principal_name`.
- `display_name`.
- `source`.
- `is_privileged`.

Do not store passwords, hashes, tokens, or secrets.

### Domain

Reserved for future Active Directory integration.

Required properties when implemented:

- `id`.
- `name`.
- `dns_name`.
- `source`.

### Group

Reserved for future Active Directory integration.

Required properties when implemented:

- `id`.
- `name`.
- `source`.
- `is_privileged`.

### Technique

Represents a MITRE ATT&CK technique.

Required properties:

- `id`: PostgreSQL MITRE technique UUID.
- `technique_id`: ATT&CK technique ID.
- `name`.
- `tactic_name`.

## Relationship Types

### `(:Host)-[:RUNS]->(:Service)`

Represents a service running on a host.

Properties:

- `scan_run_id`.
- `first_seen_at`.
- `last_seen_at`.
- `confidence`.

Cardinality:

- One host can run many services.
- One service belongs to one host in the first implementation.

### `(:Service)-[:HAS_VULNERABILITY]->(:Vulnerability)`

Represents a service affected by a vulnerability.

Properties:

- `finding_id`.
- `evidence`.
- `confidence`.
- `first_seen_at`.
- `last_seen_at`.

### `(:Host)-[:HAS_FINDING]->(:Finding)`

Represents a finding observed on a host.

Properties:

- `scan_run_id`.
- `first_seen_at`.
- `last_seen_at`.

### `(:Service)-[:HAS_FINDING]->(:Finding)`

Represents a finding observed on a specific service.

Properties:

- `scan_run_id`.
- `first_seen_at`.
- `last_seen_at`.

### `(:Finding)-[:REFERENCES]->(:Vulnerability)`

Connects a contextual finding to normalized vulnerability intelligence.

Properties:

- `confidence`.
- `evidence`.

### `(:Host)-[:MEMBER_OF]->(:NetworkSegment)`

Represents host membership in a network segment.

Properties:

- `source`.
- `confidence`.

### `(:Host)-[:TAGGED_AS]->(:AssetTag)`

Represents asset classification.

Properties:

- `source`.
- `created_at`.

### `(:Host)-[:CONNECTS_TO]->(:Host)`

Represents observed or inferred connectivity between hosts.

Properties:

- `source`.
- `protocol`.
- `port`.
- `confidence`.
- `first_seen_at`.
- `last_seen_at`.
- `cost`.

This relationship should only be created from defensible evidence such as scan observations, routing/import data, firewall data, or explicit user configuration.

### `(:Service)-[:EXPOSES]->(:NetworkSegment)`

Represents a service exposed to a network segment.

Properties:

- `exposure`.
- `confidence`.
- `cost`.

### `(:Host)-[:TRUSTS]->(:Host)`

Represents a trust relationship between hosts.

Properties:

- `source`.
- `trust_type`.
- `confidence`.
- `cost`.

For the first implementation this relationship may be absent unless there is explicit evidence. It is primarily reserved for future Active Directory and infrastructure integrations.

### `(:User)-[:MEMBER_OF]->(:Group)`

Reserved for Active Directory integration.

Properties:

- `source`.
- `confidence`.

### `(:Group)-[:MEMBER_OF]->(:Group)`

Reserved for nested group membership.

Properties:

- `source`.
- `confidence`.

### `(:User)-[:HAS_SESSION]->(:Host)`

Reserved for defensive identity telemetry integration.

Properties:

- `source`.
- `observed_at`.
- `confidence`.

### `(:Finding)-[:MAPS_TO]->(:Technique)`

Maps findings to MITRE ATT&CK techniques.

Properties:

- `confidence`.
- `evidence`.

### `(:Vulnerability)-[:MAPS_TO]->(:Technique)`

Maps known vulnerabilities to MITRE ATT&CK techniques.

Properties:

- `confidence`.
- `evidence`.

## Graph Projection Rules

### Source of Truth

- PostgreSQL hosts project to `Host`.
- PostgreSQL services project to `Service`.
- PostgreSQL vulnerabilities project to `Vulnerability`.
- PostgreSQL findings project to `Finding`.
- PostgreSQL network segments project to `NetworkSegment`.
- PostgreSQL asset tags project to `AssetTag`.
- PostgreSQL MITRE techniques project to `Technique`.

### Idempotency

All projected nodes should be merged by stable `id`. Relationships should be merged by:

- Source node ID.
- Target node ID.
- Relationship type.
- Context identifier such as `finding_id` when applicable.

### Deletion and Staleness

The graph should prefer marking stale entities over immediate deletion:

- Closed services can remain with stale metadata for historical path comparison.
- Resolved findings should remain visible when viewing historical scans.
- Active graph views should filter to current or open status by default.

### Projection Failure

If projection fails:

- PostgreSQL scan data remains authoritative.
- Projection status should be marked failed in `graph_projection_jobs`.
- Graph endpoints should report that graph data may be stale.
- Projection retries must not duplicate nodes or relationships.

### Graph Freshness

Graph APIs should expose freshness metadata derived from the latest `graph_projection_jobs` record:

- Latest projection status.
- Related scan run ID.
- Projection completion timestamp.
- Retry count.
- Staleness indicator.

Freshness metadata must not block inventory APIs. It exists so users can distinguish current PostgreSQL inventory from stale graph projection state.

## Constraints and Indexes

Recommended Neo4j constraints:

- Unique `Host.id`.
- Unique `Service.id`.
- Unique `Vulnerability.id`.
- Unique `Finding.id`.
- Unique `NetworkSegment.id`.
- Unique `AssetTag.id`.
- Unique `Technique.id`.

Recommended indexes:

- `Host.primary_ip`.
- `Host.hostname`.
- `Host.risk_score`.
- `Service.port`.
- `Service.protocol`.
- `Service.service_name`.
- `Service.exposure`.
- `Vulnerability.cve_id`.
- `Vulnerability.severity`.
- `Finding.status`.
- `Finding.risk_score`.
- `AssetTag.name`.
- `Technique.technique_id`.

## Attack Path Semantics

Attack paths are defensive models of plausible movement or exposure. They are not instructions for exploitation.

Path traversal can use:

- `RUNS` to move from host to exposed services.
- `HAS_VULNERABILITY` or `HAS_FINDING` to identify risky services.
- `CONNECTS_TO` to move between hosts.
- `TRUSTS` to model trust relationships.
- `MEMBER_OF` to move through segments or identity groups.
- `MAPS_TO` to enrich with ATT&CK context.

## Edge Cost Model

Weighted pathfinding should use a cost model where lower cost means easier or more concerning traversal.

Recommended factors:

- Service exposure.
- Finding risk score.
- Vulnerability EPSS probability.
- Asset criticality.
- Asset tags such as `Production`, `PCI`, `Critical`, `DMZ`, and `DomainController`.
- Relationship confidence.
- Network segment sensitivity.

Example cost interpretation:

- External exposed critical vulnerability: low cost.
- Internal filtered service with weak evidence: high cost.
- Explicit trust relationship to critical host: low to medium cost depending on confidence.

The exact formula should be versioned and stored with path results.

## Visualization Model

The frontend should not request the full graph for large environments. Graph API responses should support:

- Root node.
- Direction.
- Maximum depth.
- Maximum nodes.
- Relationship filters.
- Node label filters.
- Asset tag filters.
- Finding status filters.
- Minimum risk score.

Recommended default:

- Depth: 2.
- Maximum nodes: 250.
- Include open findings only.

## Initial Graph Model

The first implementation should support only:

- `Host`.
- `Service`.
- `Vulnerability`.
- `Finding`.
- `NetworkSegment`.
- `AssetTag`.
- `Technique`.
- `RUNS`.
- `HAS_FINDING`.
- `HAS_VULNERABILITY`.
- `REFERENCES`.
- `MEMBER_OF`.
- `TAGGED_AS`.
- `MAPS_TO`.

Relationships such as `TRUSTS`, user/group membership, and sessions should be designed but not implemented until a real identity data source exists.

## Query Patterns

Primary read patterns:

- Get services for a host.
- Get vulnerabilities for a host.
- Get open findings above a risk threshold.
- Filter hosts by asset tag.
- Get graph neighborhood around a host.
- Get shortest path between two hosts.
- Get highest-risk path to a critical asset.
- Get MITRE techniques mapped to a finding or path.

Operational safeguards:

- Every traversal query should have bounded depth.
- Every visualization query should enforce node and relationship limits.
- Long-running analysis should execute as a background job.

## Known Risks

- Inferred relationships can produce misleading paths if confidence is not visible.
- Product/version matching can overstate vulnerability exposure.
- Full graph queries can become expensive at target scale.
- Identity graph expansion can rapidly increase relationship count.
- Deleting projected nodes can break historical path references.

## Future Active Directory Model

When Active Directory support is introduced, add:

- `Domain`.
- `User`.
- `Group`.
- `Computer` or reuse `Host` with AD-specific properties.
- `MEMBER_OF`.
- `ADMIN_TO`.
- `HAS_SESSION`.
- `TRUSTS`.
- `CAN_RDP`.
- `CAN_PSH_REMOTE`.

Security boundary:

- Store defensive relationship metadata only.
- Do not store plaintext credentials.
- Do not store reusable secrets.
- Do not provide automated abuse actions from graph paths.
