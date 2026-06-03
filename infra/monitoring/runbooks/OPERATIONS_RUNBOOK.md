# Monitoring Operations Runbook

## Quick Reference Commands

### Check Scan Status
```bash
psql -c "SELECT id, status, error_code, created_at FROM scan_runs ORDER BY created_at DESC LIMIT 10;"
```

### Monitor Celery Tasks
```bash
# Active tasks
celery -A app.worker inspect active

# Registered tasks
celery -A app.worker inspect registered

# Worker stats
celery -A app.worker inspect stats
```

### Check Error Rates
```bash
psql -c "SELECT error_code, COUNT(*) as count FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code ORDER BY count DESC;"
```

### Check Graph Projections
```bash
psql -c "SELECT status, COUNT(*) as count FROM graph_projection_jobs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"
```

### Monitor API Response Times
```bash
# View Prometheus metrics
curl http://localhost:5000/metrics | grep http_request_duration_seconds
```

### Check Database Connections
```bash
psql -c "SELECT datname, usename, state, COUNT(*) FROM pg_stat_activity WHERE datname IS NOT NULL GROUP BY datname, usename, state;"
```

### Monitor Redis
```bash
redis-cli INFO stats
redis-cli INFO memory
redis-cli DBSIZE
```

### Check Neo4j Connectivity
```bash
curl -u neo4j:password http://localhost:7687/db/
```

---

## Daily Operations

### Morning Health Check (Start of Shift)
```bash
#!/bin/bash

echo "=== SentinelAI Daily Health Check ==="
echo ""

echo "1. System Status"
systemctl status sentinelai-api sentinelai-celery sentinelai-redis sentinelai-postgres

echo ""
echo "2. Database Status"
psql -c "\conninfo"
psql -c "SELECT COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours';"

echo ""
echo "3. Celery Workers"
celery -A app.worker inspect active_queues

echo ""
echo "4. Recent Errors"
psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '1 hour' GROUP BY error_code;"

echo ""
echo "5. Alert Summary"
curl -s http://localhost:9090/api/v1/alerts | jq '.data | group_by(.labels.severity) | map({severity: .[0].labels.severity, count: length})'
```

### Evening Health Check (End of Shift)
```bash
#!/bin/bash

echo "=== SentinelAI Evening Health Check ==="
echo ""

echo "1. 24-Hour Scan Summary"
psql -c "SELECT status, COUNT(*) as count FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"

echo ""
echo "2. Success Rate"
psql -c "SELECT ROUND(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours';"

echo ""
echo "3. Critical Errors"
psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code ORDER BY count DESC LIMIT 5;"

echo ""
echo "4. Performance Metrics"
psql -c "SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' AND status = 'success';"

echo ""
echo "5. Resource Summary"
free -h
df -h
```

---

## Incident Response Procedures

### High Error Rate Response (>10%)

**Symptoms**:
- Alert: `HighScanErrorRate` fired
- Scan success rate dropped below 90%
- Multiple failed scans appearing in logs

**Diagnosis**:
```bash
# 1. Check error breakdown
psql -c "SELECT error_code, COUNT(*), MAX(created_at) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '1 hour' GROUP BY error_code ORDER BY count DESC;"

# 2. Check scan logs
tail -50 /tmp/flask_server.log | grep -i error

# 3. Check Celery worker logs
tail -50 /tmp/celery_worker.log | grep -i error

# 4. Check database connectivity
psql -c "SELECT version();"
```

**Resolution Steps**:
1. Identify the dominant error code(s)
2. Check affected workers for issues
3. Restart affected components if necessary
4. Verify system health metrics
5. Run diagnostic scans to confirm recovery

**Escalation**: If error rate stays > 5% after 15 minutes, page engineering team

---

### Worker Disconnection Response

**Symptoms**:
- Alert: `CeleryWorkerDisconnected` fired
- No active Celery workers
- Tasks stuck in queue

**Diagnosis**:
```bash
# 1. Check worker status
celery -A app.worker inspect active

# 2. Check worker processes
ps aux | grep celery

# 3. Check Redis connectivity (worker communication)
redis-cli PING

# 4. Check worker logs
tail -100 /tmp/celery_worker.log
```

**Resolution Steps**:
1. Stop the celery worker: `pkill -f 'celery.*worker'`
2. Check for hanging processes: `ps aux | grep celery`
3. Verify Redis is running: `redis-cli PING`
4. Restart Celery: `celery -A app.worker -l info`
5. Verify workers reconnect: `celery -A app.worker inspect active`

