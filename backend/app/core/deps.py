from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User
from app.models.enums import UserStatus
from app.services.permissions import effective_permission_codes, is_owner

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    cred_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        if payload.get("type", "access") != "access":
            raise cred_exc          # refresh tokens cannot authenticate requests
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise cred_exc
    user = db.get(User, user_id)
    if user is None:
        raise cred_exc
    if user.status != UserStatus.active:
        raise HTTPException(status_code=403, detail="User account is not active")
    return user


def require_permission(code: str):
    """Dependency factory enforcing a single permission code (module:action).

    Owner always passes. This is the server-side gate; the frontend hiding is
    only cosmetic.
    """
    def checker(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        if is_owner(user, db):
            return user
        if code not in effective_permission_codes(db, user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {code}",
            )
        return user
    return checker


def require_any_permission(*codes: str):
    """Passes if the user holds ANY of the given permission codes (Owner always
    passes). Useful where multiple roles legitimately perform an action, e.g.
    order dispatch transitions (Orders:edit OR Dispatch:edit)."""
    def checker(
        user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        if is_owner(user, db):
            return user
        held = effective_permission_codes(db, user)
        if not any(c in held for c in codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: one of {', '.join(codes)}",
            )
        return user
    return checker
