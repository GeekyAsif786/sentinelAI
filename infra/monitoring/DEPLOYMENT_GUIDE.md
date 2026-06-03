# SentinelAI Staging Monitoring - Deployment Guide

## Pre-Deployment Checklist

### 1. Infrastructure Setup
```bash
# Verify Prometheus is running
systemctl status prometheus

# Verify Grafana is running
systemctl status grafana-server

# Verify exporters are running
ps aux | grep postgres_exporter
ps aux | grep redis_exporter

# Verify database is accessible
psql -c "SELECT COUNT(*) FROM information_schema.tables;"
```

### 2. Load Alert Rules
```bash
# Copy alert rules to Prometheus config directory
cp /Users/asif/SentinelAI/infra/monitoring/ALERT_RULES.yaml /etc/prometheus/alert_rules.yml

# Add to prometheus.yml:
# global:
#   scrape_interval: 30s
#
# rule_files:
#   - '/etc/prometheus/alert_rules.yml'
#
# scrape_configs:
#   - job_name: 'prometheus'
#     static_configs:
#       - targets: ['localhost:9090']

# Reload Prometheus configuration
systemctl reload prometheus
```

### 3. Configure Alertmanager
```bash
# Verify Alertmanager running
systemctl status alertmanager

# Test alert routing
curl http://localhost:9093/api/v1/status

# Configure notification channels in alertmanager.yml
# See ALERT_RULES.yaml for webhook endpoints
```

### 4. Provision Grafana Dashboards
```bash
# Access Grafana
# http://localhost:3000 (default: admin/admin)

# Add Prometheus as data source
# - Name: Prometheus
# - URL: http://localhost:9090
# - Default: Yes

# Import dashboards from grafana/ directory
# Dashboard JSON files location: /Users/asif/SentinelAI/infra/grafana/provisioning/
```

---

## Monitoring Infrastructure Installation Commands

### Quick Install for Staging

```bash
#!/bin/bash
# Install monitoring infrastructure

# 1. Create monitoring directories
mkdir -p /var/log/monitoring
mkdir -p /etc/prometheus/rules

# 2. Copy monitoring files to appropriate locations
cp /Users/asif/SentinelAI/infra/monitoring/ALERT_RULES.yaml /etc/prometheus/alert_rules.yml
cp /Users/asif/SentinelAI/infra/monitoring/queries/monitoring_queries.sql /var/lib/monitoring/
cp /Users/asif/SentinelAI/infra/monitoring/scripts/log_collection.sh /usr/local/bin/
chmod +x /usr/local/bin/log_collection.sh

# 3. Set up cron jobs for log collection
echo "0 */6 * * * /usr/local/bin/log_collection.sh /var/log/monitoring/logs_\$(date +\\%Y\\%m\\%d_\\%H\\%M\\%S).txt" | crontab -

# 4. Reload Prometheus
systemctl reload prometheus

# 5. Verify alert rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules | length'
```

---

## Deployment Timeline

### T-0: Pre-Deployment (30 minutes before)
- [ ] Review MONITORING_CHECKLIST.md
- [ ] Verify all infrastructure components running
- [ ] Test alert notification channels
- [ ] Load alert rules into Prometheus
- [ ] Verify Prometheus scraping targets

### T+0: Deployment Start
- [ ] Begin SentinelAI service startup
- [ ] Monitor logs using log_collection.sh
- [ ] Watch Prometheus for new metrics

### T+15 min: Initial Validation
- [ ] Execute health checks from OPERATIONS_RUNBOOK.md
- [ ] Verify all services responding
- [ ] Check for immediate errors
- [ ] Record baseline metrics

### T+30 min: First Test Scans
- [ ] Trigger test scans
- [ ] Monitor execution in Prometheus/Grafana
- [ ] Verify metrics appearing
- [ ] Check database connectivity

### T+2 hours: Initial Deployment Phase Complete
- [ ] All services stable
- [ ] No critical errors
- [ ] Baseline metrics established
- [ ] Begin 24-hour validation phase

---

## Daily Monitoring Procedures

### Morning (Start of Shift)

```bash
#!/bin/bash
# Morning health check script

echo "=== Morning SentinelAI Health Check ==="
echo "Time: $(date)"
echo ""

# 1. Service status
echo "1. Service Status:"
systemctl status sentinelai-api sentinelai-celery sentinelai-redis sentinelai-postgres

# 2. Metrics collection
echo ""
echo "2. Collecting logs and metrics..."
/usr/local/bin/log_collection.sh /var/log/monitoring/morning_check_$(date +%Y%m%d).txt

# 3. Run monitoring queries
echo ""
echo "3. Running monitoring queries..."
psql -f /Users/asif/SentinelAI/infra/monitoring/queries/monitoring_queries.sql

# 4. Check alerts
echo ""
echo "4. Alert Status:"
curl -s http://localhost:9090/api/v1/alerts | jq '.data | group_by(.labels.severity) | map({severity: .[0].labels.severity, count: length})'

echo ""
echo "✓ Morning health check complete"
```

### Evening (End of Shift)

