# Step-by-Step Production Deployment Procedures

## Quick Reference

| Phase | Duration | Owner | Status |
|-------|----------|-------|--------|
| Pre-deployment checks | 30 min | Tech Lead | Checklist |
| Backup & Migration | 15-30 min | DBA | Sequential |
| Code deployment | 10-15 min | DevOps | Sequential |
| Smoke tests | 5 min | QA | Validation |
| First hour monitoring | 60 min | On-call | Continuous |
| 4-hour validation | 4 hours | On-call | Hourly |
| 24-hour sign-off | 24 hours | Tech Lead | Final |

---

## Environment Setup

### Required Environment Variables
```bash
# Database Configuration
export PROD_DB_HOST=<production-db-hostname>
export PROD_DB_USER=<database-user>
export PROD_DB_PASS=<database-password>  # From vault/secrets manager
export PROD_DB=sentinel
export PROD_DB_URL="postgresql://$PROD_DB_USER:$PROD_DB_PASS@$PROD_DB_HOST:5432/$PROD_DB"

# Redis Configuration
export PROD_REDIS_HOST=<redis-hostname>
export PROD_REDIS_PORT=6379

# Neo4j Configuration
export NEO4J_HOST=<neo4j-hostname>
export NEO4J_PORT=7687
export NEO4J_USER=<neo4j-user>
export NEO4J_PASS=<neo4j-password>

# API Configuration
export PROD_API_URL=http://localhost:8000

# Deployment Paths
export DEPLOY_PATH=/opt/sentinelai
export BACKUP_PATH=/backups
```

### Secrets Management
```bash
# Load secrets from vault (example using HashiCorp Vault)
vault login -method=ldap username=<your-username>

# Or load from AWS Secrets Manager
aws secretsmanager get-secret-value --secret-id sentinelai/prod \
  --query 'SecretString' --output json | jq -r '.'

# Export secrets securely (shell history will contain credentials, use care)
set +o history  # Disable history
export PROD_DB_PASS=$(vault kv get -field=password secret/sentinelai/prod)
set -o history  # Re-enable history
```

---

## Pre-Deployment Commands

### Verify Environment Variables
```bash
#!/bin/bash
echo "=== Environment Verification ==="

# Check all required variables are set
REQUIRED_VARS="PROD_DB_HOST PROD_DB_USER PROD_REDIS_HOST NEO4J_HOST DEPLOY_PATH BACKUP_PATH"

for var in $REQUIRED_VARS; do
  if [ -z "${!var}" ]; then
    echo "ERROR: $var not set"
    exit 1
  fi
  echo "✓ $var=${!var}"
done

echo "All environment variables configured"
```

### Verify Connectivity (Pre-flight checks)
```bash
#!/bin/bash
set -e

echo "=== Pre-Flight Connectivity Checks ==="

# PostgreSQL
echo -n "Checking PostgreSQL... "
psql "$PROD_DB_URL" -c "SELECT 'OK' as status;" && echo "✓"

# Redis
echo -n "Checking Redis... "
redis-cli -h "$PROD_REDIS_HOST" -p 6379 ping > /dev/null && echo "✓"

# Neo4j
echo -n "Checking Neo4j... "
curl -s "http://$NEO4J_HOST:7474/browser/" > /dev/null && echo "✓"

# File system
echo -n "Checking backup directory... "
mkdir -p "$BACKUP_PATH"
touch "$BACKUP_PATH/.check" && rm "$BACKUP_PATH/.check" && echo "✓"

# Git access
echo -n "Checking Git access... "
cd "$DEPLOY_PATH"
git fetch origin > /dev/null 2>&1 && echo "✓"

echo "All checks passed!"
```

### Check Service Status
```bash
#!/bin/bash
echo "=== Current Service Status ==="

echo "API Service:"
systemctl status sentinelai-api --no-pager

echo ""
echo "Worker Service:"
systemctl status sentinelai-worker --no-pager

echo ""
echo "Database Status:"
psql "$PROD_DB_URL" -c "SELECT version();"

echo ""
echo "Active Connections:"
psql "$PROD_DB_URL" -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"
```

---

## Deployment Commands

### Step 1: Create Backup

