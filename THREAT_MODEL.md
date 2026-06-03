# Threat Model

## Assets

- User identities and roles.
- Scan policies and scanner profiles.
- Raw scan artifacts.
- Asset inventory.
- Vulnerability findings.
- Graph projection data.
- AI prompts and generated explanations.
- Audit logs.

## Primary Risks

- Unauthorized scan execution.
- Out-of-scope target scanning.
- Scanner profile abuse.
- Sensitive artifact leakage.
- AI hallucination presented as fact.
- Graph projection drift.
- Excessive graph responses causing resource exhaustion.
- Weak JWT secret management.

## Mitigations

- Enforce RBAC.
- Require scan policies.
- Hide raw scanner flags from users.
- Store AI output separately from deterministic findings.
- Keep graph projection retryable and freshness-visible.
- Bound API pagination and graph depth.
- Use production secret management.
- Audit security-relevant actions.

