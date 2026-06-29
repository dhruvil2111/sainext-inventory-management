"""Salesman and Accounts dashboards (Phase 7)."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Dealer, User, Order, StockBlock, PaymentRecord
from app.models.enums import OrderStatus, BlockStatus, PaymentType
from app.services.scoping import dealer_scope_ids

router = APIRouter(tags=["dashboards"])


def _month_start():
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _aware(dt):
    """Coerce naive datetimes (SQLite) to UTC-aware so comparisons are safe."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.get("/salesman/dashboard")
def salesman_dashboard(db: Session = Depends(get_db),
                       user: User = Depends(require_permission("Salesman Dashboard:view"))):
    # dealers this user can see (salesman -> assigned)
    scope = dealer_scope_ids(db, user)
    dstmt = select(Dealer)
    if scope is not None:
        dstmt = dstmt.where(Dealer.id.in_(scope)) if scope else dstmt.where(Dealer.id == -1)
    dealers = db.execute(dstmt).scalars().all()
    dealer_ids = [d.id for d in dealers]

    ostmt = select(Order)
    if dealer_ids:
        ostmt = ostmt.where(Order.dealer_id.in_(dealer_ids))
    elif scope is not None:
        ostmt = ostmt.where(Order.salesman_id == user.id)
    orders = db.execute(ostmt).scalars().all()

    achieved = sum(o.total_amount for o in orders
                   if o.created_at and _aware(o.created_at) >= _month_start()
                   and o.status not in (OrderStatus.CANCELLED, OrderStatus.REJECTED))
    pending = sum(1 for o in orders if o.status == OrderStatus.PENDING_APPROVAL)

    blk = select(func.count()).select_from(StockBlock).where(
        StockBlock.status == BlockStatus.APPROVED)
    if dealer_ids:
        blk = blk.where(StockBlock.dealer_id.in_(dealer_ids))
    blocked = db.scalar(blk) or 0

    target = user.monthly_target or 0.0
    return {
        "salesman": {"id": user.id, "name": user.name},
        "monthly_target": target,
        "target_achieved": achieved,
        "target_pct": round((achieved / target * 100), 1) if target else 0,
        "total_orders": len(orders),
        "order_amount": sum(o.total_amount for o in orders),
        "pending_approvals": pending,
        "blocked_material": blocked,
        "dealers": [{"id": d.id, "firm_name": d.firm_name, "rating": d.rating,
                     "category": d.category, "credit_period_days": d.credit_period_days}
                    for d in dealers],
    }


@router.get("/accounts/dashboard")
def accounts_dashboard(db: Session = Depends(get_db),
                       _=Depends(require_permission("Accounts:view"))):
    dealers = db.execute(select(Dealer)).scalars().all()
    rows = []
    total_outstanding = 0.0
    for d in dealers:
        dues = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
            PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.DUE)) or 0.0
        paid = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
            PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.PAYMENT)) or 0.0
        outstanding = dues - paid
        total_outstanding += outstanding
        rows.append({
            "dealer_id": d.id, "firm_name": d.firm_name,
            "credit_period_days": d.credit_period_days, "rating": d.rating,
            "total_dues": dues, "total_paid": paid, "outstanding": outstanding,
            "alert": outstanding > 0,
        })
    rows.sort(key=lambda r: -r["outstanding"])
    return {
        "total_outstanding": total_outstanding,
        "dealers_with_dues": sum(1 for r in rows if r["outstanding"] > 0),
        "rows": rows,
    }
