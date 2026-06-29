from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Role, Permission, RolePermission, User
from app.schemas import RoleOut, RoleCreate, RoleUpdate, RolePermissionsUpdate
from app.services.audit import log_action
from app.services.permissions import effective_permission_codes

router = APIRouter(prefix="/roles", tags=["roles"])


def _role_out(db: Session, role: Role) -> RoleOut:
    codes = [
        c[0] for c in db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        ).all()
    ]
    return RoleOut(id=role.id, name=role.name, description=role.description,
                   is_system=role.is_system, permission_codes=sorted(codes))


@router.get("", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db),
               _=Depends(require_permission("Roles & Permissions:view"))):
    return [_role_out(db, r) for r in db.execute(select(Role).order_by(Role.id)).scalars().all()]


@router.post("", response_model=RoleOut, status_code=201)
def create_role(payload: RoleCreate, db: Session = Depends(get_db),
                user: User = Depends(require_permission("Roles & Permissions:create"))):
    if db.execute(select(Role).where(Role.name == payload.name)).scalar_one_or_none():
        raise HTTPException(409, "Role name already exists")
    role = Role(name=payload.name, description=payload.description, is_system=False)
    db.add(role)
    db.flush()
    log_action(db, user.id, "Roles & Permissions", "create", "Role", role.id,
               new_value={"name": role.name})
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.put("/{role_id}", response_model=RoleOut)
def update_role(role_id: int, payload: RoleUpdate, db: Session = Depends(get_db),
                user: User = Depends(require_permission("Roles & Permissions:edit"))):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    if payload.name is not None:
        role.name = payload.name
    if payload.description is not None:
        role.description = payload.description
    log_action(db, user.id, "Roles & Permissions", "edit", "Role", role.id)
    db.commit()
    db.refresh(role)
    return _role_out(db, role)


@router.delete("/{role_id}")
def delete_role(role_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_permission("Roles & Permissions:delete"))):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    if role.is_system:
        raise HTTPException(400, "System roles cannot be deleted")
    in_use = db.execute(select(func.count()).select_from(User).where(User.role_id == role_id)).scalar()
    if in_use:
        raise HTTPException(409, f"Role is assigned to {in_use} user(s); reassign them first")
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    db.delete(role)
    log_action(db, user.id, "Roles & Permissions", "delete", "Role", role_id)
    db.commit()
    return {"detail": "Role deleted"}


@router.put("/{role_id}/permissions", response_model=RoleOut)
def set_role_permissions(role_id: int, payload: RolePermissionsUpdate,
                         db: Session = Depends(get_db),
                         user: User = Depends(require_permission("Roles & Permissions:manage_permissions"))):
    role = db.get(Role, role_id)
    if not role:
        raise HTTPException(404, "Role not found")
    if role.name == "Owner":
        raise HTTPException(400, "Owner role always has all permissions and cannot be edited")
    valid = {c: pid for pid, c in db.execute(select(Permission.id, Permission.code)).all()}
    db.query(RolePermission).filter(RolePermission.role_id == role_id).delete()
    for code in payload.permission_codes:
        if code in valid:
            db.add(RolePermission(role_id=role_id, permission_id=valid[code]))
    log_action(db, user.id, "Roles & Permissions", "manage_permissions", "Role",
               role.id, new_value={"count": len(payload.permission_codes)})
    db.commit()
    db.refresh(role)
    return _role_out(db, role)