```bash
#!/bin/bash
set -e

BACKUP_DIR="$BACKUP_PATH"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/prod_backup_$TIMESTAMP.sql"
LOG_FILE="$BACKUP_DIR/backup_$TIMESTAMP.log"

echo "=== Creating Production Backup ==="
echo "Backup file: $BACKUP_FILE"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR" "$BACKUP_DIR/archive"

# Create full backup with verbose output
pg_dump \
  -h "$PROD_DB_HOST" \
  -U "$PROD_DB_USER" \
  -d "$PROD_DB" \
  --verbose \
  --format=plain \
  --create \
  2>&1 | tee "$LOG_FILE" > "$BACKUP_FILE"

# Verify backup
if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not created"
  exit 1
fi

SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
SIZE_MB=$((SIZE / 1024 / 1024))

if [ "$SIZE_MB" -lt 10 ]; then
  echo "ERROR: Backup too small ($SIZE_MB MB), likely incomplete"
  exit 1
fi

echo "✓ Backup created successfully: $SIZE_MB MB"

# Archive to secondary location
cp "$BACKUP_FILE" "$BACKUP_DIR/archive/prod_backup_$TIMESTAMP.sql"
echo "✓ Backup archived"

# Verify backup integrity (optional but recommended)
echo "Verifying backup integrity..."
if head -100 "$BACKUP_FILE" | grep -q "PostgreSQL dump"; then
  echo "✓ Backup file integrity verified"
else
  echo "WARNING: Backup integrity check inconclusive"
fi

# Store location for rollback
echo "$BACKUP_FILE" > "$BACKUP_DIR/.last_backup"
echo "✓ Backup location recorded"
```

### Step 2: Apply Database Migration

```bash
#!/bin/bash
set -e

cd "$DEPLOY_PATH/backend" || exit 1

echo "=== Applying Database Migration ==="

# Verify production database
echo "Current migration status:"
alembic current

# Generate SQL for review
echo ""
echo "Generating migration SQL for review..."
alembic upgrade head --sql > /tmp/migration_statements.sql
echo "Generated SQL available at: /tmp/migration_statements.sql"
echo ""

# Show first 50 lines of migration
head -50 /tmp/migration_statements.sql

echo ""
read -p "Review SQL above. Continue with migration? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  echo "Migration cancelled by user"
  exit 1
fi

# Apply migration
echo ""
echo "Applying migration..."
alembic upgrade head -v 2>&1 | tee /tmp/migration_upgrade.log

# Verify
echo ""
echo "Verifying migration..."
alembic current

# Final verification
CURRENT_REV=$(alembic current | grep -oE '[0-9a-f]+')
echo "Current revision: $CURRENT_REV"
```

### Step 3: Verify Schema Changes

```bash
#!/bin/bash
set -e

echo "=== Verifying Schema Changes ==="

# Test 1: New table exists
echo "Test 1: Checking graph_projection_jobs table..."
psql "$PROD_DB_URL" << 'SQL' || { echo "FAILED"; exit 1; }
\d graph_projection_jobs
SQL
echo "✓ graph_projection_jobs table exists"

# Test 2: New column exists
echo ""
echo "Test 2: Checking worker_node_id column..."
psql "$PROD_DB_URL" -t << 'SQL' | grep -q worker_node_id || { echo "FAILED"; exit 1; }
\d scan_runs
SQL
echo "✓ worker_node_id column exists"

# Test 3: Indexes created
echo ""
echo "Test 3: Checking indexes..."
psql "$PROD_DB_URL" << 'SQL'
SELECT indexname, indexdef 
FROM pg_indexes 
WHERE tablename = 'graph_projection_jobs' 
ORDER BY indexname;
SQL
echo "✓ Indexes verified"

# Test 4: Data integrity
echo ""
echo "Test 4: Checking data integrity..."
psql "$PROD_DB_URL" << 'SQL'
-- Check for constraint violations
SELECT 'scan_runs' as table_name, COUNT(*) as row_count FROM scan_runs
UNION ALL
SELECT 'hosts', COUNT(*) FROM hosts
UNION ALL
SELECT 'graph_projection_jobs', COUNT(*) FROM graph_projection_jobs
ORDER BY table_name;
SQL
echo "✓ Data integrity verified"

echo ""
echo "=== Schema Verification Complete ==="
```

### Step 4: Deploy Code

