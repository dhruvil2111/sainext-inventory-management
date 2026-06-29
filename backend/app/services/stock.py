"""Transactional stock operations. Every stock change posts a stock_ledger row
with before/after quantities and keeps stock_items.available_qty in sync. Stock
is never overwritten without a ledger entry (mandatory rule).

All public functions here flush within the caller's session but DO NOT commit;
the route handler owns the transaction boundary so a failure rolls back cleanly.
"""
from datetime import date
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models import StockItem, StockLedger, Batch, StockBlock, StockBlockItem, Order
from app.models.enums import LedgerTxnType, StockItemType, BlockStatus, OrderStatus


def _post_ledger(db: Session, *, item: StockItem, txn_type: LedgerTxnType,
                 qty: float, before: float, after: float, created_by=None,
                 ref_type=None, ref_id=None, remarks=None) -> StockLedger:
    entry = StockLedger(
        product_id=item.product_id, warehouse_id=item.warehouse_id,
        batch_id=item.batch_id, stock_item_id=item.id, txn_type=txn_type,
        qty=qty, before_qty=before, after_qty=after, created_by=created_by,
        ref_type=ref_type, ref_id=ref_id, remarks=remarks,
    )
    db.add(entry)
    return entry


def get_or_create_batch(db: Session, product_id: int, batch_no: str | None,
                        batch_date: date | None) -> Batch | None:
    if not batch_no:
        return None
    batch = db.execute(
        select(Batch).where(Batch.product_id == product_id, Batch.batch_no == batch_no)
    ).scalar_one_or_none()
    if batch:
        if batch_date and not batch.batch_date:
            batch.batch_date = batch_date
        return batch
    batch = Batch(product_id=product_id, batch_no=batch_no, batch_date=batch_date)
    db.add(batch)
    db.flush()
    return batch


def inward(db: Session, *, product_id: int, warehouse_id: int, quantity: float,
           unit: str, item_type: StockItemType = StockItemType.ROLL,
           batch_no: str | None = None, batch_date: date | None = None,
           roll_no: str | None = None, roll_date: date | None = None,
           box_count: int | None = None, purchase_date: date | None = None,
           inward_date: date | None = None, remarks: str | None = None,
           created_by=None, txn_type: LedgerTxnType = LedgerTxnType.INWARD) -> StockItem:
    """Create a new physical stock item and post the INWARD/RETURN_IN entry."""
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero")
    batch = get_or_create_batch(db, product_id, batch_no, batch_date)
    item = StockItem(
        product_id=product_id, warehouse_id=warehouse_id,
        batch_id=batch.id if batch else None, item_type=item_type,
        roll_no=roll_no, roll_date=roll_date, box_count=box_count,
        purchase_date=purchase_date, inward_date=inward_date or date.today(),
        original_qty=quantity, available_qty=quantity, unit=unit,
        status="available", remarks=remarks, created_by=created_by,
    )
    db.add(item)
    db.flush()
    _post_ledger(db, item=item, txn_type=txn_type, qty=quantity,
                 before=0, after=quantity, created_by=created_by,
                 ref_type="stock_item", ref_id=item.id, remarks=remarks)
    return item


def adjust(db: Session, *, stock_item_id: int, delta: float, created_by=None,
           remarks: str | None = None, allow_negative: bool = False) -> StockItem:
    """Positive delta -> ADJUSTMENT_IN, negative -> ADJUSTMENT_OUT.

    Negative resulting stock is rejected unless allow_negative is set, which the
    route only honours for admin-level users (explicit admin adjustment)."""
    item = db.get(StockItem, stock_item_id)
    if not item:
        raise ValueError("Stock item not found")
    if delta == 0:
        raise ValueError("Adjustment delta cannot be zero")
    before = item.available_qty
    after = before + delta
    if after < 0 and not allow_negative:
        raise ValueError("Adjustment would make available stock negative")
    item.available_qty = after
    txn = LedgerTxnType.ADJUSTMENT_IN if delta > 0 else LedgerTxnType.ADJUSTMENT_OUT
    _post_ledger(db, item=item, txn_type=txn, qty=abs(delta), before=before,
                 after=after, created_by=created_by, ref_type="adjustment",
                 remarks=remarks)
    return item


def damage(db: Session, *, stock_item_id: int, quantity: float, created_by=None,
           remarks: str | None = None) -> StockItem:
    item = db.get(StockItem, stock_item_id)
    if not item:
        raise ValueError("Stock item not found")
    if quantity <= 0:
        raise ValueError("Damage quantity must be greater than zero")
    before = item.available_qty
    if quantity > before:
        raise ValueError("Damage quantity exceeds available stock")
    after = before - quantity
    item.available_qty = after
    _post_ledger(db, item=item, txn_type=LedgerTxnType.DAMAGE, qty=quantity,
                 before=before, after=after, created_by=created_by,
                 ref_type="damage", remarks=remarks)
    return item


