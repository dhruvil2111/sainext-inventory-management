from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_permission
from app.models import (
    User, Warehouse, Product, Order, StockBlock, Dealer, StockItem,
)
from app.models.enums import OrderStatus, BlockStatus

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
def stats(db: Session = Depends(get_db),
          _=Depends(require_permission("Dashboard:view"))):
    def count(model, *where):
        stmt = select(func.count()).select_from(model)
        for w in where:
            stmt = stmt.where(w)
        return db.scalar(stmt) or 0

    return {
        "users": count(User),
        "warehouses": count(Warehouse),
        "products": count(Product),
        "dealers": count(Dealer),
        "stock_items": count(StockItem),
        "orders_total": count(Order),
        "orders_pending": count(Order, Order.status == OrderStatus.PENDING_APPROVAL),
        "blocks_pending": count(StockBlock, StockBlock.status == BlockStatus.PENDING_APPROVAL),
        "blocks_approved": count(StockBlock, StockBlock.status == BlockStatus.APPROVED),
    }