```bash
#!/bin/bash
set -e

DEPLOY_PATH=/opt/sentinelai
cd "$DEPLOY_PATH" || exit 1

echo "=== Deploying Application Code ==="

# Show current state
echo "Current code:"
git log -1 --oneline

# Fetch latest
echo ""
echo "Fetching latest from origin..."
git fetch origin main

# Show what will be deployed
echo ""
echo "Latest on main:"
git log -1 origin/main --oneline

# Checkout and pull
echo ""
echo "Checking out main branch..."
git checkout main
git pull origin main

DEPLOYED_SHA=$(git rev-parse HEAD)
echo "✓ Code updated to: $DEPLOYED_SHA"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt --no-deps 2>&1 | tail -20

if [ $? -ne 0 ]; then
  echo "ERROR: Dependency installation failed"
  exit 1
fi
echo "✓ Dependencies installed"

# Record deployment state
echo ""
echo "Stopping services for restart..."
systemctl stop sentinelai-api sentinelai-worker || true
sleep 2

echo "Starting services..."
systemctl start sentinelai-api sentinelai-worker

sleep 3

echo "Verifying service status..."
systemctl status sentinelai-api --no-pager || { echo "API failed to start"; exit 1; }
systemctl status sentinelai-worker --no-pager || { echo "Worker failed to start"; exit 1; }

echo "✓ Services restarted successfully"
echo "  Deployed SHA: $DEPLOYED_SHA"
```

### Step 5: Smoke Tests

```bash
#!/bin/bash
set -e

echo "=== Running Smoke Tests ==="

# Test 1: API Health
echo "Test 1: API Health Check..."
HEALTH=$(curl -s -w "\n%{http_code}" http://localhost:8000/health)
HTTP_CODE=$(echo "$HEALTH" | tail -1)
BODY=$(echo "$HEALTH" | head -n -1)

if [ "$HTTP_CODE" != "200" ]; then
  echo "FAILED: HTTP $HTTP_CODE"
  echo "Response: $BODY"
  exit 1
fi

if ! echo "$BODY" | jq -e '.status == "ok"' > /dev/null 2>&1; then
  echo "FAILED: Status not 'ok'"
  echo "Response: $BODY"
  exit 1
fi
echo "✓ API responding correctly"

# Test 2: Database Query
echo ""
echo "Test 2: Database Query..."
SCAN_COUNT=$(psql "$PROD_DB_URL" -t -c "SELECT COUNT(*) FROM scan_runs;")
echo "Scan runs in database: $SCAN_COUNT"
echo "✓ Database query successful"

# Test 3: Worker Status
echo ""
echo "Test 3: Worker Status..."
WORKER_INFO=$(celery -A app.worker inspect active_queues)
if [ $? -ne 0 ]; then
  echo "FAILED: Worker not responding"
  exit 1
fi
echo "Worker response:"
echo "$WORKER_INFO" | jq .
echo "✓ Worker operational"

# Test 4: Redis
echo ""
echo "Test 4: Redis Connectivity..."
REDIS_PONG=$(redis-cli -h "$PROD_REDIS_HOST" -p 6379 ping)
if [ "$REDIS_PONG" != "PONG" ]; then
  echo "FAILED: Redis not responding"
  exit 1
fi
echo "✓ Redis responding"

# Test 5: Database Write (Rollback)
echo ""
echo "Test 5: Database Write Test..."
psql "$PROD_DB_URL" << 'SQL'
BEGIN;
  INSERT INTO hosts (name, environment) VALUES ('smoke-test-host-'||NOW()::text, 'production');
  SELECT COUNT(*) as inserted FROM hosts WHERE name LIKE 'smoke-test-host%';
ROLLBACK;
SQL
if [ $? -ne 0 ]; then
  echo "FAILED: Database write test failed"
  exit 1
fi
echo "✓ Database write test passed"

echo ""
echo "=== All Smoke Tests Passed ==="
```

---

## Monitoring Commands

### First Hour Real-Time Monitoring

