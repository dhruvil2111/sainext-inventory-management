import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import Setting, User
from app.services.audit import log_action

router = APIRouter(prefix="/settings", tags=["settings"])

DEFAULT_BRANDING = {
    "company_name": "Sainext",
    "currency": "INR",
    "brand_primary": "#121824",
    "brand_accent": "#c98a1a",
    "company_logo": None,        # base64 data URL when uploaded
}

LOGO_MAX_BYTES = 1_000_000       # 1 MB
LOGO_TYPES = {"image/png", "image/jpeg", "image/svg+xml", "image/webp", "image/gif"}


class SettingIn(BaseModel):
    key: str
    value: object


def _get(db: Session, key: str, default=None):
    s = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    return s.value if s else default


def _set(db: Session, key: str, value):
    s = db.execute(select(Setting).where(Setting.key == key)).scalar_one_or_none()
    if s:
        s.value = value
    else:
        db.add(Setting(key=key, value=value))


@router.get("/branding")
def branding(db: Session = Depends(get_db)):
    """Public brand/company config (colors, name, logo) — drives the UI theme.
    Not sensitive; available pre-login so the sign-in screen can be branded too."""
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
    _set(db, payload.key, payload.value)
    log_action(db, actor.id, "Settings", "edit", "Setting", None,
               new_value={payload.key: payload.value})
    db.commit()
    return {"key": payload.key, "value": payload.value}


@router.post("/logo")
def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Settings:edit"))):
    ctype = (file.content_type or "").split(";")[0].strip().lower()
    if ctype not in LOGO_TYPES:
        raise HTTPException(400, "Unsupported image type (use PNG, JPG, SVG, WEBP or GIF)")
    data = file.file.read()
    if len(data) > LOGO_MAX_BYTES:
        raise HTTPException(400, "Logo too large (max 1 MB)")
    if not data:
        raise HTTPException(400, "Empty file")
    data_url = f"data:{ctype};base64,{base64.b64encode(data).decode()}"
    _set(db, "company_logo", data_url)
    log_action(db, actor.id, "Settings", "edit", "Setting", None,
               new_value={"company_logo": f"<{ctype}, {len(data)} bytes>"})
    db.commit()
    return {"company_logo": data_url}


@router.delete("/logo")
def remove_logo(db: Session = Depends(get_db),
                actor: User = Depends(require_permission("Settings:edit"))):
    _set(db, "company_logo", None)
    log_action(db, actor.id, "Settings", "edit", "Setting", None,
               new_value={"company_logo": None})
    db.commit()
    return {"company_logo": None}
