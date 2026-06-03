# Deployment Day Quick Start (Print this!)

## 30 Minutes Before Deployment

```
□ Load environment variables
  export PROD_DB_URL=postgresql://...
  export PROD_REDIS_HOST=...
  export BACKUP_PATH=/backups

□ Verify connectivity
  psql $PROD_DB_URL -c "SELECT 1"
  redis-cli -h $PROD_REDIS_HOST ping
  curl http://localhost:8000/health

□ Confirm team ready
  ✓ Tech Lead: Present
  ✓ On-call: Present  
  ✓ DBA: Available
  ✓ DevOps: Ready

□ Open communication channels
  Slack: #sentinelai-incidents
  Zoom: [link]
  Bridge: [phone] / Code: [code]

□ Start monitoring
  Grafana dashboards open
  Error rate visible
  Latency graphs loaded
```

---

## Deployment Timeline

| Time | Action | Owner | Duration | Status |
|------|--------|-------|----------|--------|
| T-15m | Final checks | Tech Lead | 5 min | □ |
| T-10m | Create backup | DBA | 10-15 min | □ |
| T+5m | Apply migration | DBA | 10 min | □ |
| T+15m | Verify schema | DBA | 5 min | □ |
| T+20m | Deploy code | DevOps | 10 min | □ |
| T+30m | Smoke tests | QA | 5 min | □ |
| T+35m | Monitor (1h) | On-call | 60 min | □ |
| T+95m | 4h validation | On-call | 180 min | □ |
| T+275m | 24h sign-off | Tech Lead | Ongoing | □ |

---

## Deployment Commands (Copy-Paste Ready)

### Step 1: Backup (T-10m)
```bash
BACKUP_FILE="/backups/prod_backup_$(date +%Y%m%d_%H%M%S).sql"
pg_dump -h $PROD_DB_HOST -U $PROD_DB_USER -d $PROD_DB > "$BACKUP_FILE"
echo "$BACKUP_FILE" > /backups/.last_backup
ls -lh "$BACKUP_FILE"  # Verify size > 10MB
```

### Step 2: Migration (T+5m)
```bash
cd /opt/sentinelai/backend
alembic current
alembic upgrade head -v 2>&1 | tee /tmp/migration.log
alembic current  # Verify: should show 0002_add_graph_jobs
```

### Step 3: Verify Schema (T+15m)
```bash
psql $PROD_DB_URL -c "\d graph_projection_jobs" | head -10
psql $PROD_DB_URL -c "SELECT COUNT(*) FROM graph_projection_jobs;"
psql $PROD_DB_URL -c "\d scan_runs" | grep worker_node_id
```

### Step 4: Deploy Code (T+20m)
```bash
cd /opt/sentinelai
git fetch origin main
git checkout main && git pull origin main
pip install -r requirements.txt --no-deps
systemctl stop sentinelai-api sentinelai-worker
sleep 2
systemctl start sentinelai-api sentinelai-worker
sleep 3
systemctl status sentinelai-api sentinelai-worker
```

### Step 5: Smoke Tests (T+30m)
```bash
# Test 1: API
curl -s http://localhost:8000/health | jq .status

# Test 2: Database
psql $PROD_DB_URL -c "SELECT COUNT(*) FROM scan_runs;"

# Test 3: Worker
celery -A app.worker inspect active_queues | jq .

# Test 4: Redis
redis-cli -h $PROD_REDIS_HOST ping

# Test 5: Write test
psql $PROD_DB_URL << 'SQL'
BEGIN;
INSERT INTO hosts (name, environment) VALUES ('test', 'prod');
ROLLBACK;
SQL
```

---

## Metrics to Watch (First Hour)

Check every 5 minutes:

```
ERROR RATE: ____%  (Target: < 2%)
✓ Green   (< 2%)
✓ Yellow  (2-5%)
✗ Red     (> 5%)

LATENCY P95: _____ms  (Target: < 500ms)
✓ Green   (< 500ms)
✓ Yellow  (500-1000ms)
✗ Red     (> 1000ms)

DB CONNECTIONS: _____  (Target: < 25 of 50)
✓ Green   (< 25)
✓ Yellow  (25-40)
✗ Red     (> 40)

WORKER TASKS: _____  (Target: < 10 active)
✓ Green   (< 10)
✓ Yellow  (10-20)
✗ Red     (> 20)

SCANS COMPLETED: _____  (Target: > 0 after 4h)
Status: ___________
```

---

## Decision Tree (If Issue Occurs)

```
ISSUE DETECTED
    ↓
Is error rate > 10%?
├─ YES → ROLLBACK IMMEDIATELY
│        Contact: CTO + Tech Lead
│        Procedure: PRODUCTION_DEPLOYMENT_CHECKLIST.md
│        
└─ NO → Is error rate > 5%?
        ├─ YES → War Room Meeting
        │        Decision: Fix (< 15 min) or Rollback?
        │        Contact: Tech Lead
        │        Time limit: 15 minutes
        │
        └─ NO → Continue Monitoring
                Error rate < 5% = acceptable
                Monitor every 5 minutes
```

