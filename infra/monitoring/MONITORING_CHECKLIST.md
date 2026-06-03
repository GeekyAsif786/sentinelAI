# SentinelAI Staging Monitoring Checklist

## Pre-Deployment Setup (Before Phase 2-4 Staging Launch)

### Infrastructure Prerequisites
- [ ] Prometheus server deployed and configured
- [ ] Grafana server deployed and accessible
- [ ] PostgreSQL database with monitoring tables created
- [ ] Redis cache running and monitored
- [ ] Neo4j graph database running and monitored
- [ ] Celery worker pool initialized
- [ ] All exporters configured (postgres_exporter, redis_exporter, etc.)

### Monitoring Configuration
- [ ] Prometheus scrape jobs configured for all services
- [ ] Alert rules loaded into Prometheus/Alertmanager
- [ ] Grafana dashboards provisioned
- [ ] Notification channels configured (email, Slack, webhook)
- [ ] Log aggregation pipeline setup (if applicable)
- [ ] Data retention policies configured

---

## Deployment Phase (First 2 hours)

### During Service Startup
- [ ] All services starting without errors
- [ ] Log streams flowing to aggregation system
- [ ] Prometheus metrics collection confirmed
- [ ] Database schema initialized and accessible

### Initial Health Checks (T+15 minutes)
- [ ] Flask API responding to health checks
- [ ] Celery workers connected and accepting tasks
- [ ] PostgreSQL database connectivity verified
- [ ] Redis cache responding to commands
- [ ] Neo4j graph database accepting connections
- [ ] No immediate errors in application logs

### Baseline Metrics (T+30 minutes)
- [ ] Prometheus successfully scraping all targets
- [ ] Grafana dashboards loading without errors
- [ ] All metrics visible in Prometheus query interface
- [ ] Initial metric values recorded as baseline
- [ ] Alert evaluation running without errors

### First Test Scans (T+45 minutes to T+2 hours)
- [ ] Trigger 5-10 test scans manually or via API
- [ ] Monitor scan execution in real-time
- [ ] Verify scans appear in database
- [ ] Check celery task execution logs
- [ ] Confirm graph projections starting
- [ ] Monitor worker resource utilization

---

## 24-Hour Staging Validation Phase

### Hourly Checks (Every hour for first 24 hours)

**System Availability**
- [ ] All services still running (no crashes)
- [ ] No unhandled errors in application logs
- [ ] Database connection pool not exhausted
- [ ] Redis memory usage stable
- [ ] Celery worker nodes still connected

**Scan Execution**
- [ ] New scans starting normally
- [ ] Scan completion times within baseline
- [ ] Success rate maintained above 95%
- [ ] No accumulation of failed tasks

**Data Integrity**
- [ ] Scan results persisting to database
- [ ] Host/service records correctly created
- [ ] Finding records populating
- [ ] No data duplication or corruption
- [ ] Foreign key relationships intact

**Performance Metrics**
- [ ] Database query performance stable
- [ ] API response times consistent
- [ ] No increasing latency trends
- [ ] Worker CPU/memory usage normal
- [ ] No I/O bottlenecks detected

### Daily Reviews (Once per 24-hour period)

**Error Analysis**
- [ ] Review aggregated error logs
- [ ] Categorize any errors by type
- [ ] Identify new or recurring error patterns
- [ ] Check error rate trend
- [ ] Verify error rates < 5%

**Performance Analysis**
- [ ] Calculate success rate: (successful / total) × 100
- [ ] Calculate average execution time
- [ ] Identify any performance degradation
- [ ] Review resource utilization trends
- [ ] Check for any bottlenecks

**Security & Compliance**
- [ ] Review audit logs for unusual activity
- [ ] Verify no unauthorized access attempts
- [ ] Check data retention compliance
- [ ] Confirm backup processes running
- [ ] Validate security headers in API responses

**Graph Processing**
- [ ] Verify graph projection jobs completing
- [ ] Check graph projection success rate
- [ ] Validate attack path calculations
- [ ] Confirm Neo4j data consistency
- [ ] Review MITRE mapping completeness