```bash
#!/bin/bash
# Evening health check and report generation

echo "=== Evening SentinelAI Report Generation ==="
echo "Time: $(date)"
echo ""

# 1. Generate monitoring report
echo "1. Generating monitoring report..."
cp /Users/asif/SentinelAI/infra/monitoring/MONITORING_REPORT_TEMPLATE.md /tmp/report_$(date +%Y%m%d_%H%M%S).md

# 2. Collect detailed metrics
echo ""
echo "2. Collecting detailed metrics..."
{
    echo "## Scan Execution (24 hours)"
    psql -c "SELECT status, COUNT(*) FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY status;"
    echo ""
    echo "## Error Summary (24 hours)"
    psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code ORDER BY count DESC LIMIT 5;"
    echo ""
    echo "## Performance Metrics"
    psql -c "SELECT ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_sec FROM scan_runs WHERE status = 'success' AND created_at > NOW() - INTERVAL '24 hours';"
} >> /tmp/report_$(date +%Y%m%d_%H%M%S).md

echo "✓ Report generated"

# 3. Archive logs
echo ""
echo "3. Archiving logs..."
tar -czf /var/log/monitoring/archived_$(date +%Y%m%d).tar.gz /var/log/monitoring/*.txt

echo "✓ Evening report complete"
```

---

## Alert Response Quick Reference

| Alert | Severity | Response Time | Runbook |
|-------|----------|---------------|---------|
| CeleryWorkerDisconnected | CRITICAL | Immediate | CELERY_WORKER_RECOVERY.md |
| ScanExecutionCriticalFailure | CRITICAL | Immediate | SCAN_FAILURE_INVESTIGATION.md |
| DatabaseConnectionPoolExhausted | CRITICAL | 5 minutes | DB_CONNECTION_RECOVERY.md |
| RedisConnectionLoss | CRITICAL | 5 minutes | REDIS_RECOVERY.md |
| Neo4jGraphDatabaseDown | CRITICAL | 5 minutes | NEO4J_RECOVERY.md |
| HighScanErrorRate | WARNING | 15 minutes | SCAN_FAILURE_INVESTIGATION.md |
| GraphProjectionFailureRateHigh | WARNING | 15 minutes | runbooks/OPERATIONS_RUNBOOK.md |
| APIResponseTimeExceeded | WARNING | 15 minutes | runbooks/OPERATIONS_RUNBOOK.md |

---

## Monitoring Data Access

### SQL Query Examples

```bash
# Get recent scan status
psql -c "SELECT id, status, error_code, created_at FROM scan_runs ORDER BY created_at DESC LIMIT 20;"

# Get error breakdown (24 hours)
psql -c "SELECT error_code, COUNT(*) FROM scan_runs WHERE error_code IS NOT NULL AND created_at > NOW() - INTERVAL '24 hours' GROUP BY error_code ORDER BY count DESC;"

# Get worker performance
psql -c "SELECT COALESCE(worker_node_id, 'unassigned') as worker, COUNT(*) as scans_count, ROUND(AVG(EXTRACT(EPOCH FROM (completed_at - started_at))), 2) as avg_duration_sec FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours' GROUP BY worker_node_id ORDER BY scans_count DESC;"

# Get success rate
psql -c "SELECT ROUND(SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as success_rate_pct FROM scan_runs WHERE created_at > NOW() - INTERVAL '24 hours';"
```

### Prometheus Query Examples

```
# Scan success rate (last 1 hour)
rate(scan_success_total[1h]) / rate(scan_attempts_total[1h])

# Error rate
rate(scan_failures_total[5m]) / rate(scan_attempts_total[5m])

# API response time P95
histogram_quantile(0.95, http_request_duration_seconds)

# Worker availability
celery_worker_pool_size

# Database connections in use
pg_stat_activity_count{state="active"}
```

---

## Troubleshooting

### Monitoring Infrastructure Issues

**Problem**: Prometheus not scraping targets
```bash
# Check targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.health != "up")'

# Verify scrape configs
curl http://localhost:9090/api/v1/targets/metadata | head -20
```

**Problem**: Alerts not firing
```bash
# Verify alert rules loaded
curl http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | select(.name == "ALERT_NAME")'

# Check Alertmanager status
curl http://localhost:9093/api/v1/status
```

**Problem**: Missing metrics
```bash
# Check if metric exported
curl http://localhost:5000/metrics | grep metric_name

# Verify job scraping metric
curl http://localhost:9090/api/v1/targets | grep job_name
```

---

## Success Validation

After 24 hours of monitoring:

- [ ] Zero unhandled exceptions in logs
- [ ] Scan success rate > 95%
- [ ] Error rate < 5%
- [ ] Average execution time < 5 minutes
- [ ] No data loss or corruption
- [ ] All alerts functional
- [ ] Grafana dashboards populated
- [ ] No performance degradation over time

---

## Documentation References

- Full setup validation: MONITORING_CHECKLIST.md
- Metrics overview: MONITORING_DASHBOARD.md
- Alert definitions: ALERT_RULES.yaml
- SQL queries: queries/monitoring_queries.sql
- Daily operations: runbooks/OPERATIONS_RUNBOOK.md
- Incident runbooks: runbooks/*.md

---

## Support Contacts

- Monitoring Infrastructure: DevOps Team
- Database Monitoring: Database Team
- Application Metrics: Backend Team
- On-Call Escalation: [CONTACT]

---

**Ready for Staging Deployment** ✓

All monitoring infrastructure files validated and ready for Phase 2-4 deployment.