def transfer(db: Session, *, stock_item_id: int, to_warehouse_id: int,
             quantity: float, created_by=None, remarks: str | None = None
             ) -> tuple[StockItem, StockItem]:
    """Move quantity from a source item (TRANSFER_OUT) to a destination
    warehouse, creating a destination stock item (TRANSFER_IN). Batch / roll
    metadata is preserved so old-stock-first ordering still works downstream."""
    src = db.get(StockItem, stock_item_id)
    if not src:
        raise ValueError("Source stock item not found")
    if quantity <= 0:
        raise ValueError("Transfer quantity must be greater than zero")
    if quantity > src.available_qty:
        raise ValueError("Transfer quantity exceeds available stock")
    if to_warehouse_id == src.warehouse_id:
        raise ValueError("Destination warehouse must differ from source")

    before = src.available_qty
    src.available_qty = before - quantity
    _post_ledger(db, item=src, txn_type=LedgerTxnType.TRANSFER_OUT, qty=quantity,
                 before=before, after=src.available_qty, created_by=created_by,
                 ref_type="transfer", remarks=remarks)

    dest = StockItem(
        product_id=src.product_id, warehouse_id=to_warehouse_id,
        batch_id=src.batch_id, item_type=src.item_type, roll_no=src.roll_no,
        roll_date=src.roll_date, box_count=src.box_count,
        purchase_date=src.purchase_date, inward_date=src.inward_date,
        original_qty=quantity, available_qty=quantity, unit=src.unit,
        status="available", remarks=f"Transfer from WH {src.warehouse_id}",
        created_by=created_by,
    )
    db.add(dest)
    db.flush()
    _post_ledger(db, item=dest, txn_type=LedgerTxnType.TRANSFER_IN, qty=quantity,
                 before=0, after=quantity, created_by=created_by,
                 ref_type="transfer", ref_id=src.id, remarks=remarks)
    return src, dest


# --------------------------------------------------------------------------- #
# Stock figures (used by Stock Check / recommendation in later phases, and to
# expose saleable stock now).
# --------------------------------------------------------------------------- #
def approved_blocked_qty(db: Session, product_id: int, warehouse_id: int | None = None) -> float:
    stmt = (
        select(func.coalesce(func.sum(StockBlockItem.qty), 0.0))
        .join(StockBlock, StockBlock.id == StockBlockItem.block_id)
        .where(StockBlock.status == BlockStatus.APPROVED)
        .join(StockItem, StockItem.id == StockBlockItem.stock_item_id)
        .where(StockItem.product_id == product_id)
    )
    if warehouse_id:
        stmt = stmt.where(StockBlockItem.warehouse_id == warehouse_id)
    return float(db.scalar(stmt) or 0.0)


def actual_qty(db: Session, product_id: int, warehouse_id: int | None = None) -> float:
    stmt = select(func.coalesce(func.sum(StockItem.available_qty), 0.0)).where(
        StockItem.product_id == product_id
    )
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    return float(db.scalar(stmt) or 0.0)


def saleable_qty(db: Session, product_id: int, warehouse_id: int | None = None) -> float:
    """Saleable = available (which already excludes committed orders, since
    ORDER_COMMIT reduces available_qty) minus APPROVED blocks. Pending blocks do
    not reduce saleable stock."""
    return actual_qty(db, product_id, warehouse_id) - approved_blocked_qty(db, product_id, warehouse_id)


def _approved_blocked_by_item(db: Session, product_id: int) -> dict[int, float]:
    """Map stock_item_id -> approved-blocked qty for one product."""
    rows = db.execute(
        select(StockBlockItem.stock_item_id, func.coalesce(func.sum(StockBlockItem.qty), 0.0))
        .join(StockBlock, StockBlock.id == StockBlockItem.block_id)
        .join(StockItem, StockItem.id == StockBlockItem.stock_item_id)
        .where(StockBlock.status == BlockStatus.APPROVED, StockItem.product_id == product_id)
        .group_by(StockBlockItem.stock_item_id)
    ).all()
    return {sid: float(q) for sid, q in rows}


def _avail_status(saleable: float, required: float) -> str:
    """Green/red/yellow indicator. required<=0 -> just presence."""
    if saleable <= 0:
        return "red"
    if required and saleable < required:
        return "yellow"     # partially available
    return "green"


