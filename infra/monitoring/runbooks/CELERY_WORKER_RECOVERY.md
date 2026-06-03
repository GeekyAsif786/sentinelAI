# Celery Worker Disconnection Recovery Runbook

**Alert Name**: CeleryWorkerDisconnected  
**Severity**: CRITICAL  
**Estimated Time to Resolve**: 5-15 minutes

## Symptoms

- Alert `CeleryWorkerDisconnected` triggered
- No active Celery workers responding to commands
- `celery -A app.worker inspect active` returns empty
- Scan tasks accumulating in queue without processing

## Immediate Actions (First 3 minutes)

### 1. Assess Current Status
```bash
# Check active workers
celery -A app.worker inspect active

# Check if workers are registered
celery -A app.worker inspect registered

# Check worker stats
celery -A app.worker inspect stats

# Check queue depth
redis-cli LLEN celery:celery  # or your task queue name
```

### 2. Verify Redis Connection (Required for Celery)
```bash
# Test Redis connectivity
redis-cli PING

# Check Redis info
redis-cli INFO stats

# Check if celery keys exist
redis-cli KEYS "celery:*" | head -10
```

**If Redis is down**, follow REDIS_RECOVERY.md immediately

### 3. Check Worker Process
```bash
# List all celery processes
ps aux | grep celery

# Look for zombie processes
ps aux | grep -i "[z]" celery
```

## Recovery Procedures

### Option 1: Soft Restart (Graceful)
```bash
# Send shutdown signal
pkill -15 -f 'celery.*worker'

# Wait for graceful shutdown (max 30 seconds)
sleep 2

# Verify process terminated
ps aux | grep celery | grep -v grep

# Restart Celery with info logging
celery -A app.worker -l info --loglevel=info

# Verify reconnection
sleep 5
celery -A app.worker inspect active
```

### Option 2: Hard Restart (Kill)
```bash
# Force kill all celery processes
pkill -9 -f 'celery.*worker'

# Verify all terminated
ps aux | grep celery | grep -v grep

# Clear any orphaned connections
redis-cli FLUSHDB  # WARNING: Only if isolated Redis instance

# Restart Celery
celery -A app.worker -l info

# Verify reconnection
sleep 5
celery -A app.worker inspect active
```

### Option 3: Background Restart (Daemonized)
```bash
# Stop existing daemon
service sentinelai-celery stop

# Verify stopped
ps aux | grep celery | grep -v grep

# Start daemon
service sentinelai-celery start

# Wait for startup
sleep 3

# Verify started
celery -A app.worker inspect active
```

## Verification

After restarting, verify recovery:

```bash
#!/bin/bash

echo "Verifying Celery Worker Recovery..."
echo ""

# 1. Check active workers
echo "1. Active workers:"
celery -A app.worker inspect active || echo "FAILED"

# 2. Check registered tasks
echo ""
echo "2. Registered tasks count:"
celery -A app.worker inspect registered | wc -l

# 3. Check worker stats
echo ""
echo "3. Worker stats:"
celery -A app.worker inspect stats

# 4. Test with a simple task
echo ""
echo "4. Sending test task..."
python -c "from app.tasks import test_task; test_task.delay()" 2>/dev/null && echo "Test task sent" || echo "Failed to send test task"

# 5. Check queue depth
echo ""
echo "5. Queue depth:"
redis-cli LLEN celery

echo ""
echo "✓ Recovery verification complete"
```

## Common Issues and Fixes

### Workers Start but Don't Accept Tasks

**Symptom**: Workers show as active but don't process tasks

**Solution**:
```bash
# Clear stale worker heartbeats
redis-cli DEL celery:0:reserved

# Restart workers
pkill -f 'celery.*worker'
sleep 2
celery -A app.worker -l info

# Verify
celery -A app.worker inspect active
```

### Worker Memory Leak Detected

**Symptom**: Worker process grows indefinitely in memory

**Solution**:
1. Set max tasks per worker: `celery -A app.worker -l info --max-tasks-per-child=1000`
2. Monitor memory: `watch ps aux | grep celery`
3. Consider restarting periodically

### Tasks Stuck in Queue

**Symptom**: Tasks not being processed even after worker restart

**Solution**:
```bash
# Check queue contents
redis-cli LRANGE celery 0 -1 | head -20

# If needed, purge failed tasks
celery -A app.worker purge

# Resubmit critical scans via API if needed
```

## Post-Recovery Checklist

- [ ] Celery workers showing as active
- [ ] New tasks being accepted into queue
- [ ] Tasks completing successfully
- [ ] No error messages in logs
- [ ] Redis connection stable
- [ ] Alert cleared automatically

## Prevention

1. **Monitor worker health regularly**:
   ```bash
   # Add to crontab
   */5 * * * * celery -A app.worker inspect active > /dev/null || send_alert
   ```

2. **Set up worker restart on failure**:
   - Use systemd/supervisor to auto-restart on crash
   - Monitor for frequent restarts as sign of deeper issue

3. **Log worker events**:
   ```bash
   celery -A app.events
   ```

4. **Regular resource monitoring**:
   - Monitor Celery worker memory usage
   - Set up alerts for OOM conditions

## Escalation

**If issue persists after 15 minutes**:
1. Check infrastructure (Redis, PostgreSQL)
2. Review application logs for errors
3. Consider rolling back recent changes
4. Contact DevOps/Infrastructure team

**Critical contacts**:
- On-call Engineer: [CONTACT]
- Infrastructure Lead: [CONTACT]
- Product Lead: [CONTACT]
