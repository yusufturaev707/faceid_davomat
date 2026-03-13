import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1.router import api_router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import logger, setup_logging
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
    threading.Thread(target=init_face_app, daemon=True).start()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Yuz aniqlash va rasm tekshiruv API",
    lifespan=lifespan,
)

# Exception handlers
register_exception_handlers(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routerlarini ulash
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["health"])
def health_check():
    """Sog'liqni tekshirish endpointi."""
    return {"status": "ok"}
