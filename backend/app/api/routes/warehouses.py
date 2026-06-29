from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Warehouse, User
from app.models.enums import WarehouseStatus
from app.schemas import WarehouseOut, WarehouseCreate, WarehouseUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/warehouses", tags=["warehouses"])


@router.get("", response_model=list[WarehouseOut])
def list_warehouses(db: Session = Depends(get_db),
                    _=Depends(require_permission("Warehouses:view"))):
    rows = db.execute(select(Warehouse).order_by(Warehouse.id)).scalars().all()
    return [WarehouseOut.model_validate({**w.__dict__, "status": w.status.value}) for w in rows]


@router.post("", response_model=WarehouseOut, status_code=201)
def create_warehouse(payload: WarehouseCreate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("Warehouses:create"))):
    if db.execute(select(Warehouse).where(Warehouse.code == payload.code)).scalar_one_or_none():
        raise HTTPException(409, "Warehouse code already exists")
    w = Warehouse(**payload.model_dump(), created_by=actor.id)
    db.add(w)
    db.flush()
    log_action(db, actor.id, "Warehouses", "create", "Warehouse", w.id,
               new_value={"code": w.code})
    db.commit()
    db.refresh(w)
    return WarehouseOut.model_validate({**w.__dict__, "status": w.status.value})


@router.put("/{wid}", response_model=WarehouseOut)
def update_warehouse(wid: int, payload: WarehouseUpdate, db: Session = Depends(get_db),
                     actor: User = Depends(require_permission("Warehouses:edit"))):
    w = db.get(Warehouse, wid)
    if not w:
        raise HTTPException(404, "Warehouse not found")
    for f, v in payload.model_dump(exclude_unset=True).items():
        if f == "status" and v is not None:
            w.status = WarehouseStatus(v)
        elif v is not None:
            setattr(w, f, v)
    log_action(db, actor.id, "Warehouses", "edit", "Warehouse", w.id)
    db.commit()
    db.refresh(w)
    return WarehouseOut.model_validate({**w.__dict__, "status": w.status.value})


@router.delete("/{wid}")
def disable_warehouse(wid: int, db: Session = Depends(get_db),
                      actor: User = Depends(require_permission("Warehouses:delete"))):
    w = db.get(Warehouse, wid)
    if not w:
        raise HTTPException(404, "Warehouse not found")
    w.status = WarehouseStatus.inactive
    log_action(db, actor.id, "Warehouses", "delete", "Warehouse", w.id)
    db.commit()
    return {"detail": "Warehouse disabled"}
