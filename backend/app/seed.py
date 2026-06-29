"""Idempotent seed: permissions matrix, default roles, users, demo stock.

Run automatically on startup (SEED_ON_STARTUP) or manually:  python -m app.seed
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.core.database import SessionLocal, Base, engine
from app.core.security import hash_password
from app.core.constants import MODULE_ACTIONS, DEFAULT_ROLES
from app.models import (
    Role, Permission, RolePermission, User, Warehouse, Product, Batch,
    StockItem, StockLedger, Dealer, ProductCategory,
)
from app.models.enums import (
    ProductType, ProductStatus, StockItemType, LedgerTxnType, UserStatus,
)

# Per-role permission policy. Owner is implicitly all-access (handled in code).
ROLE_POLICY = {
    "Admin": "ALL_EXCEPT_OWNER_ONLY",
    "Manager": [
        "Dashboard:view", "Users:view", "Warehouses:view", "Products:view",
        "Products:view_price", "Stock Inward:view", "Stock Inward:create",
        "Stock Check:view", "Stock Check:view_price", "Stock Check:view_batch_details",
        "Stock Check:export", "Stock Check:print",
        "Stock Blocking:view", "Stock Blocking:create", "Stock Blocking:approve",
        "Stock Blocking:reject", "Stock Blocking:block_stock", "Stock Blocking:release_stock",
        "Stock Blocking:convert_block_to_order",
        "Orders:view", "Orders:create", "Orders:approve", "Orders:reject",
        "Dealers:view", "Dealers:view_price", "Salesman Dashboard:view",
        "Dispatch:view", "Accounts:view", "Reports:view", "Reports:view_reports",
        "Reports:export", "Reports:print", "Settings:view",
    ],
    "Operator": [
        "Dashboard:view", "Warehouses:view", "Products:view",
        "Stock Inward:view", "Stock Inward:create", "Stock Inward:edit",
        "Stock Check:view", "Stock Check:view_batch_details",
        "Stock Blocking:view", "Stock Blocking:create", "Stock Blocking:approve",
        "Stock Blocking:block_stock", "Stock Blocking:release_stock",
        "Orders:view", "Orders:create",
    ],
    "Salesman": [
        "Dashboard:view", "Products:view",
        "Stock Check:view", "Stock Check:view_price", "Stock Check:view_batch_details",
        "Stock Blocking:view", "Stock Blocking:create", "Stock Blocking:block_stock",
        "Orders:view", "Orders:create",
        "Dealers:view", "Dealers:create", "Dealers:edit", "Dealers:view_price",
        "Salesman Dashboard:view", "Reports:view",
    ],
    "Dealer/Partner": [
        "Dashboard:view", "Stock Check:view", "Stock Check:view_price",
        "Stock Check:view_batch_details", "Orders:view", "Orders:create",
        "Salesman Dashboard:view",
    ],
    "Dispatch Team": [
        "Dashboard:view", "Orders:view", "Dispatch:view", "Dispatch:edit",
        "Stock Check:view",
    ],
    "Accounts Team": [
        "Dashboard:view", "Accounts:view", "Accounts:edit", "Accounts:export",
        "Dealers:view", "Orders:view", "Reports:view", "Reports:view_reports",
        "Reports:export",
    ],
    "Telecaller": [
        "Dashboard:view", "Stock Check:view", "Dealers:view", "Orders:view",
    ],
}


def seed_permissions(db):
    existing = {p.code for p in db.execute(select(Permission)).scalars().all()}
    for module, actions in MODULE_ACTIONS.items():
        for action in actions:
            code = f"{module}:{action}"
            if code not in existing:
                db.add(Permission(module=module, action=action, code=code,
                                  description=f"{action} on {module}"))
    db.commit()


def all_codes(db):
    return [p.code for p in db.execute(select(Permission)).scalars().all()]


def seed_roles(db):
    codes = all_codes(db)
    code_to_id = {p.code: p.id for p in db.execute(select(Permission)).scalars().all()}
    for name in DEFAULT_ROLES:
        role = db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()
        if not role:
            role = Role(name=name, description=f"{name} role", is_system=True)
            db.add(role)
            db.flush()
        # Resolve policy
        if name == "Owner":
            wanted = []  # Owner is implicit-all; no rows needed
        elif ROLE_POLICY.get(name) == "ALL_EXCEPT_OWNER_ONLY":
            wanted = [c for c in codes if c != "Roles & Permissions:manage_permissions"] + \
                     ["Roles & Permissions:manage_permissions"]
        else:
            wanted = ROLE_POLICY.get(name, [])
        # Only set if role currently has no permission rows (don't clobber edits)
        has_any = db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        ).first()
        if not has_any and wanted:
            for c in wanted:
                if c in code_to_id:
                    db.add(RolePermission(role_id=role.id, permission_id=code_to_id[c]))
    db.commit()


def seed_users(db):
    def ensure(email, name, role_name, pw, mobile=None, wh_code=None):
        if db.execute(select(User).where(User.email == email)).scalar_one_or_none():
            return
        role = db.execute(select(Role).where(Role.name == role_name)).scalar_one()
        wh = None
        if wh_code:
            wh = db.execute(select(Warehouse).where(Warehouse.code == wh_code)).scalar_one_or_none()
        db.add(User(name=name, email=email, mobile=mobile, role_id=role.id,
                    password_hash=hash_password(pw), status=UserStatus.active,
                    assigned_warehouse_id=wh.id if wh else None))
    ensure("owner@sainext.app", "System Owner", "Owner", "Owner@123", "9000000001")
    ensure("admin@sainext.app", "Admin User", "Admin", "Admin@123", "9000000002")
    ensure("manager@sainext.app", "Warehouse Manager", "Manager", "Manager@123", "9000000003", "WH-A")
    ensure("operator@sainext.app", "Stock Operator", "Operator", "Operator@123", "9000000004", "WH-A")
    ensure("salesman@sainext.app", "Field Salesman", "Salesman", "Sales@123", "9000000005")
    ensure("dispatch@sainext.app", "Dispatch Lead", "Dispatch Team", "Dispatch@123", "9000000006")
    ensure("accounts@sainext.app", "Accounts Exec", "Accounts Team", "Accounts@123", "9000000007")
    db.commit()


def seed_warehouses(db):
    data = [
        ("Main Warehouse A", "WH-A", "Region 1"),
        ("Secondary Warehouse B", "WH-B", "Region 2"),
        ("Transit Hub C", "WH-C", "Region 3"),
    ]
    for name, code, loc in data:
        if not db.execute(select(Warehouse).where(Warehouse.code == code)).scalar_one_or_none():
            db.add(Warehouse(name=name, code=code, location=loc, address=f"{loc} address"))
    db.commit()


def seed_categories(db):
    cats = [
        ("Flooring", "Vinyl / laminate flooring"),
        ("Vinyl Rolls", "Roll-form vinyl material"),
        ("Carpet", "Carpet tiles and rolls"),
    ]
    for name, desc in cats:
        if not db.execute(select(ProductCategory).where(ProductCategory.name == name)).scalar_one_or_none():
            db.add(ProductCategory(name=name, description=desc))
    db.commit()


def seed_products(db):
    cat = {c.name: c.id for c in db.execute(select(ProductCategory)).scalars().all()}
    data = [
        dict(pattern_no="PF-111", product_code="LUX-PF-111", name="Flooring",
             collection_name="LUXORA-1.5MM", brand="Luxora", product_type=ProductType.BOX,
             unit="BOX", unit_size='1.5MM - 6"x36"x24 PCS = 36', thickness="1.5MM",
             standard_roll_qty=36, price=2400, category_id=cat.get("Flooring")),
        dict(pattern_no="PF-102", product_code="55440H/PF-102", name="Vinyl Roll",
             collection_name="PRIME-0.65", brand="Prime", product_type=ProductType.ROLL,
             unit="SQM", unit_size="2M x 30M", thickness="0.65MM", roll_size="2M x 30M",
             standard_roll_qty=60, price=520, category_id=cat.get("Vinyl Rolls")),
        dict(pattern_no="PF-205", product_code="LUX-PF-205", name="Carpet Tile",
             collection_name="SOFTSTEP", brand="SoftStep", product_type=ProductType.BOX,
             unit="BOX", unit_size='50x50cm x 20 PCS', thickness="6MM",
             standard_roll_qty=20, price=1800, category_id=cat.get("Carpet")),
    ]
    for d in data:
        if not db.execute(select(Product).where(Product.product_code == d["product_code"])).scalar_one_or_none():
            db.add(Product(status=ProductStatus.CONTINUED, is_active=True, **d))
    db.commit()


def _post_inward(db, item):
    """Create a stock_item and its INWARD ledger entry."""
    db.add(item)
    db.flush()
    db.add(StockLedger(
        product_id=item.product_id, warehouse_id=item.warehouse_id,
        batch_id=item.batch_id, stock_item_id=item.id,
        txn_type=LedgerTxnType.INWARD, qty=item.available_qty,
        before_qty=0, after_qty=item.available_qty, ref_type="seed",
        remarks="Seed inward",
    ))


def seed_stock(db):
    if db.execute(select(StockItem)).first():
        return  # already seeded
    wh = {w.code: w for w in db.execute(select(Warehouse)).scalars().all()}
    prod = {p.product_code: p for p in db.execute(select(Product)).scalars().all()}

    roll = prod["55440H/PF-102"]
    # two batches of the roll product, different dates -> old-stock-first demo
    b1 = Batch(product_id=roll.id, batch_no="24CA", batch_date=date(2024, 8, 3))
    b2 = Batch(product_id=roll.id, batch_no="25CB", batch_date=date(2025, 3, 25))
    db.add_all([b1, b2]); db.flush()
    _post_inward(db, StockItem(product_id=roll.id, warehouse_id=wh["WH-A"].id,
        batch_id=b1.id, item_type=StockItemType.ROLL, roll_no="18",
        roll_date=date(2024, 8, 3), inward_date=date(2024, 8, 5),
        original_qty=60, available_qty=60, unit="SQM"))
    _post_inward(db, StockItem(product_id=roll.id, warehouse_id=wh["WH-A"].id,
        batch_id=b1.id, item_type=StockItemType.LOOSE, roll_no="18A",
        roll_date=date(2024, 8, 3), inward_date=date(2024, 8, 5),
        original_qty=39, available_qty=39, unit="SQM"))
    _post_inward(db, StockItem(product_id=roll.id, warehouse_id=wh["WH-B"].id,
        batch_id=b2.id, item_type=StockItemType.ROLL, roll_no="32",
        roll_date=date(2025, 3, 25), inward_date=date(2025, 3, 27),
        original_qty=60, available_qty=48, unit="SQM"))

    box = prod["LUX-PF-111"]
    _post_inward(db, StockItem(product_id=box.id, warehouse_id=wh["WH-A"].id,
        item_type=StockItemType.BOX, box_count=150, inward_date=date(2025, 1, 10),
        original_qty=150, available_qty=150, unit="BOX"))
    _post_inward(db, StockItem(product_id=box.id, warehouse_id=wh["WH-B"].id,
        item_type=StockItemType.BOX, box_count=20, inward_date=date(2025, 2, 1),
        original_qty=20, available_qty=20, unit="BOX"))
    db.commit()


def seed_dealers(db):
    if db.execute(select(Dealer)).first():
        return
    salesman = db.execute(select(User).where(User.email == "salesman@sainext.app")).scalar_one_or_none()
    sid = salesman.id if salesman else None
    db.add_all([
        Dealer(firm_name="Sunrise Interiors", owner_name="R. Mehta",
               concern_person="R. Mehta", contact="9810000001",
               assigned_salesman_id=sid, category="Gold", credit_period_days=30,
               rating=4.5, price_list_access=True),
        Dealer(firm_name="Metro Decor House", owner_name="S. Khan",
               concern_person="A. Khan", contact="9810000002",
               assigned_salesman_id=sid, category="Silver", credit_period_days=15,
               rating=4.0),
    ])
    db.commit()


def seed_payments_and_targets(db):
    from app.models import PaymentRecord
    from app.models.enums import PaymentType
    # give the salesman a monthly target
    sm = db.execute(select(User).where(User.email == "salesman@sainext.app")).scalar_one_or_none()
    if sm and not sm.monthly_target:
        sm.monthly_target = 100000.0
    # seed a few dues/payments if none exist
    if not db.execute(select(PaymentRecord)).first():
        dealers = db.execute(select(Dealer)).scalars().all()
        for i, d in enumerate(dealers):
            db.add(PaymentRecord(dealer_id=d.id, amount=50000 + i * 10000,
                                 type=PaymentType.DUE, remarks="Opening due"))
            db.add(PaymentRecord(dealer_id=d.id, amount=20000,
                                 type=PaymentType.PAYMENT, remarks="Part payment"))
    db.commit()


def seed_settings(db):
    from app.models import Setting
    defaults = {
        "company_name": "Sainext", "currency": "INR",
        "brand_primary": "#121824", "brand_accent": "#c98a1a",
    }
    # one-time correction: replace the pre-redesign brand colors if still stored
    legacy = {"brand_primary": "#1f2530", "brand_accent": "#f5a623"}
    for k, v in defaults.items():
        row = db.execute(select(Setting).where(Setting.key == k)).scalar_one_or_none()
        if not row:
            db.add(Setting(key=k, value=v))
        elif k in legacy and row.value == legacy[k]:
            row.value = v  # upgrade old default to the refined token
    db.commit()


def seed_demo_orders(db):
    """A couple of demo orders so dashboards/reports aren't empty out of the box."""
    from app.services import orders as order_svc
    from app.models import Order, Product, StockItem, Dealer, User
    if db.execute(select(Order)).first():
        return
    roll = db.execute(select(Product).where(Product.product_code == "55440H/PF-102")).scalar_one_or_none()
    dealer = db.execute(select(Dealer)).scalars().first()
    salesman = db.execute(select(User).where(User.email == "salesman@sainext.app")).scalar_one_or_none()
    owner = db.execute(select(User).where(User.email == "owner@sainext.app")).scalar_one_or_none()
    if not (roll and owner):
        return
    item = db.execute(select(StockItem).where(StockItem.product_id == roll.id,
                                              StockItem.available_qty > 10)).scalars().first()
    if not item:
        return
    try:
        order = order_svc.create_order(
            db, product_id=roll.id, allocations=[{"stock_item_id": item.id, "qty": 10}],
            dealer_id=dealer.id if dealer else None,
            salesman_id=salesman.id if salesman else None,
            submit=True, created_by=owner.id)
        db.flush()
        order_svc.approve_order(db, order, approver_id=owner.id)
        db.commit()
    except Exception:
        db.rollback()


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_permissions(db)
        seed_warehouses(db)
        seed_roles(db)
        seed_users(db)
        seed_categories(db)
        seed_products(db)
        seed_stock(db)
        seed_dealers(db)
        seed_payments_and_targets(db)
        seed_settings(db)
        seed_demo_orders(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
    print("Seed complete.")
