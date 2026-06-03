# SentinelAI Staging Monitoring Infrastructure

## Overview

Comprehensive monitoring, metrics, and alerting infrastructure for SentinelAI Phase 2-4 deployment on staging. This monitoring suite provides real-time visibility into system health, scan execution, performance metrics, and enables rapid incident response through automated alerts and detailed runbooks.

## Directory Structure

```
infra/monitoring/
├── README.md                              # This file
├── MONITORING_DASHBOARD.md                # Dashboard configuration and metrics overview
├── MONITORING_CHECKLIST.md                # Pre-deployment and ongoing validation
├── MONITORING_REPORT_TEMPLATE.md          # Standardized reporting format
├── ALERT_RULES.yaml                       # Prometheus alert rule definitions (20+ rules)
├── SETUP_COMPLETION_LOG.md                # Setup validation and completion status
│
├── queries/
│   └── monitoring_queries.sql             # 12 comprehensive monitoring SQL queries
│
├── scripts/
│   └── log_collection.sh                  # Automated log aggregation script
│
└── runbooks/
    ├── OPERATIONS_RUNBOOK.md              # Daily operations and procedures
    ├── CELERY_WORKER_RECOVERY.md          # Worker disconnection recovery (CRITICAL)
    ├── SCAN_FAILURE_INVESTIGATION.md      # Scan failure diagnosis and recovery
    ├── DB_CONNECTION_RECOVERY.md          # Database connection pool issues
    ├── REDIS_RECOVERY.md                  # Redis connectivity and memory issues
    └── NEO4J_RECOVERY.md                  # Neo4j graph database recovery
```

## Quick Start

### Access Monitoring Dashboards

- **Prometheus**: http://localhost:9090
  - Real-time metrics
  - Alert status
  - Query builder for custom queries

- **Grafana**: http://localhost:3000
  - Visual dashboards
  - Scan execution trends
  - System health overview
  - Custom alerts and notifications

### Run Monitoring Queries

```bash
# Execute all monitoring queries to get current system state
psql -f infra/monitoring/queries/monitoring_queries.sql

# Or run specific query
psql -c "SELECT status, COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"
```

### Collect Aggregated Logs

```bash
# Generate comprehensive log collection with system state
./infra/monitoring/scripts/log_collection.sh

# Save to specific file
./infra/monitoring/scripts/log_collection.sh monitoring_report_$(date +%Y%m%d).txt
```

### Check System Health

```bash
# Flask API
curl http://localhost:5000/health

# Celery Workers
celery -A app.worker inspect active

# Redis
redis-cli PING

# PostgreSQL
psql -c "SELECT version();"
```

## Key Metrics Tracked

### Scan Execution
- Success rate (target: >95%)
- Average execution time (target: <5 minutes)
- Error rate by type (target: <5%)
- Scan throughput (scans/hour)

### System Performance
- API response time P95 (target: <5s)
- Database query performance (target: P95 <1s)
- Celery task queue depth (target: <1000)
- Worker resource utilization (target: <80%)

### Infrastructure Health
- Database connection pool usage (alert >80%, critical >95%)
- Redis memory usage (alert >90%)
- Worker availability (alert if any offline)
- Neo4j connectivity (alert if down)

### Data Processing
- Graph projection success rate (target: >98%)
- Host/service discovery accuracy
- Vulnerability finding completeness
- Attack path generation success

## Alert Rules

21 alert rules across three severity levels:

### CRITICAL (Immediate Response Required)
- Celery worker disconnected
- Scan failure rate > 50%
- Database connection pool exhausted
- Redis connection lost
- Neo4j unreachable

### WARNING (Investigate Within 15 minutes)
- Scan error rate > 10%
- Graph projection failure rate > 5%
- API response time > 5 seconds
- Connection pool > 80%
- Celery queue depth > 1000 tasks
- Redis memory > 90%

### INFO (Monitor and Trend)
- Worker CPU usage > 85%
- Worker memory usage > 80%
- Increasing scan execution times
- No recent scan activity (>1 hour)

See **ALERT_RULES.yaml** for complete definitions and thresholds.

## Monitoring Workflows

### Daily Operations

**Morning Health Check** (See: OPERATIONS_RUNBOOK.md)
```bash
# Check system status
systemctl status sentinelai-api sentinelai-celery

# Check database connectivity
psql -c "\conninfo"

# Check for errors (last hour)
psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '1 hour' GROUP BY error_code;"

# Check alerts
curl http://localhost:9090/api/v1/alerts
```

**Evening Health Check**
```bash
# 24-hour summary
psql -c "SELECT status, COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"

# Success rate
psql -c "SELECT ROUND(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours';"

# Performance metrics
psql -c "SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec FROM scan_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours';"
```

### Incident Response

When an alert fires:

1. **Identify alert type and severity**
   - Check alert name against ALERT_RULES.yaml
   - Determine severity (CRITICAL/WARNING/INFO)

2. **Find appropriate runbook**
   - Critical worker issues → CELERY_WORKER_RECOVERY.md
   - Scan failures → SCAN_FAILURE_INVESTIGATION.md
   - Database issues → DB_CONNECTION_RECOVERY.md
   - Redis issues → REDIS_RECOVERY.md
   - Neo4j issues → NEO4J_RECOVERY.md

3. **Execute recovery procedures**
   - Follow diagnosis steps in runbook
   - Implement recovery steps
   - Verify recovery with checks

4. **Document incident**
   - Record in MONITORING_REPORT_TEMPLATE.md
   - Note root cause and resolution
   - Update prevention procedures

## Monitoring Validation Checklist

Before production deployment, complete MONITORING_CHECKLIST.md:

