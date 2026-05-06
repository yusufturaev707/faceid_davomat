import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
    get_swagger_ui_oauth2_redirect_html,
)
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
from app.core.middleware import RequestIdMiddleware, get_metrics_text
from app.core.permission_sync import sync_permission_catalog
from app.core.rate_limit import limiter
from app.core.security_headers import SecurityHeadersMiddleware
from app.db.session import engine
from app.services.face_service import init_face_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    # Startup: DB ulanishini tekshirish
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    logger.info("DB ulanishi muvaffaqiyatli!")

    # Permission catalog avto-sinxronlash (yangi permissionlar DB ga tushadi,
    # admin roliga to'liq biriktiriladi). Idempotent.
    try:
        sync_permission_catalog()
    except Exception:
        logger.exception("Permission catalog sync startup'da xato — davom etilmoqda")

    # InsightFace modelni background threadda yuklash
    # (embedding endpoint sinxron ishlatadi, shuning uchun kerak)
    threading.Thread(target=init_face_app, daemon=True).start()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Yuz aniqlash va rasm tekshiruv API",
    lifespan=lifespan,
    docs_url=None,  # Default /docs ni o'chirish
    redoc_url=None,  # Default /redoc ni o'chirish
)

# Static fayllarni mount qilish
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Security headers (eng tashqi — har javobga ulaniadi)
app.add_middleware(SecurityHeadersMiddleware)

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
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-API-Key",
        "X-Request-ID",
        "X-CSRF-Token",
    ],
    expose_headers=["X-Request-ID"],
)

# API routerlarini ulash
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    """Sog'liqni tekshirish endpointi."""
    return {"status": "ok"}


@app.get("/metrics", tags=["ops"], include_in_schema=False)
def metrics(request: Request):
    """Prometheus-compatible text format. METRICS_AUTH_TOKEN o'rnatilgan bo'lsa,
    so'rovda `Authorization: Bearer <token>` bo'lishi shart. Bo'sh bo'lsa endpoint o'chiriladi."""
    import secrets as _secrets

    from fastapi import HTTPException
    from fastapi.responses import PlainTextResponse

    expected = settings.METRICS_AUTH_TOKEN
    if not expected:
        raise HTTPException(status_code=404, detail="Not found")

    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer ") or not _secrets.compare_digest(
        auth[7:], expected
    ):
        raise HTTPException(status_code=401, detail="Unauthorized")

    return PlainTextResponse(get_metrics_text(), media_type="text/plain; version=0.0.4")


# Custom Swagger UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger/swagger-ui.css",
        swagger_favicon_url="/static/swagger/favicon-32x32.png",
    )


@app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
async def swagger_ui_redirect():
    return get_swagger_ui_oauth2_redirect_html()


# Custom ReDoc
@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url=app.openapi_url,
        title=app.title + " - ReDoc",
        redoc_js_url="/static/swagger/redoc.standalone.js",  # ReDoc kerak bo'lsa
    )
