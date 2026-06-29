from fastapi import APIRouter

from app.api.routes import (
    auth, permissions, roles, users, warehouses, dashboard, products, stock,
    blocks, orders, dealers, dashboards, reports, settings, audit, notifications,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(dashboard.router)
api_router.include_router(permissions.router)
api_router.include_router(roles.router)
api_router.include_router(users.router)
api_router.include_router(warehouses.router)
api_router.include_router(products.router)
api_router.include_router(stock.router)
api_router.include_router(blocks.router)
api_router.include_router(orders.router)
api_router.include_router(dealers.router)
api_router.include_router(dashboards.router)
api_router.include_router(reports.router)
api_router.include_router(settings.router)
api_router.include_router(audit.router)
api_router.include_router(notifications.router)
