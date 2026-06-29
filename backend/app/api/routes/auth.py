from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.limiter import limiter
from app.core.security import (
    create_access_token, create_refresh_token, decode_token, verify_password, REFRESH,
)
from app.models import User, Role, RevokedToken, Permission
from app.schemas import Token, MeOut, RefreshRequest
from app.services.permissions import effective_permission_codes

router = APIRouter(prefix="/auth", tags=["auth"])


def _is_revoked(db: Session, jti: str) -> bool:
    return db.execute(select(RevokedToken).where(RevokedToken.jti == jti)).scalar_one_or_none() is not None


def _issue_tokens(user: User) -> Token:
    access = create_access_token(user.id)
    refresh, _jti, _exp = create_refresh_token(user.id)
    return Token(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(),
          db: Session = Depends(get_db)):
    user = db.execute(select(User).where(User.email == form.username)).scalar_one_or_none()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if user.status.value != "active":
        raise HTTPException(status_code=403, detail="Account is not active")
    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    cred_exc = HTTPException(status_code=401, detail="Invalid or expired refresh token")
    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise cred_exc
    if data.get("type") != REFRESH:
        raise cred_exc
    jti = data.get("jti")
    if not jti or _is_revoked(db, jti):
        raise cred_exc
    user = db.get(User, int(data.get("sub")))
    if not user or user.status.value != "active":
        raise cred_exc
    # rotate: revoke the old refresh jti, issue a fresh pair
    db.add(RevokedToken(jti=jti, expires_at=datetime.fromtimestamp(data["exp"], tz=timezone.utc)))
    db.commit()
    return _issue_tokens(user)


@router.post("/logout")
def logout(payload: RefreshRequest | None = None, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    # Revoke the presented refresh token so it can no longer mint access tokens.
    if payload and payload.refresh_token:
        try:
            data = decode_token(payload.refresh_token)
            if data.get("type") == REFRESH and data.get("jti") and not _is_revoked(db, data["jti"]):
                db.add(RevokedToken(
                    jti=data["jti"],
                    expires_at=datetime.fromtimestamp(data["exp"], tz=timezone.utc)))
                db.commit()
        except JWTError:
            pass
    return {"detail": "Logged out"}


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    role = db.get(Role, user.role_id)
    perms = sorted(effective_permission_codes(db, user))
    if role and role.name == "Owner":
        perms = sorted(c[0] for c in db.execute(select(Permission.code)).all())
    return MeOut(
        id=user.id, name=user.name, email=user.email, mobile=user.mobile,
        role_id=user.role_id, status=user.status.value,
        assigned_warehouse_id=user.assigned_warehouse_id,
        created_at=user.created_at, role_name=role.name if role else "",
        permissions=perms,
    )
