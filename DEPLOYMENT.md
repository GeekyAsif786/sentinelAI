# Deployment

## Local Stack

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Frontend: `http://localhost:5173`
- PostgreSQL: `localhost:5432`
- Neo4j browser: `http://localhost:7474`
- Redis: `localhost:6379`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Configuration

Required production settings:

- `DATABASE_URL`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`
- `REDIS_URL`
- `JWT_SECRET_KEY`
- `AI_ENABLED`

Do not commit production secrets. Use platform secret management.

## Production Notes

- Run API and workers separately.
- Run one scheduler instance.
- Use managed PostgreSQL, Neo4j, and Redis where possible.
- Restrict scanner workers to authorized network segments.
- Keep scan policies mandatory for scheduled and manual scans.
- Monitor API latency, queue depth, scan duration, graph size, graph freshness, and AI provider latency.

