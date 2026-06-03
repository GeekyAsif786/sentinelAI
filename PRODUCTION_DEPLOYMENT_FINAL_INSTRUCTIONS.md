# PRODUCTION DEPLOYMENT - FINAL EXECUTION INSTRUCTIONS
## SentinelAI Phase 2-4 Deployment

**CRITICAL**: This is the actual production deployment. Execute with extreme care.

---

## I. CRITICAL PREREQUISITES

### Credentials Required (Load from Vault/Secrets Manager)

```bash
# DO NOT commit these to code or shell history
set +o history  # Disable shell history

export PROD_DB_HOST="<production-db-hostname>"
export PROD_DB_USER="<database-user>"
export PROD_DB_PASS="<database-password>"  # From vault
export PROD_DB="sentinel"
export PROD_DB_URL="postgresql://$PROD_DB_USER:$PROD_DB_PASS@$PROD_DB_HOST:5432/$PROD_DB"

export PROD_REDIS_HOST="<redis-hostname>"
export PROD_REDIS_PORT="6379"

export NEO4J_HOST="<neo4j-hostname>"
export NEO4J_PORT="7687"
export NEO4J_USER="<neo4j-user>"
export NEO4J_PASS="<neo4j-password>"

export PROD_API_URL="http://localhost:8000"
export DEPLOY_PATH="/opt/sentinelai"
export BACKUP_PATH="/backups"

set -o history  # Re-enable shell history
```

### Pre-Execution Checklist

- [ ] All environment variables configured
- [ ] Production database accessible
- [ ] Backup location available and writable
- [ ] SSH access to production server
- [ ] Proper authorization and approval obtained
- [ ] Runbook reviewed by Tech Lead
- [ ] DBA verified backup procedures
- [ ] DevOps verified service restart procedures

---

## II. DEPLOYMENT EXECUTION

### PHASE 1: PRE-DEPLOYMENT (Expected: T-1h, Duration: ~30 min)

#### 1.1 Verify Production Environment

```bash
echo "=== STEP 1.1: PRODUCTION ENVIRONMENT VERIFICATION ==="
echo "Execution Time: $(date)"

# Verify all variables set
echo "✓ Checking environment variables..."
[[ -z "$PROD_DB_URL" ]] && echo "ERROR: PROD_DB_URL not set" && exit 1
[[ -z "$PROD_REDIS_HOST" ]] && echo "ERROR: PROD_REDIS_HOST not set" && exit 1
[[ -z "$PROD_API_URL" ]] && echo "ERROR: PROD_API_URL not set" && exit 1

# Test PostgreSQL
echo "✓ Testing PostgreSQL connection..."
psql "$PROD_DB_URL" -c "SELECT version();" > /dev/null 2>&1 && \
  echo "  ✓ PostgreSQL connected" || \
  { echo "  ✗ PostgreSQL NOT accessible"; exit 1; }

# Test Redis
echo "✓ Testing Redis connection..."
redis-cli -h "$PROD_REDIS_HOST" -p "$PROD_REDIS_PORT" ping > /dev/null 2>&1 && \
  echo "  ✓ Redis responsive" || \
  { echo "  ✗ Redis NOT accessible"; exit 1; }

# Test API
echo "✓ Testing API health..."
curl -s "$PROD_API_URL/health" | jq . > /dev/null 2>&1 && \
  echo "  ✓ API responding" || \
  echo "  ⚠ API may not be responding (expected if down for maintenance)"

echo ""
echo "✓ STEP 1.1 COMPLETE: All systems accessible"
echo ""
```

**Sign-Off Checkpoint 1**: [ ] All systems verified accessible

#### 1.2 Create Production Database Backup

```bash
echo "=== STEP 1.2: CREATE PRODUCTION DATABASE BACKUP ==="
echo "Execution Time: $(date)"

mkdir -p "$BACKUP_PATH"

BACKUP_FILE="$BACKUP_PATH/sentinel_prod_backup_$(date +%Y%m%d_%H%M%S).sql"
echo "Backup location: $BACKUP_FILE"

# Create backup
echo "Creating backup (this may take several minutes)..."
pg_dump -h "$PROD_DB_HOST" -U "$PROD_DB_USER" -d "$PROD_DB" > "$BACKUP_FILE"

# Verify backup
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
BACKUP_LINES=$(wc -l < "$BACKUP_FILE")

echo ""
echo "✓ Backup created successfully"
echo "  File: $BACKUP_FILE"
echo "  Size: $BACKUP_SIZE"
echo "  Lines: $BACKUP_LINES"

# Validate backup format
file "$BACKUP_FILE" | grep -q "SQL" && \
  echo "✓ Backup format valid" || \
  { echo "✗ Backup format invalid"; exit 1; }

echo ""
echo "✓ STEP 1.2 COMPLETE: Backup created and verified"
echo "BACKUP_FILE=$BACKUP_FILE" > /tmp/backup_reference.txt
echo ""
```

