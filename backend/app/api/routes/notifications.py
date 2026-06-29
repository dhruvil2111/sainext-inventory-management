from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import StockBlock, Order, Dealer, PaymentRecord, User
from app.models.enums import BlockStatus, OrderStatus, PaymentType
from app.services.permissions import effective_permission_codes, is_owner

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def notifications(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owner = is_owner(user, db)
    perms = effective_permission_codes(db, user)

    def can(code: str) -> bool:
        return owner or code in perms

    def count(model, *where):
        s = select(func.count()).select_from(model)
        for w in where:
            s = s.where(w)
        return db.scalar(s) or 0

    items = []

    if can("Stock Blocking:approve") or can("Stock Blocking:view"):
        n = count(StockBlock, StockBlock.status == BlockStatus.PENDING_APPROVAL)
        if n:
            items.append({"type": "block_approval", "label": "Blocks awaiting approval",
                          "count": n, "link": "/blocks", "tone": "warning"})
        now = datetime.now(timezone.utc)
        eod = now.replace(hour=23, minute=59, second=59)
        exp = count(StockBlock, StockBlock.status == BlockStatus.APPROVED,
                    StockBlock.hold_until.is_not(None),
                    StockBlock.hold_until >= now, StockBlock.hold_until <= eod)
        if exp:
            items.append({"type": "block_expiring", "label": "Blocks expiring today",
                          "count": exp, "link": "/blocks", "tone": "danger"})

    if can("Orders:approve") or can("Orders:view"):
        n = count(Order, Order.status == OrderStatus.PENDING_APPROVAL)
        if n:
            items.append({"type": "order_approval", "label": "Orders awaiting approval",
                          "count": n, "link": "/orders", "tone": "warning"})

    if can("Accounts:view"):
        overdue = 0
        for d in db.execute(select(Dealer)).scalars().all():
            due = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
                PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.DUE)) or 0.0
            paid = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
                PaymentRecord.dealer_id == d.id, PaymentRecord.type == PaymentType.PAYMENT)) or 0.0
            if due - paid > 0:
                overdue += 1
        if overdue:
            items.append({"type": "dues", "label": "Dealers with outstanding dues",
                          "count": overdue, "link": "/accounts", "tone": "danger"})

    return {"count": sum(i["count"] for i in items), "items": items}
