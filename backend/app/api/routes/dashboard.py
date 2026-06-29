from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import (
    User, Warehouse, Product, Order, StockBlock, Dealer, StockItem, StockLedger,
    PaymentRecord,
)
from app.models.enums import OrderStatus, BlockStatus, LedgerTxnType, PaymentType

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

IN_TXNS = {LedgerTxnType.INWARD, LedgerTxnType.RETURN_IN, LedgerTxnType.TRANSFER_IN,
           LedgerTxnType.ADJUSTMENT_IN}


@router.get("/stats")
def stats(db: Session = Depends(get_db),
          _=Depends(require_permission("Dashboard:view"))):
    def count(model, *where):
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return db.scalar(stmt) or 0

    return {
        "users": count(User),
        "warehouses": count(Warehouse),
        "products": count(Product),
        "dealers": count(Dealer),
        "stock_items": count(StockItem),
        "orders_total": count(Order),
        "orders_pending": count(Order, Order.status == OrderStatus.PENDING_APPROVAL),
        "blocks_pending": count(StockBlock, StockBlock.status == BlockStatus.PENDING_APPROVAL),
        "blocks_approved": count(StockBlock, StockBlock.status == BlockStatus.APPROVED),
    }


@router.get("/analytics")
def analytics(days: int = 14, db: Session = Depends(get_db),
              _=Depends(require_permission("Dashboard:view"))):
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # ledger movement per day (inward vs outward)
    rows = db.execute(
        select(StockLedger.txn_type, StockLedger.qty, StockLedger.created_at)
        .where(StockLedger.created_at >= since)
    ).all()
    by_day: dict[str, dict] = {}
    for txn, qty, created in rows:
        if not created:
            continue
        d = created.date().isoformat()
        slot = by_day.setdefault(d, {"date": d, "in": 0.0, "out": 0.0})
        if txn in IN_TXNS:
            slot["in"] += qty
        else:
            slot["out"] += qty
    movement = sorted(by_day.values(), key=lambda x: x["date"])

    # orders by status
    status_rows = db.execute(
        select(Order.status, func.count()).group_by(Order.status)
    ).all()
    orders_by_status = [{"status": s.value, "count": c} for s, c in status_rows]

    # top outstanding dealers
    dealers = db.execute(select(Dealer)).scalars().all()
    dues = []
    for d in dealers:
        due = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
            PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.DUE)) or 0.0
        paid = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
            PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.PAYMENT)) or 0.0
        out = due - paid
        if out > 0:
            dues.append({"dealer": d.firm_name, "outstanding": out})
    dues.sort(key=lambda x: -x["outstanding"])

    return {"movement": movement, "orders_by_status": orders_by_status,
            "top_dues": dues[:5]}
