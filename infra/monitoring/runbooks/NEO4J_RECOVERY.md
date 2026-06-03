# Neo4j Graph Database Recovery Runbook

**Alert Name**: Neo4jGraphDatabaseDown  
**Severity**: CRITICAL  
**Estimated Time to Resolve**: 10-20 minutes

## Symptoms

- Alert `Neo4jGraphDatabaseDown` triggered
- Error: `Could not connect to Neo4j`
- Graph projection jobs failing
- Attack path queries failing

## Quick Diagnosis

### Check Neo4j Status
```bash
# Test Neo4j connectivity
curl -u neo4j:password http://localhost:7474/db/data/

# Check if service running
systemctl status neo4j

# Check Neo4j logs
tail -50 /var/log/neo4j/neo4j.log

# Check disk space
df -h | grep neo4j

# Check heap memory
neo4j-admin info
```

## Recovery Steps

### 1. Soft Restart
```bash
# Restart Neo4j service
systemctl restart neo4j

# Wait for startup
sleep 10

# Test connectivity
curl -s http://localhost:7474/db/data/ | jq
```

### 2. Check Neo4j Health
```bash
# Check database status
neo4j-admin check

# Clear cache if safe
cypher-shell "CALL db.procedure()" -u neo4j -p password
```

### 3. Requeue Failed Jobs
```bash
# Mark failed projection jobs for retry
psql -c "UPDATE graph_projection_jobs SET status = 'pending' WHERE status = 'failed' AND created_at > NOW() - INTERVAL '1 hour';"

# Monitor retry progress
watch psql -c "SELECT status, COUNT(*) FROM graph_projection_jobs WHERE created_at > NOW() - INTERVAL '1 hour' GROUP BY status;"
```

## Prevention

1. Monitor disk space for Neo4j
2. Monitor heap memory usage
3. Set up automated backups
4. Monitor query performance

## Verification

- [ ] Neo4j responding to queries
- [ ] Graph projections completing
- [ ] Attack paths generating correctly
