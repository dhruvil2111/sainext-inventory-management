from datetime import datetime, date

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, JSON, String,
    Text, UniqueConstraint, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models import enums as E


# --------------------------------------------------------------------------- #
# Auth, roles, permissions
# --------------------------------------------------------------------------- #
class Role(Base):
    __tablename__ = "roles"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(String(255))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    permissions: Mapped[list["RolePermission"]] = relationship(back_populates="role", cascade="all, delete-orphan")
    users: Mapped[list["User"]] = relationship(back_populates="role")


class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(80), index=True)
    action: Mapped[str] = mapped_column(String(60), index=True)
    code: Mapped[str] = mapped_column(String(160), unique=True, index=True)  # module:action
    description: Mapped[str | None] = mapped_column(String(255))


class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[Role] = relationship(back_populates="permissions")
    permission: Mapped[Permission] = relationship()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    mobile: Mapped[str | None] = mapped_column(String(30))
    password_hash: Mapped[str] = mapped_column(String(255))
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    status: Mapped[E.UserStatus] = mapped_column(Enum(E.UserStatus), default=E.UserStatus.active)
    assigned_warehouse_id: Mapped[int | None] = mapped_column(ForeignKey("warehouses.id"))
    # Optional links: a user (e.g. a dealer login or operator) can be tied to a
    # salesman and/or a dealer record.
    assigned_salesman_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    assigned_dealer_id: Mapped[int | None] = mapped_column(ForeignKey("dealers.id"))
    monthly_target: Mapped[float] = mapped_column(Float, default=0.0)  # salesman target
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    role: Mapped[Role] = relationship(back_populates="users")
    overrides: Mapped[list["UserPermissionOverride"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class UserPermissionOverride(Base):
    __tablename__ = "user_permission_overrides"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    permission_id: Mapped[int] = mapped_column(ForeignKey("permissions.id", ondelete="CASCADE"))
    allow: Mapped[bool] = mapped_column(Boolean, default=True)
    user: Mapped[User] = relationship(back_populates="overrides")
    permission: Mapped[Permission] = relationship()
    __table_args__ = (UniqueConstraint("user_id", "permission_id", name="uq_user_perm"),)


# --------------------------------------------------------------------------- #
# Warehouses / products
# --------------------------------------------------------------------------- #
class Warehouse(Base):
    __tablename__ = "warehouses"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    location: Mapped[str | None] = mapped_column(String(120))
    address: Mapped[str | None] = mapped_column(Text)
    status: Mapped[E.WarehouseStatus] = mapped_column(Enum(E.WarehouseStatus), default=E.WarehouseStatus.active)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ProductCategory(Base):
    __tablename__ = "product_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str | None] = mapped_column(String(255))


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    pattern_no: Mapped[str] = mapped_column(String(80), index=True)
    product_code: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # design code
    name: Mapped[str] = mapped_column(String(160))
    collection_name: Mapped[str | None] = mapped_column(String(120), index=True)
    brand: Mapped[str | None] = mapped_column(String(120), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("product_categories.id"))
    product_type: Mapped[E.ProductType] = mapped_column(Enum(E.ProductType), default=E.ProductType.ROLL)
    unit: Mapped[str] = mapped_column(String(20), default="SQM")
    unit_size: Mapped[str | None] = mapped_column(String(80))
    thickness: Mapped[str | None] = mapped_column(String(40))
    roll_size: Mapped[str | None] = mapped_column(String(80))
    standard_roll_qty: Mapped[float | None] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[E.ProductStatus] = mapped_column(Enum(E.ProductStatus), default=E.ProductStatus.CONTINUED)
    remarks: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Batch(Base):
    __tablename__ = "batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    batch_no: Mapped[str] = mapped_column(String(80), index=True)
    batch_date: Mapped[date | None] = mapped_column(Date)
    remarks: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- #
# Stock
# --------------------------------------------------------------------------- #
class StockItem(Base):
    __tablename__ = "stock_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"), index=True)
    item_type: Mapped[E.StockItemType] = mapped_column(Enum(E.StockItemType), default=E.StockItemType.ROLL)
    roll_no: Mapped[str | None] = mapped_column(String(60))
    box_count: Mapped[int | None] = mapped_column(Integer)
    roll_date: Mapped[date | None] = mapped_column(Date)
    inward_date: Mapped[date | None] = mapped_column(Date, server_default=func.now())
    purchase_date: Mapped[date | None] = mapped_column(Date)
    original_qty: Mapped[float] = mapped_column(Float, default=0.0)
    available_qty: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="SQM")
    status: Mapped[str] = mapped_column(String(30), default="available")
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StockLedger(Base):
    __tablename__ = "stock_ledger"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"), index=True)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    stock_item_id: Mapped[int | None] = mapped_column(ForeignKey("stock_items.id"))
    txn_type: Mapped[E.LedgerTxnType] = mapped_column(Enum(E.LedgerTxnType), index=True)
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    before_qty: Mapped[float] = mapped_column(Float, default=0.0)
    after_qty: Mapped[float] = mapped_column(Float, default=0.0)
    ref_type: Mapped[str | None] = mapped_column(String(40))
    ref_id: Mapped[int | None] = mapped_column(Integer)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    remarks: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------------------- #
