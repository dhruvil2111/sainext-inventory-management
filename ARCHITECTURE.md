# Sainext — Architecture, Database Schema & Development Plan

Sainext is a production-grade web PWA for inventory, stock checking, material
blocking, order approval, dealer/salesman dashboards, and role-permission
management. It is built for internal business use and dealer/salesman workflows
and replaces manual stock checking and order handling with a web dashboard.

This document is the single source of truth for the system design. It covers the
architecture, the complete data model, the non-negotiable business rules (stock
ledger, old-stock-first allocation, partial ordering, approval-based commit), and
the phased delivery plan.

---

## 1. Technology Stack

| Layer | Choice | Notes |
|-------|--------|-------|
| Frontend | React 18 + TypeScript + Vite | PWA (manifest + service worker), responsive desktop/tablet/mobile |
| Styling | Tailwind CSS + CSS variable theme | Global theme tokens, dark/light ready |
| State/data | React Context + TanStack Query | Auth context, permission hooks, server-cache |
| Backend | FastAPI (Python 3.11) | Auto OpenAPI docs at `/api/docs` |
| ORM | SQLAlchemy 2.0 | Declarative models, transactional stock ops |
| Database | PostgreSQL 16 | Normalized schema |
| Auth | JWT (access token) | OAuth2 password flow, bcrypt hashing |
| Cache/Queue | Redis | Background worker broker |
| Background jobs | Worker process | Auto-release of expired blocks |
| DevOps | Docker Compose | `db`, `redis`, `backend`, `worker`, `frontend` |

The full system runs locally with `docker compose up`.

---

## 2. High-Level Architecture

```
                         ┌──────────────────────────┐
                         │   React + TS PWA (Vite)   │
                         │  theme · RBAC route guard │
                         │  permission-based UI       │
                         └─────────────┬─────────────┘
                                       │ HTTPS / JWT
                                       ▼
                         ┌──────────────────────────┐
                         │       FastAPI API         │
                         │  auth · permission deps   │
                         │  services (ledger, reco)  │
                         └───────┬───────────┬───────┘
                                 │           │
                     ┌───────────▼──┐   ┌────▼──────────┐
                     │ PostgreSQL   │   │  Redis broker │
                     │ source of    │   └────┬──────────┘
                     │ truth        │        │
                     └──────────────┘   ┌────▼──────────┐
                                        │  Worker        │
                                        │ expire blocks  │
                                        └───────────────┘
```

Key architectural principles:

- **Backend is the source of truth.** Stock is never computed only on the
  frontend. All stock mutations happen inside database transactions.
- **Two-layer permission enforcement.** The frontend hides menus and buttons by
  permission; the backend independently enforces every permission on every
  endpoint. Frontend hiding alone is never sufficient.
- **Append-only stock ledger.** Stock is never silently overwritten. Every
  change is a ledger transaction with before/after quantities.
- **Service layer for business logic.** Ledger posting, saleable-stock
  computation, and the recommendation engine live in reusable services, not in
  route handlers.

---

## 3. Roles & Permission Model

Roles are dynamic (stored in the database, editable by Owner/Admin), but the
system seeds sensible defaults: **Owner, Admin, Manager, Operator, Salesman,
Dealer/Partner, Dispatch Team, Accounts Team, Telecaller.**

Permissions are `(module, action)` pairs. Actions include: `view, create, edit,
delete, approve, reject, export, print, block_stock, release_stock,
convert_block_to_order, view_price, view_batch_details, view_reports,
manage_users, manage_permissions`.

Modules: `Dashboard, Users, Roles & Permissions, Warehouses, Products, Stock
Inward, Stock Check, Stock Blocking, Orders, Dealers, Salesman Dashboard,
Dispatch, Accounts, Reports, Settings`.

Effective permissions for a user = role permissions ± per-user overrides
(`user_permission_overrides`, where `allow` can grant or revoke a single
permission). The backend resolves effective permissions once per request.

---

## 4. Database Schema (ERD)

```
roles ─┐
       ├─< role_permissions >─ permissions
users ─┤
       ├─< user_permission_overrides >─ permissions
       ├─ assigned_warehouse → warehouses
       └─< audit_logs

warehouses ─< stock_items
products   ─< stock_items ─< stock_ledger
products   ─< batches ─< stock_items
stock_items ─< order_allocations
stock_items ─< stock_block_items

dealers ─< salesman_dealer_mapping >─ users(salesman)
dealers ─< orders ─< order_items ─< order_allocations
dealers ─< stock_blocks ─< stock_block_items
orders  ─ dispatch_records
dealers ─< payment_records
settings (singleton-ish key/value)
```

### Core tables

**roles** — `id, name (unique), description, is_system, created_at, updated_at`

