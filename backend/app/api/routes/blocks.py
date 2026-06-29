from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission, get_current_user
from app.models import StockBlock, StockBlockItem, Product, Dealer, User
from app.models.enums import BlockStatus
from app.schemas import (
    BlockCreate, BlockExtend, BlockActionRemarks, BlockOut, BlockItemOut, Paginated,
)
from app.services import blocks as block_svc
from app.services import recommendation as reco_svc
from app.services.audit import log_action

router = APIRouter(prefix="/blocks", tags=["blocks"])


def _enrich(db: Session, b: StockBlock) -> BlockOut:
    product = db.get(Product, b.product_id)
    dealer = db.get(Dealer, b.dealer_id) if b.dealer_id else None
    items = db.execute(select(StockBlockItem).where(StockBlockItem.block_id == b.id)).scalars().all()
    return BlockOut(
        id=b.id, block_no=b.block_no, product_id=b.product_id, dealer_id=b.dealer_id,
        salesman_id=b.salesman_id, required_qty=b.required_qty, hold_until=b.hold_until,
        status=b.status.value, approved_by=b.approved_by, approved_at=b.approved_at,
        remarks=b.remarks, created_by=b.created_by, created_at=b.created_at,
        product_code=product.product_code if product else None,
        product_name=product.name if product else None,
        dealer_name=dealer.firm_name if dealer else None,
        items=[BlockItemOut.model_validate(i) for i in items],
    )


@router.get("", response_model=Paginated)
def list_blocks(
    status: str | None = None,
    dealer_id: int | None = None,
    product_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Stock Blocking:view")),
):
    stmt = select(StockBlock)
    if status:
        stmt = stmt.where(StockBlock.status == BlockStatus(status))
    if dealer_id:
        stmt = stmt.where(StockBlock.dealer_id == dealer_id)
    if product_id:
        stmt = stmt.where(StockBlock.product_id == product_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(StockBlock.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return Paginated(total=total or 0, page=page, page_size=page_size,
                     items=[_enrich(db, b) for b in rows])


@router.get("/summary")
def block_summary(db: Session = Depends(get_db),
                  _=Depends(require_permission("Stock Blocking:view"))):
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    end_of_day = now.replace(hour=23, minute=59, second=59)

    def count(*where):
        s = select(func.count()).select_from(StockBlock)
        for w in where:
            s = s.where(w)
        return db.scalar(s) or 0

    return {
        "pending_approval": count(StockBlock.status == BlockStatus.PENDING_APPROVAL),
        "approved": count(StockBlock.status == BlockStatus.APPROVED),
        "expiring_today": count(StockBlock.status == BlockStatus.APPROVED,
                                StockBlock.hold_until.is_not(None),
                                StockBlock.hold_until <= end_of_day,
                                StockBlock.hold_until >= now),
        "expired": count(StockBlock.status == BlockStatus.EXPIRED),
    }


@router.get("/{block_id}", response_model=BlockOut)
def get_block(block_id: int, db: Session = Depends(get_db),
              _=Depends(require_permission("Stock Blocking:view"))):
    b = db.get(StockBlock, block_id)
    if not b:
        raise HTTPException(404, "Block not found")
    return _enrich(db, b)


@router.post("", response_model=BlockOut, status_code=201)
def create_block(payload: BlockCreate, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("Stock Blocking:create"))):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(400, "Invalid product_id")

    items = [{"stock_item_id": i.stock_item_id, "qty": i.qty} for i in payload.items]
    # auto-allocate from recommendation if no explicit items
    if not items and payload.auto_allocate and payload.required_qty:
        reco = reco_svc.recommend(db, product, payload.required_qty,
                                  warehouse_id=None)
        if not reco["options"]:
            raise HTTPException(400, "No allocation available for the required quantity")
        items = [{"stock_item_id": p["stock_item_id"], "qty": p["alloc_qty"]}
                 for p in reco["options"][0]["picks"]]
    try:
        block = block_svc.create_block(
            db, product_id=payload.product_id, items=items,
            dealer_id=payload.dealer_id, salesman_id=payload.salesman_id,
            hold_until=payload.hold_until, remarks=payload.remarks,
            submit=payload.submit, created_by=actor.id,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "create", "StockBlock", block.id,
               new_value={"qty": block.required_qty, "submit": payload.submit})
    db.commit()
    db.refresh(block)
    return _enrich(db, block)


def _load(db, block_id) -> StockBlock:
    b = db.get(StockBlock, block_id)
    if not b:
        raise HTTPException(404, "Block not found")
    return b


@router.post("/{block_id}/approve", response_model=BlockOut)
def approve(block_id: int, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("Stock Blocking:approve"))):
    b = _load(db, block_id)
    try:
        block_svc.approve_block(db, b, approver_id=actor.id)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "approve", "StockBlock", b.id)
    db.commit(); db.refresh(b)
    return _enrich(db, b)


@router.post("/{block_id}/reject", response_model=BlockOut)
def reject(block_id: int, payload: BlockActionRemarks | None = None,
           db: Session = Depends(get_db),
           actor: User = Depends(require_permission("Stock Blocking:reject"))):
    b = _load(db, block_id)
    try:
        block_svc.reject_block(db, b, actor_id=actor.id,
                               remarks=payload.remarks if payload else None)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "reject", "StockBlock", b.id)
    db.commit(); db.refresh(b)
    return _enrich(db, b)


@router.post("/{block_id}/release", response_model=BlockOut)
def release(block_id: int, db: Session = Depends(get_db),
            actor: User = Depends(require_permission("Stock Blocking:release_stock"))):
    b = _load(db, block_id)
    try:
        block_svc.release_block(db, b, actor_id=actor.id)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "release", "StockBlock", b.id)
    db.commit(); db.refresh(b)
    return _enrich(db, b)


@router.post("/{block_id}/extend", response_model=BlockOut)
def extend(block_id: int, payload: BlockExtend, db: Session = Depends(get_db),
           actor: User = Depends(require_permission("Stock Blocking:edit"))):
    b = _load(db, block_id)
    try:
        block_svc.extend_block(db, b, hold_until=payload.hold_until)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "extend", "StockBlock", b.id)
    db.commit(); db.refresh(b)
    return _enrich(db, b)


@router.post("/{block_id}/convert-to-order")
def convert_to_order(block_id: int, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("Stock Blocking:convert_block_to_order"))):
    b = _load(db, block_id)
    try:
        order = block_svc.convert_to_order(db, b, actor_id=actor.id)
    except ValueError as e:
        db.rollback(); raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Blocking", "convert_block_to_order",
               "StockBlock", b.id, new_value={"order_id": order.id})
    db.commit()
    return {"detail": "Converted to order", "order_id": order.id,
            "order_no": order.order_no, "block_id": b.id}
