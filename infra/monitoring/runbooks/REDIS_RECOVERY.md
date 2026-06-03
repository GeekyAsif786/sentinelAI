# Redis Recovery Runbook

**Alert Name**: RedisConnectionLoss / RedisMemoryUsageHigh  
**Severity**: CRITICAL / WARNING  
**Estimated Time to Resolve**: 5-15 minutes

## Symptoms - Connection Loss

- Alert `RedisConnectionLoss` triggered
- Error: `Could not connect to Redis`
- Error: `redis.exceptions.ConnectionError`
- Celery tasks not being queued
- Session data unavailable

## Quick Diagnosis

### Check Redis Status
```bash
# Test Redis ping
redis-cli PING

# Get Redis info
redis-cli INFO

# Check if Redis process running
ps aux | grep redis

# Check Redis port
netstat -tlnp | grep 6379

# Check Redis logs
tail -50 /var/log/redis/redis-server.log
```

## Recovery - Connection Loss

### Restart Redis
```bash
# Stop Redis
redis-cli SHUTDOWN SAVE

# Wait for shutdown
sleep 2

# Verify stopped
ps aux | grep redis | grep -v grep

# Start Redis
redis-server /etc/redis/redis.conf

# Verify running
redis-cli PING

# Check Celery workers reconnected
celery -A app.worker inspect active
```

## Symptoms - Memory Exhaustion

- Alert `RedisMemoryUsageHigh` triggered (>90%)
- Redis commands slow or failing
- Eviction events in logs

## Recovery - Memory Exhaustion

### Check Memory Usage
```bash
# Get detailed memory info
redis-cli INFO memory

# Identify large keys
redis-cli --bigkeys

# Find keys by pattern
redis-cli KEYS "celery:*" | head -20
```

### Clean Up Redis

```bash
# Option 1: Clear old task results
redis-cli EVAL "return redis.call('del', KEYS[0])" 1 celery_results

# Option 2: Clear expired keys
redis-cli SCRIPT LOAD "return redis.call('FLUSHDB', 'ASYNC')" 

# Option 3: Set max memory policy
redis-cli CONFIG SET maxmemory-policy allkeys-lru

# Monitor cleanup
redis-cli INFO memory
```

## Prevention

1. **Set maxmemory limits** in Redis config
2. **Use connection pooling** in application
3. **Monitor memory trends** continuously
4. **Set eviction policies** appropriately

## Verification

- [ ] Redis PING returns PONG
- [ ] Celery workers show active
- [ ] Memory usage < 80%
- [ ] Task queue processing
