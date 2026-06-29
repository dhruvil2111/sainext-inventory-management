from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Permission
from app.schemas import PermissionOut

router = APIRouter(prefix="/permissions", tags=["permissions"])


@router.get("", response_model=list[PermissionOut])
def list_permissions(
    db: Session = Depends(get_db),
    _=Depends(require_permission("Roles & Permissions:view")),
):
    return db.execute(select(Permission).order_by(Permission.module, Permission.action)).scalars().all()
