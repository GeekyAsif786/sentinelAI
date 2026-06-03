# Staging Deployment Quick Reference

## Current Status: ✅ ALL SERVICES RUNNING

**Deployment Time:** 2026-06-03 18:49:30 UTC  
**Method:** Docker Compose

---

## Quick Service Access

```
API (Uvicorn)      → http://localhost:8000
API Health         → http://localhost:8000/health
API Docs (Swagger) → http://localhost:8000/docs
Frontend (Vite)    → http://localhost:5173
Prometheus         → http://localhost:9090
Grafana            → http://localhost:3000
Neo4j Browser      → http://localhost:7474
```

---

## Service Status

| Service | Port | Status | Command |
|---------|------|--------|---------|
| Redis | 6379 | ✅ Running | `docker-compose ps redis` |
| PostgreSQL | 5432 | ✅ Running | `docker-compose ps postgres` |
| Celery Worker | - | ✅ Ready | `docker-compose ps worker` |
| API | 8000 | ✅ Running | `docker-compose ps api` |
| Neo4j | 7687 | ✅ Running | `docker-compose ps neo4j` |
| Prometheus | 9090 | ✅ Running | `docker-compose ps prometheus` |
| Grafana | 3000 | ✅ Running | `docker-compose ps grafana` |
| Frontend | 5173 | ✅ Running | `docker-compose ps frontend` |

---

## Essential Commands

### View Status
```bash
docker-compose ps                    # All services
docker-compose ps [service]          # Specific service
```

### View Logs
```bash
docker-compose logs -f               # All services (follow)
docker-compose logs -f api           # API only
docker-compose logs -f worker        # Worker only
docker-compose logs --tail=100       # Last 100 lines
```

### Restart Services
```bash
docker-compose restart               # All services
docker-compose restart api           # API only
docker-compose restart worker        # Worker only
```

### Database Access
```bash
docker-compose exec postgres psql -U sentinel -d sentinel
# or
psql -h localhost -U sentinel -d sentinel
# Password: sentinel
```

### Execute Commands
```bash
docker-compose exec api python3 -c "import app; print(app.__version__)"
docker-compose exec worker celery -A app.worker inspect active
```

---

## Stopping Services

### Stop All Services
```bash
cd /Users/asif/SentinelAI
docker-compose down
```

### Stop and Remove Volumes (Full Cleanup)
```bash
cd /Users/asif/SentinelAI
docker-compose down -v
```

### Stop and Remove Images
```bash
cd /Users/asif/SentinelAI
docker-compose down --remove-orphans --rmi all
```

---

## Restarting Services

### Restart All
```bash
cd /Users/asif/SentinelAI
docker-compose restart
```

### Restart Specific Service
```bash
docker-compose restart api
docker-compose restart worker
docker-compose restart postgres
```

---

## Health Checks

```bash
# Redis
docker-compose exec redis redis-cli ping

# PostgreSQL
docker-compose exec postgres psql -U sentinel -d sentinel -c "SELECT 1;"

# API
curl http://localhost:8000/health

# Celery Worker
docker-compose exec worker celery -A app.worker inspect active_queues
```

---

## Common Issues & Solutions

### Service Not Responding
```bash
docker-compose ps                    # Check status
docker-compose logs -f [service]     # Check logs
docker-compose restart [service]     # Restart
```

### Database Connection Error
```bash
docker-compose exec postgres psql -U sentinel -d sentinel -c "SELECT NOW();"
```

### Celery Worker Not Accepting Tasks
```bash
docker-compose logs -f worker
docker-compose restart worker
```

### Port Already in Use
```bash
# Identify what's using the port
lsof -i :8000

# Or just restart Docker Compose
docker-compose down && docker-compose up -d
```

---

## Performance Monitoring

```bash
# Docker resource usage
docker stats

# Service logs with timestamps
docker-compose logs -f --timestamps

# Prometheus metrics
curl http://localhost:9090/api/v1/query?query=up
```

---

## Database Operations

### Backup Database
```bash
docker-compose exec postgres pg_dump -U sentinel sentinel > backup.sql
```

### List Database Tables
```bash
docker-compose exec postgres psql -U sentinel -d sentinel -c "\dt"
```

### Check Database Size
```bash
docker-compose exec postgres psql -U sentinel -d sentinel -c "
  SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
  FROM pg_tables WHERE schemaname = 'public' ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"
```

---

## Task Queue Operations

### Active Tasks
```bash
docker-compose exec worker celery -A app.worker inspect active
```

### Worker Stats
```bash
docker-compose exec worker celery -A app.worker inspect stats
```

### Registered Tasks
```bash
docker-compose exec worker celery -A app.worker inspect registered
```

### Queue Status
```bash
docker-compose exec worker celery -A app.worker inspect active_queues
```

---

## Rebuilding Services

### Rebuild All Images
```bash
docker-compose build --no-cache
```

### Rebuild Specific Service
```bash
docker-compose build --no-cache api
docker-compose build --no-cache worker
```

### Rebuild and Restart
```bash
docker-compose up -d --build
```

---

## Clean Up

### Remove Stopped Containers
```bash
docker container prune
```

### Remove Unused Networks
```bash
docker network prune
```

### Remove Unused Volumes
```bash
docker volume prune
```

### Full Cleanup
```bash
docker system prune -a
```

---

## Environment Variables

Located in `docker-compose.yml`:

- **DATABASE_URL:** `postgresql+psycopg://sentinel:sentinel@postgres:5432/sentinel`
- **NEO4J_URI:** `bolt://neo4j:7687`
- **NEO4J_AUTH:** `neo4j/sentinelpassword`
- **REDIS_URL:** `redis://redis:6379/0`
- **JWT_SECRET_KEY:** `local-development-change-me`
- **AI_ENABLED:** `false`

---

## Files & Directories

```
/Users/asif/SentinelAI/
├── docker-compose.yml          # Main orchestration file
├── backend/
│   ├── Dockerfile              # API & Worker image
│   ├── app/
│   │   ├── main.py             # Flask app entry
│   │   ├── worker.py           # Celery worker config
│   │   └── tasks.py            # Task definitions
│   ├── alembic/                # Database migrations
│   └── tests/                  # Test suite
├── frontend/                   # Vite React app
├── infra/
│   ├── prometheus/             # Prometheus config
│   └── grafana/                # Grafana provisioning
└── docs/                       # Documentation
```

---

## Resources

- **Docker Docs:** https://docs.docker.com/
- **Docker Compose:** https://docs.docker.com/compose/
- **Celery:** https://docs.celeryproject.io/
- **PostgreSQL:** https://www.postgresql.org/docs/
- **Redis:** https://redis.io/documentation
- **Neo4j:** https://neo4j.com/docs/

---

**Last Updated:** 2026-06-03T18:50:10Z
