# Sainext — Deployment Guide

This covers running Sainext locally and deploying it to a server. The stack is
Postgres + Redis + a FastAPI backend + a background worker + a React/Vite PWA,
orchestrated with Docker Compose.

## 1. Local development

```bash
cd sainext-app
docker compose up --build
```

- Frontend (PWA): http://localhost:5173
- API docs (Swagger): http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health

The backend creates all tables and seeds demo data on first start. The frontend
source is bind-mounted, so edits hot-reload. Backend changes need a rebuild:

```bash
docker compose up -d --build backend worker
```

Demo logins (change before any non-local use):

| Role | Email | Password |
|------|-------|----------|
| Owner | owner@sainext.app | Owner@123 |
| Admin | admin@sainext.app | Admin@123 |
| Manager | manager@sainext.app | Manager@123 |
| Operator | operator@sainext.app | Operator@123 |
| Salesman | salesman@sainext.app | Sales@123 |
| Dispatch | dispatch@sainext.app | Dispatch@123 |
| Accounts | accounts@sainext.app | Accounts@123 |

## 2. Environment variables (backend)

| Var | Purpose | Production guidance |
|-----|---------|---------------------|
| `DATABASE_URL` | Postgres DSN | managed Postgres, not the compose container |
| `JWT_SECRET` | token signing key | **set a strong 32+ char random secret** |
| `JWT_ALGORITHM` | default HS256 | leave as is |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | session length | tune to policy (default 480) |
| `REDIS_URL` | worker broker | managed Redis |
| `CORS_ORIGINS` | allowed web origins | set to your real frontend URL(s) |
| `SEED_ON_STARTUP` | seed demo data | **set `false` in production** |

Frontend build-time vars: `VITE_API_BASE` (default `/api`) and
`VITE_PROXY_TARGET` (dev proxy target; in compose it's `http://backend:8000`).

## 3. Production checklist

1. **Secrets:** set a strong `JWT_SECRET`; rotate all seeded passwords (or seed
   with `SEED_ON_STARTUP=false` and create the first Owner manually).
2. **Database:** point `DATABASE_URL` at managed Postgres with backups. The app
   uses `create_all` plus a small idempotent column migration on startup; for a
   long-lived production system, adopt Alembic migrations before schema changes.
3. **Disable demo seed:** `SEED_ON_STARTUP=false`.
4. **CORS:** restrict `CORS_ORIGINS` to your frontend domain(s).
5. **Frontend build:** serve the built assets (`npm run build` → static host /
   CDN) rather than the Vite dev server. Point it at the backend via a reverse
   proxy so `/api` reaches FastAPI.
6. **TLS:** terminate HTTPS at a reverse proxy (nginx/Caddy/Traefik) in front of
   both the static frontend and the API.
7. **Worker:** keep the `worker` service running — it auto-releases expired
   stock blocks every 60s.
8. **Scaling:** run the API with multiple uvicorn/gunicorn workers behind the
   proxy; the DB is the source of truth and all stock mutations are
   transactional, so horizontal scaling is safe.

## 4. Building the frontend for production

```bash
cd frontend
npm install
npm run build      # outputs to dist/
npm run preview    # local preview of the production build
```

Serve `dist/` from any static host. Ensure requests to `/api/*` are proxied to
the backend.

## 5. Running tests

```bash
cd backend
pip install -r requirements.txt
pytest             # runs against an isolated SQLite DB, no Postgres needed
```

## 6. Backups & data

- Postgres holds all business data; back it up regularly.
- The stock ledger is append-only and is the audit source of truth for stock.
- `audit_logs` records who changed what across modules.