**permissions** — `id, module, action, code (module:action, unique),
description`

**role_permissions** — `role_id, permission_id` (composite PK)

**user_permission_overrides** — `id, user_id, permission_id, allow (bool)` —
overrides role default for a single permission.

**users** — `id, name, email (unique), mobile, password_hash, role_id, status
(active/inactive/suspended), assigned_warehouse_id?, created_at, updated_at`.

**warehouses** — `id, name, code (unique), location, address, status, created_by,
created_at, updated_at`.

**product_categories** — `id, name, description`.

**products** — `id, pattern_no, product_code (unique design code), name,
collection_name, brand, category_id?, product_type (ROLL/BOX/LOOSE/BATCH), unit
(SQM/SQFT/MTR/BOX/PCS…), unit_size, thickness, roll_size, standard_roll_qty,
price, status (CONTINUED/DISCONTINUED), remarks, is_active, created_at`.

**batches** — `id, product_id, batch_no, batch_date, remarks` (a logical lot;
roll/box detail lives on stock_items).

**stock_items** — physical unit of stock. `id, product_id, warehouse_id,
batch_id?, item_type (ROLL/BOX/LOOSE), roll_no?, box_count?, roll_date?,
inward_date, purchase_date?, original_qty, available_qty, unit, status, remarks,
created_by, created_at`. `available_qty` is a denormalized convenience kept in
sync transactionally with the ledger; the ledger remains authoritative.

**stock_ledger** — append-only. `id, product_id, warehouse_id, batch_id?,
stock_item_id?, txn_type (INWARD/OUTWARD/BLOCK/BLOCK_RELEASE/ORDER_COMMIT/
ORDER_CANCEL_RELEASE/TRANSFER_IN/TRANSFER_OUT/ADJUSTMENT_IN/ADJUSTMENT_OUT/
DAMAGE/RETURN_IN), qty, before_qty, after_qty, ref_type?, ref_id?, created_by,
created_at, remarks`.

### Blocking

**stock_blocks** — `id, block_no, dealer_id?, salesman_id?, product_id,
required_qty, hold_until (expiry), status (DRAFT/PENDING_APPROVAL/APPROVED/
REJECTED/RELEASED/EXPIRED/CONVERTED), approved_by?, approved_at?, remarks,
created_by, created_at`.

**stock_block_items** — `id, block_id, stock_item_id, warehouse_id, batch_id?,
qty`.

### Orders

**orders** — `id, order_no, dealer_id, salesman_id?, status (DRAFT/
PENDING_APPROVAL/APPROVED/BLOCKED/IN_PROCESS/READY_FOR_DISPATCH/DISPATCHED/
COMPLETED/CANCELLED/REJECTED/PRE_ORDER), total_amount, is_partial,
stock_committed (bool), source_block_id?, approved_by?, dispatch_by?, remarks,
created_by, created_at`.

**order_items** — `id, order_id, product_id, qty, unit, price, amount,
product_snapshot (JSON)`.

**order_allocations** — `id, order_item_id, stock_item_id, warehouse_id,
batch_id?, roll_no?, alloc_qty, wastage_qty, is_full_roll, same_batch`.

### Dealers / dispatch / accounts

**dealers** — `id, firm_name, owner_name, concern_person, contact, alt_contact,
address, gst_no, assigned_salesman_id?, category, credit_period_days, rating,
price_list_access, offer_letter_access, status, login_user_id?, created_at`.

**salesman_dealer_mapping** — `id, salesman_id, dealer_id` (a dealer maps to one
salesman; table allows history/override).

**dispatch_records** — `id, order_id, status, notes, transport_details,
dispatched_by?, dispatched_at, created_at`.

**payment_records** — `id, dealer_id, order_id?, amount, type (DUE/PAYMENT),
due_date?, paid_at?, remarks, created_at`.

### Cross-cutting

**audit_logs** — `id, user_id?, module, action, record_type, record_id,
old_value (JSON), new_value (JSON), created_at`.

**settings** — `id, key (unique), value (JSON), updated_at`.

---

## 5. Stock Ledger Rules (mandatory)

Every stock change is recorded as a ledger transaction carrying `before_qty` and
`after_qty`. Stock is **never** overwritten without a ledger entry.

```
Actual Stock  = Σ(INWARD, RETURN_IN, ADJUSTMENT_IN, TRANSFER_IN)
              − Σ(OUTWARD, DAMAGE, ADJUSTMENT_OUT, TRANSFER_OUT)

Saleable Stock = Actual Stock
               − Approved Blocked Stock
               − Approved/Committed Order Stock
```

- **Pending** blocks do **not** reduce saleable stock.
- **Approved** blocks reduce saleable stock.
- **Approved/committed** orders reduce/commit stock.
- **Expired** blocks auto-release (background worker) and restore availability.