### Pre-Deployment Setup
- [ ] Prometheus and Grafana deployed
- [ ] All exporters configured
- [ ] Alert rules loaded
- [ ] Notification channels configured

### Deployment Phase (First 2 Hours)
- [ ] All services started
- [ ] No immediate errors
- [ ] Prometheus scraping targets
- [ ] Baseline metrics recorded

### 24-Hour Validation
- [ ] Scan success rate > 95%
- [ ] Average execution time < 5 minutes
- [ ] Error rate < 5%
- [ ] No data loss or corruption
- [ ] No unhandled exceptions
- [ ] Graph projections completing

### Success Criteria
- ✓ 100 consecutive scans without failure
- ✓ No memory leaks detected
- ✓ Stable performance over 24 hours
- ✓ Complete audit trail

## Reporting

### Generate Monitoring Report

1. Use MONITORING_REPORT_TEMPLATE.md as guide
2. Populate metrics from:
   - Prometheus dashboard
   - SQL monitoring queries (monitoring_queries.sql)
   - Alert history
   - Log collection output (log_collection.sh)
3. Document any incidents and resolutions
4. Record recommendation (Ready/Needs Testing/Blocking Issues)

### Dashboard Screenshots

Export key Grafana dashboards:
- Scan Execution Overview (24h trend)
- Worker Performance (utilization by worker)
- System Health (infrastructure resources)
- Error Analysis (error distribution)

## SQL Monitoring Queries

12 comprehensive queries available in `queries/monitoring_queries.sql`:

1. **Scan Execution Status** - Success rate and duration by status
2. **Error Analysis** - Error breakdown and frequency
3. **Graph Projection Status** - Projection job performance
4. **Scan Execution Rate** - Hourly throughput breakdown
5. **Host and Service Counts** - Inventory metrics per scan
6. **Worker Performance** - Per-worker statistics
7. **Database Connection Pool** - Real-time connection status
8. **Slow Queries** - Performance bottleneck identification
9. **Findings and Vulnerabilities** - Security findings by severity
10. **Recent Scan Details** - Latest 10 scans with metrics
11. **Attack Path Generation** - Attack path statistics
12. **Health Check Summary** - Quick system state overview

## Log Collection

Automated log aggregation via `scripts/log_collection.sh`:

```bash
# Generate comprehensive log collection
./infra/monitoring/scripts/log_collection.sh

# Output includes:
# - Application logs (Flask, Celery, Redis)
# - Database activity and statistics
# - System resources (CPU, memory, disk)
# - Network connections
# - Recent errors from database
# - Application health endpoints
```

## Integration Points

### Prometheus Scrape Targets

Configure Prometheus to scrape:

- **Flask API** (port 5000)
  - Endpoint: `/metrics`
  - Interval: 30s

- **PostgreSQL** (via postgres_exporter)
  - Port: 9187
  - Interval: 30s

- **Redis** (via redis_exporter)
  - Port: 9121
  - Interval: 30s

- **Celery Workers**
  - Via Redis events
  - Interval: 30s

### Grafana Provisioning

Provisioning configs in `infra/grafana/provisioning/`:

- Datasources: Prometheus
- Dashboards: Provided JSON templates

### Alert Notification Channels

Configure in Alertmanager:

- Slack webhook for immediate notifications
- Email for critical alerts
- PagerDuty for on-call escalation
- Custom webhook for internal systems

## Performance Baselines

After 24-hour validation, document baseline metrics:

```
Scan Execution:
  - Average: [X] seconds
  - P50: [X] seconds
  - P95: [X] seconds
  - P99: [X] seconds

Error Rates:
  - Baseline: [X]%
  - Critical threshold: 10%
  - Warning threshold: 5%

Resource Usage:
  - CPU: [X]% average, [X]% peak
  - Memory: [X]% average, [X]% peak
  - Disk I/O: [X] ops/sec
```

## Troubleshooting

### Metrics Not Appearing

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq

# Verify exporters running
netstat -tlnp | grep :9187  # postgres_exporter
netstat -tlnp | grep :9121  # redis_exporter
```

### Alerts Not Firing

```bash
# Check Alertmanager config
curl http://localhost:9093/api/v1/alerts

# Verify alert rules loaded
curl http://localhost:9090/api/v1/rules | jq

# Test alert firing manually
curl -X POST http://localhost:9090/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[{"labels": {"alertname": "TestAlert"}}]'
```

### Slow Queries in Prometheus

```bash
# Find slow metric queries
curl http://localhost:9090/api/v1/query_range?query=[QUERY]&start=[T1]&end=[T2]&step=60s

# Check Prometheus load
curl http://localhost:9090/api/v1/query?query=up | jq
```

## References

- Prometheus Docs: https://prometheus.io/docs/
- Grafana Docs: https://grafana.com/docs/
- PostgreSQL Monitoring: https://www.postgresql.org/docs/current/monitoring.html
- Celery Monitoring: https://docs.celeryproject.io/en/stable/userguide/monitoring.html
- Neo4j Monitoring: https://neo4j.com/docs/operations-manual/current/monitoring/

## Support

For monitoring infrastructure issues:

1. Check relevant runbook in `runbooks/`
2. Review OPERATIONS_RUNBOOK.md for diagnostic procedures
3. Consult monitoring_queries.sql for current system state
4. Generate log collection for investigation

For deployment questions:
- Reference MONITORING_CHECKLIST.md
- Use MONITORING_REPORT_TEMPLATE.md for tracking
- Check SETUP_COMPLETION_LOG.md for validation status

## Version

- **Version**: 1.0
- **Created**: Phase 2-4 Deployment
- **Status**: Ready for Staging Deployment
- **Last Updated**: [DATE]

---

**All monitoring infrastructure ready for SentinelAI Phase 2-4 staging deployment** ✓
