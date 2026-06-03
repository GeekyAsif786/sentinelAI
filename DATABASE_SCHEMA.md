# Database Schema

## Scope

This document describes the target PostgreSQL schema for AI Network Mapper. PostgreSQL is the authoritative system of record for users, scans, assets, services, vulnerabilities, findings, risk scores, AI explanations, alerts, and audit records.

The current repository contains no implemented database models or migrations. The schema below is a design baseline for future SQLAlchemy 2.0 models and Alembic migrations.

## Design Principles

- PostgreSQL owns canonical state.
- Neo4j owns derived graph projections.
- Scan history is append-only where practical.
- Inventory entities are idempotently upserted from scan observations.
- Raw scan artifacts are retained for traceability.
- External identifiers are stored explicitly.
- Risk scores are versioned so scoring logic can evolve.
- All security-relevant actions are auditable.

## Naming Conventions

- Table names use plural snake_case.
- Primary keys use `id`.
- Foreign keys use `<entity>_id`.
- Timestamps use `created_at`, `updated_at`, `deleted_at`, `first_seen_at`, and `last_seen_at`.
- Soft deletion should only be used where historical visibility matters.
- Enumerations should be represented by constrained strings or database enums through migrations.

## Entity Relationship Overview

```text
users
  |-- user_roles -- roles
  |-- scan_runs
  |-- audit_events

scan_runs
  |-- scan_policies
  |-- scanner_profiles
  |-- scan_targets
  |-- scan_artifacts
  |-- scan_observations
  |-- graph_projection_jobs
  |-- findings

hosts
  |-- services
  |-- findings
  |-- host_segments -- network_segments
  |-- host_asset_tags -- asset_tags

services
  |-- findings

vulnerabilities
  |-- vulnerability_references
  |-- vulnerability_mitre_techniques
  |-- findings

findings
  |-- risk_scores -- risk_models
  |-- finding_mitre_techniques
  |-- ai_explanations
  |-- alerts

attack_paths
  |-- attack_path_nodes
  |-- attack_path_edges
  |-- attack_path_mitre_techniques
```

## Core Tables

### users

Stores application users.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| email | text | Unique, lowercased |
| password_hash | text | Nullable if external identity provider is used |
| display_name | text | Required |
| is_active | boolean | Defaults to true |
| last_login_at | timestamptz | Nullable |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `email`.
- Index on `is_active`.

### roles

Stores RBAC roles.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| name | text | Unique, examples: `admin`, `analyst`, `viewer`, `auditor` |
| description | text | Required |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `name`.

### user_roles

Maps users to roles.

| Column | Type | Notes |
| --- | --- | --- |
| user_id | uuid | FK to `users.id` |
| role_id | uuid | FK to `roles.id` |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `user_id`, `role_id`.

### scan_policies

Defines governance controls for scan scope and rate. Every scan must reference an enabled policy before target validation and queue submission.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| name | text | Required, unique |
| description | text | Required |
| allowed_cidrs | cidr[] | CIDR ranges that may be scanned |
| blocked_cidrs | cidr[] | CIDR ranges that must never be scanned |
| max_targets | integer | Maximum resolved targets per scan |
| max_scan_rate | integer | Maximum provider-specific scan rate |
| provider_restrictions | jsonb | Allowed or blocked providers and profile constraints |
| is_enabled | boolean | Defaults to true |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `name`.
- Index on `is_enabled`.

Notes:

- Policy validation must run before target validation.
- Blocked CIDRs override allowed CIDRs.
- Scheduled scans must use the same policy validation path as interactive scans.

### scanner_profiles

Stores reusable provider configurations. Users should select profiles instead of submitting raw scanner arguments.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| name | text | Required, unique per provider |
| provider | text | Example: `nmap` |
| description | text | Required |
| configuration | jsonb | Sanitized provider configuration |
| is_enabled | boolean | Defaults to true |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `provider`, `name`.
- Index on `provider`.
- Index on `is_enabled`.

Examples:

- Quick Discovery.
- Service Detection.
- Safe Internal Scan.
- Full Inventory Scan.

### scan_runs

