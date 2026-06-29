from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.core.security import hash_password
from app.models import User, Role, Permission, RolePermission, UserPermissionOverride
from app.models.enums import UserStatus
from app.schemas import (
    UserOut, UserCreate, UserUpdate, Paginated, UserPermissionsOut,
    UserOverridesUpdate,
)
from app.services.audit import log_action
from app.services.permissions import effective_permission_codes

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=Paginated)
def list_users(
    q: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _=Depends(require_permission("Users:view")),
):
    stmt = select(User)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((User.name.ilike(like)) | (User.email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(
        stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    items = [UserOut.model_validate(
        {**u.__dict__, "status": u.status.value}) for u in rows]
    return Paginated(total=total or 0, page=page, page_size=page_size, items=items)


@router.post("", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Users:create"))):
    if db.execute(select(User).where(User.email == payload.email)).scalar_one_or_none():
        raise HTTPException(409, "Email already registered")
    if not db.get(Role, payload.role_id):
        raise HTTPException(400, "Invalid role_id")
    user = User(
        name=payload.name, email=payload.email, mobile=payload.mobile,
        role_id=payload.role_id, assigned_warehouse_id=payload.assigned_warehouse_id,
        assigned_salesman_id=payload.assigned_salesman_id,
        assigned_dealer_id=payload.assigned_dealer_id,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.flush()
    log_action(db, actor.id, "Users", "create", "User", user.id,
               new_value={"email": user.email})
    db.commit()
    db.refresh(user)
    return UserOut.model_validate({**user.__dict__, "status": user.status.value})


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Users:edit"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if payload.name is not None:
        user.name = payload.name
    if payload.mobile is not None:
        user.mobile = payload.mobile
    if payload.role_id is not None:
        user.role_id = payload.role_id
    if payload.assigned_warehouse_id is not None:
        user.assigned_warehouse_id = payload.assigned_warehouse_id
    if payload.assigned_salesman_id is not None:
        user.assigned_salesman_id = payload.assigned_salesman_id
    if payload.assigned_dealer_id is not None:
        user.assigned_dealer_id = payload.assigned_dealer_id
    if payload.monthly_target is not None:
        user.monthly_target = payload.monthly_target
    if payload.status is not None:
        user.status = UserStatus(payload.status)
    if payload.password:
        user.password_hash = hash_password(payload.password)
    log_action(db, actor.id, "Users", "edit", "User", user.id)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate({**user.__dict__, "status": user.status.value})


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Users:delete"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == actor.id:
        raise HTTPException(400, "You cannot delete your own account")
    user.status = UserStatus.inactive  # soft-disable
    log_action(db, actor.id, "Users", "delete", "User", user.id)
    db.commit()
    return {"detail": "User disabled"}


# --------------------------------------------------------------------------- #
# Per-user permission overrides (role permissions ± overrides)
# --------------------------------------------------------------------------- #
def _role_codes(db: Session, role_id: int) -> set[str]:
    return {
        c[0] for c in db.execute(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role_id)
        ).all()
    }


@router.get("/{user_id}/permissions", response_model=UserPermissionsOut)
def get_user_permissions(user_id: int, db: Session = Depends(get_db),
                         _=Depends(require_permission("Roles & Permissions:manage_permissions"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    role_codes = _role_codes(db, user.role_id)
    overrides = db.execute(
        select(Permission.code, UserPermissionOverride.allow)
        .join(UserPermissionOverride, UserPermissionOverride.permission_id == Permission.id)
        .where(UserPermissionOverride.user_id == user.id)
    ).all()
    allow = [c for c, a in overrides if a]
    deny = [c for c, a in overrides if not a]
    role = db.get(Role, user.role_id)
    effective = (sorted(c[0] for c in db.execute(select(Permission.code)).all())
                 if role and role.name == "Owner"
                 else sorted(effective_permission_codes(db, user)))
    return UserPermissionsOut(
        role_codes=sorted(role_codes), override_allow=sorted(allow),
        override_deny=sorted(deny), effective=effective,
    )


@router.put("/{user_id}/overrides", response_model=UserPermissionsOut)
def set_user_overrides(user_id: int, payload: UserOverridesUpdate,
                       db: Session = Depends(get_db),
                       actor: User = Depends(require_permission("Roles & Permissions:manage_permissions"))):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    code_to_id = {c: pid for pid, c in db.execute(select(Permission.id, Permission.code)).all()}
    # Replace the user's overrides wholesale.
    db.query(UserPermissionOverride).filter(UserPermissionOverride.user_id == user_id).delete()
    seen: set[str] = set()
    for code in payload.allow:
        if code in code_to_id and code not in seen:
            db.add(UserPermissionOverride(user_id=user_id, permission_id=code_to_id[code], allow=True))
            seen.add(code)
    for code in payload.deny:
        if code in code_to_id and code not in seen:
            db.add(UserPermissionOverride(user_id=user_id, permission_id=code_to_id[code], allow=False))
            seen.add(code)
    log_action(db, actor.id, "Roles & Permissions", "manage_permissions", "User",
               user.id, new_value={"allow": payload.allow, "deny": payload.deny})
    db.commit()
    return get_user_permissions(user_id, db)  # type: ignore[arg-type]
