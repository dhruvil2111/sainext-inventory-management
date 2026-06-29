from datetime import date, datetime, time

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import AuditLog, User
from app.schemas import Paginated

router = APIRouter(prefix="/audit-logs", tags=["audit"])

# Gated to admin-level roles (Owner implicit-all + Admin hold this permission).
_GUARD = require_permission("Roles & Permissions:view")


@router.get("", response_model=Paginated)
def list_audit_logs(
    module: str | None = None,
    action: str | None = None,
    user_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(_GUARD),
):
    stmt = select(AuditLog)
    if module:
        stmt = stmt.where(AuditLog.module == module)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= datetime.combine(date_to, time.max))

    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    names = {u.id: u.name for u in db.execute(select(User)).scalars().all()}
    items = [{
        "id": r.id, "user_id": r.user_id, "user_name": names.get(r.user_id, "system"),
        "module": r.module, "action": r.action, "record_type": r.record_type,
        "record_id": r.record_id, "old_value": r.old_value, "new_value": r.new_value,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    } for r in rows]
    return Paginated(total=total or 0, page=page, page_size=page_size, items=items)


@router.get("/meta")
def audit_meta(db: Session = Depends(get_db), _: User = Depends(_GUARD)):
    modules = [m[0] for m in db.execute(select(AuditLog.module).distinct()).all()]
    actions = [a[0] for a in db.execute(select(AuditLog.action).distinct()).all()]
    return {"modules": sorted(modules), "actions": sorted(actions)}