Stores each scan execution request and lifecycle state.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| requested_by_user_id | uuid | FK to `users.id` |
| scan_policy_id | uuid | FK to `scan_policies.id` |
| scanner_profile_id | uuid | FK to `scanner_profiles.id` |
| provider | text | Example: `nmap` |
| status | text | `queued`, `running`, `completed`, `failed`, `cancelled`, `partial` |
| scan_type | text | Example: `discovery`, `service_detection`, `vulnerability_detection` |
| started_at | timestamptz | Nullable |
| completed_at | timestamptz | Nullable |
| error_code | text | Nullable |
| error_message | text | Nullable, sanitized |
| provider_version | text | Nullable |
| configuration | jsonb | Sanitized scan configuration |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Index on `requested_by_user_id`.
- Index on `scan_policy_id`.
- Index on `scanner_profile_id`.
- Index on `provider`.
- Index on `status`.
- Index on `created_at`.

### scan_targets

Stores validated targets for a scan.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| scan_run_id | uuid | FK to `scan_runs.id` |
| target_value | text | IP, CIDR, hostname, or named segment |
| target_type | text | `ip`, `cidr`, `hostname`, `segment` |
| validation_status | text | `valid`, `invalid`, `blocked` |
| validation_message | text | Nullable |
| created_at | timestamptz | Required |

Indexes:

- Index on `scan_run_id`.
- Index on `target_type`.

### scan_artifacts

Stores raw scanner output references. Large artifacts should be stored in object storage or a mounted artifact volume, with this table storing metadata and location.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| scan_run_id | uuid | FK to `scan_runs.id` |
| artifact_type | text | Example: `nmap_xml`, `nmap_text`, `provider_json` |
| storage_uri | text | Required |
| sha256 | text | Required |
| size_bytes | bigint | Required |
| created_at | timestamptz | Required |

Indexes:

- Index on `scan_run_id`.
- Unique index on `sha256`.

### hosts

Stores canonical host inventory.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| primary_ip | inet | Required |
| hostname | text | Nullable |
| mac_address | macaddr | Nullable |
| os_name | text | Nullable |
| os_version | text | Nullable |
| os_confidence | numeric | Nullable |
| asset_criticality | integer | 1-5 scale |
| source | text | Provider or import source |
| first_seen_at | timestamptz | Required |
| last_seen_at | timestamptz | Required |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `primary_ip`.
- Index on `hostname`.
- Index on `mac_address`.
- Index on `last_seen_at`.
- Index on `asset_criticality`.

Notes:

- `primary_ip` is unique for the first implementation. Future multi-interface hosts may require a separate `host_addresses` table.

### network_segments

Stores logical network groupings.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| name | text | Required |
| cidr | cidr | Nullable |
| description | text | Nullable |
| criticality | integer | 1-5 scale |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `name`.
- Index on `cidr`.

### host_segments

Maps hosts to network segments.

| Column | Type | Notes |
| --- | --- | --- |
| host_id | uuid | FK to `hosts.id` |
| network_segment_id | uuid | FK to `network_segments.id` |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `host_id`, `network_segment_id`.

### asset_tags

Stores reusable asset classifications.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| name | text | Required, unique |
| description | text | Nullable |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `name`.

Examples:

- Production.
- Development.
- Database.
- PCI.
- Critical.
- DMZ.
- DomainController.

### host_asset_tags

Maps hosts to asset tags for filtering, risk prioritization, reporting, and attack path prioritization.

| Column | Type | Notes |
| --- | --- | --- |
| host_id | uuid | FK to `hosts.id` |
| asset_tag_id | uuid | FK to `asset_tags.id` |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `host_id`, `asset_tag_id`.

Indexes:

- Index on `asset_tag_id`.

### services

Stores network services observed on hosts.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| host_id | uuid | FK to `hosts.id` |
| port | integer | 0-65535 |
| protocol | text | `tcp`, `udp`, or provider-specific validated value |
| service_name | text | Nullable |
| product | text | Nullable |
| version | text | Nullable |
| banner | text | Nullable, sanitized |
| state | text | `open`, `closed`, `filtered`, `unknown` |
| exposure | text | `internal`, `external`, `unknown` |
| first_seen_at | timestamptz | Required |
| last_seen_at | timestamptz | Required |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `host_id`, `port`, `protocol`.
- Index on `service_name`.
- Index on `product`.
- Index on `state`.
- Index on `exposure`.
- Index on `last_seen_at`.

### vulnerabilities

