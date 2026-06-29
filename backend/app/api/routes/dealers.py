from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Dealer, User, Order, StockBlock, PaymentRecord
from app.models.enums import WarehouseStatus, OrderStatus, BlockStatus, PaymentType
from app.schemas import (
    DealerCreate, DealerUpdate, DealerOut, PaymentCreate, PaymentOut, Paginated,
)
from app.services.audit import log_action
from app.services.scoping import dealer_scope_ids

router = APIRouter(prefix="/dealers", tags=["dealers"])


def _out(db: Session, d: Dealer) -> DealerOut:
    sm = db.get(User, d.assigned_salesman_id) if d.assigned_salesman_id else None
    return DealerOut.model_validate({**d.__dict__, "status": d.status.value,
                                     "salesman_name": sm.name if sm else None})


@router.get("", response_model=Paginated)
def list_dealers(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Dealers:view")),
):
    stmt = select(Dealer)
    scope = dealer_scope_ids(db, user)
    if scope is not None:
        if not scope:
            return Paginated(total=0, page=page, page_size=page_size, items=[])
        stmt = stmt.where(Dealer.id.in_(scope))
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Dealer.firm_name.ilike(like)) | (Dealer.owner_name.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(Dealer.firm_name)
                      .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return Paginated(total=total or 0, page=page, page_size=page_size,
                     items=[_out(db, d) for d in rows])


@router.post("", response_model=DealerOut, status_code=201)
def create_dealer(payload: DealerCreate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("Dealers:create"))):
    d = Dealer(**payload.model_dump(), status=WarehouseStatus.active)
    db.add(d)
    db.flush()
    log_action(db, actor.id, "Dealers", "create", "Dealer", d.id,
               new_value={"firm": d.firm_name})
    db.commit()
    db.refresh(d)
    return _out(db, d)


@router.put("/{dealer_id}", response_model=DealerOut)
def update_dealer(dealer_id: int, payload: DealerUpdate, db: Session = Depends(get_db),
                  actor: User = Depends(require_permission("Dealers:edit"))):
    d = db.get(Dealer, dealer_id)
    if not d:
        raise HTTPException(404, "Dealer not found")
    for f, v in payload.model_dump(exclude_unset=True).items():
        if f == "status" and v is not None:
            d.status = WarehouseStatus(v)
        elif v is not None:
            setattr(d, f, v)
    log_action(db, actor.id, "Dealers", "edit", "Dealer", d.id)
    db.commit()
    db.refresh(d)
    return _out(db, d)


@router.get("/{dealer_id}/dashboard")
def dealer_dashboard(dealer_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_permission("Dealers:view"))):
    d = db.get(Dealer, dealer_id)
    if not d:
        raise HTTPException(404, "Dealer not found")
    scope = dealer_scope_ids(db, user)
    if scope is not None and dealer_id not in scope:
        raise HTTPException(403, "Not allowed to view this dealer")

    orders = db.execute(select(Order).where(Order.dealer_id == dealer_id)).scalars().all()
    order_amount = sum(o.total_amount for o in orders)
    pending = sum(1 for o in orders if o.status == OrderStatus.PENDING_APPROVAL)
    blocks = db.scalar(select(func.count()).select_from(StockBlock).where(
        StockBlock.dealer_id == dealer_id, StockBlock.status == BlockStatus.APPROVED)) or 0
    dues = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
        PaymentRecord.dealer_id == dealer_id, PaymentRecord.type == PaymentType.DUE)) or 0.0
    paid = db.scalar(select(func.coalesce(func.sum(PaymentRecord.amount), 0.0)).where(
        PaymentRecord.dealer_id == dealer_id, PaymentRecord.type == PaymentType.PAYMENT)) or 0.0
    payments = db.execute(select(PaymentRecord).where(PaymentRecord.dealer_id == dealer_id)
                          .order_by(PaymentRecord.id.desc()).limit(20)).scalars().all()
    return {
        "dealer": _out(db, d).model_dump(),
        "total_orders": len(orders),
        "order_amount": order_amount,
        "pending_approvals": pending,
        "blocked_material": blocks,
        "outstanding": dues - paid,
        "total_dues": dues,
        "total_paid": paid,
        "rating": d.rating,
        "credit_period_days": d.credit_period_days,
        "payment_history": [PaymentOut.model_validate(p).model_dump() for p in payments],
    }


# ---- payments ----
@router.post("/payments", response_model=PaymentOut, status_code=201)
def add_payment(payload: PaymentCreate, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Accounts:edit"))):
    if not db.get(Dealer, payload.dealer_id):
        raise HTTPException(400, "Invalid dealer_id")
    rec = PaymentRecord(
        dealer_id=payload.dealer_id, order_id=payload.order_id, amount=payload.amount,
        type=PaymentType(payload.type), due_date=payload.due_date, remarks=payload.remarks,
        paid_at=datetime.now(timezone.utc) if payload.type == "PAYMENT" else None,
    )
    db.add(rec)
    db.flush()
    log_action(db, actor.id, "Accounts", "create", "PaymentRecord", rec.id,
               new_value={"type": payload.type, "amount": payload.amount})
    db.commit()
    db.refresh(rec)
    return PaymentOut.model_validate(rec)
