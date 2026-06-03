# Database Connection Pool Recovery Runbook

**Alert Name**: DatabaseConnectionPoolExhausted  
**Severity**: CRITICAL  
**Estimated Time to Resolve**: 10-20 minutes

## Symptoms

- Alert `DatabaseConnectionPoolExhausted` triggered (>95% usage)
- Alert `DatabaseConnectionPoolWarning` triggered (>80% usage)
- API requests timeout with connection errors
- New database operations fail to get connections
- Error: `too many connections`

## Quick Diagnosis (First 5 minutes)

### 1. Check Connection Pool Status
```bash
# See all active connections
psql -c "SELECT datname, usename, application_name, state, COUNT(*) as count FROM pg_stat_activity WHERE datname IS NOT NULL GROUP BY datname, usename, application_name, state ORDER BY count DESC;"

# Get total connection count
psql -c "SELECT COUNT(*) as active_connections FROM pg_stat_activity;"

# Get max connections setting
psql -c "SHOW max_connections;"

# Calculate utilization percentage
psql -c "SELECT COUNT(*) * 100.0 / (SELECT setting::int FROM pg_settings WHERE name='max_connections') as utilization_pct FROM pg_stat_activity;"
```

### 2. Identify Idle Connections (Resource Waste)
```bash
# Long-idle connections
psql -c "SELECT pid, usename, application_name, state, NOW() - state_change as idle_duration FROM pg_stat_activity WHERE state = 'idle' ORDER BY state_change LIMIT 20;"

# Very old idle connections (> 1 hour)
psql -c "SELECT COUNT(*) as long_idle_count FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '1 hour';"
```

### 3. Check for Long-Running Queries (Holding Locks)
```bash
# Active queries and their duration
psql -c "SELECT pid, usename, query_start, query, NOW() - query_start as duration FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start LIMIT 10;"

# Queries running > 5 minutes
psql -c "SELECT COUNT(*) as long_running FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '5 minutes';"
```

## Recovery Procedures

### Step 1: Safely Terminate Idle Connections

```bash
# Find connection idle for > 10 minutes (safe to kill)
psql -c "SELECT pid, usename, application_name, NOW() - state_change as idle_duration FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"

# Terminate these idle connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '10 minutes';"

# Verify termination
sleep 2
psql -c "SELECT COUNT(*) as remaining_idle FROM pg_stat_activity WHERE state = 'idle';"
```

### Step 2: Address Long-Running Queries

```bash
# Check what's holding connections
psql -c "SELECT pid, usename, query_start, query FROM pg_stat_activity WHERE state = 'active' ORDER BY query_start LIMIT 5;"

# For queries > 30 minutes, consider terminating
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND query_start < NOW() - INTERVAL '30 minutes';"
```

### Step 3: Restart Connection-Consuming Services

If pool still exhausted, restart services gracefully:

```bash
# Restart Flask workers (closes stale connections)
systemctl restart sentinelai-api

# Wait for restart
sleep 5

# Check pool status
psql -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active';"
```

### Step 4: Monitor Pool Recovery

```bash
#!/bin/bash

# Monitor connection pool recovery
for i in {1..30}; do
    COUNT=$(psql -t -c "SELECT COUNT(*) FROM pg_stat_activity;")
    UTILIZATION=$(psql -t -c "SELECT ROUND(COUNT(*) * 100.0 / (SELECT setting::int FROM pg_settings WHERE name='max_connections'), 2) FROM pg_stat_activity;")
    echo "[$i/30] Connections: $COUNT, Utilization: $UTILIZATION%"
    sleep 2
done
```

## Long-Term Fixes

### 1. Increase Connection Pool Size
```bash
# Check current max_connections
psql -c "SHOW max_connections;"

# Modify PostgreSQL config (requires restart)
# Edit postgresql.conf:
# max_connections = 400  # increased from 100

# Then restart PostgreSQL
systemctl restart postgresql
```

### 2. Configure Application Connection Pooling

```python
# In SQLAlchemy configuration
engine = create_engine(
    'postgresql://...',
    pool_size=20,              # size of the pool
    max_overflow=40,           # max overflow size
    pool_recycle=3600,         # recycle connections after 1 hour
    pool_pre_ping=True,        # test connections before using
    connect_args={'connect_timeout': 5}
)
```

### 3. Implement Connection Pool Monitoring

```python
# Add to Flask app for health checks
@app.route('/health/db')
def db_health():
    pool = db.engine.pool
    return {
        'pool_size': pool.size(),
        'checked_out': pool.checkedout(),
        'utilization': pool.checkedout() / pool.size() * 100
    }
```

### 4. Set Idle Connection Timeout

```bash
# Add to PostgreSQL config
# idle_in_transaction_session_timeout = '5min'
# idle_session_timeout = '30min'

# Then reload configuration
psql -c "ALTER SYSTEM SET idle_in_transaction_session_timeout = '5min';"
psql -c "SELECT pg_reload_conf();"
```

## Prevention

### 1. Regular Monitoring
```bash
# Add to monitoring script (run every 5 min)
psql -c "SELECT COUNT(*) as connections, MAX(COUNT(*)) OVER () as max FROM pg_stat_activity;" >> /var/log/db_connections.log
```

### 2. Alert Thresholds
- Warning: 80% utilization
- Critical: 95% utilization
- Action: Page on-call if critical for 5 minutes

### 3. Connection Leak Detection
```bash
# Check if connections growing over time
SELECT DATE_TRUNC('hour', now()) as hour,
       AVG(connection_count) as avg_connections
FROM connection_history
GROUP BY DATE_TRUNC('hour', now())
ORDER BY hour DESC
LIMIT 24;
```

## Verification After Recovery

```bash
# 1. Check utilization back to normal
psql -c "SELECT ROUND(COUNT(*) * 100.0 / (SELECT setting::int FROM pg_settings WHERE name='max_connections'), 2) as utilization_pct FROM pg_stat_activity;"

# 2. Verify no long-idle connections
psql -c "SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'idle' AND query_start < NOW() - INTERVAL '5 minutes';"

# 3. Test new connections work
psql -c "SELECT version();"

# 4. API responding normally
curl -s http://localhost:5000/health | jq
```

## Post-Recovery Checklist

- [ ] Connection count < 70% of max
- [ ] No error messages in logs
- [ ] API responding normally
- [ ] All services back online
- [ ] Alert cleared automatically

## Root Cause Analysis

If pool exhaustion recurring:

1. **Connection leak**: Application not closing connections properly
2. **Idle buildup**: Connections not being recycled
3. **High load**: Need to increase pool size
4. **Hanging queries**: Queries stuck, holding connections

Check each before considering this "resolved".

## Escalation

**If pool exhaustion recurring within 1 hour**:
1. Investigate for connection leak in code
2. Check for stuck transactions
3. Consider load testing to find limits
4. Escalate to database/infrastructure team

## Related Runbooks

- SLOW_QUERY_ANALYSIS.md - if long queries holding connections
- API_LATENCY_DEBUG.md - if API slow due to connection timeouts