def build_stock_check(db: Session, product, *, warehouse_id: int | None = None,
                      batch_no: str | None = None, required_qty: float = 0.0,
                      include_batch_detail: bool = True) -> dict:
    """Compute warehouse-/batch-/item-wise availability for one product.

    saleable(item) = available_qty - approved_blocked(item). Pending blocks do
    not reduce saleable. Returns totals, per-warehouse rows (with status colour),
    and — when permitted — per-batch rows and the item-level detail used by the
    View Batch modal.
    """
    from app.models import Warehouse, Batch

    stmt = select(StockItem).where(StockItem.product_id == product.id)
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    items = db.execute(stmt).scalars().all()

    if batch_no:
        bid = {b.id: b for b in db.execute(
            select(Batch).where(Batch.product_id == product.id)).scalars().all()}
        items = [i for i in items if i.batch_id and bid.get(i.batch_id) and
                 bid[i.batch_id].batch_no == batch_no]

    blocked_map = _approved_blocked_by_item(db, product.id)
    wh_names = {w.id: w.name for w in db.execute(select(Warehouse)).scalars().all()}
    batches = {b.id: b for b in db.execute(
        select(Batch).where(Batch.product_id == product.id)).scalars().all()}

    wh_agg: dict[int, dict] = {}
    batch_agg: dict[int, dict] = {}
    detail = []
    t_avail = t_blocked = 0.0

    for it in items:
        blk = blocked_map.get(it.id, 0.0)
        sale = it.available_qty - blk
        t_avail += it.available_qty
        t_blocked += blk

        w = wh_agg.setdefault(it.warehouse_id, {
            "warehouse_id": it.warehouse_id,
            "warehouse_name": wh_names.get(it.warehouse_id, str(it.warehouse_id)),
            "available": 0.0, "blocked": 0.0, "saleable": 0.0})
        w["available"] += it.available_qty
        w["blocked"] += blk
        w["saleable"] += sale

        if it.batch_id:
            b = batches.get(it.batch_id)
            ba = batch_agg.setdefault(it.batch_id, {
                "batch_id": it.batch_id,
                "batch_no": b.batch_no if b else None,
                "batch_date": b.batch_date.isoformat() if b and b.batch_date else None,
                "available": 0.0, "blocked": 0.0, "saleable": 0.0})
            ba["available"] += it.available_qty
            ba["blocked"] += blk
            ba["saleable"] += sale

        b = batches.get(it.batch_id) if it.batch_id else None
        detail.append({
            "stock_item_id": it.id, "warehouse_id": it.warehouse_id,
            "warehouse_name": wh_names.get(it.warehouse_id),
            "batch_id": it.batch_id, "batch_no": b.batch_no if b else None,
            "batch_date": b.batch_date.isoformat() if b and b.batch_date else None,
            "item_type": it.item_type.value, "roll_no": it.roll_no,
            "box_count": it.box_count, "unit": it.unit,
            "roll_date": it.roll_date.isoformat() if it.roll_date else None,
            "inward_date": it.inward_date.isoformat() if it.inward_date else None,
            "purchase_date": it.purchase_date.isoformat() if it.purchase_date else None,
            "original_qty": it.original_qty, "available_qty": it.available_qty,
            "blocked_qty": blk, "saleable_qty": sale, "status": it.status,
        })

    t_saleable = t_avail - t_blocked
    for w in wh_agg.values():
        w["status"] = _avail_status(w["saleable"], required_qty)

    # by-type loose/box/roll rollup of saleable
    by_type = {"ROLL": 0.0, "BOX": 0.0, "LOOSE": 0.0}
    for d in detail:
        by_type[d["item_type"]] = by_type.get(d["item_type"], 0.0) + d["saleable_qty"]

    result = {
        "total_available": t_avail,
        "total_blocked": t_blocked,
        "total_saleable": t_saleable,
        "required_qty": required_qty,
        "can_fulfill": (t_saleable >= required_qty) if required_qty else (t_saleable > 0),
        "status": _avail_status(t_saleable, required_qty),
        "negative_warning": t_saleable < 0,
        "by_type": by_type,
        "warehouses": sorted(wh_agg.values(), key=lambda x: x["warehouse_name"]),
    }
    if include_batch_detail:
        result["batches"] = sorted(
            batch_agg.values(),
            key=lambda x: (x["batch_date"] or "9999", x["batch_no"] or ""))
        result["items"] = sorted(detail, key=lambda d: (
            d["inward_date"] or "9999", d["batch_no"] or "", d["roll_no"] or ""))
    return result
