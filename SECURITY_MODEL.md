# Security Model

## Roles

- `admin`: users, settings, integrations, and all scans.
- `analyst`: run scans, inspect assets, request analysis.
- `viewer`: read-only dashboard access.
- `auditor`: read-only audit and reporting access.

## Controls

- JWT authentication.
- RBAC checks on protected endpoints.
- Mandatory scan policy selection.
- Scanner profile selection instead of raw scanner flags.
- Request logging with sensitive data redaction.
- Audit trails for scan creation, configuration changes, user changes, and AI analysis requests.
- Rate limiting at the API edge in production.

## Scan Governance

Every scan must pass:

1. Enabled scan policy validation.
2. Provider/profile restriction validation.
3. Target validation.
4. Queue submission.

No API route should directly run a scanner process.

