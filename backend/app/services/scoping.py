"""Dealer visibility scoping.

Owner / Admin / Manager: all dealers.
Salesman: only dealers assigned to them.
Dealer/Partner: only their own dealer record (user.assigned_dealer_id).
Other roles (Accounts, Telecaller, Dispatch): all dealers (read for their function).
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Dealer, Role, User


def dealer_scope_ids(db: Session, user: User) -> list[int] | None:
    """Return a list of dealer ids the user may see, or None for unrestricted."""
    role = db.get(Role, user.role_id)
    rname = role.name if role else ""
    if rname in ("Owner", "Admin", "Manager", "Accounts Team", "Telecaller", "Dispatch Team"):
        return None  # unrestricted
    if rname == "Salesman":
        rows = db.execute(select(Dealer.id).where(Dealer.assigned_salesman_id == user.id)).all()
        return [r[0] for r in rows]
    if rname == "Dealer/Partner":
        return [user.assigned_dealer_id] if user.assigned_dealer_id else []
    return None