Stores normalized vulnerability intelligence.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| cve_id | text | Unique when available |
| title | text | Required |
| description | text | Required |
| cvss_score | numeric | Nullable |
| cvss_vector | text | Nullable |
| severity | text | `critical`, `high`, `medium`, `low`, `informational`, `unknown` |
| epss_probability | numeric | Nullable, 0-1 |
| epss_percentile | numeric | Nullable, 0-1 |
| published_at | timestamptz | Nullable |
| modified_at | timestamptz | Nullable |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Unique index on `cve_id` where `cve_id` is not null.
- Index on `severity`.
- Index on `cvss_score`.
- Index on `epss_probability`.
- Index on `published_at`.

### vulnerability_references

Stores references for vulnerabilities.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| vulnerability_id | uuid | FK to `vulnerabilities.id` |
| reference_url | text | Required |
| source_name | text | Nullable |
| tags | text[] | Nullable |
| created_at | timestamptz | Required |

Indexes:

- Index on `vulnerability_id`.
- Unique index on `vulnerability_id`, `reference_url`.

### findings

Stores observed security findings in a scan context.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| scan_run_id | uuid | FK to `scan_runs.id` |
| host_id | uuid | FK to `hosts.id` |
| service_id | uuid | Nullable FK to `services.id` |
| vulnerability_id | uuid | Nullable FK to `vulnerabilities.id` |
| finding_type | text | `vulnerability`, `exposure`, `misconfiguration`, `weak_auth`, `informational` |
| title | text | Required |
| description | text | Required |
| evidence | jsonb | Required sanitized evidence |
| status | text | `open`, `resolved`, `accepted_risk`, `false_positive` |
| first_seen_at | timestamptz | Required |
| last_seen_at | timestamptz | Required |
| created_at | timestamptz | Required |
| updated_at | timestamptz | Required |

Indexes:

- Index on `scan_run_id`.
- Index on `host_id`.
- Index on `service_id`.
- Index on `vulnerability_id`.
- Index on `finding_type`.
- Index on `status`.
- Index on `last_seen_at`.

### risk_models

Stores immutable risk scoring definitions.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| version | text | Unique semantic or date-based version |
| name | text | Required |
| description | text | Required |
| formula_summary | text | Human-readable scoring formula summary |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `version`.

Notes:

- Risk model records should be append-only.
- Future scoring changes must create a new risk model version instead of mutating historical definitions.

### risk_scores

Stores versioned risk calculations for findings and attack paths.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| finding_id | uuid | Nullable FK to `findings.id` |
| attack_path_id | uuid | Nullable FK to `attack_paths.id` |
| risk_model_id | uuid | FK to `risk_models.id` |
| score | numeric | 0-100 |
| severity | text | `critical`, `high`, `medium`, `low`, `informational` |
| scoring_version | text | Required |
| cvss_component | numeric | Nullable |
| epss_component | numeric | Nullable |
| exposure_component | numeric | Nullable |
| asset_criticality_component | numeric | Nullable |
| explanation | text | Deterministic explanation |
| created_at | timestamptz | Required |

Constraints:

- Exactly one of `finding_id` or `attack_path_id` should be set.
- `scoring_version` should match the referenced `risk_models.version` at write time for denormalized reporting.

Indexes:

- Index on `finding_id`.
- Index on `attack_path_id`.
- Index on `risk_model_id`.
- Index on `score`.
- Index on `severity`.
- Index on `created_at`.

### mitre_tactics

Stores ATT&CK tactics.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| tactic_id | text | Unique ATT&CK tactic ID |
| name | text | Required |
| description | text | Nullable |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `tactic_id`.

### mitre_techniques

Stores ATT&CK techniques.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| tactic_id | uuid | FK to `mitre_tactics.id` |
| technique_id | text | Unique ATT&CK technique ID |
| name | text | Required |
| description | text | Nullable |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `technique_id`.
- Index on `tactic_id`.

### finding_mitre_techniques

Maps findings to ATT&CK techniques.

| Column | Type | Notes |
| --- | --- | --- |
| finding_id | uuid | FK to `findings.id` |
| mitre_technique_id | uuid | FK to `mitre_techniques.id` |
| confidence | numeric | 0-1 |
| evidence | text | Required |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `finding_id`, `mitre_technique_id`.

### vulnerability_mitre_techniques

Maps known vulnerabilities to ATT&CK techniques.

| Column | Type | Notes |
| --- | --- | --- |
| vulnerability_id | uuid | FK to `vulnerabilities.id` |
| mitre_technique_id | uuid | FK to `mitre_techniques.id` |
| confidence | numeric | 0-1 |
| evidence | text | Required |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `vulnerability_id`, `mitre_technique_id`.