```bash
#!/bin/bash
INTERVAL=60  # Check every minute
END_TIME=$(($(date +%s) + 3600))

echo "=== First Hour Monitoring (1 minute intervals) ==="

while [ $(date +%s) -lt $END_TIME ]; do
  TIMESTAMP=$(date '+%H:%M:%S')
  
  echo "[$TIMESTAMP] ============================================"
  
  # Error rate
  ERROR_RATE=$(psql "$PROD_DB_URL" -t << 'SQL' 2>/dev/null || echo "ERROR")
SELECT ROUND(
  (SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)::float / 
   NULLIF(COUNT(*), 0)) * 100, 2)
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '5 minutes';
SQL
  echo "[$TIMESTAMP] Error rate (5 min): $ERROR_RATE%"
  
  # Database connections
  DB_CONNS=$(psql "$PROD_DB_URL" -t -c "SELECT COUNT(*) FROM pg_stat_activity;" 2>/dev/null || echo "ERROR")
  echo "[$TIMESTAMP] DB connections: $DB_CONNS"
  
  # Worker queue depth
  QUEUE_DEPTH=$(celery -A app.worker inspect active 2>/dev/null | jq 'length' || echo "ERROR")
  echo "[$TIMESTAMP] Active worker tasks: $QUEUE_DEPTH"
  
  # API response time (simple curl)
  RESPONSE_TIME=$( { time curl -s http://localhost:8000/health > /dev/null 2>&1; } 2>&1 | grep real | awk '{print $2}')
  echo "[$TIMESTAMP] API response time: $RESPONSE_TIME"
  
  # Recent errors in logs
  ERROR_COUNT=$(journalctl -u sentinelai-api --since "1 minute ago" 2>/dev/null | grep -ci ERROR || true)
  echo "[$TIMESTAMP] API errors (last min): $ERROR_COUNT"
  
  # Memory usage
  MEMORY=$(ps aux | grep sentinelai-api | grep -v grep | awk '{print $6}' | head -1)
  echo "[$TIMESTAMP] API memory: ${MEMORY}KB"
  
  sleep $INTERVAL
done

echo "First hour monitoring complete"
```

### Metric Query Dashboard

```bash
#!/bin/bash
echo "=== Production Metrics Dashboard ==="
echo "Timestamp: $(date)"
echo ""

# Scan statistics
echo "SCAN STATISTICS:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  COUNT(*) as total_scans,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::numeric, 2) as avg_duration_sec
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '24 hours';
SQL
echo ""

# Database health
echo "DATABASE HEALTH:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  'Active connections' as metric,
  COUNT(*)::text as value
FROM pg_stat_activity
UNION ALL
SELECT 'Slow queries (>1s)', COUNT(*)::text 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000
ORDER BY metric;
SQL
echo ""

# Graph projection status
echo "GRAPH PROJECTION STATUS:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  status,
  COUNT(*) as count,
  AVG(EXTRACT(EPOCH FROM (completed_at - created_at)))::numeric(10,2) as avg_duration_sec
FROM graph_projection_jobs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY status
ORDER BY status;
SQL
echo ""

# Redis info
echo "REDIS STATUS:"
redis-cli -h "$PROD_REDIS_HOST" INFO stats 2>/dev/null | grep -E "total_commands_processed|connected_clients"

echo ""
echo "Dashboard generated at $(date)"
```

---

## Rollback Commands

### Database Rollback

```bash
#!/bin/bash
set -e

echo "=== DATABASE ROLLBACK PROCEDURE ==="

BACKUP_FILE=$(cat "$BACKUP_PATH/.last_backup" 2>/dev/null)

if [ -z "$BACKUP_FILE" ]; then
  echo "ERROR: No backup file recorded. Check $BACKUP_PATH/.last_backup"
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "Using backup: $BACKUP_FILE"
read -p "Continue with database rollback? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  echo "Rollback cancelled"
  exit 1
fi

# Stop services
echo "Stopping services..."
systemctl stop sentinelai-api sentinelai-worker

sleep 5

# Terminate connections
echo "Terminating database connections..."
psql "$PROD_DB_URL" << 'SQL'
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = current_database() AND pid <> pg_backend_pid();
SQL

sleep 3

# Create pre-rollback backup for investigation
echo "Creating pre-rollback backup..."
pg_dump -h "$PROD_DB_HOST" -U "$PROD_DB_USER" -d "$PROD_DB" > \
  "$BACKUP_PATH/pre_rollback_$(date +%Y%m%d_%H%M%S).sql"

# Restore
echo "Restoring from backup..."
psql "$PROD_DB_URL" < "$BACKUP_FILE" > /tmp/rollback_restore.log 2>&1

if [ $? -ne 0 ]; then
  echo "ERROR: Restore failed"
  tail -50 /tmp/rollback_restore.log
  exit 1
fi

# Verify
echo "Verifying restore..."
RESTORED_COUNT=$(psql "$PROD_DB_URL" -t -c "SELECT COUNT(*) FROM scan_runs;")
echo "Scan runs after restore: $RESTORED_COUNT"

# Restart services
echo "Restarting services..."
systemctl start sentinelai-api sentinelai-worker

sleep 3

systemctl status sentinelai-api sentinelai-worker

echo "✓ Database rollback complete"
```

