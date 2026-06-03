# Architecture Review Changes

## Scope

This document records Phase 0.5 architecture refinements made after senior architecture review. The changes are documentation-only and do not include production code, migrations, or source files.

## Summary

The review focused on governance, traceability, repeatability, graph reliability, MVP scope control, AI optionality, and open-source safety boundaries.

Updated documents:

- `SYSTEM_DESIGN.md`.
- `DATABASE_SCHEMA.md`.
- `NEO4J_GRAPH_MODEL.md`.
- `PROJECT_ROADMAP.md`.

## Changes

### Scan Policies

What changed:

- Added `scan_policies` as a required governance concept.
- Added scan policy fields for allowed CIDRs, blocked CIDRs, target limits, scan rate limits, provider restrictions, and enabled state.
- Added `scan_runs.scan_policy_id`.
- Updated scan flow to require policy validation before target validation and queueing.

Why it changed:

- The previous design allowed scan creation but did not define explicit scope governance.

Expected benefits:

- Reduces accidental or unauthorized scanning.
- Makes scan authorization and scope decisions auditable.
- Gives administrators a central control point for scanning behavior.

Migration impact:

- Future migrations need a new `scan_policies` table.
- `scan_runs` needs a required `scan_policy_id` foreign key once policies exist.
- Existing scan creation paths must be designed so no scan can bypass policy validation.

### Scanner Profiles

What changed:

- Added `scanner_profiles` for reusable provider configurations.
- Added `scan_runs.scanner_profile_id`.
- Updated design so users select profiles instead of raw scanner arguments.

Why it changed:

- Raw scanner configuration is hard to govern and easy to misuse.

Expected benefits:

- Centralizes scanner settings.
- Makes scan behavior repeatable.
- Simplifies future policy enforcement by allowing policy restrictions on profiles and providers.

Migration impact:

- Future migrations need a new `scanner_profiles` table.
- `scan_runs` needs a `scanner_profile_id` foreign key.
- API design should validate profile availability before queueing scans.

### Asset Tagging

What changed:

- Added `asset_tags` and `host_asset_tags`.
- Added asset tag use cases for filtering, risk prioritization, reporting, and attack path prioritization.
- Added `AssetTag` nodes and `TAGGED_AS` relationships to the Neo4j projection.

Why it changed:

- Hosts needed a flexible classification mechanism independent of hostname, subnet, or criticality score.

Expected benefits:

- Better operational filtering.
- Better reporting.
- More accurate prioritization for critical environments such as production, PCI, DMZ, and domain controller assets.

Migration impact:

- Future migrations need `asset_tags` and `host_asset_tags`.
- Graph projection must include asset tag nodes and host tag relationships.

### Graph Projection Job Tracking

What changed:

- Added `graph_projection_jobs`.
- Added projection status values: `queued`, `running`, `completed`, `failed`.
- Updated graph consistency rules so projection failure never invalidates PostgreSQL inventory.
- Added graph freshness metadata requirements.

Why it changed:

- Neo4j projection failures need first-class visibility and retry tracking.

Expected benefits:

- Operators can distinguish fresh graph data from stale projections.
- Failed projections can be retried safely.
- PostgreSQL remains authoritative even when graph projection is degraded.

Migration impact:

- Future migrations need `graph_projection_jobs`.
- Graph APIs should surface projection status and freshness.
- Projection jobs must be idempotent by scan run and stable graph identifiers.

### Risk Model Versioning

What changed:

- Added `risk_models`.
- Added `risk_scores.risk_model_id`.
- Clarified that risk model definitions are immutable and historical scores remain reproducible.

Why it changed:

- `risk_scores.scoring_version` existed, but the scoring definition itself was not stored.

Expected benefits:

- Historical reports remain explainable.
- Future scoring changes do not mutate old results.
- Risk calculations can be audited against a specific model.

Migration impact:

- Future migrations need `risk_models`.
- `risk_scores` needs a `risk_model_id` foreign key.
- Risk scoring code must write scores against a concrete model version.

### Roadmap Restructuring

What changed:

- Replaced the old Phase 5 attack path phase with a new Phase 5 Graph Analytics Foundation.
- Moved Attack Path Engine to Phase 6.
- Shifted MITRE mapping, AI, dashboard, monitoring, and hardening phases later.

Why it changed:

- Attack paths depend on graph quality, relationship confidence, bounded traversal, and graph freshness.

Expected benefits:

- Avoids producing misleading attack paths from immature graph data.
- Establishes graph health metrics before advanced path scoring.
- Gives relationship confidence modeling a clear delivery point.

Migration impact:

- No schema migration impact by itself.
- Future implementation sequencing should avoid attack path persistence until graph analytics foundations are stable.

### MVP Scope Simplification

What changed:

- Preserved `DiscoveryProvider`.
- Explicitly limited MVP scanning to Nmap XML ingestion.
- Excluded Masscan, RustScan, OpenVAS, and Nessus from MVP.

Why it changed:

- Multiple scanner integrations would increase early complexity before the normalized ingestion model is proven.

Expected benefits:

- Keeps the first implementation focused.
- Reduces parser and provider variability.
- Preserves extension points without committing to early provider support.

Migration impact:

- No database migration impact beyond scanner profiles and provider fields already documented.
- Provider-specific schema should not be added for non-MVP scanners.

### AI Optionality

What changed:

- AI is now disabled by default.
- The platform must function fully without AI.
- Critical workflows must rely on inventory, risk scores, MITRE mapping, and graph analysis.
- Provider failure must not affect platform functionality.

Why it changed:

- AI is useful for explanation but should not be a hard dependency for security workflows.

Expected benefits:

- Easier local deployment.
- Lower operational risk from provider outages.
- Clear separation between deterministic analysis and generated explanation.

Migration impact:

- No required migration beyond the already documented `ai_explanations` table.
- Future configuration should include an explicit AI enablement flag.

### Open Source Readiness

What changed:

- Added future documentation requirements:
  - `SECURITY_BOUNDARIES.md`.
  - `THREAT_MODEL.md`.
  - `RESPONSIBLE_DISCLOSURE.md`.
- Added contributor guidance against offensive automation, exploit generation, payload generation, and credential abuse features.

Why it changed:

- A defensive security project needs explicit contribution and safety boundaries before public release.

Expected benefits:

- Reduces ambiguity for contributors.
- Keeps the project aligned with defensive and analytical use cases.
- Improves readiness for responsible open-source release.

Migration impact:

- No database migration impact.
- Future repository setup should include these documents before open-source release.

## Verification Notes

- The changes are documentation-only.
- No implementation code was added.
- No migrations were generated.
- Existing architectural decisions were preserved where they remained correct.