## Attack Path Tables

### attack_paths

Stores calculated attack paths.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| source_host_id | uuid | Nullable FK to `hosts.id` |
| target_host_id | uuid | Nullable FK to `hosts.id` |
| algorithm | text | `bfs`, `dfs`, `dijkstra` |
| status | text | `active`, `stale`, `failed` |
| total_cost | numeric | Nullable |
| risk_score | numeric | 0-100 |
| graph_snapshot_id | text | Identifies graph projection version |
| calculated_at | timestamptz | Required |
| created_at | timestamptz | Required |

Indexes:

- Index on `source_host_id`.
- Index on `target_host_id`.
- Index on `algorithm`.
- Index on `risk_score`.
- Index on `calculated_at`.

### attack_path_nodes

Stores ordered nodes in a path.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| attack_path_id | uuid | FK to `attack_paths.id` |
| sequence_index | integer | Required |
| node_type | text | `host`, `service`, `vulnerability`, `user`, `domain`, `network_segment` |
| external_id | uuid | ID from PostgreSQL when available |
| neo4j_element_id | text | Neo4j reference for diagnostics |
| label | text | Display label |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `attack_path_id`, `sequence_index`.
- Index on `node_type`, `external_id`.

### attack_path_edges

Stores ordered edges in a path.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| attack_path_id | uuid | FK to `attack_paths.id` |
| sequence_index | integer | Required |
| relationship_type | text | Example: `RUNS`, `EXPOSES`, `CONNECTS_TO` |
| source_node_external_id | uuid | Nullable |
| target_node_external_id | uuid | Nullable |
| cost | numeric | Nullable |
| evidence | jsonb | Required |
| created_at | timestamptz | Required |

Indexes:

- Unique index on `attack_path_id`, `sequence_index`.
- Index on `relationship_type`.

### attack_path_mitre_techniques

Maps attack paths to ATT&CK techniques.

| Column | Type | Notes |
| --- | --- | --- |
| attack_path_id | uuid | FK to `attack_paths.id` |
| mitre_technique_id | uuid | FK to `mitre_techniques.id` |
| confidence | numeric | 0-1 |
| evidence | text | Required |
| created_at | timestamptz | Required |

Constraints:

- Composite primary key on `attack_path_id`, `mitre_technique_id`.

## AI and Alerting Tables

### ai_explanations

Stores AI-generated explanations with traceability.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| finding_id | uuid | Nullable FK to `findings.id` |
| attack_path_id | uuid | Nullable FK to `attack_paths.id` |
| provider | text | Example: `ollama`, `openai_compatible` |
| model | text | Required |
| prompt_version | text | Required |
| input_evidence | jsonb | Evidence sent to provider |
| explanation | text | Generated text |
| safety_status | text | `allowed`, `blocked`, `redacted` |
| latency_ms | integer | Required |
| created_by_user_id | uuid | FK to `users.id` |
| created_at | timestamptz | Required |

Constraints:

- Exactly one of `finding_id` or `attack_path_id` should be set.

Indexes:

- Index on `finding_id`.
- Index on `attack_path_id`.
- Index on `provider`, `model`.
- Index on `created_by_user_id`.
- Index on `created_at`.

### alerts

Stores generated alerts from monitoring and risk changes.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| finding_id | uuid | Nullable FK to `findings.id` |
| host_id | uuid | Nullable FK to `hosts.id` |
| alert_type | text | `new_host`, `new_service`, `new_vulnerability`, `risk_increase`, `topology_change` |
| severity | text | `critical`, `high`, `medium`, `low`, `informational` |
| title | text | Required |
| description | text | Required |
| status | text | `open`, `acknowledged`, `closed` |
| created_at | timestamptz | Required |
| acknowledged_at | timestamptz | Nullable |
| acknowledged_by_user_id | uuid | Nullable FK to `users.id` |

Indexes:

- Index on `finding_id`.
- Index on `host_id`.
- Index on `alert_type`.
- Index on `severity`.
- Index on `status`.
- Index on `created_at`.

### audit_events

Stores security-relevant events.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| actor_user_id | uuid | Nullable FK to `users.id` |
| action | text | Required |
| resource_type | text | Required |
| resource_id | uuid | Nullable |
| ip_address | inet | Nullable |
| user_agent | text | Nullable |
| request_id | text | Nullable |
| metadata | jsonb | Sanitized metadata |
| created_at | timestamptz | Required |