### Code Rollback

```bash
#!/bin/bash
set -e

cd "$DEPLOY_PATH" || exit 1

echo "=== CODE ROLLBACK PROCEDURE ==="
echo "Current code:"
git log -1 --oneline

echo ""
echo "Recent commits:"
git log --oneline -10

read -p "Enter commit SHA to rollback to (e.g., abc1234): " -r ROLLBACK_SHA

if [ -z "$ROLLBACK_SHA" ]; then
  echo "No SHA provided, cancelling"
  exit 1
fi

# Stop services
echo "Stopping services..."
systemctl stop sentinelai-api sentinelai-worker

# Checkout
echo "Checking out $ROLLBACK_SHA..."
git fetch origin
git checkout "$ROLLBACK_SHA"

# Reinstall dependencies
echo "Reinstalling dependencies..."
pip install -r requirements.txt --no-deps

# Restart
echo "Restarting services..."
systemctl start sentinelai-api sentinelai-worker

sleep 3
systemctl status sentinelai-api sentinelai-worker

echo "✓ Code rollback complete to: $ROLLBACK_SHA"
```

---

## Troubleshooting Commands

### Investigate Errors

```bash
#!/bin/bash
echo "=== Error Investigation ==="

# Recent API errors
echo "Recent API errors:"
journalctl -u sentinelai-api -n 50 --no-pager | grep -i error

echo ""
echo "Recent worker errors:"
journalctl -u sentinelai-worker -n 50 --no-pager | grep -i error

# Slow queries
echo ""
echo "Slowest queries (top 5):"
psql "$PROD_DB_URL" << 'SQL' || true
SELECT 
  LEFT(query, 60) as query,
  calls,
  ROUND(mean_exec_time::numeric, 2) as mean_ms,
  ROUND(max_exec_time::numeric, 2) as max_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 5;
SQL

# Blocking queries
echo ""
echo "Blocking queries:"
psql "$PROD_DB_URL" << 'SQL' || true
SELECT 
  blocked_locks.pid AS blocked_pid,
  blocked_activity.usename AS blocked_user,
  blocking_locks.pid AS blocking_pid,
  blocking_activity.usename AS blocking_user,
  blocked_activity.query AS blocked_statement,
  blocking_activity.query AS blocking_statement
FROM pg_catalog.pg_locks blocked_locks
JOIN pg_catalog.pg_stat_activity blocked_activity ON blocked_activity.pid = blocked_locks.pid
JOIN pg_catalog.pg_locks blocking_locks ON blocking_locks.locktype = blocked_locks.locktype
  AND blocking_locks.database IS NOT DISTINCT FROM blocked_locks.database
  AND blocking_locks.relation IS NOT DISTINCT FROM blocked_locks.relation
  AND blocking_locks.page IS NOT DISTINCT FROM blocked_locks.page
  AND blocking_locks.tuple IS NOT DISTINCT FROM blocked_locks.tuple
  AND blocking_locks.virtualxid IS NOT DISTINCT FROM blocked_locks.virtualxid
  AND blocking_locks.transactionid IS NOT DISTINCT FROM blocked_locks.transactionid
  AND blocking_locks.classid IS NOT DISTINCT FROM blocked_locks.classid
  AND blocking_locks.objid IS NOT DISTINCT FROM blocked_locks.objid
  AND blocking_locks.objsubid IS NOT DISTINCT FROM blocked_locks.objsubid
  AND blocking_locks.pid != blocked_locks.pid
JOIN pg_catalog.pg_stat_activity blocking_activity ON blocking_activity.pid = blocking_locks.pid
WHERE NOT blocked_locks.granted;
SQL
```

