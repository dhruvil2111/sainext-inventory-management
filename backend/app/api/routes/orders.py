from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission, require_any_permission
from app.models import Order, OrderItem, OrderAllocation, Dealer, User
from app.models.enums import OrderStatus
from app.schemas import (
    OrderCreate, OrderOut, OrderItemOut, OrderAllocOut, DispatchAction,
    OrderActionRemarks, Paginated,
)
from app.services import orders as order_svc
from app.services import recommendation as reco_svc
from app.models import Product
from app.services.audit import log_action

router = APIRouter(prefix="/orders", tags=["orders"])


def _enrich(db: Session, o: Order) -> OrderOut:
    dealer = db.get(Dealer, o.dealer_id) if o.dealer_id else None
    items = db.execute(select(OrderItem).where(OrderItem.order_id == o.id)).scalars().all()
    item_out = []
    for it in items:
        allocs = db.execute(
            select(OrderAllocation).where(OrderAllocation.order_item_id == it.id)
        ).scalars().all()
        item_out.append(OrderItemOut.model_validate({
            **it.__dict__, "allocations": [OrderAllocOut.model_validate(a) for a in allocs],
        }))
    return OrderOut(
        id=o.id, order_no=o.order_no, dealer_id=o.dealer_id, salesman_id=o.salesman_id,
        status=o.status.value, total_amount=o.total_amount, is_partial=o.is_partial,
        stock_committed=o.stock_committed, source_block_id=o.source_block_id,
        approved_by=o.approved_by, dispatch_by=o.dispatch_by, remarks=o.remarks,
        created_by=o.created_by, created_at=o.created_at,
        dealer_name=dealer.firm_name if dealer else None, items=item_out,
    )


@router.get("", response_model=Paginated)
def list_orders(
    status: str | None = None,
    dealer_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Orders:view")),
):
    stmt = select(Order)
    if status:
        stmt = stmt.where(Order.status == OrderStatus(status))
    if dealer_id:
        stmt = stmt.where(Order.dealer_id == dealer_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(Order.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return Paginated(total=total or 0, page=page, page_size=page_size,
                     items=[_enrich(db, o) for o in rows])


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db),
              _=Depends(require_permission("Orders:view"))):
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return _enrich(db, o)


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("Orders:create"))):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(400, "Invalid product_id")
    allocs = [{"stock_item_id": a.stock_item_id, "qty": a.qty} for a in payload.allocations]
    if not allocs and payload.auto_allocate and payload.required_qty:
        reco = reco_svc.recommend(db, product, payload.required_qty)
        if not reco["options"]:
            raise HTTPException(400, "No allocation available for the required quantity")
        allocs = [{"stock_item_id": p["stock_item_id"], "qty": p["alloc_qty"]}
                  for p in reco["options"][0]["picks"]]
    try:
        order = order_svc.create_order(
            db, product_id=payload.product_id, allocations=allocs,
            dealer_id=payload.dealer_id, salesman_id=payload.salesman_id,
            is_partial=payload.is_partial, remarks=payload.remarks,
            submit=payload.submit, created_by=actor.id,
        )
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Orders", "create", "Order", order.id,
               new_value={"submit": payload.submit})
    db.commit(); db.refresh(order)
    return _enrich(db, order)


def _load(db, order_id) -> Order:
    o = db.get(Order, order_id)
    if not o:
        raise HTTPException(404, "Order not found")
    return o


@router.post("/{order_id}/approve", response_model=OrderOut)
def approve(order_id: int, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("Orders:approve"))):
    o = _load(db, order_id)
    try:
        order_svc.approve_order(db, o, approver_id=actor.id)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Orders", "approve", "Order", o.id)
    db.commit(); db.refresh(o)
    return _enrich(db, o)


@router.post("/{order_id}/reject", response_model=OrderOut)
def reject(order_id: int, payload: OrderActionRemarks | None = None,
           db: Session = Depends(get_db),
           actor: User = Depends(require_permission("Orders:reject"))):
    o = _load(db, order_id)
    try:
        order_svc.reject_order(db, o, actor_id=actor.id,
                               remarks=payload.remarks if payload else None)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Orders", "reject", "Order", o.id)
    db.commit(); db.refresh(o)
    return _enrich(db, o)


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel(order_id: int, db: Session = Depends(get_db),
           actor: User = Depends(require_permission("Orders:edit"))):
    o = _load(db, order_id)
    try:
        order_svc.cancel_order(db, o, actor_id=actor.id)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Orders", "cancel", "Order", o.id)
    db.commit(); db.refresh(o)
    return _enrich(db, o)


def _do_transition(db, order_id, target, actor, payload: DispatchAction | None):
    o = _load(db, order_id)
    try:
        order_svc.transition(db, o, target, actor_id=actor.id,
                             notes=payload.notes if payload else None,
                             transport=payload.transport_details if payload else None)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Orders", target.value, "Order", o.id)
    db.commit(); db.refresh(o)
    return _enrich(db, o)


# dispatch-stage transitions: Orders:edit OR Dispatch:edit
_dispatch_guard = require_any_permission("Orders:edit", "Dispatch:edit")


@router.post("/{order_id}/in-process", response_model=OrderOut)
def in_process(order_id: int, payload: DispatchAction | None = None,
               db: Session = Depends(get_db), actor: User = Depends(_dispatch_guard)):
    return _do_transition(db, order_id, OrderStatus.IN_PROCESS, actor, payload)


@router.post("/{order_id}/ready-for-dispatch", response_model=OrderOut)
def ready(order_id: int, payload: DispatchAction | None = None,
          db: Session = Depends(get_db), actor: User = Depends(_dispatch_guard)):
    return _do_transition(db, order_id, OrderStatus.READY_FOR_DISPATCH, actor, payload)


@router.post("/{order_id}/dispatched", response_model=OrderOut)
def dispatched(order_id: int, payload: DispatchAction | None = None,
               db: Session = Depends(get_db), actor: User = Depends(_dispatch_guard)):
    return _do_transition(db, order_id, OrderStatus.DISPATCHED, actor, payload)


@router.post("/{order_id}/completed", response_model=OrderOut)
def completed(order_id: int, payload: DispatchAction | None = None,
              db: Session = Depends(get_db), actor: User = Depends(_dispatch_guard)):
    return _do_transition(db, order_id, OrderStatus.COMPLETED, actor, payload)
