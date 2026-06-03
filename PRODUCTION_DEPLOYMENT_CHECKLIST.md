# SentinelAI Phase 2-4 Production Deployment Checklist

## Pre-Deployment Verification (48 hours before)

### Infrastructure Readiness
- [ ] Production PostgreSQL database online and responsive
- [ ] Production Redis cluster operational and accessible
- [ ] Neo4j production instance configured and running
- [ ] All services accessible from deployment location
- [ ] Network connectivity verified (SSH, git, cloud CLI)
- [ ] Sufficient disk space available (10GB+ for database backups)
- [ ] CPU and memory adequate (8+ cores, 16GB+ RAM minimum)
- [ ] Firewall rules configured for all services
- [ ] SSL/TLS certificates valid and not expiring soon

### Code and Schema Readiness
- [ ] All code merged to main branch
- [ ] Code review completed and approved by 2+ reviewers
- [ ] All tests passing (22/22)
- [ ] No outstanding linting issues
- [ ] Migration script reviewed by DBA
- [ ] Rollback procedure documented and tested
- [ ] Database backup strategy confirmed
- [ ] Schema changes compatible with current version
- [ ] Data migration scripts tested on staging
- [ ] Foreign key and constraint integrity verified

### Team Readiness
- [ ] Deployment scheduled outside peak hours (off-peak window identified)
- [ ] On-call team briefed and confirmed attending
- [ ] Rollback procedures reviewed with entire team
- [ ] Communication channels established (Slack, war room, bridge line)
- [ ] Stakeholders notified and aware of maintenance window
- [ ] Runbook printed or readily accessible
- [ ] Team roster and emergency contacts visible
- [ ] No team members on vacation during deployment window

### Monitoring Setup
- [ ] Production Prometheus configured and scraping metrics
- [ ] Grafana dashboards loaded and accessible
- [ ] Alert rules imported and tested
- [ ] Log aggregation pipeline configured
- [ ] On-call pagerduty/OpsGenie configured
- [ ] Slack notifications enabled for critical alerts
- [ ] Health check endpoints configured
- [ ] Baseline metrics captured for comparison
- [ ] Custom dashboards for deployment monitoring ready

---

## Deployment Execution (T-0 hours)

### T-1h: Final Preparation
- [ ] All team members online and ready
- [ ] Database backups automated and running
- [ ] Monitoring dashboards visible to all team members
- [ ] Chat room established for real-time updates
- [ ] Rollback plan reviewed one final time
- [ ] Load balancers configured appropriately
- [ ] CDN cache cleared if applicable
- [ ] All environment variables verified correct
- [ ] Secrets validated in production environment

### T-15m: Pre-Flight Checks

**Run pre-flight verification script:**
```bash
#!/bin/bash
set -e

echo "[$(date)] Starting pre-flight checks..."

# Database connectivity
echo "[$(date)] Checking database..."
psql $PROD_DB_URL -c "SELECT version();" > /dev/null || { 
  echo "ERROR: Database check failed"; exit 1; 
}

# Redis connectivity
echo "[$(date)] Checking Redis..."
redis-cli -h $PROD_REDIS_HOST -p 6379 ping > /dev/null || { 
  echo "ERROR: Redis check failed"; exit 1; 
}

# API health
echo "[$(date)] Checking API health..."
curl -s http://localhost:8000/health | jq . > /dev/null || { 
  echo "ERROR: API health check failed"; exit 1; 
}

# Neo4j connectivity
echo "[$(date)] Checking Neo4j..."
curl -s http://$NEO4J_HOST:7474 > /dev/null || { 
  echo "ERROR: Neo4j check failed"; exit 1; 
}

# Disk space
echo "[$(date)] Checking disk space..."
DISK_AVAIL=$(df /opt/sentinelai | tail -1 | awk '{print $4}')
if [ $DISK_AVAIL -lt 10485760 ]; then
  echo "ERROR: Insufficient disk space (need 10GB, have $(( $DISK_AVAIL / 1048576 ))GB)"; 
  exit 1;
fi

echo "[$(date)] Pre-flight checks PASSED"
```

- [ ] Database responsive to queries
- [ ] Redis responding to PING
- [ ] API responding with 200 status
- [ ] Neo4j accessible
- [ ] Disk space > 10GB available
- [ ] No critical alerts triggered
- [ ] No active incidents reported

### T-0m: Deploy