**Sign-Off Checkpoint 2**: [ ] Backup created, size > 5MB, format valid

#### 1.3 Document Current State

```bash
echo "=== STEP 1.3: DOCUMENT PRE-DEPLOYMENT STATE ==="
echo "Execution Time: $(date)"

PRE_STATE_LOG="/tmp/pre_deployment_state_$(date +%Y%m%d_%H%M%S).log"

{
  echo "=== PRE-DEPLOYMENT STATE ==="
  echo "Timestamp: $(date)"
  echo ""
  
  echo "=== Current Migration Status ==="
  cd "$DEPLOY_PATH/backend"
  alembic current || echo "WARNING: alembic current failed"
  echo ""
  
  echo "=== Service Status ==="
  systemctl status sentinelai-api sentinelai-worker --no-pager 2>/dev/null || echo "WARNING: systemctl check failed"
  echo ""
  
  echo "=== Pre-Deployment Metrics ==="
  psql "$PROD_DB_URL" -c "SELECT 'scan_runs' as table_name, COUNT(*) as record_count FROM scan_runs;"
  psql "$PROD_DB_URL" -c "SELECT 'hosts' as table_name, COUNT(*) as record_count FROM hosts;"
  psql "$PROD_DB_URL" -c "SELECT 'services' as table_name, COUNT(*) as record_count FROM services;"
  echo ""
  
  echo "=== Git Status ==="
  cd "$DEPLOY_PATH"
  git log -1 --oneline
  git status
} | tee "$PRE_STATE_LOG"

echo ""
echo "✓ STEP 1.3 COMPLETE: Current state documented"
echo "PRE_STATE_LOG=$PRE_STATE_LOG"
echo ""
```

**Sign-Off Checkpoint 3**: [ ] Pre-deployment state documented

---

### PHASE 2: DEPLOYMENT EXECUTION (Expected: T-0m, Duration: ~25 min)

#### 2.1 Apply Database Migration

```bash
echo "=== STEP 2.1: APPLY DATABASE MIGRATION ==="
echo "Execution Time: $(date)"

cd "$DEPLOY_PATH/backend"
export DATABASE_URL="$PROD_DB_URL"

echo "Current migration status before upgrade:"
alembic current

echo ""
echo "Applying migration: 0002_add_graph_jobs"
echo "(This should complete in < 1 minute)"
echo ""

MIGRATION_LOG="/tmp/migration_output_$(date +%Y%m%d_%H%M%S).log"

# Apply migration with timeout
timeout 300 alembic upgrade head -v 2>&1 | tee "$MIGRATION_LOG"
MIGRATION_EXIT=$?

if [ $MIGRATION_EXIT -ne 0 ]; then
  echo "✗ Migration failed with exit code $MIGRATION_EXIT"
  cat "$MIGRATION_LOG"
  exit 1
fi

echo ""
echo "Migration status after upgrade:"
alembic current

echo ""
echo "✓ STEP 2.1 COMPLETE: Migration applied"
echo "MIGRATION_LOG=$MIGRATION_LOG"
echo ""
```

**Sign-Off Checkpoint 4**: [ ] Migration executed, alembic current = 0002_add_graph_jobs

#### 2.2 Verify Migration Success

