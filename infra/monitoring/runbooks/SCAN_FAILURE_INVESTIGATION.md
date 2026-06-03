# Scan Failure Investigation Runbook

**Alert Name**: ScanExecutionCriticalFailure / HighScanErrorRate  
**Severity**: CRITICAL / WARNING  
**Estimated Time to Resolve**: 15-30 minutes

## Symptoms

- Alert triggered: error rate > 10% or > 50%
- Multiple failed scans in rapid succession
- `ScanExecutionCriticalFailure` or `HighScanErrorRate` alert firing
- User-facing scan failures increasing

## Investigation (First 10 minutes)

### 1. Get Error Breakdown
```bash
# Identify top error codes (Last hour)
psql -c "SELECT error_code, COUNT(*) as count, MAX(created_at) as last_seen FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '1 hour' GROUP BY error_code ORDER BY count DESC LIMIT 10;"

# Get recent error details
psql -c "SELECT id, error_code, error_message, created_at FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '1 hour' ORDER BY created_at DESC LIMIT 20;"
```

### 2. Check Application Logs
```bash
# Flask application logs
tail -100 /tmp/flask_server.log | grep -i error

# Look for patterns
tail -100 /tmp/flask_server.log | grep -E "ERROR|Exception|Traceback"

# Celery worker logs
tail -100 /tmp/celery_worker.log | grep -E "ERROR|Exception"
```

### 3. Check Infrastructure Health
```bash
# Database connectivity
psql -c "SELECT COUNT(*) FROM scan_runs;"

# Redis connectivity
redis-cli PING

# Check Neo4j if graph projection errors
curl -s http://neo4j:7474/db/admin/server/config | head -20

# System resources
top -b -n 1 | head -20
```

### 4. Determine Error Category

Based on error code/message, categorize:

- **Database Errors**: `psql: connection refused`, `connection timeout`
- **Graph Errors**: `Neo4j connection failed`, `Cypher query timeout`
- **Task Errors**: `Task timeout`, `Worker disconnected`
- **Scan Errors**: `Target unreachable`, `Invalid credentials`
- **Data Errors**: `Duplicate key`, `Constraint violation`

## Recovery by Error Type

### Database Connectivity Errors

**Symptoms**:
- Error: `psql: could not connect to server`
- Error: `connection timeout`
- Error: `too many connections`

**Investigation**:
```bash
# Check database status
systemctl status postgresql

# Check connections
psql -c "SELECT COUNT(*) FROM pg_stat_activity;"

# Check locks
psql -c "SELECT * FROM pg_locks WHERE NOT granted;"
```

**Recovery**:
```bash
# 1. Restart PostgreSQL (if safe)
systemctl restart postgresql

# 2. If connection pool exhausted, terminate idle connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '5 minutes';"

# 3. Clear application connection pool
# (Restart Flask workers)
```

### Neo4j/Graph Processing Errors

**Symptoms**:
- Error: `Neo4j connection refused`
- Error: `Graph projection timeout`
- Error: `Cypher query failed`

**Investigation**:
```bash
# Check Neo4j service
systemctl status neo4j

# Test connectivity
curl -u neo4j:password http://localhost:7787/db/

# Check Neo4j logs
tail -50 /var/log/neo4j/neo4j.log

# Check database size
psql -c "SELECT COUNT(*) FROM graph_projection_jobs WHERE status = 'failed' AND created_at > NOW() - INTERVAL '1 hour';"
```

**Recovery**:
```bash
# 1. Restart Neo4j
systemctl restart neo4j

# 2. Requeue failed projection jobs
psql -c "UPDATE graph_projection_jobs SET status = 'pending' WHERE status = 'failed' AND created_at > NOW() - INTERVAL '1 hour';"

# 3. Monitor retries
watch psql -c "SELECT status, COUNT(*) FROM graph_projection_jobs WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY status;"
```

### Celery Task Timeout Errors