**Escalation**: If workers don't reconnect after restart, check infrastructure logs

---

### Database Connection Pool Exhaustion

**Symptoms**:
- Alert: `DatabaseConnectionPoolExhausted` fired
- New connections fail
- API requests timeout

**Diagnosis**:
```bash
# 1. Check connection status
psql -c "SELECT datname, usename, state, COUNT(*) FROM pg_stat_activity WHERE datname IS NOT NULL GROUP BY datname, usename, state;"

# 2. Check for idle connections
psql -c "SELECT pid, usename, state, query_start FROM pg_stat_activity WHERE state = 'idle' ORDER BY query_start LIMIT 20;"

# 3. Check for long-running queries
psql -c "SELECT pid, usename, query_start, query FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start LIMIT 10;"
```

**Resolution Steps**:
1. Identify idle connections holding resources
2. Carefully terminate idle connections: `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';`
3. Check for and optimize long-running queries
4. Increase pool size if load is legitimate
5. Restart connection pooler if necessary

**Prevention**: Monitor pool usage continuously, set idle timeouts

---

### Redis Memory Exhaustion

**Symptoms**:
- Alert: `RedisMemoryUsageHigh` fired
- Redis operations slow or failing
- Eviction policies triggering

**Diagnosis**:
```bash
# 1. Check memory usage
redis-cli INFO memory

# 2. Check memory policy
redis-cli CONFIG GET maxmemory-policy

# 3. Check top keys by size
redis-cli --bigkeys

# 4. Check command latency
redis-cli LATENCY LATEST
```

**Resolution Steps**:
1. Identify and remove unnecessary cached data
2. Clear old task results: `redis-cli EVAL "return redis.call('eval', 'return redis.call(\"flushdb\")', 0)" 0`
3. Adjust Redis maxmemory if possible
4. Monitor for memory leaks in application
5. Consider Redis cluster/sentinel for scaling

---

### API Response Time Degradation

**Symptoms**:
- Alert: `APIResponseTimeExceeded` fired
- Response times > 5 seconds P95
- User-visible performance issues

**Diagnosis**:
```bash
# 1. Check API metrics
curl http://localhost:5000/metrics | grep http_request_duration_seconds

# 2. Check slow queries
psql -c "SELECT query, calls, mean_time FROM pg_stat_statements WHERE mean_time > 100 ORDER BY mean_time DESC LIMIT 10;"

# 3. Check database performance
psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# 4. Check system resources
top -b -n 1 | head -20
```

**Resolution Steps**:
1. Identify slow queries using pg_stat_statements
2. Add indexes if needed
3. Check worker resource usage
4. Restart API server if memory leak suspected
5. Scale workers if CPU-bound

---

### Neo4j Graph Database Issues

**Symptoms**:
- Alert: `Neo4jGraphDatabaseDown` fired
- Graph projection jobs failing
- Attack path queries failing

**Diagnosis**:
```bash
# 1. Test Neo4j connectivity
curl -u neo4j:password http://localhost:7687/db/

# 2. Check Neo4j logs
# (location varies by deployment)

# 3. Check active connections
psql -c "SELECT COUNT(*) FROM pg_stat_activity WHERE application_name LIKE '%neo4j%';"
```

**Resolution Steps**:
1. Check Neo4j service status
2. Verify network connectivity to Neo4j
3. Check Neo4j disk space and heap memory
4. Restart Neo4j if necessary
5. Requeue failed graph projection jobs

---

## Monitoring Data Collection

### Generate Daily Report
```bash
#!/bin/bash

DATE=$(date +%Y-%m-%d)
OUTPUT_FILE="monitoring_report_${DATE}.txt"

{
    echo "=== SentinelAI Monitoring Report for $DATE ==="
    echo ""
    echo "Generated: $(date)"
    echo ""
    
    echo "--- Scan Execution Summary ---"
    psql -c "SELECT status, COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"
    
    echo ""
    echo "--- Error Analysis ---"
    psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code ORDER BY count DESC LIMIT 5;"
    
    echo ""
    echo "--- Performance Metrics ---"
    psql -c "SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_sec FROM scan_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours';"
    
} > "$OUTPUT_FILE"

echo "Report saved to: $OUTPUT_FILE"
```

---

## Useful Links

- **Prometheus Dashboard**: http://localhost:9090
- **Grafana Dashboards**: http://localhost:3000
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **Celery Documentation**: https://docs.celeryproject.io/
- **Neo4j Documentation**: https://neo4j.com/docs/
