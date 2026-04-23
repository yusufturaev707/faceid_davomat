"""Pytest fixtures.

MUHIM: production DB ni ishlatmaslik uchun har bir test run uchun in-memory
SQLite yaratiladi. Shuningdek, `settings` obyekti'ga test qiymatlari qo'yiladi.
"""

import os
import tempfile

# Testlarda albatta ishlash kerak bo'lgan env qiymatlar — settings obyekti
# yuklashdan oldin o'rnatilishi shart.
os.environ.setdefault("APP_NAME", "FaceID Test")
os.environ.setdefault("API_V1_PREFIX", "/api/v1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-do-not-use-in-prod")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "7")
os.environ.setdefault("API_KEY_PEPPER", "test-pepper-12345")
os.environ.setdefault(
    "DATABASE_URL", f"sqlite:///{tempfile.gettempdir()}/faceid_test.db"
)
os.environ.setdefault("MAX_BASE64_SIZE", "5242880")
os.environ.setdefault("MIN_WIDTH", "100")
os.environ.setdefault("MAX_WIDTH", "1000")
os.environ.setdefault("MIN_HEIGHT", "100")
os.environ.setdefault("MAX_HEIGHT", "1000")
os.environ.setdefault("MIN_PALITRA_VALUE", "0")
os.environ.setdefault("AGE_TOLERANCE", "10")
os.environ.setdefault("SIMILARITY_THRESHOLD", "0.45")
os.environ.setdefault("BG_COLOR_THRESHOLD", "100")
os.environ.setdefault("UPLOADS_PHOTO_DIR", tempfile.mkdtemp())
os.environ.setdefault("UPLOADS_FACE_DIR", tempfile.mkdtemp())
os.environ.setdefault("THUMBNAIL_SIZE", "150")
os.environ.setdefault("WEBP_QUALITY", "80")
os.environ.setdefault("MAX_CONCURRENT_INFERENCE", "2")
os.environ.setdefault("INFERENCE_TIMEOUT_SECONDS", "10")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("TASK_RESULT_TTL", "60")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost"]')

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.dependencies import get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    """In-memory SQLite — tezkor, izolyatsiyalangan."""
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture(scope="session")
def tables(engine):
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(engine, tables):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
