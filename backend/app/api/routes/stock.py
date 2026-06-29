from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import StockItem, StockLedger, Product, Warehouse, Batch, User, Role
from app.models.enums import StockItemType, LedgerTxnType
from app.schemas import (
    InwardRequest, AdjustmentRequest, TransferRequest, DamageRequest,
    StockItemOut, StockItemRow, LedgerRow, Paginated,
)
from app.services import stock as stock_svc
from app.services import recommendation as reco_svc
from app.services.audit import log_action
from app.services.permissions import effective_permission_codes, is_owner
from pydantic import BaseModel

router = APIRouter(prefix="/stock", tags=["stock"])


def _can(db: Session, user: User, code: str) -> bool:
    return is_owner(user, db) or code in effective_permission_codes(db, user)


class RecommendationRequest(BaseModel):
    product_id: int
    required_qty: float
    warehouse_id: int | None = None


@router.post("/recommendation")
def stock_recommendation(payload: RecommendationRequest, db: Session = Depends(get_db),
                         _=Depends(require_permission("Stock Check:view"))):
    product = db.get(Product, payload.product_id)
    if not product:
        raise HTTPException(404, "Product not found")
    if payload.required_qty <= 0:
        raise HTTPException(422, "required_qty must be greater than zero")
    result = reco_svc.recommend(db, product, payload.required_qty,
                                warehouse_id=payload.warehouse_id)
    return result


@router.get("/check")
def stock_check(
    q: str | None = None,
    product_id: int | None = None,
    batch_no: str | None = None,
    warehouse_id: int | None = None,
    required_qty: float = 0.0,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("Stock Check:view")),
):
    """Fast stock check. Resolves matching product(s) and returns warehouse-,
    batch- and item-wise availability. Price and batch/roll detail are included
    only when the user has the corresponding permission."""
    from sqlalchemy import or_

    can_price = _can(db, user, "Stock Check:view_price")
    can_batch = _can(db, user, "Stock Check:view_batch_details")

    if product_id:
        products = [p for p in [db.get(Product, product_id)] if p]
    elif q:
        like = f"%{q}%"
        products = db.execute(
            select(Product).where(or_(
                Product.pattern_no.ilike(like), Product.product_code.ilike(like),
                Product.name.ilike(like), Product.collection_name.ilike(like),
                Product.brand.ilike(like),
            )).limit(10)
        ).scalars().all()
    else:
        raise HTTPException(422, "Provide a search term (q) or product_id")

    results = []
    for p in products:
        check = stock_svc.build_stock_check(
            db, p, warehouse_id=warehouse_id, batch_no=batch_no,
            required_qty=required_qty, include_batch_detail=can_batch,
        )
        product_out = {
            "id": p.id, "pattern_no": p.pattern_no, "product_code": p.product_code,
            "name": p.name, "collection_name": p.collection_name, "brand": p.brand,
            "product_type": p.product_type.value, "unit": p.unit,
            "unit_size": p.unit_size, "thickness": p.thickness,
            "roll_size": p.roll_size, "status": p.status.value,
            "remarks": p.remarks,
            "price": p.price if can_price else None,
        }
        results.append({"product": product_out, **check})

    return {
        "count": len(results),
        "can_view_price": can_price,
        "can_view_batch_details": can_batch,
        "results": results,
    }


# --------------------------------------------------------------------------- #
# Mutations (Stock Inward module). All wrapped in a single transaction.
# --------------------------------------------------------------------------- #
@router.post("/inward", response_model=StockItemOut, status_code=201)
def stock_inward(payload: InwardRequest, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("Stock Inward:create"))):
    if not db.get(Product, payload.product_id):
        raise HTTPException(400, "Invalid product_id")
    if not db.get(Warehouse, payload.warehouse_id):
        raise HTTPException(400, "Invalid warehouse_id")
    kind = payload.entry_kind.upper()
    txn = LedgerTxnType.RETURN_IN if kind == "RETURN_IN" else LedgerTxnType.INWARD
    try:
        item = stock_svc.inward(
            db, product_id=payload.product_id, warehouse_id=payload.warehouse_id,
            quantity=payload.quantity, unit=payload.unit,
            item_type=StockItemType(payload.item_type),
            batch_no=payload.batch_no, batch_date=payload.batch_date,
            roll_no=payload.roll_no, roll_date=payload.roll_date,
            box_count=payload.box_count, purchase_date=payload.purchase_date,
            inward_date=payload.inward_date, remarks=payload.remarks,
            created_by=actor.id, txn_type=txn,
        )
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Inward", "create", "StockItem", item.id,
               new_value={"qty": payload.quantity, "txn": txn.value})
    db.commit()
    db.refresh(item)
    return StockItemOut.model_validate({**item.__dict__, "item_type": item.item_type.value})


