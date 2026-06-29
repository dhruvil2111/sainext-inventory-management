import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.database import Base, engine
from app.core.limiter import limiter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sainext")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Conservative security headers for an API + SPA behind a proxy."""
    async def dispatch(self, request: Request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        resp.headers.setdefault("X-XSS-Protection", "0")
        if settings.ENABLE_HSTS:
            resp.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return resp


def _ensure_columns():
    """Lightweight dev migration: add columns introduced after a table already
    exists (create_all never ALTERs). Idempotent; Postgres only. For a full
    production setup this would be replaced by Alembic migrations."""
    if engine.dialect.name != "postgresql":
        return  # fresh sqlite/test DBs already have the latest schema
    statements = [
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_salesman_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS assigned_dealer_id INTEGER",
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS monthly_target DOUBLE PRECISION DEFAULT 0",
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))

app = FastAPI(
    title="Sainext API",
    version="0.1.0",
    description="Inventory, stock check, blocking, orders & RBAC backend.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    # Import models so metadata is populated before create_all.
    import app.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    if settings.SEED_ON_STARTUP:
        from app.seed import run_seed
        try:
            run_seed()
            logger.info("Seed completed.")
        except Exception as exc:  # pragma: no cover
            logger.exception("Seed failed: %s", exc)
