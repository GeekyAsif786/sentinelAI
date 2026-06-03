# SentinelAI Production Deployment Runbook Index

## Overview
Complete production deployment documentation for SentinelAI Phase 2-4, including checklists, procedures, emergency contacts, and escalation protocols.

---

## Quick Navigation

### 📋 Main Documents

1. **PRODUCTION_DEPLOYMENT_CHECKLIST.md** (24 KB)
   - Pre-deployment verification (48 hours before)
   - Deployment execution step-by-step
   - Post-deployment monitoring (1h, 4h, 24h)
   - Rollback procedures
   - Sign-off and documentation
   - Incident response playbook
   - **Use this for:** Complete deployment checklist, verification, and monitoring

2. **PRODUCTION_DEPLOYMENT_PROCEDURES.md** (21 KB)
   - Environment setup and configuration
   - Command reference library
   - Executable bash scripts for each step
   - Smoke tests and verification commands
   - Monitoring commands for real-time tracking
   - Rollback command sequences
   - Troubleshooting procedures
   - **Use this for:** Exact commands to execute, quick reference, scripts

3. **DEPLOYMENT_EMERGENCY_CONTACTS.md** (13 KB)
   - On-call rotation and team contacts
   - Communication channels (Slack, calls, bridge lines)
   - Escalation matrix for Level 1/2/3 incidents
   - Contact procedures and sequences
   - Incident response playbook with examples
   - Communication templates (Slack, email)
   - Post-incident RCA procedures
   - Monthly drill procedures
   - **Use this for:** Who to contact, how to escalate, communication templates

---

## Deployment Phases

### Phase 1: Pre-Deployment (48 hours before)
**Owner:** Technical Lead  
**Duration:** 30 minutes  
**Checklist:** See PRODUCTION_DEPLOYMENT_CHECKLIST.md → Pre-Deployment Verification

Items:
- [ ] Infrastructure readiness (database, Redis, Neo4j)
- [ ] Code review and testing complete
- [ ] Team briefing and rollback review
- [ ] Monitoring setup and dashboards ready

### Phase 2: Deployment Execution (T-0 hours)
**Owner:** DevOps/On-call Engineer  
**Duration:** 30-45 minutes  
**Checklist:** See PRODUCTION_DEPLOYMENT_CHECKLIST.md → Deployment Execution

Steps:
1. Database backup (5-10 min)
2. Migration application (10-15 min)
3. Schema verification (5 min)
4. Code deployment (10-15 min)
5. Smoke tests (5 min)

**Commands:** See PRODUCTION_DEPLOYMENT_PROCEDURES.md → Deployment Commands

### Phase 3: Post-Deployment Monitoring
**Owner:** On-call team  
**Duration:** 24 hours (with variable intensity)

Timeline:
- **First Hour:** Continuous monitoring (every 5 minutes)
- **4 Hours:** Extended validation (every 15 minutes)
- **24 Hours:** Long-term stability checks (every hour)

**Metrics Dashboard:** See PRODUCTION_DEPLOYMENT_CHECKLIST.md → Critical Metrics Dashboard

### Phase 4: Sign-Off and RCA
**Owner:** Technical Lead  
**Duration:** Ongoing

- 24-hour validation passes → Sign-off forms completed
- Post-incident RCA (if rollback occurred)
- Knowledge base updates
- Team training and process improvements

---

## Key Metrics and Thresholds

| Metric | Target | Alert | Critical |
|--------|--------|-------|----------|
| Error Rate | < 2% | > 5% | > 10% |
| P95 Latency | < 500ms | > 1000ms | > 5s |
| Scan Success Rate | > 98% | < 95% | < 90% |
| Worker Health | All online | 1 offline | > 1 offline |
| DB Connections | < 50% max | > 80% | 100% (full) |
| Graph Jobs Complete | > 90% | < 70% | < 50% |
| API Response | < 500ms | > 1s | > 5s |

---

## Escalation Quick Reference

### Level 1 (Error rate 2-5%)
- **Action:** Investigate, fix forward if < 5 min
- **Notify:** On-call engineer
- **Timeline:** Fix or escalate within 10 min

### Level 2 (Error rate 5-10%)
- **Action:** War room, consider rollback
- **Notify:** Tech Lead + On-call
- **Timeline:** Decision within 15 min

### Level 3 (Error rate > 10%)
- **Action:** IMMEDIATE ROLLBACK
- **Notify:** CTO + Engineering Manager
- **Timeline:** Rollback within 5 min