Indexes:

- Index on `actor_user_id`.
- Index on `action`.
- Index on `resource_type`, `resource_id`.
- Index on `created_at`.

## Scan Observation Tables

### scan_observations

Stores normalized observations before or alongside canonical upserts.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| scan_run_id | uuid | FK to `scan_runs.id` |
| observation_type | text | `host`, `service`, `os`, `script`, `vulnerability` |
| observed_ip | inet | Nullable |
| observed_port | integer | Nullable |
| observed_protocol | text | Nullable |
| payload | jsonb | Normalized observation |
| created_at | timestamptz | Required |

Indexes:

- Index on `scan_run_id`.
- Index on `observation_type`.
- Index on `observed_ip`.
- Index on `observed_port`, `observed_protocol`.

### graph_projection_jobs

Tracks Neo4j projection lifecycle and graph freshness after scan ingestion.

| Column | Type | Notes |
| --- | --- | --- |
| id | uuid | Primary key |
| scan_run_id | uuid | FK to `scan_runs.id` |
| status | text | `queued`, `running`, `completed`, `failed` |
| started_at | timestamptz | Nullable |
| completed_at | timestamptz | Nullable |
| error_message | text | Nullable, sanitized |
| retry_count | integer | Defaults to 0 |
| created_at | timestamptz | Required |

Indexes:

- Index on `scan_run_id`.
- Index on `status`.
- Index on `created_at`.

Requirements:

- Projection failures must never invalidate PostgreSQL inventory.
- Projection retries must be idempotent.
- Graph freshness must be visible to API consumers and operators.

## Idempotency Rules

- Scan runs must reference a validated `scan_policy_id` and enabled `scanner_profile_id`.
- Hosts are matched by `primary_ip` in the first implementation.
- Services are matched by `host_id`, `port`, and `protocol`.
- Vulnerabilities are matched by `cve_id` when present.
- Findings should be matched by host, service, vulnerability, finding type, and stable evidence fingerprint.
- Scan artifacts are matched by SHA-256.
- Graph projection should use PostgreSQL UUIDs as stable external identifiers.
- Graph projection jobs are retried by `scan_run_id` and must merge by stable node and relationship keys.

## Required Indexes for Scale

To support 10,000 hosts, 100,000 services, and high scan history volume:

- `hosts(primary_ip)`.
- `hosts(last_seen_at)`.
- `asset_tags(name)`.
- `host_asset_tags(host_id, asset_tag_id)`.
- `host_asset_tags(asset_tag_id)`.
- `services(host_id, port, protocol)`.
- `services(state, exposure)`.
- `findings(host_id, status)`.
- `findings(vulnerability_id, status)`.
- `risk_models(version)`.
- `risk_scores(risk_model_id)`.
- `risk_scores(score)`.
- `scan_policies(is_enabled)`.
- `scanner_profiles(provider, name)`.
- `scan_runs(status, created_at)`.
- `scan_observations(scan_run_id, observation_type)`.
- `graph_projection_jobs(scan_run_id)`.
- `graph_projection_jobs(status, created_at)`.
- `audit_events(created_at)`.

## Data Retention

Recommended defaults:

- Raw scan artifacts: 90 days by default, configurable.
- Scan observations: 180 days by default, configurable.
- Canonical inventory: retained until explicitly deleted or aged out by policy.
- Findings: retained for historical reporting even after resolution.
- Audit events: at least 1 year.
- AI explanations: retained with source evidence unless policy requires deletion.

## Migration Strategy

Initial Alembic migration order:

1. Users, roles, user roles.
2. Scan policies and scanner profiles.
3. Scan runs, targets, artifacts, observations.
4. Hosts, network segments, host segments, asset tags, host asset tags.
5. Services.
6. Vulnerabilities and references.
7. Findings, risk models, and risk scores.
8. MITRE tactics and techniques.
9. Graph projection jobs.
10. Attack paths.
11. AI explanations, alerts, audit events.

## Known Future Schema Extensions

- `host_addresses` for multi-interface hosts.
- `domains`, `users`, and `groups` for Active Directory integration.
- `credentials_metadata` for defensive metadata only, never secrets.
- `scanner_credentials` stored through a secrets manager reference, not plaintext.
- `report_exports` for generated reports.
- `integration_runs` for external vulnerability intelligence syncs.
