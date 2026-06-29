# Sainext

Production-grade web PWA for inventory, stock checking, material blocking, order
approval, dealer/salesman dashboards, and role-permission management.

This repository contains **Phase 1** of the phased build defined in
[`ARCHITECTURE.md`](./ARCHITECTURE.md): project setup, JWT auth, dynamic
roles & permissions (with a matrix UI and server-side enforcement), the global
theme/design system, the dashboard shell, user management, warehouse management,
the complete database schema for the whole system, and seed data. Later phases
(stock check, recommendation engine, blocking, orders, dispatch, accounts,
reports) plug into the model and navigation that are already wired up.

## Stack

- **Frontend:** React 18 + TypeScript + Vite, Tailwind CSS, PWA, TanStack Query
- **Backend:** FastAPI + SQLAlchemy 2.0, JWT auth, role/permission middleware
- **Database:** PostgreSQL 16
- **Cache/Queue:** Redis + a background worker (auto-releases expired blocks)
- **DevOps:** Docker Compose

## Run it (one command)

```bash
cd sainext-app
docker compose up --build
```

Then open:

- Frontend (PWA): http://localhost:5173
- API docs (Swagger): http://localhost:8000/api/docs
- Health check: http://localhost:8000/api/health

The backend creates all tables and seeds default data on first startup.

## Demo accounts

| Role | Email | Password |
|------|-------|----------|
| Owner | owner@sainext.app | Owner@123 |
| Admin | admin@sainext.app | Admin@123 |
| Manager | manager@sainext.app | Manager@123 |
| Operator | operator@sainext.app | Operator@123 |
| Salesman | salesman@sainext.app | Sales@123 |
| Dispatch Team | dispatch@sainext.app | Dispatch@123 |
| Accounts Team | accounts@sainext.app | Accounts@123 |

Sign in as different roles to see permission-based menu and button visibility.
The Owner sees everything; a Salesman sees only stock check, blocking, orders,
dealers, and their dashboard.

> Change `JWT_SECRET` and all seeded passwords before any non-local use.

## Local development without Docker

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# point DATABASE_URL at a running Postgres (or use sqlite for a quick spin:
# export DATABASE_URL="sqlite:///./sainext.db")
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to localhost:8000
```

## Project layout

```
sainext-app/
├── ARCHITECTURE.md          # design, full schema, business rules, dev plan
├── docker-compose.yml
├── backend/
│   └── app/
│       ├── core/            # config, db, security, deps, constants
│       ├── models/          # full SQLAlchemy schema + enums
│       ├── schemas/         # Pydantic request/response models
│       ├── services/        # permissions, audit (+ ledger/reco in later phases)
│       ├── api/routes/      # auth, users, roles, permissions, warehouses, dashboard
│       ├── workers/         # expired-block auto-release worker
│       ├── seed.py          # idempotent seed
│       └── main.py
└── frontend/
    └── src/
        ├── theme/           # global CSS-variable theme (charcoal + gold)
        ├── components/ui/   # button, card, badge, modal, table, toast, etc.
        ├── components/layout/  # sidebar, drawer, guards, page header
        ├── context/         # auth + toast
        ├── lib/             # api client, navigation model
        └── pages/           # login, dashboard, users, roles, warehouses, ...
```

## Security model

Permissions are `(module, action)` pairs resolved per request as
`role permissions ± per-user overrides`. The **frontend** hides menu items and
action buttons the user can't use; the **backend** independently enforces every
permission via a `require_permission(code)` dependency on each endpoint. Frontend
hiding alone is never trusted. The Owner role implicitly has all permissions.

## Core rules already encoded (for later phases)

- **Append-only stock ledger** with before/after quantities and all transaction
  types (INWARD, OUTWARD, BLOCK, BLOCK_RELEASE, ORDER_COMMIT, …). The seed posts
  INWARD ledger entries for all demo stock.
- **Saleable stock** = actual − approved blocks − committed orders. Pending
  blocks do not reduce saleable stock.
- **Expired blocks auto-release** via the `worker` service.
- Schema supports **old-stock-first allocation** (batch/roll/inward/purchase
  dates), **partial roll ordering** (original/cut/remaining/wastage on
  `order_allocations`), and **approval-based commit** (`orders.stock_committed`).

See `ARCHITECTURE.md` §5–§9 for the full rules and the recommendation engine
design.