All commit/block/release operations run inside a single DB transaction. Stock is
validated before approval; overselling and double-deduction are prevented;
negative saleable stock is disallowed unless an explicit admin adjustment.

---

## 6. Old-Stock-First Allocation & Recommendation Engine

A reusable backend service (`services/recommendation.py`) suggests allocations
when a user enters a required quantity.

Sorting parameters for "old stock first": batch_date → roll_date → inward_date →
purchase_date → stock entry (created_at).

**Priority order**

1. Fulfil the required quantity exactly if possible.
2. Minimum wastage.
3. Old stock first.
4. Same batch.
5. Same warehouse.
6. Mixed batch only when needed.

**Case 1 — required < one roll:** prefer loose material, oldest stock, the
nearest available quantity ≥ required, same batch — to minimise wastage.

**Case 2 — required > one roll:** suggest combinations of full rolls + loose
rolls, preferring same-batch combinations, with different-batch fallback. Each
suggestion shows full/loose flag, same/different batch flag, warehouse, batch,
roll no, quantity, remaining, and wastage.

**Partial ordering:** a roll of 50m can be ordered as 5/10/25/50m. The cut
quantity is recorded as an allocation; remaining quantity stays available as
loose/remaining stock. The system tracks original, ordered/cut, remaining, and
wastage quantities.

---

## 7. Order & Block Lifecycles

**Block:** DRAFT → PENDING_APPROVAL → APPROVED → (RELEASED | EXPIRED |
CONVERTED). REJECTED is terminal from PENDING_APPROVAL.

**Order:** DRAFT → PENDING_APPROVAL → APPROVED → IN_PROCESS →
READY_FOR_DISPATCH → DISPATCHED → COMPLETED. CANCELLED/REJECTED are terminal.
**Stock is committed at the APPROVED stage.** Dispatch/invoice updates status but
never deducts stock a second time.

---

## 8. API Surface (REST, prefix `/api`)

Auth: `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`.
Roles/perms: `GET/POST /roles`, `PUT /roles/{id}`, `GET /permissions`,
`PUT /roles/{id}/permissions`.
Warehouses: `GET/POST /warehouses`, `PUT/DELETE /warehouses/{id}`.
Products: `GET/POST /products`, `PUT /products/{id}`, `GET /products/search`.
Stock: `POST /stock/inward`, `/adjustment`, `/transfer`; `GET /stock/check`,
`/stock/batches`, `/stock/ledger`; `POST /stock/recommendation`.
Blocks: `GET/POST /blocks`, `POST /blocks/{id}/{approve|reject|release|extend|
convert-to-order}`.
Orders: `GET/POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/{approve|
reject|cancel|in-process|ready-for-dispatch|dispatched|completed}`.
Dealers: `GET/POST /dealers`, `PUT /dealers/{id}`, `GET /dealers/{id}/dashboard`.
Reports: `GET /reports/{stock|blocks|orders|dispatch|payments}` + export.

All list endpoints are paginated and filterable. Every mutating endpoint is
guarded by a permission dependency and writes an audit log for important actions.

---

## 9. Phased Delivery Plan — all phases complete ✅

- **Phase 1 ✅:** project setup, Docker Compose, JWT auth, roles & permissions
  (matrix UI + per-user overrides + backend enforcement), global theme,
  dashboard shell, users management, seed data. Full DB schema created up front.
- **Phase 2 ✅:** warehouse management, product master (+ categories), stock
  inward (all entry types), transactional stock ledger.
- **Phase 3 ✅:** stock check, batch/roll/box detail, warehouse-wise
  availability with green/red/yellow status, price/batch permission visibility,
  View Batch modal.
- **Phase 4 ✅:** recommendation engine — old-stock-first, partial-roll
  allocation, minimum-wastage single & combination suggestions.
- **Phase 5 ✅:** material blocking — create/approve/reject/release/extend,
  expiry auto-release worker, convert-to-order.
- **Phase 6 ✅:** order management, approval-based stock commit, cancel/release,
  full dispatch lifecycle (no double deduction), order history.
- **Phase 7 ✅:** dealer/vendor management with salesman scoping, salesman &
  accounts dashboards, payments, reports for 6 domains with CSV/XLSX export and
  print.
- **Phase 8 ✅:** Settings (company + live brand theme), seed refinement,
  committed pytest suite, deployment documentation (`DEPLOYMENT.md`).

---

## 10. Brand & Theme

Primary deep charcoal/navy, accent golden yellow/orange, success green, danger
red, neutral grey/white — all configurable from a single theme file
(`frontend/src/theme/theme.css` CSS variables, mirrored in Tailwind config).
Availability indicators: green = available, red = not available, yellow =
partial/blocked/warning.
