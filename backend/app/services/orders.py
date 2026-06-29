"""Order management service (Phase 6).

Lifecycle:
  DRAFT -> PENDING_APPROVAL -> APPROVED -> IN_PROCESS -> READY_FOR_DISPATCH
        -> DISPATCHED -> COMPLETED
  CANCELLED / REJECTED are terminal. BLOCKED/PRE_ORDER supported by the model.

Stock rule: stock is COMMITTED at the APPROVED stage (ORDER_COMMIT reduces
available_qty). Dispatch transitions only change status — they never deduct
stock again. Cancelling a committed order releases stock (ORDER_CANCEL_RELEASE).

Saleable = available_qty - approved blocks. Because commit reduces available_qty,
an approved/committed order automatically reduces saleable; pending orders do
not (matching the spec).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import (
    Order, OrderItem, OrderAllocation, StockItem, StockLedger, Product,
    DispatchRecord,
)
from app.models.enums import OrderStatus, LedgerTxnType
from app.services.blocks import saleable_for_item  # available - approved blocks

EPS = 1e-9

# allowed forward transitions (cancel handled separately)
TRANSITIONS = {
    OrderStatus.APPROVED: {OrderStatus.IN_PROCESS, OrderStatus.READY_FOR_DISPATCH},
    OrderStatus.IN_PROCESS: {OrderStatus.READY_FOR_DISPATCH},
    OrderStatus.READY_FOR_DISPATCH: {OrderStatus.DISPATCHED},
    OrderStatus.DISPATCHED: {OrderStatus.COMPLETED},
}
CANCELLABLE = {
    OrderStatus.DRAFT, OrderStatus.PENDING_APPROVAL, OrderStatus.APPROVED,
    OrderStatus.BLOCKED, OrderStatus.IN_PROCESS, OrderStatus.READY_FOR_DISPATCH,
}


def _next_no(db: Session) -> str:
    n = db.scalar(select(func.count()).select_from(Order)) or 0
    return f"ORD-{n + 1:05d}"


def create_order(db: Session, *, product_id: int, allocations: list[dict],
                 dealer_id=None, salesman_id=None, is_partial=False,
                 remarks=None, submit=False, created_by=None) -> Order:
    product = db.get(Product, product_id)
    if not product:
        raise ValueError("Invalid product")
    if not allocations:
        raise ValueError("At least one allocation is required")

    total_qty = 0.0
    for a in allocations:
        si = db.get(StockItem, a["stock_item_id"])
        if not si or si.product_id != product_id:
            raise ValueError("Invalid stock item for this product")
        qty = float(a["qty"])
        if qty <= 0:
            raise ValueError("Allocation quantity must be greater than zero")
        if qty > saleable_for_item(db, si) + EPS:
            raise ValueError(f"Only {saleable_for_item(db, si)} saleable for item {si.id}")
        total_qty += qty

    price = product.price or 0.0
    order = Order(
        order_no=_next_no(db), dealer_id=dealer_id, salesman_id=salesman_id,
        status=OrderStatus.PENDING_APPROVAL if submit else OrderStatus.DRAFT,
        total_amount=price * total_qty, is_partial=is_partial,
        stock_committed=False, remarks=remarks, created_by=created_by,
    )
    db.add(order)
    db.flush()

    oi = OrderItem(
        order_id=order.id, product_id=product_id, qty=total_qty, unit=product.unit,
        price=price, amount=price * total_qty,
        product_snapshot={"product_code": product.product_code, "name": product.name},
    )
    db.add(oi)
    db.flush()

    for a in allocations:
        si = db.get(StockItem, a["stock_item_id"])
        db.add(OrderAllocation(
            order_item_id=oi.id, stock_item_id=si.id, warehouse_id=si.warehouse_id,
            batch_id=si.batch_id, roll_no=si.roll_no, alloc_qty=float(a["qty"]),
            wastage_qty=0.0, is_full_roll=abs(float(a["qty"]) - si.available_qty) < EPS,
            same_batch=True,
        ))
    return order


def _allocations(db, order_id):
    return db.execute(
        select(OrderAllocation)
        .join(OrderItem, OrderItem.id == OrderAllocation.order_item_id)
        .where(OrderItem.order_id == order_id)
    ).scalars().all()


def approve_order(db: Session, order: Order, *, approver_id) -> Order:
    if order.status not in (OrderStatus.PENDING_APPROVAL, OrderStatus.DRAFT):
        raise ValueError(f"Cannot approve an order in status {order.status.value}")
    allocs = _allocations(db, order.id)
    # re-validate saleable before committing (prevents overselling / double commit)
    for al in allocs:
        si = db.get(StockItem, al.stock_item_id)
        if not si or al.alloc_qty > saleable_for_item(db, si) + EPS:
            raise ValueError("Insufficient saleable stock to approve this order")
    # commit
    for al in allocs:
        si = db.get(StockItem, al.stock_item_id)
        before = si.available_qty
        si.available_qty = before - al.alloc_qty
        db.add(StockLedger(
            product_id=si.product_id, warehouse_id=si.warehouse_id,
            batch_id=si.batch_id, stock_item_id=si.id,
            txn_type=LedgerTxnType.ORDER_COMMIT, qty=al.alloc_qty,
            before_qty=before, after_qty=si.available_qty,
            ref_type="order", ref_id=order.id, created_by=approver_id,
            remarks=f"Committed on approval ({order.order_no})",
        ))
    order.status = OrderStatus.APPROVED
    order.stock_committed = True
    order.approved_by = approver_id
    return order


def reject_order(db: Session, order: Order, *, actor_id, remarks=None) -> Order:
    if order.status not in (OrderStatus.PENDING_APPROVAL, OrderStatus.DRAFT):
        raise ValueError("Only pending/draft orders can be rejected")
    order.status = OrderStatus.REJECTED
    if remarks:
        order.remarks = remarks
    return order


def cancel_order(db: Session, order: Order, *, actor_id) -> Order:
    if order.status not in CANCELLABLE:
        raise ValueError(f"Cannot cancel an order in status {order.status.value}")
    if order.stock_committed:
        for al in _allocations(db, order.id):
            si = db.get(StockItem, al.stock_item_id)
            if si:
                before = si.available_qty
                si.available_qty = before + al.alloc_qty   # release committed stock
                db.add(StockLedger(
                    product_id=si.product_id, warehouse_id=si.warehouse_id,
                    batch_id=si.batch_id, stock_item_id=si.id,
                    txn_type=LedgerTxnType.ORDER_CANCEL_RELEASE, qty=al.alloc_qty,
                    before_qty=before, after_qty=si.available_qty,
                    ref_type="order", ref_id=order.id, created_by=actor_id,
                    remarks=f"Released on cancel ({order.order_no})",
                ))
        order.stock_committed = False
    order.status = OrderStatus.CANCELLED
    return order


def transition(db: Session, order: Order, target: OrderStatus, *, actor_id,
               notes=None, transport=None) -> Order:
    allowed = TRANSITIONS.get(order.status, set())
    if target not in allowed:
        raise ValueError(f"Cannot move from {order.status.value} to {target.value}")
    order.status = target
    if target in (OrderStatus.IN_PROCESS, OrderStatus.READY_FOR_DISPATCH,
                  OrderStatus.DISPATCHED):
        rec = DispatchRecord(
            order_id=order.id, status=target.value, notes=notes,
            transport_details=transport, dispatched_by=actor_id,
            dispatched_at=datetime.now(timezone.utc) if target == OrderStatus.DISPATCHED else None,
        )
        db.add(rec)
        if target == OrderStatus.DISPATCHED:
            order.dispatch_by = actor_id
    # Note: dispatch transitions never touch stock — it was committed at approval.
    return order