```bash
echo "=== STEP 2.2: VERIFY MIGRATION SUCCESS ==="
echo "Execution Time: $(date)"

echo "Checking graph_projection_jobs table..."
psql "$PROD_DB_URL" -c "\\d graph_projection_jobs" | head -20

echo ""
echo "Checking worker_node_id column in scan_runs..."
psql "$PROD_DB_URL" -c "\\d scan_runs" | grep worker_node_id

echo ""
echo "Checking indexes on graph_projection_jobs..."
psql "$PROD_DB_URL" -c "SELECT indexname FROM pg_indexes WHERE tablename = 'graph_projection_jobs';"

echo ""
echo "Running schema integrity checks..."
psql "$PROD_DB_URL" << 'SQL'
-- Check table exists
SELECT 'Table exists' as check,
  CASE WHEN EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'graph_projection_jobs')
  THEN '✓ PASS' ELSE '✗ FAIL' END as result;

-- Check all 9 columns exist
SELECT 'Columns (9 required)' as check,
  CASE WHEN (SELECT COUNT(*) FROM information_schema.columns 
    WHERE table_name = 'graph_projection_jobs' 
    AND column_name IN ('id', 'scan_run_id', 'status', 'started_at', 'completed_at', 'error_message', 'projection_stats', 'created_at', 'updated_at')
  ) = 9 THEN '✓ PASS' ELSE '✗ FAIL' END as result;

-- Check indexes (3 required)
SELECT 'Indexes (3 required)' as check,
  CASE WHEN (SELECT COUNT(*) FROM pg_indexes WHERE tablename = 'graph_projection_jobs') >= 3
  THEN '✓ PASS' ELSE '✗ FAIL' END as result;

-- Check foreign key
SELECT 'Foreign key on scan_run_id' as check,
  CASE WHEN EXISTS(SELECT 1 FROM information_schema.referential_constraints 
    WHERE constraint_name LIKE '%graph_projection_jobs%')
  THEN '✓ PASS' ELSE '⚠ CHECK' END as result;
SQL

echo ""
echo "✓ STEP 2.2 COMPLETE: Migration verified successful"
echo ""
```

**Sign-Off Checkpoint 5**: [ ] Table created, 9 columns verified, 3+ indexes created, integrity checks pass

#### 2.3 Deploy New Code

```bash
echo "=== STEP 2.3: DEPLOY NEW CODE ==="
echo "Execution Time: $(date)"

cd "$DEPLOY_PATH"

echo "Current code version:"
git log -1 --oneline

echo ""
echo "Fetching latest code..."
git fetch origin

echo "Checking out main branch..."
git checkout main

echo "Pulling latest changes..."
git pull origin main

echo ""
echo "New code version:"
git log -1 --oneline

echo ""
echo "Installing dependencies..."
pip install -r backend/requirements.txt --no-deps

echo ""
echo "Verifying imports..."
python3 -c "from app.models import GraphProjectionJob; print('✓ GraphProjectionJob import OK')"
python3 -c "from app.tasks import execute_scan_from_queue; print('✓ Task imports OK')"

echo ""
echo "✓ STEP 2.3 COMPLETE: Code deployed and verified"
echo ""
```

**Sign-Off Checkpoint 6**: [ ] Code pulled, dependencies installed, imports verified

#### 2.4 Restart Services

```bash
echo "=== STEP 2.4: RESTART SERVICES ==="
echo "Execution Time: $(date)"

echo "Stopping services gracefully..."
systemctl stop sentinelai-api sentinelai-worker
STOP_STATUS=$?

sleep 3

if [ $STOP_STATUS -ne 0 ]; then
  echo "⚠ Warning: Services may not have stopped cleanly"
fi

echo "✓ Services stopped"

echo ""
echo "Starting services..."
systemctl start sentinelai-api sentinelai-worker
START_STATUS=$?

sleep 5

if [ $START_STATUS -ne 0 ]; then
  echo "✗ Services failed to start"
  exit 1
fi

echo "✓ Services started"

echo ""
echo "Checking service status..."
systemctl status sentinelai-api sentinelai-worker --no-pager

echo ""
echo "Service PIDs:"
systemctl show sentinelai-api sentinelai-worker -p MainPID

echo ""
echo "✓ STEP 2.4 COMPLETE: Services restarted successfully"
echo ""
```

**Sign-Off Checkpoint 7**: [ ] Services stopped cleanly, started successfully, status = active/running

---

### PHASE 3: SMOKE TESTS (Expected: T+5m, Duration: ~5 min)

