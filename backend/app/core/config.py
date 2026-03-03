from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ilova nomi
    APP_NAME: str = "FaceID Verification API"
    API_V1_PREFIX: str = "/api/v1"

    # JWT sozlamalari
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "postgresql://postgres:4144@localhost:5432/faceid_db"

    # Rasm tekshiruv parametrlari
    MAX_BASE64_SIZE: int = 10 * 1024 * 1024  # 10 MB
    REQUIRED_WIDTH: int = 354
    REQUIRED_HEIGHT: int = 472
    MIN_PALITRA_VALUE: int = 50
    AGE_TOLERANCE: int = 5  # ± yillar

    # Rasm saqlash
    UPLOADS_DIR: str = "uploads/verifications"
    THUMBNAIL_SIZE: int = 150  # thumbnail kengligi px
    WEBP_QUALITY: int = 80  # WebP sifati (0-100)

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    class Config:
        env_file = ".env"


settings = Settings()
