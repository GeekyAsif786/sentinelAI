#!/bin/sh
# backend/docker-entrypoint.sh
# Runs Alembic migrations and seeds dev data, then starts the process passed as $@
set -e

echo "[entrypoint] Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! python -c "from sqlalchemy import create_engine; import os; engine = create_engine(os.environ['DATABASE_URL']); engine.connect()" > /dev/null 2>&1; do
    RETRY_COUNT=$((RETRY_COUNT+1))
    if [ $RETRY_COUNT -ge $MAX_RETRIES ]; then
        echo "[entrypoint] Database connection failed after $MAX_RETRIES attempts, exiting."
        exit 1
    fi
    echo "[entrypoint] Database unavailable, retrying in 2 seconds ($RETRY_COUNT/$MAX_RETRIES)..."
    sleep 2
done

echo "[entrypoint] Database is ready."

echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head

echo "[entrypoint] Seeding dev fixtures (idempotent)..."
python - <<'PYEOF'
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])

seed_sql = """
-- Dev user (matches the UUID issued by /auth/dev-token)
INSERT INTO users (id, email, password_hash, display_name, is_active, created_at, updated_at)
VALUES (
    '00000000-0000-0000-0000-000000000001'::uuid,
    'dev-analyst@example.com',
    NULL,
    'Dev Analyst',
    true,
    NOW(), NOW()
) ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;

-- Default scan policy (allows RFC-1918 and a scoped public lab range)
INSERT INTO scan_policies (
    id, name, description,
    allowed_cidrs, blocked_cidrs,
    max_targets, max_scan_rate,
    provider_restrictions, is_enabled,
    created_at, updated_at
) VALUES (
    'c001e000-0000-0000-0000-000000000001'::uuid,
    'dev-default',
    'Default development scan policy',
    ARRAY['127.0.0.0/8','10.0.0.0/8','192.168.0.0/16','110.224.103.114/32','110.224.103.0/24']::cidr[],
    ARRAY[]::cidr[],
    100, 1000, '{}', true,
    NOW(), NOW()
) ON CONFLICT (id) DO NOTHING;

-- Default nmap scanner profile
INSERT INTO scanner_profiles (
    id, name, provider, description,
    configuration, is_enabled,
    created_at, updated_at
) VALUES (
    'c002e000-0000-0000-0000-000000000001'::uuid,
    'dev-nmap',
    'nmap',
    'Default development nmap profile',
    '{"timing": "T3"}', true,
    NOW(), NOW()
) ON CONFLICT (id) DO NOTHING;
"""

with engine.begin() as conn:
    conn.execute(text(seed_sql))

print("[entrypoint] Dev fixtures applied.")
PYEOF

echo "[entrypoint] Starting: $@"
exec "$@"