#### Step 1: Create Production Backup
```bash
BACKUP_DIR="/backups"
BACKUP_FILE="$BACKUP_DIR/prod_backup_$(date +%Y%m%d_%H%M%S).sql"

echo "[$(date)] Starting database backup..."
pg_dump -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB \
  --verbose 2>&1 | tee "$BACKUP_DIR/backup_$(date +%s).log" > "$BACKUP_FILE"

# Verify backup
BACKUP_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
echo "[$(date)] Backup created: $BACKUP_FILE ($(( $BACKUP_SIZE / 1024 / 1024 ))MB)"

if [ $BACKUP_SIZE -lt 10485760 ]; then
  echo "ERROR: Backup too small ($(( $BACKUP_SIZE / 1024 / 1024 ))MB), likely incomplete"
  exit 1
fi

# Archive backup to secondary location
cp "$BACKUP_FILE" "$BACKUP_DIR/archive/$(basename $BACKUP_FILE)"
```

- [ ] Backup started successfully
- [ ] Backup completed without errors
- [ ] Backup size > 10MB (data captured)
- [ ] Backup location documented (location: `$BACKUP_FILE`)
- [ ] Secondary archive copy created
- [ ] Backup integrity verified

#### Step 2: Apply Database Migration

```bash
cd /opt/sentinelai/backend

# Verify we're pointing to production
echo "[$(date)] Database URL: $DATABASE_URL" | grep -q prod || {
  echo "ERROR: Not connected to production database!"
  exit 1
}

# Show current migration status
echo "[$(date)] Current migration status:"
alembic current

# Generate migration SQL for review (optional)
echo "[$(date)] Generating migration SQL..."
alembic upgrade head --sql > /tmp/migration_statements_$(date +%s).sql
echo "[$(date)] SQL preview saved to /tmp/migration_statements_*.sql"

# Run migration with verbose logging
echo "[$(date)] Applying migration..."
alembic upgrade head -v 2>&1 | tee /tmp/migration_upgrade_$(date +%s).log

# Verify migration succeeded
echo "[$(date)] Verifying migration status..."
CURRENT_REVISION=$(alembic current)
echo "[$(date)] Migration complete: $CURRENT_REVISION"

# Ensure we reached the target revision
if ! echo "$CURRENT_REVISION" | grep -q "0002_add_graph_jobs"; then
  echo "ERROR: Migration did not reach expected revision!"
  exit 1
fi
```

- [ ] Connected to production database (verified in URL)
- [ ] Migration executed without errors
- [ ] No timeout or connection errors
- [ ] No constraint violations
- [ ] Alembic current shows: 0002_add_graph_jobs (or expected revision)
- [ ] Migration log reviewed for warnings

#### Step 3: Verify Production Schema Changes

```bash
echo "[$(date)] Verifying schema changes..."

# Verify new table exists
echo "[$(date)] Checking graph_projection_jobs table..."
psql $PROD_DB_URL -c "\\d graph_projection_jobs" | head -20

# Count rows
GRAPH_JOBS=$(psql $PROD_DB_URL -t -c "SELECT COUNT(*) FROM graph_projection_jobs;")
echo "[$(date)] graph_projection_jobs row count: $GRAPH_JOBS"

# Verify new column exists in scan_runs
echo "[$(date)] Checking scan_runs columns..."
psql $PROD_DB_URL -c "\\d scan_runs" | grep worker_node_id

# Verify indexes created
echo "[$(date)] Checking indexes on graph_projection_jobs..."
psql $PROD_DB_URL -c "SELECT indexname FROM pg_indexes 
WHERE tablename = 'graph_projection_jobs' ORDER BY indexname;"

# Verify index count
INDEX_COUNT=$(psql $PROD_DB_URL -t -c "SELECT COUNT(*) FROM pg_indexes 
WHERE tablename = 'graph_projection_jobs';")
echo "[$(date)] Indexes on graph_projection_jobs: $INDEX_COUNT"
```

- [ ] graph_projection_jobs table exists and accessible
- [ ] graph_projection_jobs row count verified (0 initially is expected)
- [ ] worker_node_id column exists on scan_runs table
- [ ] At least 2 indexes present (status, created_at, or scan_run_id)
- [ ] No errors or warnings during verification
- [ ] Primary keys and constraints intact
- [ ] Existing data not corrupted