**Full procedures:** See DEPLOYMENT_EMERGENCY_CONTACTS.md → Escalation Matrix

---

## Team Contact Summary

### On-Call Team
- **Primary:** [Name/Phone] - Slack: @[handle]
- **Secondary:** [Name/Phone] - Slack: @[handle]
- **Backup:** [Name/Phone] - Slack: @[handle]

### Leadership
- **Tech Lead:** [Name] - Available 8am-6pm EST
- **DevOps Lead:** [Name] - Available 8am-6pm EST
- **DBA:** [Name] - Available 8am-6pm EST
- **CTO:** [Name] - Emergency only

**Full directory:** See DEPLOYMENT_EMERGENCY_CONTACTS.md → Primary Deployment Team Contacts

---

## Communication Channels

| Channel | Purpose | Cadence |
|---------|---------|---------|
| #sentinelai-incidents | Active incidents | Real-time |
| #sentinelai-deployments | Deployment coordination | Per-deployment |
| Zoom War Room | Video call | On-demand |
| Bridge Line | Audio backup | On-demand |
| Status Page | External communication | Real-time |

---

## Rollback Decision Flowchart

```
Issue Detected
    ↓
Error Rate < 2%? → No issues, continue monitoring
    ↓ Yes
Error Rate < 5%?
    ├─ Yes → Quick fix possible?
    │         ├─ Yes (< 5 min) → Deploy hotfix
    │         └─ No → Escalate to Level 2
    │
    └─ No (5-10%) → War room + Technical Lead
                    ├─ Quick fix?
                    │   ├─ Yes (< 15 min) → Deploy
                    │   └─ No → Level 2 Escalation
                    └─ Cannot fix?
                        └─ Execute Rollback (Option 1: DB only)

Error Rate > 10% → IMMEDIATE ROLLBACK (Level 3)
```

---

## File References

### Configuration Files
- Database credentials: Managed by vault/secrets manager
- Environment: `.env` template in `/opt/sentinelai`
- Backup location: `/backups` (10GB+ available)

### Deployment Paths
- Application: `/opt/sentinelai`
- Backend: `/opt/sentinelai/backend`
- Database migrations: `/opt/sentinelai/backend/alembic`
- Logs: `/var/log/sentinelai/`

### Monitoring
- Grafana: https://grafana.sentinelai.com
- Prometheus: https://prometheus.sentinelai.com
- Logs: https://logs.sentinelai.com
- Status: https://status.sentinelai.com

---

## Pre-Deployment Checklist (Quick Version)

Run this before deployment execution:

```bash
# 1. Verify environment variables
PROD_DB_HOST=? PROD_DB_USER=? PROD_REDIS_HOST=? ✓

# 2. Test connectivity
psql $PROD_DB_URL -c "SELECT 1" ✓
redis-cli -h $PROD_REDIS_HOST ping ✓
curl http://localhost:8000/health ✓

# 3. Verify team is ready
- Tech Lead: Present
- On-call: Present
- DBA: Available
- DevOps: Ready

# 4. Backup strategy confirmed
Backup path: /backups/prod_backup_YYYYMMDD_HHMMSS.sql ✓

# 5. Rollback procedure reviewed
Runbook: PRODUCTION_DEPLOYMENT_CHECKLIST.md ✓
Backup location: Confirmed ✓

→ READY TO DEPLOY
```

---

## Common Issues and Solutions

### Issue: Database Migration Timeout
**Solution:** 
- Check for active locks: `SELECT * FROM pg_stat_activity;`
- Increase timeout in alembic config
- Consider deployment during off-peak hours

### Issue: Worker Not Processing Tasks
**Solution:**
- Check Redis: `redis-cli -h $PROD_REDIS_HOST ping`
- Inspect queue: `celery -A app.worker inspect active_queues`
- Restart worker: `systemctl restart sentinelai-worker`

### Issue: API Response Time Slow
**Solution:**
- Check slow queries: `SELECT * FROM pg_stat_statements ORDER BY total_time DESC;`
- Verify indexes: `SELECT * FROM pg_indexes WHERE tablename = 'scan_runs';`
- Scale horizontally if needed

See PRODUCTION_DEPLOYMENT_PROCEDURES.md → Troubleshooting Commands for full details.

---

## Commands Quick Reference