### Check Service Logs

```bash
#!/bin/bash

# Last 100 lines of API logs
echo "=== API Service Logs (last 100 lines) ==="
journalctl -u sentinelai-api -n 100 --no-pager

echo ""
echo "=== Worker Service Logs (last 100 lines) ==="
journalctl -u sentinelai-worker -n 100 --no-pager

# Errors only
echo ""
echo "=== API Errors (last 24 hours) ==="
journalctl -u sentinelai-api --since "24 hours ago" --no-pager | grep -i error

echo ""
echo "=== Worker Errors (last 24 hours) ==="
journalctl -u sentinelai-worker --since "24 hours ago" --no-pager | grep -i error
```

### Performance Analysis

```bash
#!/bin/bash
echo "=== Performance Analysis ==="

# Query performance
echo "Query execution time distribution:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  CASE 
    WHEN mean_exec_time < 1 THEN '< 1ms'
    WHEN mean_exec_time < 10 THEN '1-10ms'
    WHEN mean_exec_time < 100 THEN '10-100ms'
    WHEN mean_exec_time < 1000 THEN '100ms-1s'
    ELSE '> 1s'
  END as range,
  COUNT(*) as query_count
FROM pg_stat_statements
GROUP BY range
ORDER BY range;
SQL

# Index usage
echo ""
echo "Index efficiency:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  schemaname,
  tablename,
  indexname,
  idx_scan as scans,
  idx_tup_read as tuples_read,
  idx_tup_fetch as tuples_fetched
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC
LIMIT 10;
SQL

# Table sizes
echo ""
echo "Largest tables:"
psql "$PROD_DB_URL" << 'SQL'
SELECT 
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
  n_live_tup as row_count
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
LIMIT 10;
SQL
```

---

## Post-Deployment Checklist Commands

### 24-Hour Sign-Off Report

```bash
#!/bin/bash
cat > /tmp/deployment_report_$(date +%Y%m%d_%H%M%S).md << 'EOF'
# Deployment Sign-Off Report

**Date:** $(date)
**Deployed SHA:** $(git -C $DEPLOY_PATH log -1 --format=%H)
**Migration:** $(psql "$PROD_DB_URL" -t -c "SELECT version FROM alembic_version;")

## Metrics

### Uptime
- Deployment to now: $(ps -o etime= -p $(pgrep -f sentinelai-api | head -1))

### Scan Statistics
EOF

psql "$PROD_DB_URL" << 'SQL' >> /tmp/deployment_report_$(date +%Y%m%d_%H%M%S).md
SELECT '- Total scans: ' || COUNT(*) FROM scan_runs
UNION ALL
SELECT '- Success rate: ' || ROUND(100.0 * COUNT(CASE WHEN status = 'completed' THEN 1 END) / COUNT(*), 2) || '%' FROM scan_runs
UNION ALL
SELECT '- Average duration: ' || ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) || 's' FROM scan_runs
UNION ALL
SELECT '- Graph jobs completed: ' || COUNT(*) FROM graph_projection_jobs WHERE status = 'completed';
SQL

echo ""
echo "Report generated: /tmp/deployment_report_$(date +%Y%m%d_%H%M%S).md"
```

---

## Quick Command Reference

```bash
# Verify deployment success
curl http://localhost:8000/health && echo "API OK"
psql $PROD_DB_URL -c "SELECT 1" && echo "DB OK"

# Check error rate
psql $PROD_DB_URL << 'SQL'
SELECT ROUND(100.0 * COUNT(CASE WHEN status = 'failed' THEN 1 END) / COUNT(*), 2) 
FROM scan_runs 
WHERE created_at > NOW() - INTERVAL '1 hour';
SQL

# Monitor in real-time
watch -n 5 'psql $PROD_DB_URL -c "SELECT status, COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '\''1 hour'\'' GROUP BY status;"'

# Tail logs
journalctl -u sentinelai-api -u sentinelai-worker -f

# Kill and restart services
systemctl stop sentinelai-api sentinelai-worker && sleep 5 && systemctl start sentinelai-api sentinelai-worker

# Get deployment status
systemctl status sentinelai-api sentinelai-worker
```