---

## Rollback Command (If Needed)

```bash
# OPTION 1: Database Only (Fastest)
systemctl stop sentinelai-api sentinelai-worker
sleep 5

BACKUP_FILE=$(cat /backups/.last_backup)
psql $PROD_DB_URL < "$BACKUP_FILE"

systemctl start sentinelai-api sentinelai-worker
curl http://localhost:8000/health  # Verify


# OPTION 2: Full Rollback (Code + DB)
cd /opt/sentinelai
git checkout v1.0.0  # Previous stable version
cd backend
alembic downgrade 0001_foundation

systemctl restart sentinelai-api sentinelai-worker
```

---

## Escalation Contacts

| When | Who | Phone | Slack |
|------|-----|-------|-------|
| Error 2-5% | On-call | [phone] | @[handle] |
| Error 5-10% | Tech Lead | [phone] | @[handle] |
| Error > 10% | CTO | [phone] | @[handle] |

**War Room:** Zoom [link] | Bridge [phone] Code [code]

---

## What NOT to Do

❌ Don't deploy during peak hours without warning  
❌ Don't skip backup verification  
❌ Don't ignore > 5% error rate  
❌ Don't restart services without monitoring status  
❌ Don't change two things at once  
❌ Don't hesitate to rollback if unsure  
❌ Don't forget to update status page  

---

## Success Checklist

After deployment, verify:

- [ ] Error rate remains < 2%
- [ ] Response latency < 500ms P95
- [ ] All services running (systemctl status)
- [ ] Database accessible (psql ... -c "SELECT 1")
- [ ] Worker processing tasks (celery inspect)
- [ ] New scans executing after 4 hours
- [ ] No data corruption
- [ ] No cascading failures
- [ ] Team debriefed on status
- [ ] Status page updated

---

## Real-Time Monitoring Scripts

### Watch Error Rate
```bash
watch -n 5 'psql $PROD_DB_URL -t -c "SELECT ROUND(100.0 * COUNT(CASE WHEN status = '\''failed'\'' THEN 1 END) / COUNT(*), 2) FROM scan_runs WHERE created_at > NOW() - INTERVAL '\''5 minutes'\'';"'
```

### Watch DB Connections
```bash
watch -n 5 'psql $PROD_DB_URL -c "SELECT count(*) FROM pg_stat_activity;"'
```

### Watch Services
```bash
watch -n 5 'systemctl status sentinelai-api sentinelai-worker --no-pager'
```

### Watch Logs (New Errors)
```bash
journalctl -u sentinelai-api -u sentinelai-worker -f | grep ERROR
```

---

## Sign-Off Template

After 24 hours, fill this out:

```
DEPLOYMENT SIGN-OFF
───────────────────────────────────

Date: ________________
Deployed SHA: ________________
Migration: 0002_add_graph_jobs

✓ Pre-checks: PASSED
✓ Migration: SUCCESSFUL  
✓ Smoke tests: ALL PASS
✓ Error rate: < 2% ✓
✓ No data loss: CONFIRMED
✓ Services stable: YES

Approved by:
  Tech Lead: ________________
  DevOps: ________________
  DBA: ________________

Status: ☐ APPROVED  ☐ APPROVED W/ CONDITIONS
───────────────────────────────────
```

---

## Incident Communications

### Initial Alert (Post to #sentinelai-incidents)
```
:warning: ISSUE DETECTED

Error rate: X%
Service: [API/Worker/Database]
Status: Investigating
Commander: @[name]
War room: [zoom]
```

### Status Update (Every 5-10 min)
```
:clock1: Update (T+Xmin)

Current error rate: X%
Action: [Investigating/Fixing/Rolling Back]
ETA: [time]
```

### Resolution
```
:checkered_flag: RESOLVED

Issue: [brief description]
Action taken: [rollback/fix/other]
Recovery time: [Xmin]
RCA: [scheduled date/time]
```

---

## File Locations

- Full Checklist: `/Users/asif/SentinelAI/PRODUCTION_DEPLOYMENT_CHECKLIST.md`
- Procedures: `/Users/asif/SentinelAI/PRODUCTION_DEPLOYMENT_PROCEDURES.md`
- Contacts: `/Users/asif/SentinelAI/DEPLOYMENT_EMERGENCY_CONTACTS.md`
- Index: `/Users/asif/SentinelAI/DEPLOYMENT_RUNBOOK_INDEX.md`
- **This guide:** `/Users/asif/SentinelAI/DEPLOYMENT_DAY_QUICKSTART.md`

---

## Last Deployment

- Date: __________
- Duration: __________
- Issues: __________
- Lesson Learned: __________

---

**IMPORTANT: Print this page and have it in the war room during deployment!**

Questions? See DEPLOYMENT_RUNBOOK_INDEX.md or ask #sentinelai-deployments