```bash
# Pre-deployment
source /opt/sentinelai/.env.prod  # Load environment variables
bash PRODUCTION_DEPLOYMENT_PROCEDURES.md  # See step-by-step

# Create backup
pg_dump $PROD_DB_URL > backup_$(date +%s).sql

# Apply migration
cd /opt/sentinelai/backend && alembic upgrade head

# Deploy code
cd /opt/sentinelai && git pull origin main

# Restart services
systemctl restart sentinelai-api sentinelai-worker

# Smoke tests
curl http://localhost:8000/health
psql $PROD_DB_URL -c "SELECT COUNT(*) FROM scan_runs;"

# Monitor
watch -n 5 'systemctl status sentinelai-api sentinelai-worker'

# Rollback database
pg_restore < /backups/prod_backup_YYYYMMDD_HHMMSS.sql

# Check status
journalctl -u sentinelai-api -f
journalctl -u sentinelai-worker -f
```

---

## Success Criteria

**Deployment considered successful when:**

✅ All pre-deployment checks passed  
✅ Database migration applied without errors  
✅ Schema changes verified  
✅ Code deployed and services restarted  
✅ All 5 smoke tests passed  
✅ Error rate remains < 2% for first hour  
✅ Completed scans > 0 within 4 hours  
✅ No data corruption detected  
✅ 24-hour monitoring shows stability  
✅ Team signs off on deployment  

**If any criteria fail → Evaluate rollback**

---

## Documentation Maintenance

### Update Frequency
- Contact information: Monthly (or when changes occur)
- Procedures: After each incident or process improvement
- Metrics thresholds: Quarterly review
- Emergency contacts: Before each major deployment

### Document Owners
- Checklist: Technical Lead
- Procedures: DevOps Lead
- Contacts: Engineering Manager
- Runbooks: Team collaboration

### Version Control
All files stored in `/Users/asif/SentinelAI/` with git history tracked.

```bash
git log PRODUCTION_DEPLOYMENT_CHECKLIST.md
git log PRODUCTION_DEPLOYMENT_PROCEDURES.md
git log DEPLOYMENT_EMERGENCY_CONTACTS.md
```

---

## Related Documentation

- **DEPLOYMENT.md** - General deployment guide
- **ARCHITECTURE.md** - System architecture
- **SECURITY_BOUNDARIES.md** - Security considerations
- **MONITORING_INFRASTRUCTURE_SUMMARY.txt** - Monitoring setup
- **PHASE_3_DEPLOYMENT_REPORT.md** - Phase 3 details
- **PHASE_4_IMPLEMENTATION.md** - Phase 4 details

---

## Monthly Deployment Drill

Every first Friday of the month at 10am EST:

**Drill Scenario:** Deployment causes 15% error rate

**Steps:**
1. Fake alert posted in #sentinelai-incidents
2. On-call responds and escalates
3. War room established
4. Team executes full rollback procedure
5. Drill leader evaluates response
6. Lessons learned documented

**Goal:** Ensure procedures work and team is trained

---

## Last Updated
- **Checklist:** [Auto-generated date]
- **Procedures:** [Auto-generated date]
- **Contacts:** [Update manually]
- **This index:** [Auto-generated date]

---

## How to Use These Documents

1. **Before Deployment:**
   - Review PRODUCTION_DEPLOYMENT_CHECKLIST.md (Pre-Deployment section)
   - Verify all team contacts in DEPLOYMENT_EMERGENCY_CONTACTS.md
   - Confirm on-call engineer is available

2. **During Deployment:**
   - Follow steps in PRODUCTION_DEPLOYMENT_PROCEDURES.md
   - Use PRODUCTION_DEPLOYMENT_CHECKLIST.md as verification
   - Have DEPLOYMENT_EMERGENCY_CONTACTS.md open for quick escalation

3. **During Incident:**
   - Reference escalation matrix in DEPLOYMENT_EMERGENCY_CONTACTS.md
   - Follow incident response playbook (same document)
   - Use templates for Slack/email communications

4. **After Deployment:**
   - Compare metrics against PRODUCTION_DEPLOYMENT_CHECKLIST.md thresholds
   - Document any issues encountered
   - Schedule RCA if rollback occurred

---

## Support and Questions

**For questions about:**
- **Deployment steps:** See PRODUCTION_DEPLOYMENT_PROCEDURES.md or contact DevOps Lead
- **Decision criteria:** See PRODUCTION_DEPLOYMENT_CHECKLIST.md or contact Tech Lead
- **Team contact:** See DEPLOYMENT_EMERGENCY_CONTACTS.md or ask Slack #sentinelai-deployments
- **Process improvement:** Create issue in project tracker

---

**Key Point:** These documents are living documents. Update them after each deployment with lessons learned.