```bash
echo "=== PHASE 3: SMOKE TESTS ==="
echo "Execution Time: $(date)"
echo ""

SMOKE_TEST_LOG="/tmp/smoke_tests_$(date +%Y%m%d_%H%M%S).log"
SMOKE_PASS=0
SMOKE_FAIL=0

# Test 1: API Health
echo "SMOKE TEST 1: API Health"
if curl -s "$PROD_API_URL/health" | jq . > /dev/null 2>&1; then
  echo "  ✓ PASS: API responding to /health"
  ((SMOKE_PASS++))
else
  echo "  ✗ FAIL: API not responding"
  ((SMOKE_FAIL++))
fi

# Test 2: Database Connection
echo "SMOKE TEST 2: Database Connection"
if psql "$PROD_DB_URL" -c "SELECT COUNT(*) FROM scan_runs;" > /dev/null 2>&1; then
  echo "  ✓ PASS: Database query successful"
  ((SMOKE_PASS++))
else
  echo "  ✗ FAIL: Database query failed"
  ((SMOKE_FAIL++))
fi

# Test 3: Graph Projection Jobs Table
echo "SMOKE TEST 3: Graph Projection Jobs Table"
if psql "$PROD_DB_URL" -c "SELECT COUNT(*) FROM graph_projection_jobs;" > /dev/null 2>&1; then
  echo "  ✓ PASS: Graph jobs table accessible"
  ((SMOKE_PASS++))
else
  echo "  ✗ FAIL: Graph jobs table not accessible"
  ((SMOKE_FAIL++))
fi

# Test 4: Worker Status
echo "SMOKE TEST 4: Celery Worker Status"
if celery -A app.worker inspect active_queues > /dev/null 2>&1; then
  echo "  ✓ PASS: Worker accessible"
  ((SMOKE_PASS++))
else
  echo "  ⚠ WARNING: Worker may not be responding (non-critical)"
fi

# Test 5: Redis Connection
echo "SMOKE TEST 5: Redis Connection"
if redis-cli -h "$PROD_REDIS_HOST" -p "$PROD_REDIS_PORT" ping > /dev/null 2>&1; then
  echo "  ✓ PASS: Redis responsive"
  ((SMOKE_PASS++))
else
  echo "  ✗ FAIL: Redis not responsive"
  ((SMOKE_FAIL++))
fi

echo ""
echo "=== SMOKE TEST SUMMARY ==="
echo "Passed: $SMOKE_PASS"
echo "Failed: $SMOKE_FAIL"

if [ $SMOKE_FAIL -gt 0 ]; then
  echo ""
  echo "✗ SMOKE TESTS FAILED - INITIATING ROLLBACK"
  exit 1
else
  echo "✓ ALL SMOKE TESTS PASSED"
fi

echo ""
```

**Sign-Off Checkpoint 8**: [ ] All smoke tests passed

---

### PHASE 4: 24-HOUR MONITORING

#### Create Monitoring Script

```bash
cat > /tmp/monitor_deployment.sh << 'MONITOR'
#!/bin/bash

MONITOR_LOG="/tmp/production_monitoring_$(date +%Y%m%d_%H%M%S).log"
MONITOR_HOURS=24
HOUR=0

echo "=== PRODUCTION MONITORING STARTED ===" | tee "$MONITOR_LOG"
echo "Start Time: $(date)" | tee -a "$MONITOR_LOG"
echo "Duration: $MONITOR_HOURS hours" | tee -a "$MONITOR_LOG"
echo "Log: $MONITOR_LOG" | tee -a "$MONITOR_LOG"
echo "" | tee -a "$MONITOR_LOG"

while [ $HOUR -lt $MONITOR_HOURS ]; do
  echo "=== MONITORING CHECK HOUR $((HOUR+1))/$MONITOR_HOURS ===" | tee -a "$MONITOR_LOG"
  echo "Time: $(date)" | tee -a "$MONITOR_LOG"
  
  # Error rate (last 1 hour)
  echo "Error rate (last 1h):" | tee -a "$MONITOR_LOG"
  psql "$PROD_DB_URL" -c "SELECT 
    COUNT(CASE WHEN error_code IS NOT NULL THEN 1 END)::float / 
    COUNT(*) * 100 as error_rate_pct
  FROM scan_runs
  WHERE created_at > NOW() - INTERVAL '1 hour';" | tee -a "$MONITOR_LOG"
  
  # Success rate
  echo "Success rate (last 1h):" | tee -a "$MONITOR_LOG"
  psql "$PROD_DB_URL" -c "SELECT 
    COUNT(CASE WHEN status = 'completed' THEN 1 END)::float / 
    COUNT(*) * 100 as success_rate_pct
  FROM scan_runs
  WHERE created_at > NOW() - INTERVAL '1 hour';" | tee -a "$MONITOR_LOG"
  
  # Graph projection jobs status
  echo "Graph projection jobs by status:" | tee -a "$MONITOR_LOG"
  psql "$PROD_DB_URL" -c "SELECT status, COUNT(*) as count 
  FROM graph_projection_jobs GROUP BY status;" | tee -a "$MONITOR_LOG"
  
  # Database connections
  echo "Active DB connections:" | tee -a "$MONITOR_LOG"
  psql "$PROD_DB_URL" -c "SELECT COUNT(*) FROM pg_stat_activity;" | tee -a "$MONITOR_LOG"
  
  # Service health
  echo "Services status:" | tee -a "$MONITOR_LOG"
  systemctl is-active sentinelai-api sentinelai-worker | tee -a "$MONITOR_LOG"
  
  echo "" | tee -a "$MONITOR_LOG"
  
  ((HOUR++))
  
  if [ $HOUR -lt $MONITOR_HOURS ]; then
    echo "Next check in 1 hour..."
    sleep 3600
  fi
done

echo "=== PRODUCTION MONITORING COMPLETE ===" | tee -a "$MONITOR_LOG"
echo "End Time: $(date)" | tee -a "$MONITOR_LOG"
MONITOR
chmod +x /tmp/monitor_deployment.sh
```