# Blocking
# --------------------------------------------------------------------------- #
class StockBlock(Base):
    __tablename__ = "stock_blocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    block_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    dealer_id: Mapped[int | None] = mapped_column(ForeignKey("dealers.id"))
    salesman_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    required_qty: Mapped[float] = mapped_column(Float, default=0.0)
    hold_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[E.BlockStatus] = mapped_column(Enum(E.BlockStatus), default=E.BlockStatus.DRAFT, index=True)
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["StockBlockItem"]] = relationship(back_populates="block", cascade="all, delete-orphan")


class StockBlockItem(Base):
    __tablename__ = "stock_block_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    block_id: Mapped[int] = mapped_column(ForeignKey("stock_blocks.id", ondelete="CASCADE"))
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    block: Mapped[StockBlock] = relationship(back_populates="items")


# --------------------------------------------------------------------------- #
# Orders
# --------------------------------------------------------------------------- #
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    dealer_id: Mapped[int | None] = mapped_column(ForeignKey("dealers.id"))
    salesman_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[E.OrderStatus] = mapped_column(Enum(E.OrderStatus), default=E.OrderStatus.DRAFT, index=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0)
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False)
    stock_committed: Mapped[bool] = mapped_column(Boolean, default=False)
    source_block_id: Mapped[int | None] = mapped_column(ForeignKey("stock_blocks.id"))
    approved_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    dispatch_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    qty: Mapped[float] = mapped_column(Float, default=0.0)
    unit: Mapped[str] = mapped_column(String(20), default="SQM")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    product_snapshot: Mapped[dict | None] = mapped_column(JSON)
    order: Mapped[Order] = relationship(back_populates="items")
    allocations: Mapped[list["OrderAllocation"]] = relationship(back_populates="order_item", cascade="all, delete-orphan")


class OrderAllocation(Base):
    __tablename__ = "order_allocations"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id", ondelete="CASCADE"))
    stock_item_id: Mapped[int] = mapped_column(ForeignKey("stock_items.id"))
    warehouse_id: Mapped[int] = mapped_column(ForeignKey("warehouses.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    roll_no: Mapped[str | None] = mapped_column(String(60))
    alloc_qty: Mapped[float] = mapped_column(Float, default=0.0)
    wastage_qty: Mapped[float] = mapped_column(Float, default=0.0)
    is_full_roll: Mapped[bool] = mapped_column(Boolean, default=False)
    same_batch: Mapped[bool] = mapped_column(Boolean, default=True)
    order_item: Mapped[OrderItem] = relationship(back_populates="allocations")


# --------------------------------------------------------------------------- #
# Dealers / dispatch / accounts
# --------------------------------------------------------------------------- #
class Dealer(Base):
    __tablename__ = "dealers"
    id: Mapped[int] = mapped_column(primary_key=True)
    firm_name: Mapped[str] = mapped_column(String(160))
    owner_name: Mapped[str | None] = mapped_column(String(120))
    concern_person: Mapped[str | None] = mapped_column(String(120))
    contact: Mapped[str | None] = mapped_column(String(30))
    alt_contact: Mapped[str | None] = mapped_column(String(30))
    address: Mapped[str | None] = mapped_column(Text)
    gst_no: Mapped[str | None] = mapped_column(String(40))
    assigned_salesman_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    category: Mapped[str | None] = mapped_column(String(60))
    credit_period_days: Mapped[int] = mapped_column(Integer, default=0)
    rating: Mapped[float | None] = mapped_column(Float)
    price_list_access: Mapped[bool] = mapped_column(Boolean, default=False)
    offer_letter_access: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[E.WarehouseStatus] = mapped_column(Enum(E.WarehouseStatus), default=E.WarehouseStatus.active)
    login_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SalesmanDealerMapping(Base):
    __tablename__ = "salesman_dealer_mapping"
    id: Mapped[int] = mapped_column(primary_key=True)
    salesman_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    dealer_id: Mapped[int] = mapped_column(ForeignKey("dealers.id"))


class DispatchRecord(Base):
    __tablename__ = "dispatch_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"))
    status: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)
    transport_details: Mapped[str | None] = mapped_column(Text)
    dispatched_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaymentRecord(Base):
    __tablename__ = "payment_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    dealer_id: Mapped[int] = mapped_column(ForeignKey("dealers.id"))
    order_id: Mapped[int | None] = mapped_column(ForeignKey("orders.id"))
    amount: Mapped[float] = mapped_column(Float, default=0.0)
    type: Mapped[E.PaymentType] = mapped_column(Enum(E.PaymentType), default=E.PaymentType.DUE)
    due_date: Mapped[date | None] = mapped_column(Date)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    remarks: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# --------------------------------------------------------------------------- #
# Cross-cutting
# --------------------------------------------------------------------------- #
class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    module: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(60))
    record_type: Mapped[str | None] = mapped_column(String(80))
    record_id: Mapped[int | None] = mapped_column(Integer)
    old_value: Mapped[dict | None] = mapped_column(JSON)
    new_value: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    __tablename__ = "settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    value: Mapped[dict | None] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class RevokedToken(Base):
    """Denylist of revoked refresh-token JTIs (populated on logout / rotation)."""
    __tablename__ = "revoked_tokens"
    id: Mapped[int] = mapped_column(primary_key=True)
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