@router.post("/adjustment", response_model=StockItemOut)
def stock_adjustment(payload: AdjustmentRequest, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("Stock Inward:edit"))):
    # Negative-stock override is only honoured for admin-level roles.
    role = db.get(Role, actor.role_id)
    is_admin = bool(role and role.name in ("Owner", "Admin"))
    allow_negative = payload.allow_negative and is_admin
    try:
        item = stock_svc.adjust(db, stock_item_id=payload.stock_item_id,
                                delta=payload.delta, created_by=actor.id,
                                remarks=payload.remarks, allow_negative=allow_negative)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Inward", "adjustment", "StockItem",
               payload.stock_item_id, new_value={"delta": payload.delta})
    db.commit()
    db.refresh(item)
    return StockItemOut.model_validate({**item.__dict__, "item_type": item.item_type.value})


@router.post("/damage", response_model=StockItemOut)
def stock_damage(payload: DamageRequest, db: Session = Depends(get_db),
                 actor: User = Depends(require_permission("Stock Inward:edit"))):
    try:
        item = stock_svc.damage(db, stock_item_id=payload.stock_item_id,
                                quantity=payload.quantity, created_by=actor.id,
                                remarks=payload.remarks)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Inward", "damage", "StockItem",
               payload.stock_item_id, new_value={"qty": payload.quantity})
    db.commit()
    db.refresh(item)
    return StockItemOut.model_validate({**item.__dict__, "item_type": item.item_type.value})


@router.post("/transfer")
def stock_transfer(payload: TransferRequest, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("Stock Inward:edit"))):
    if not db.get(Warehouse, payload.to_warehouse_id):
        raise HTTPException(400, "Invalid destination warehouse")
    try:
        src, dest = stock_svc.transfer(
            db, stock_item_id=payload.stock_item_id,
            to_warehouse_id=payload.to_warehouse_id, quantity=payload.quantity,
            created_by=actor.id, remarks=payload.remarks)
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    log_action(db, actor.id, "Stock Inward", "transfer", "StockItem", src.id,
               new_value={"to": payload.to_warehouse_id, "qty": payload.quantity})
    db.commit()
    return {"detail": "Transferred", "source_item_id": src.id, "dest_item_id": dest.id}


# --------------------------------------------------------------------------- #
# Reads
# --------------------------------------------------------------------------- #
@router.get("/items", response_model=Paginated)
def list_items(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    only_available: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Stock Inward:view")),
):
    stmt = (
        select(StockItem, Product.product_code, Product.name,
               Warehouse.name, Batch.batch_no)
        .join(Product, Product.id == StockItem.product_id)
        .join(Warehouse, Warehouse.id == StockItem.warehouse_id)
        .join(Batch, Batch.id == StockItem.batch_id, isouter=True)
    )
    if product_id:
        stmt = stmt.where(StockItem.product_id == product_id)
    if warehouse_id:
        stmt = stmt.where(StockItem.warehouse_id == warehouse_id)
    if only_available:
        stmt = stmt.where(StockItem.available_qty > 0)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(StockItem.inward_date.asc(), StockItem.id.asc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        StockItemRow.model_validate({
            **si.__dict__, "item_type": si.item_type.value,
            "product_code": code, "product_name": pname,
            "warehouse_name": wname, "batch_no": bno,
        })
        for si, code, pname, wname, bno in rows
    ]
    return Paginated(total=total or 0, page=page, page_size=page_size, items=items)


@router.get("/ledger", response_model=Paginated)
def list_ledger(
    product_id: int | None = None,
    warehouse_id: int | None = None,
    txn_type: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Stock Inward:view")),
):
    stmt = (
        select(StockLedger, Product.product_code, Warehouse.name)
        .join(Product, Product.id == StockLedger.product_id)
        .join(Warehouse, Warehouse.id == StockLedger.warehouse_id)
    )
    if product_id:
        stmt = stmt.where(StockLedger.product_id == product_id)
    if warehouse_id:
        stmt = stmt.where(StockLedger.warehouse_id == warehouse_id)
    if txn_type:
        stmt = stmt.where(StockLedger.txn_type == LedgerTxnType(txn_type))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(StockLedger.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()
    items = [
        LedgerRow.model_validate({
            **le.__dict__, "txn_type": le.txn_type.value,
            "product_code": code, "warehouse_name": wname,
        })
        for le, code, wname in rows
    ]
    return Paginated(total=total or 0, page=page, page_size=page_size, items=items)


@router.get("/batches")
def list_batches(product_id: int = Query(...), db: Session = Depends(get_db),
                 _=Depends(require_permission("Stock Inward:view"))):
    rows = db.execute(
        select(Batch).where(Batch.product_id == product_id).order_by(Batch.batch_date)
    ).scalars().all()
    return [{"id": b.id, "batch_no": b.batch_no,
             "batch_date": b.batch_date.isoformat() if b.batch_date else None}
            for b in rows]
