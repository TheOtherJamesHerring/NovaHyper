# NovaHyper v0.2

NovaHyper is an MSP hypervisor platform backend built with FastAPI, SQLAlchemy, PostgreSQL, NATS, and a small frontend dev environment.

## Stack

- FastAPI API backend
- PostgreSQL and Alembic migrations
- NATS JetStream workers
- Docker Compose development environment
- Vite frontend
- Prometheus and Grafana for observability

## Run locally

```bash
docker compose up --build
```

API: http://localhost:8000

Frontend: http://localhost:5173

## Notes

- This repository is prepared from the NovaHyper workspace as version v0.2.
- Local secrets such as `.env` are excluded from version control.