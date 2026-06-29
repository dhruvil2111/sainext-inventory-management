"""Material blocking service (Phase 5).

Lifecycle: DRAFT -> PENDING_APPROVAL -> APPROVED -> (RELEASED | EXPIRED | CONVERTED).
REJECTED is terminal from PENDING_APPROVAL.

Stock model (consistent with services.stock):
  saleable = available_qty - APPROVED block qty
A block never mutates available_qty. Only its *status* matters:
  - DRAFT / PENDING_APPROVAL: does NOT reduce saleable.
  - APPROVED: reduces saleable (counted by approved_blocked_qty).
  - RELEASED / EXPIRED / REJECTED / CONVERTED: no longer reduces saleable.

Ledger rows (BLOCK / BLOCK_RELEASE) are informational for blocks — available_qty
is unchanged — so before_qty == after_qty on those entries. Converting to an order
is where stock is actually committed (ORDER_COMMIT reduces available_qty).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import (
    StockBlock, StockBlockItem, StockItem, StockLedger, Order, OrderItem,
    OrderAllocation, Product,
)
from app.models.enums import BlockStatus, OrderStatus, LedgerTxnType

EPS = 1e-9


def _next_no(db: Session, model, attr: str, prefix: str) -> str:
    n = db.scalar(select(func.count()).select_from(model)) or 0
    return f"{prefix}-{n + 1:05d}"


def approved_blocked_for_item(db: Session, stock_item_id: int,
                              exclude_block_id: int | None = None) -> float:
    """Sum of APPROVED block quantities against a stock item."""
    stmt = (
        select(func.coalesce(func.sum(StockBlockItem.qty), 0.0))
        .join(StockBlock, StockBlock.id == StockBlockItem.block_id)
        .where(StockBlockItem.stock_item_id == stock_item_id,
               StockBlock.status == BlockStatus.APPROVED)
    )
    if exclude_block_id:
        stmt = stmt.where(StockBlock.id != exclude_block_id)
    return float(db.scalar(stmt) or 0.0)


def saleable_for_item(db: Session, item: StockItem, exclude_block_id: int | None = None) -> float:
    return item.available_qty - approved_blocked_for_item(db, item.id, exclude_block_id)


def _ledger(db, item, txn_type, qty, *, created_by, block_id, remarks):
    db.add(StockLedger(
        product_id=item.product_id, warehouse_id=item.warehouse_id,
        batch_id=item.batch_id, stock_item_id=item.id, txn_type=txn_type,
        qty=qty, before_qty=item.available_qty, after_qty=item.available_qty,
        ref_type="block", ref_id=block_id, created_by=created_by, remarks=remarks,
    ))


def create_block(db: Session, *, product_id: int, items: list[dict],
                 dealer_id=None, salesman_id=None, hold_until=None,
                 remarks=None, submit=False, created_by=None) -> StockBlock:
    if not items:
        raise ValueError("At least one stock item must be selected for the block")
    required = 0.0
    # validate each requested qty against current saleable
    for row in items:
        si = db.get(StockItem, row["stock_item_id"])
        if not si or si.product_id != product_id:
            raise ValueError("Invalid stock item for this product")
        qty = float(row["qty"])
        if qty <= 0:
            raise ValueError("Block quantity must be greater than zero")
        if qty > saleable_for_item(db, si) + EPS:
            raise ValueError(f"Only {saleable_for_item(db, si)} saleable for item {si.id}")
        required += qty

    block = StockBlock(
        block_no=_next_no(db, StockBlock, "block_no", "BLK"),
        dealer_id=dealer_id, salesman_id=salesman_id, product_id=product_id,
        required_qty=required, hold_until=hold_until, remarks=remarks,
        status=BlockStatus.PENDING_APPROVAL if submit else BlockStatus.DRAFT,
        created_by=created_by,
    )
    db.add(block)
    db.flush()
    for row in items:
        si = db.get(StockItem, row["stock_item_id"])
        db.add(StockBlockItem(block_id=block.id, stock_item_id=si.id,
                              warehouse_id=si.warehouse_id, batch_id=si.batch_id,
                              qty=float(row["qty"])))
    return block


def _items(db, block_id):
    return db.execute(select(StockBlockItem).where(StockBlockItem.block_id == block_id)).scalars().all()


def approve_block(db: Session, block: StockBlock, *, approver_id) -> StockBlock:
    if block.status not in (BlockStatus.PENDING_APPROVAL, BlockStatus.DRAFT):
        raise ValueError(f"Cannot approve a block in status {block.status.value}")
    # re-validate stock is still saleable (excluding this block)
    for it in _items(db, block.id):
        si = db.get(StockItem, it.stock_item_id)
        if not si or it.qty > saleable_for_item(db, si, exclude_block_id=block.id) + EPS:
            raise ValueError("Insufficient saleable stock to approve this block")
    block.status = BlockStatus.APPROVED
    block.approved_by = approver_id
    block.approved_at = datetime.now(timezone.utc)
    for it in _items(db, block.id):
        si = db.get(StockItem, it.stock_item_id)
        if si:
            _ledger(db, si, LedgerTxnType.BLOCK, it.qty, created_by=approver_id,
                    block_id=block.id, remarks=f"Block approved ({block.block_no})")
    return block


def reject_block(db: Session, block: StockBlock, *, actor_id, remarks=None) -> StockBlock:
    if block.status not in (BlockStatus.PENDING_APPROVAL, BlockStatus.DRAFT):
        raise ValueError("Only pending/draft blocks can be rejected")
    block.status = BlockStatus.REJECTED
    if remarks:
        block.remarks = remarks
    return block


def release_block(db: Session, block: StockBlock, *, actor_id) -> StockBlock:
    if block.status not in (BlockStatus.APPROVED, BlockStatus.PENDING_APPROVAL):
        raise ValueError("Only approved or pending blocks can be released")
    was_approved = block.status == BlockStatus.APPROVED
    block.status = BlockStatus.RELEASED
    if was_approved:
        for it in _items(db, block.id):
            si = db.get(StockItem, it.stock_item_id)
            if si:
                _ledger(db, si, LedgerTxnType.BLOCK_RELEASE, it.qty,
                        created_by=actor_id, block_id=block.id,
                        remarks=f"Block released ({block.block_no})")
    return block


def extend_block(db: Session, block: StockBlock, *, hold_until) -> StockBlock:
    if block.status not in (BlockStatus.APPROVED, BlockStatus.PENDING_APPROVAL):
        raise ValueError("Only active blocks can be extended")
    block.hold_until = hold_until
    return block


def convert_to_order(db: Session, block: StockBlock, *, actor_id) -> Order:
    """Convert an APPROVED block into a stock-committed order.

    The reservation moves from 'approved block' to 'committed order': the block
    becomes CONVERTED (stops counting as an approved block) and an order is
    created with ORDER_COMMIT ledger entries that reduce available_qty by the
    allocated amounts. Net saleable is unchanged, so there is no double counting.
    """
    if block.status != BlockStatus.APPROVED:
        raise ValueError("Only approved blocks can be converted to an order")
    product = db.get(Product, block.product_id)
    block_items = _items(db, block.id)
    total_qty = sum(it.qty for it in block_items)

    order = Order(
        order_no=_next_no(db, Order, "order_no", "ORD"),
        dealer_id=block.dealer_id, salesman_id=block.salesman_id,
        status=OrderStatus.APPROVED, stock_committed=True,
        source_block_id=block.id, approved_by=actor_id, is_partial=False,
        total_amount=(product.price or 0.0) * total_qty if product else 0.0,
        remarks=f"Converted from block {block.block_no}", created_by=actor_id,
    )
    db.add(order)
    db.flush()

    oi = OrderItem(
        order_id=order.id, product_id=block.product_id, qty=total_qty,
        unit=product.unit if product else "", price=product.price if product else 0.0,
        amount=(product.price or 0.0) * total_qty if product else 0.0,
        product_snapshot={"product_code": product.product_code,
                          "name": product.name} if product else None,
    )
    db.add(oi)
    db.flush()

    for it in block_items:
        si = db.get(StockItem, it.stock_item_id)
        if not si:
            continue
        before = si.available_qty
        si.available_qty = before - it.qty           # commit: physical reduced
        db.add(OrderAllocation(
            order_item_id=oi.id, stock_item_id=si.id, warehouse_id=si.warehouse_id,
            batch_id=si.batch_id, roll_no=si.roll_no, alloc_qty=it.qty,
            wastage_qty=0.0, is_full_roll=abs(it.qty - before) < EPS, same_batch=True,
        ))
        db.add(StockLedger(
            product_id=si.product_id, warehouse_id=si.warehouse_id,
            batch_id=si.batch_id, stock_item_id=si.id,
            txn_type=LedgerTxnType.ORDER_COMMIT, qty=it.qty,
            before_qty=before, after_qty=si.available_qty,
            ref_type="order", ref_id=order.id, created_by=actor_id,
            remarks=f"Committed from block {block.block_no}",
        ))

    block.status = BlockStatus.CONVERTED
    return order