#### Step 4: Deploy New Code

```bash
cd /opt/sentinelai

echo "[$(date)] Current code status:"
git log -1 --oneline

# Pull latest code
echo "[$(date)] Fetching latest code from main..."
git fetch origin main
git log -1 origin/main --oneline

echo "[$(date)] Checking out main branch..."
git checkout main
git pull origin main

DEPLOYED_SHA=$(git rev-parse HEAD)
echo "[$(date)] Deployed SHA: $DEPLOYED_SHA"

# Install dependencies
echo "[$(date)] Installing dependencies..."
pip install -r requirements.txt --no-deps 2>&1 | tee /tmp/pip_install_$(date +%s).log

# Check for installation errors
if [ $? -ne 0 ]; then
  echo "ERROR: Dependency installation failed!"
  exit 1
fi

# Restart application services
echo "[$(date)] Stopping services..."
systemctl stop sentinelai-api sentinelai-worker

sleep 2

echo "[$(date)] Starting services..."
systemctl start sentinelai-api sentinelai-worker

sleep 3

# Verify services started
echo "[$(date)] Verifying service status..."
systemctl status sentinelai-api sentinelai-worker
```

- [ ] Code pulled from main successfully
- [ ] Git SHA recorded for audit trail
- [ ] Dependencies installed without errors
- [ ] API service restarted successfully
- [ ] Worker service restarted successfully
- [ ] Services show "running" status
- [ ] Services have proper restart policy configured

#### Step 5: Smoke Tests

```bash
echo "[$(date)] Starting smoke tests..."

# Test 1: API responds
echo "[$(date)] Test 1: API health check..."
HEALTH_RESPONSE=$(curl -s http://localhost:8000/health)
echo "Response: $HEALTH_RESPONSE"
echo "$HEALTH_RESPONSE" | jq .status | grep -q "ok" || {
  echo "ERROR: API health check failed!"
  exit 1
}
echo "PASSED"

# Test 2: Database query works
echo "[$(date)] Test 2: Database connectivity..."
DB_COUNT=$(psql $PROD_DB_URL -t -c "SELECT COUNT(*) FROM scan_runs;")
echo "Scan runs count: $DB_COUNT"
if [ "$DB_COUNT" -ge 0 ]; then
  echo "PASSED"
else
  echo "ERROR: Database query failed!"
  exit 1
fi

# Test 3: Worker can process tasks
echo "[$(date)] Test 3: Worker queue status..."
WORKER_STATUS=$(celery -A app.worker inspect active_queues)
echo "$WORKER_STATUS" | jq . > /dev/null || {
  echo "ERROR: Worker inspection failed!"
  exit 1
}
echo "PASSED"

# Test 4: Redis functional
echo "[$(date)] Test 4: Redis connectivity..."
redis-cli -h $PROD_REDIS_HOST -p 6379 ping | grep -q "PONG" || {
  echo "ERROR: Redis check failed!"
  exit 1
}
echo "PASSED"

# Test 5: Can create basic objects
echo "[$(date)] Test 5: Database write test..."
psql $PROD_DB_URL << 'SQL'
BEGIN;
INSERT INTO hosts (name, environment) VALUES ('smoke-test-host', 'production') 
RETURNING id;
ROLLBACK;
SQL
if [ $? -eq 0 ]; then
  echo "PASSED"
else
  echo "ERROR: Database write test failed!"
  exit 1
fi

echo "[$(date)] All smoke tests PASSED"
```

- [ ] API health check returns 200 and status "ok"
- [ ] Database query succeeds and returns row count
- [ ] Worker inspection returns valid JSON
- [ ] Redis responds to PING with "PONG"
- [ ] Database write/rollback test succeeds
- [ ] No errors in service logs
- [ ] Response times acceptable (< 1 second)

---

## Post-Deployment Monitoring (T+1h to T+24h)

### First Hour Validation (T+0m to T+60m)
Monitor continuously every 5 minutes:

```bash
# Monitoring script for first hour
INTERVAL=300  # 5 minutes
END_TIME=$(($(date +%s) + 3600))

while [ $(date +%s) -lt $END_TIME ]; do
  TIMESTAMP=$(date)
  
  # Error rate check
  ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query?query='rate(http_errors[5m])' | jq '.data.result[0].value[1]' 2>/dev/null || echo "0")
  echo "[$TIMESTAMP] Error rate: $ERROR_RATE"
  
  # Latency check
  P95_LATENCY=$(curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95,rate(http_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]' 2>/dev/null || echo "0")
  echo "[$TIMESTAMP] P95 Latency: ${P95_LATENCY}s"
  
  # Database connections
  DB_CONNS=$(psql $PROD_DB_URL -t -c "SELECT count(*) FROM pg_stat_activity;")
  echo "[$TIMESTAMP] DB connections: $DB_CONNS"
  
  # Worker queue depth
  QUEUE_DEPTH=$(celery -A app.worker inspect active_queues | jq 'length' 2>/dev/null || echo "0")
  echo "[$TIMESTAMP] Worker queue depth: $QUEUE_DEPTH"
  
  # Check for errors in logs
  RECENT_ERRORS=$(journalctl -u sentinelai-api --since "5 minutes ago" | grep -c ERROR || true)
  echo "[$TIMESTAMP] API errors in last 5 minutes: $RECENT_ERRORS"
  
  echo "---"
  sleep $INTERVAL
done
```

**Monitoring checklist - verify every 5 minutes:**
- [ ] Error rate < 2% (acceptable threshold)
- [ ] Response latency P95 < 500ms
- [ ] Database connection pool usage < 50% of max
- [ ] Worker queue depth < 10 tasks
- [ ] No worker disconnects or crashes
- [ ] No API 5xx errors in logs
- [ ] Memory usage stable (not growing)
- [ ] No hanging requests or timeouts

### 4-Hour Validation (T+1h to T+5h)
Check every 15 minutes:
- [ ] Completed scan count > 0 (new scans being executed)
- [ ] Graph projection jobs executing (status = 'running' or 'completed')
- [ ] No data corruption detected
- [ ] No cascading failures
- [ ] Performance metrics stable (no degradation)
- [ ] Database backup size increasing (new data being written)
- [ ] No network issues or timeouts
- [ ] Cache hit rates appropriate

**Validation query:**
```sql
SELECT 
  COUNT(*) as total_scans,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  MIN(created_at) as oldest,
  MAX(completed_at) as most_recent
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '4 hours';
```

### 24-Hour Validation (T+5h to T+24h)
Check every hour:
- [ ] Error rate consistently < 2%
- [ ] All projection jobs completed or progressing
- [ ] No connection pool exhaustion events
- [ ] Memory usage stable (not growing unbounded)
- [ ] Disk usage stable and within limits
- [ ] No retry storms or cascading failures
- [ ] Database performance degradation < 5%
- [ ] Worker processing consistent throughput

**24-hour validation report:**
```sql
SELECT 
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as scan_count,
  COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
  COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
  ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at)))::numeric, 2) as avg_duration_sec
FROM scan_runs
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY hour DESC;
```

### Critical Metrics Dashboard
Keep visible on monitoring screens:

| Metric | Target | Alert Threshold |
|--------|--------|-----------------|
| Scan success rate | > 98% | < 95% |
| Average execution time | < 5 min | > 10 min |
| Error rate | < 2% | > 5% |
| Worker health | All online | Any offline |
| Database connections | < 50 max | > 80% |
| Graph projection status | All complete | > 10% incomplete |
| API P95 latency | < 500ms | > 1000ms |
| Redis memory | < 80% | > 90% |
| Disk usage | < 70% | > 85% |

---

## Rollback Procedures (If Issues Detected)

### Decision Criteria for Immediate Rollback
Rollback IMMEDIATELY if any of these occur:
- [ ] Error rate > 10% (10x higher than baseline)
- [ ] Any service crashes with repeated failures (> 3 restarts in 30 min)
- [ ] Database connection pool exhaustion (all connections active)
- [ ] Data corruption detected (constraint violations, invalid state)
- [ ] Critical performance degradation (API > 5s latency)
- [ ] Data loss observed (records missing without deletion)
- [ ] Security vulnerability discovered during deployment

### Rollback Execution (Estimated time: 15-30 minutes)

#### Option 1: Database Rollback Only (Preferred - Faster)
Use when: Schema changes are causing issues but code is fine

