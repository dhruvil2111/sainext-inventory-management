from sqlalchemy.orm import Session
from app.models import AuditLog


def log_action(db: Session, user_id, module, action, record_type=None,
               record_id=None, old_value=None, new_value=None):
    db.add(AuditLog(
        user_id=user_id, module=module, action=action,
        record_type=record_type, record_id=record_id,
        old_value=old_value, new_value=new_value,
    ))