**Symptoms**:
- Error: `Task timeout`
- Error: `Worker lost`
- Error: `Celery timeout`

**Investigation**:
```bash
# Check worker status
celery -A app.worker inspect active

# Check active task durations
celery -A app.worker inspect active | grep -o "clock.*"

# Check worker logs for timeouts
tail -50 /tmp/celery_worker.log | grep -i timeout
```

**Recovery**:
```bash
# 1. Increase task timeout if appropriate
# In app config: CELERY_TASK_TIME_LIMIT = 3600

# 2. Check if tasks are genuinely slow
psql -c "SELECT AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) FROM scan_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours';"

# 3. Restart workers if hung
pkill -f 'celery.*worker'
sleep 2
celery -A app.worker -l info
```

### Scan Target Errors (Invalid Targets, Credentials)

**Symptoms**:
- Error: `Target unreachable`
- Error: `Authentication failed`
- Error: `Invalid CIDR`

**Investigation**:
```bash
# Check failed scan targets
psql -c "SELECT id, scan_target, error_message, created_at FROM scan_runs WHERE error_code = 'TARGET_ERROR' ORDER BY created_at DESC LIMIT 10;"

# Verify target configuration
psql -c "SELECT id, scan_target, scan_type FROM scan_targets LIMIT 20;"
```

**Recovery**:
1. Verify target configuration is correct
2. Test manual connectivity to target
3. Check credentials if auth-based
4. Requeue specific scans after fixing configuration

### Data Constraint/Integrity Errors

**Symptoms**:
- Error: `Duplicate key value violates unique constraint`
- Error: `Foreign key constraint violation`
- Error: `NOT NULL constraint violation`

**Investigation**:
```bash
# Check for constraint violations
psql -c "SELECT * FROM pg_stat_user_tables WHERE n_tup_del > 1000 OR n_tup_upd > 1000;"

# Check scan data integrity
psql -c "SELECT COUNT(DISTINCT id) as unique_scans, COUNT(*) as total_rows FROM scan_runs;"
```

**Recovery**:
```bash
# 1. Investigate constraint conflict details
psql -c "SELECT CONSTRAINT_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE TABLE_NAME = 'scan_runs';"

# 2. Check for duplicate scan IDs
psql -c "SELECT scan_id, COUNT(*) FROM scan_runs GROUP BY scan_id HAVING COUNT(*) > 1;"

# 3. Clean up if safe, or restore from backup
```

## Response by Severity

### CRITICAL (Failure Rate > 50%)

1. **Immediate**: Check infrastructure (DB, Redis, Neo4j)
2. **Within 5 min**: Identify error pattern
3. **Within 10 min**: Either fix or roll back changes
4. **Decision point**: Continue or pause scanning

### WARNING (Failure Rate > 10%)

1. **Within 15 min**: Complete investigation
2. **Within 30 min**: Implement fix or workaround
3. **Monitor**: Track resolution

## Monitoring During Recovery

```bash
#!/bin/bash

# Monitor error rate in real-time
watch 'psql -c "SELECT ROUND(COUNT(CASE WHEN status = '\''failed'\'') * 100.0 / COUNT(*), 2) as error_rate_pct FROM scan_runs WHERE created_at > NOW() - INTERVAL '\''5 minutes'\'';"'
```

## Post-Recovery Checklist

- [ ] Error rate returned to < 5%
- [ ] Recent failed scans investigated
- [ ] Root cause identified and documented
- [ ] Fix deployed or workaround in place
- [ ] Alert cleared automatically
- [ ] No error escalation in logs

## Escalation

**If error rate > 10% after 15 minutes of investigation**:
1. Escalate to engineering team lead
2. Consider pause/rollback of recent changes
3. Consider production impact if applicable

## Prevention

1. **Pre-deployment testing**: Run extended test scan suite
2. **Gradual rollout**: Deploy to subset of workers first
3. **Error monitoring**: Set up continuous error rate tracking
4. **Alert thresholds**: Tune thresholds based on baseline
