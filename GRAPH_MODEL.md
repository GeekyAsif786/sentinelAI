# Graph Model

Neo4j stores derived graph state for traversal and visualization. PostgreSQL remains authoritative.

## Nodes

- `Host`
- `Service`
- `Vulnerability`
- `Finding`
- `NetworkSegment`
- `AssetTag`
- `Technique`
- Future: `User`, `Domain`, `Group`

## Relationships

- `(:Host)-[:RUNS]->(:Service)`
- `(:Service)-[:HAS_VULNERABILITY]->(:Vulnerability)`
- `(:Host)-[:HAS_FINDING]->(:Finding)`
- `(:Service)-[:HAS_FINDING]->(:Finding)`
- `(:Finding)-[:REFERENCES]->(:Vulnerability)`
- `(:Finding)-[:MAPS_TO]->(:Technique)`
- `(:Host)-[:TAGGED_AS]->(:AssetTag)`
- `(:Host)-[:MEMBER_OF]->(:NetworkSegment)`
- Future trust and identity relationships for Active Directory analysis.

## Projection Rules

- Use stable PostgreSQL UUIDs on graph nodes.
- Use deterministic merge keys for idempotent writes.
- Track graph projection jobs.
- Surface graph freshness in API responses.
- Do not store credentials, secrets, payloads, or exploit instructions.