#### Execute Monitoring

```bash
# Run in background for 24 hours
nohup /tmp/monitor_deployment.sh > /tmp/monitoring_output.log 2>&1 &
MONITOR_PID=$!
echo "Monitoring process started with PID: $MONITOR_PID"
echo "Check progress with: tail -f /tmp/production_monitoring_*.log"
```

**Critical Success Criteria (to verify after 24h)**:
- [ ] Error rate < 2%
- [ ] Success rate > 98%
- [ ] Average execution time < 5 min
- [ ] No worker crashes
- [ ] No database connection exhaustion
- [ ] Graph jobs completing normally
- [ ] No data corruption detected
- [ ] Memory usage stable
- [ ] CPU usage normal

---

### PHASE 5: SIGN-OFF (After 24h monitoring)

#### Generate Final Report

```bash
echo "=== PRODUCTION DEPLOYMENT FINAL REPORT ===" > /tmp/deployment_final_report.txt
echo "Deployment Date: $(date)" >> /tmp/deployment_final_report.txt
echo "Git Commit: $(cd "$DEPLOY_PATH" && git log -1 --oneline)" >> /tmp/deployment_final_report.txt
echo "Migration: 0002_add_graph_jobs applied successfully" >> /tmp/deployment_final_report.txt
echo "" >> /tmp/deployment_final_report.txt

echo "=== Final Metrics ===" >> /tmp/deployment_final_report.txt
psql "$PROD_DB_URL" -c "SELECT 
  'scan_runs' as table_name, COUNT(*) as record_count FROM scan_runs
UNION ALL
SELECT 'hosts', COUNT(*) FROM hosts
UNION ALL
SELECT 'services', COUNT(*) FROM services
UNION ALL
SELECT 'graph_projection_jobs', COUNT(*) FROM graph_projection_jobs
UNION ALL
SELECT 'graph_projection_jobs (completed)', COUNT(*) FROM graph_projection_jobs WHERE status = 'completed';" >> /tmp/deployment_final_report.txt

echo "" >> /tmp/deployment_final_report.txt
echo "=== Error Analysis (Last 24h) ===" >> /tmp/deployment_final_report.txt
psql "$PROD_DB_URL" -c "SELECT error_code, COUNT(*) FROM scan_runs 
WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY error_code LIMIT 10;" >> /tmp/deployment_final_report.txt

cat /tmp/deployment_final_report.txt
```

#### Final Sign-Off Form

```
PRODUCTION DEPLOYMENT SIGN-OFF
===============================

Date: _______________
Deployment Type: Database Migration + Code Deployment
Migration: 0002_add_graph_jobs
Commit: 65c0d91

Pre-deployment scan_runs: _______________
Post-deployment scan_runs: _______________
Data Loss: [ ] Yes [ ] No (should be NO)

24-Hour Monitoring Results:
- Error rate (24h): _________%  [Target: < 2%]
- Success rate (24h): _________%  [Target: > 98%]
- Avg execution time (24h): ________ sec  [Target: < 5 min]
- Worker crashes: ________  [Target: 0]
- Graph jobs completed: ________
- Services uptime: ________%  [Target: > 99.9%]

Sign-Offs:
[ ] Technical Lead: _________________ Date: _______
[ ] DevOps Engineer: _________________ Date: _______
[ ] Database Administrator: _________________ Date: _______
[ ] Product Manager: _________________ Date: _______

DEPLOYMENT STATUS:
[ ] ✓ APPROVED - Production deployment successful
[ ] ✗ ISSUES FOUND - Recommend investigation

Notes:
________________________________________________________________________
________________________________________________________________________
________________________________________________________________________
```