```bash
echo "[$(date)] Starting database rollback..."

# Stop application to prevent writes
echo "[$(date)] Stopping services..."
systemctl stop sentinelai-api sentinelai-worker

# Wait for connections to close
sleep 10

# Terminate any remaining connections
psql $PROD_DB_URL << 'SQL'
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'sentinel' AND pid <> pg_backend_pid();
SQL

# Find most recent backup
BACKUP_FILE=$(ls -t /backups/prod_backup_*.sql | head -1)
echo "[$(date)] Using backup: $BACKUP_FILE"

# Create pre-rollback backup (for investigation)
pg_dump -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB > \
  /backups/pre_rollback_$(date +%Y%m%d_%H%M%S).sql

# Restore from backup
echo "[$(date)] Restoring from backup..."
psql $PROD_DB_URL < "$BACKUP_FILE" 2>&1 | tee /tmp/rollback_restore_$(date +%s).log

if [ $? -ne 0 ]; then
  echo "ERROR: Restore failed!"
  exit 1
fi

# Verify restore
RESTORED_COUNT=$(psql $PROD_DB_URL -t -c "SELECT COUNT(*) FROM scan_runs;")
echo "[$(date)] Restore completed. Scan runs: $RESTORED_COUNT"

# Restart application
echo "[$(date)] Restarting services..."
systemctl start sentinelai-api sentinelai-worker

sleep 3

# Verify
systemctl status sentinelai-api sentinelai-worker
echo "[$(date)] Database rollback complete"
```

#### Option 2: Full Code + Schema Rollback
Use when: Code changes or multiple migrations need to be reverted

```bash
echo "[$(date)] Starting full rollback..."

# Stop services
systemctl stop sentinelai-api sentinelai-worker
sleep 10

# Checkout previous release
cd /opt/sentinelai
echo "[$(date)] Current code: $(git log -1 --oneline)"

git fetch origin
git checkout v1.0.0  # Or specify previous stable version
echo "[$(date)] Rolled back to: $(git log -1 --oneline)"

# Reinstall dependencies for previous version
pip install -r requirements.txt --no-deps

# Revert database migrations
cd backend
export DATABASE_URL=postgresql://$PROD_DB_USER:***@$PROD_DB_HOST:5432/sentinel

echo "[$(date)] Current migration: $(alembic current)"
alembic downgrade 0001_foundation  # Or specify previous revision
echo "[$(date)] Reverted to: $(alembic current)"

# Restart services
systemctl restart sentinelai-api sentinelai-worker

sleep 3
systemctl status sentinelai-api sentinelai-worker

echo "[$(date)] Full rollback complete"
```

#### Option 3: Partial Rollback (Selective)
Use when: Only specific components need to be reverted

```bash
# Keep database as-is, only rollback code
cd /opt/sentinelai
git revert HEAD  # Creates new commit reverting changes
pip install -r requirements.txt --no-deps
systemctl restart sentinelai-api
```

### Post-Rollback Validation (10-15 minutes)
```bash
echo "[$(date)] Running post-rollback validation..."

# Basic connectivity checks
psql $PROD_DB_URL -c "SELECT COUNT(*) FROM scan_runs;" || exit 1
redis-cli -h $PROD_REDIS_HOST ping || exit 1
curl -s http://localhost:8000/health | jq .status | grep -q ok || exit 1

# Error rate check (should return to normal)
ERRORS=$(curl -s http://localhost:9090/api/v1/query?query='rate(http_errors[5m])' | jq '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "[$(date)] Error rate after rollback: $ERRORS"

# Performance check
LATENCY=$(curl -s http://localhost:9090/api/v1/query?query='histogram_quantile(0.95,rate(http_duration_seconds_bucket[5m]))' | jq '.data.result[0].value[1]' 2>/dev/null || echo "0")
echo "[$(date)] P95 latency after rollback: ${LATENCY}s"

echo "[$(date)] Post-rollback validation complete"
```

**Post-rollback checklist:**
- [ ] Services running normally
- [ ] Error rate returns to < 2%
- [ ] Database accessible and data intact
- [ ] Performance metrics normalized
- [ ] No data loss observed
- [ ] All tests still passing
- [ ] Team notified of rollback status
- [ ] Incident management system updated
- [ ] RCA (Root Cause Analysis) initiated

---

## Sign-Off and Documentation

### Deployment Completed Successfully
After 24-hour validation passes, obtain sign-offs from:

```
╔════════════════════════════════════════════════════════╗
║         DEPLOYMENT SIGN-OFF FORM                       ║
╚════════════════════════════════════════════════════════╝

Deployment Date: _______________
Deployment Time: _____ to _____ (duration: _____)

Code Version: _______________
Git SHA: _______________
Migration Applied: 0002_add_graph_jobs

✓ Pre-deployment checks: PASSED
✓ Migration executed successfully: PASSED
✓ All smoke tests passed: PASSED
✓ First hour monitoring: PASSED
✓ 4-hour validation: PASSED
✓ 24-hour monitoring: PASSED
✓ Error rate < 2%: PASSED
✓ No data loss: CONFIRMED
✓ No rollback required: CONFIRMED

Performance Metrics:
- Error rate: ____%
- P95 latency: _____ms
- Scan completion rate: ____%
- Graph projection jobs: _____ completed
- Database connection pool: _____% utilized

Sign-Offs Required:
- [ ] Technical Lead: _________________ Date: _____
- [ ] DevOps Engineer: ________________ Date: _____
- [ ] Database Administrator: _________ Date: _____
- [ ] Product Manager: _______________ Date: _____

Approval Status: ☐ APPROVED ☐ APPROVED WITH CONDITIONS

Comments/Notes:
_________________________________________________________________

Next Review Date: _______________
```

---

## Incident Response During Deployment

### Level 1: Minor Issue (Error rate 2-5%)
1. **Investigate** - Check logs for patterns
2. **Notify** - Update team in Slack #sentinelai-incidents
3. **Fix Forward** - If fix < 5 minutes, deploy hotfix
4. **Monitor** - Increase monitoring frequency to 1 minute

### Level 2: Moderate Issue (Error rate 5-10%)
1. **Stop** - Pause any further changes
2. **Investigate** - Gather error traces and logs
3. **Decide** - Quick fix (< 15 min) or rollback?
4. **Execute** - Deploy hotfix or execute rollback
5. **Document** - Log incident details

### Level 3: Critical Issue (Error rate > 10%)
1. **Rollback** - Immediately execute rollback procedure
2. **Notify** - Emergency notification to all stakeholders
3. **Investigate** - Full RCA after system stabilized
4. **Communicate** - Status updates every 15 minutes
5. **Escalate** - Notify management and CTO

### Incident Response Checklist
- [ ] Incident created in issue tracker
- [ ] War room established (Slack + call bridge)
- [ ] Timeline documented with timestamps
- [ ] Error logs captured and archived
- [ ] Decision logged (rollback/fix/monitor)
- [ ] All team members notified
- [ ] Stakeholders given status updates
- [ ] RCA initiated within 1 hour of resolution
- [ ] Post-incident review scheduled
- [ ] Preventive measures identified

---

## Knowledge Base

### Common Issues and Solutions

**Issue: Database migration timeout**
- Check: `SELECT * FROM alembic_version;`
- Cause: Large data set or locks
- Solution: Check for active locks, increase timeout, try in lower-traffic window

**Issue: Worker not processing tasks**
- Check: `celery -A app.worker inspect active_queues`
- Check: `redis-cli -h $REDIS_HOST LLEN celery`
- Solution: Restart worker, check Redis connectivity, verify queue names

**Issue: API responding slow (> 1s)**
- Check: `SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;`
- Check: Database indexes and explain plans
- Solution: Add missing indexes, optimize queries, scale horizontally

**Issue: Memory usage growing unbounded**
- Check: `ps aux | grep python`
- Check: Application logs for memory leaks
- Solution: Restart worker, investigate code for memory leak, limit processes

### Useful Commands

**Monitor in real-time:**
```bash
# Watch error rate
watch -n 1 'curl -s http://localhost:9090/api/v1/query?query="rate(http_errors[1m])" | jq .data.result'

# Watch database connections
watch -n 1 'psql $PROD_DB_URL -c "SELECT count(*) FROM pg_stat_activity;"'

# Watch worker health
watch -n 5 'celery -A app.worker inspect active'

# Tail logs
journalctl -u sentinelai-api -f --lines=50
journalctl -u sentinelai-worker -f --lines=50
```

**Diagnostic queries:**
```sql
-- Slow queries
SELECT query, calls, total_time FROM pg_stat_statements 
ORDER BY total_time DESC LIMIT 10;

-- Table sizes
SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) 
FROM pg_tables 
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Active locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Connection details
SELECT datname, usename, application_name, state, COUNT(*) 
FROM pg_stat_activity 
GROUP BY datname, usename, application_name, state;
```
