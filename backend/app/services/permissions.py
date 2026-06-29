"""Effective-permission resolution: role permissions +/- per-user overrides."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    User, Role, RolePermission, Permission, UserPermissionOverride,
)


def effective_permission_codes(db: Session, user: User) -> set[str]:
    codes: set[str] = set()

    # 1. role permissions
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == user.role_id)
    ).all()
    codes.update(r[0] for r in rows)

    # 2. per-user overrides (allow=True adds, allow=False removes)
    overrides = db.execute(
        select(Permission.code, UserPermissionOverride.allow)
        .join(UserPermissionOverride, UserPermissionOverride.permission_id == Permission.id)
        .where(UserPermissionOverride.user_id == user.id)
    ).all()
    for code, allow in overrides:
        if allow:
            codes.add(code)
        else:
            codes.discard(code)

    return codes


def is_owner(user: User, db: Session) -> bool:
    role = db.get(Role, user.role_id)
    return bool(role and role.name == "Owner")