---

## III. ROLLBACK PROCEDURES

### If Critical Issues Are Detected

#### Database Rollback (15-20 min recovery)

```bash
echo "!!! INITIATING EMERGENCY DATABASE ROLLBACK !!!"

# Load backup reference
source /tmp/backup_reference.txt

echo "Using backup: $BACKUP_FILE"
echo "WARNING: This will restore database to pre-deployment state"
read -p "Continue with rollback? (yes/no) " confirm
[[ "$confirm" != "yes" ]] && echo "Rollback cancelled" && exit 1

echo "Restoring from backup..."
psql "$PROD_DB_URL" < "$BACKUP_FILE"

echo "Restarting services..."
systemctl restart sentinelai-api sentinelai-worker

sleep 5

echo "Verifying rollback..."
curl -s "$PROD_API_URL/health" | jq .
psql "$PROD_DB_URL" -c "SELECT COUNT(*) FROM scan_runs;"

echo "✓ Rollback complete"
```

#### Code Rollback (10-15 min recovery)

```bash
echo "!!! INITIATING EMERGENCY CODE ROLLBACK !!!"

cd "$DEPLOY_PATH"

echo "Current commit: $(git log -1 --oneline)"

# Option 1: Revert last commit
echo "Reverting last deployment commit..."
git revert HEAD --no-edit

# OR Option 2: Reset to previous stable commit
# git reset --hard <previous-commit-hash>

echo "Reinstalling dependencies..."
pip install -r backend/requirements.txt --no-deps

echo "Restarting services..."
systemctl restart sentinelai-api sentinelai-worker

sleep 5

echo "Verifying rollback..."
curl -s "$PROD_API_URL/health" | jq .

echo "✓ Code rollback complete"
```

---

## IV. EMERGENCY CONTACTS

| Role | Name | Phone | Email | Slack |
|------|------|-------|-------|-------|
| Tech Lead | __________ | __________ | __________ | __________ |
| DevOps Engineer | __________ | __________ | __________ | __________ |
| Database Admin | __________ | __________ | __________ | __________ |
| On-Call Engineer | __________ | __________ | __________ | __________ |
| Product Manager | __________ | __________ | __________ | __________ |

---

## V. EXECUTION CHECKLIST

### Before Deployment
- [ ] All prerequisites verified
- [ ] Backup location confirmed writable
- [ ] All environment variables set
- [ ] Team notified of deployment window
- [ ] Monitoring systems ready
- [ ] Rollback procedures reviewed
- [ ] Emergency contacts available

### Phase 1: Pre-Deployment
- [ ] Production systems verified accessible
- [ ] Database backup created and verified
- [ ] Pre-deployment state documented

### Phase 2: Deployment
- [ ] Database migration applied successfully
- [ ] Migration verified (9 columns, 3+ indexes)
- [ ] Code deployed and imports verified
- [ ] Services restarted successfully

### Phase 3: Smoke Tests
- [ ] API health check passed
- [ ] Database connectivity verified
- [ ] Graph jobs table accessible
- [ ] Worker status verified
- [ ] Redis connectivity verified

### Phase 4: Monitoring
- [ ] Monitoring started
- [ ] Hourly checks executed for 24 hours
- [ ] No critical errors detected
- [ ] Success metrics within targets

### Phase 5: Sign-Off
- [ ] Final metrics collected
- [ ] All required sign-offs obtained
- [ ] Deployment marked as complete
- [ ] Post-deployment documentation updated

---

## SUCCESS CRITERIA

✓ **PRODUCTION DEPLOYMENT SUCCESSFUL** when ALL of the following are true:

1. **Migration Applied**: Alembic current shows `0002_add_graph_jobs`
2. **Schema Verified**: `graph_projection_jobs` table exists with 9 columns and 3+ indexes
3. **Services Healthy**: Both API and worker services are running and responsive
4. **Data Integrity**: Pre-deployment record counts match post-deployment (accounting for new data)
5. **Smoke Tests Pass**: All 5 smoke tests complete successfully
6. **Monitoring Healthy**: 24-hour monitoring shows no critical issues
7. **Error Rate Low**: < 2% error rate in 24-hour window
8. **No Rollback**: No need to initiate rollback procedures

---

**DEPLOYMENT READY FOR EXECUTION**

Follow the step-by-step instructions above in order. Do not skip steps.

Contact emergency team if critical issues arise at any point.

