# SentinelAI

SentinelAI is a defensive security analytics platform for turning network scan data into asset inventory, vulnerability context, graph analysis, MITRE ATT&CK mappings, and evidence-grounded security explanations.

The project is intentionally defensive. It does not generate exploits, create payloads, harvest credentials, or execute attacks.

## Current Implementation

This repository now contains a production-oriented foundation:

- FastAPI backend scaffold with health, scan, asset, graph, vulnerability, attack-path, and analysis routes.
- Typed discovery provider abstraction with Nmap XML ingestion.
- Deterministic composite risk scoring that combines CVSS, EPSS, exposure, and asset criticality.
- In-memory graph algorithms for BFS, DFS, Dijkstra-style weighted paths, critical nodes, and choke points.
- MITRE ATT&CK rule mapping for defensive findings.
- AI analyst abstraction that is disabled by default and returns bounded deterministic explanations unless configured.
- React + TypeScript + Vite dashboard skeleton with asset, risk, graph, timeline, and AI panels.
- Docker Compose for API, worker placeholder, frontend, PostgreSQL, Neo4j, Redis, Prometheus, and Grafana.
- Documentation for architecture, API, deployment, graph model, security model, attack-path engine, and safety boundaries.

## Repository Layout

```text
backend/        FastAPI application, domain services, and tests
frontend/       React + TypeScript dashboard
docs/           Production and open-source readiness documentation
infra/          Prometheus and Grafana local configuration
docker-compose.yml
```

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Full local stack:

```bash
docker compose up --build
```

## Verification

Pure domain tests can run without external services:

```bash
cd backend
python -m pytest
```

The Docker stack is the intended path for validating PostgreSQL, Neo4j, Redis, Prometheus, and Grafana connectivity.

## Safety Boundaries

Allowed:

- Asset discovery ingestion.
- Inventory normalization.
- Risk scoring.
- Graph and attack-path analysis for defensive planning.
- MITRE ATT&CK mapping.
- Security explanations and remediation guidance.

Not allowed:

- Exploit generation.
- Payload generation.
- Automated exploitation.
- Credential abuse.
- Offensive command generation.
- Weaponization features.