---

## Success Criteria for Production Readiness

### Reliability Requirements
- ✓ **100 consecutive scans without failure** (or >99.5% success rate over 24 hours)
- ✓ **Error rate < 2%** across all scan types
- ✓ **No unhandled exceptions** in production logs
- ✓ **All graph projection jobs completing** within SLA
- ✓ **No data loss** or corruption detected

### Performance Requirements
- ✓ **Average scan execution time < 5 minutes** per scan
- ✓ **P95 API response time < 2 seconds**
- ✓ **Database query performance** acceptable (no queries > 10s)
- ✓ **Worker CPU usage** < 80% sustained
- ✓ **Worker memory usage** stable without leaks

### Stability Requirements
- ✓ **24-hour uptime** without service restart
- ✓ **No memory leaks** detected (stable memory profile)
- ✓ **No connection pool exhaustion** events
- ✓ **Consistent performance** without degradation over time
- ✓ **Clean graceful shutdown** capability

### Data Requirements
- ✓ **Host/service inventory** accurately captured
- ✓ **Vulnerabilities/findings** correctly identified
- ✓ **Attack paths** properly generated
- ✓ **Risk scores** calculated correctly
- ✓ **Audit trail** complete and consistent

---

## Critical Alerts to Monitor

| Alert | Threshold | Action | Owner |
|-------|-----------|--------|-------|
| Celery Worker Disconnected | Any worker offline | Page on-call immediately | SRE |
| Scan Failure Rate | > 10% | Investigate error cause | Engineering |
| Graph Projection Failure | > 5% | Debug Neo4j connection | Engineering |
| Database Connection Pool | > 80% usage | Check for connection leaks | Database Team |
| API Response Time | > 5 seconds P95 | Check database performance | Backend Team |
| Redis Memory | > 90% usage | Trigger cleanup/restart | Infrastructure |
| Celery Queue Depth | > 1000 tasks | Scale workers or investigate | Infrastructure |

---

## Escalation Procedures

### Level 1: Warning Alerts (Severity: WARNING)
- **Action**: Monitor closely, investigate root cause
- **Timeline**: Respond within 15 minutes
- **Owner**: On-call engineer

### Level 2: Critical Alerts (Severity: CRITICAL)
- **Action**: Immediate investigation and remediation
- **Timeline**: Respond within 5 minutes
- **Owner**: On-call engineer + Tech Lead

### Level 3: System Outage
- **Action**: Full incident response
- **Timeline**: Immediate
- **Owner**: Engineering Lead + Infrastructure Team

---

## Post-Deployment Monitoring Maintenance

### Daily Tasks
- [ ] Review alert summary from previous 24 hours
- [ ] Check for any unresolved warning alerts
- [ ] Verify backup completion
- [ ] Review slow query logs

### Weekly Tasks
- [ ] Analyze performance trends
- [ ] Review error patterns
- [ ] Capacity planning assessment
- [ ] Update baseline metrics

### Monthly Tasks
- [ ] Dashboard optimization review
- [ ] Alert tuning based on false positives
- [ ] Documentation updates
- [ ] Disaster recovery drill

---

## Runbooks Reference

See dedicated runbooks for incident response:
- [CELERY_WORKER_RECOVERY.md](runbooks/CELERY_WORKER_RECOVERY.md)
- [SCAN_FAILURE_INVESTIGATION.md](runbooks/SCAN_FAILURE_INVESTIGATION.md)
- [DB_CONNECTION_RECOVERY.md](runbooks/DB_CONNECTION_RECOVERY.md)
- [REDIS_RECOVERY.md](runbooks/REDIS_RECOVERY.md)
- [NEO4J_RECOVERY.md](runbooks/NEO4J_RECOVERY.md)
- [PERFORMANCE_BASELINE_CHECK.md](runbooks/PERFORMANCE_BASELINE_CHECK.md)
