from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission, get_current_user
from app.models import Setting, User
from app.services.audit import log_action
from pydantic import BaseModel

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_BRANDING = {
    "company_name": "Sainext",
    "currency": "INR",
    "brand_primary": "#121824",
    "brand_accent": "#c98a1a",
}


class SettingIn(BaseModel):
    key: str
    value: object


def _get(db: Session, key: str, default=None):
    s = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    return s.value if s else default


@router.get("/branding")
def branding(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Brand/company config available to any authenticated user (drives the UI theme)."""
    return {k: _get(db, k, v) for k, v in DEFAULT_BRANDING.items()}


@router.get("")
def list_settings(db: Session = Depends(get_db),
                  _=Depends(require_permission("Settings:view"))):
    rows = db.execute(select(Setting).order_by(Setting.key)).scalars().all()
    out = {s.key: s.value for s in rows}
    for k, v in DEFAULT_BRANDING.items():
        out.setdefault(k, v)
    return out


@router.put("")
def upsert_setting(payload: SettingIn, db: Session = Depends(get_db),
                   actor: User = Depends(require_permission("Settings:edit"))):
    s = db.execute(select(Setting).where(Setting.key == payload.key)).scalar_one_or_none()
    if s:
        s.value = payload.value
    else:
        s = Setting(key=payload.key, value=payload.value)
        db.add(s)
    log_action(db, actor.id, "Settings", "edit", "Setting", None,
               new_value={payload.key: payload.value})
    db.commit()
    return {"key": payload.key, "value": payload.value}
