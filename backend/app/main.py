import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.core.middleware import RequestIdMiddleware, get_metrics_text
from app.core.rate_limit import limiter
from app.db.session import engine
from app.services.face_service import init_face_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Startup: DB ulanishini tekshirish
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("DB ulanishi muvaffaqiyatli!")

    # InsightFace modelni background threadda yuklash
    # (embedding endpoint sinxron ishlatadi, shuning uchun kerak)
    threading.Thread(target=init_face_app, daemon=True).start()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Yuz aniqlash va rasm tekshiruv API",
    lifespan=lifespan,
)

# Request ID + access log + metrics
app.add_middleware(RequestIdMiddleware)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Exception handlers
register_exception_handlers(app)

# CORS middleware — explicit methods/headers (security best practice)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)

# API routerlarini ulash
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    """Sog'liqni tekshirish endpointi."""
    return {"status": "ok"}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics():
    """Prometheus-compatible text format. Oddiy HTTP counter + latency."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(get_metrics_text(), media_type="text/plain; version=0.0.4")
