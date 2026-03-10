from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Ilova nomi
    APP_NAME: str
    API_V1_PREFIX: str

    # JWT sozlamalari
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Database
    DATABASE_URL: str

    # Rasm tekshiruv parametrlari
    MAX_BASE64_SIZE: int
    MIN_WIDTH: int
    MAX_WIDTH: int
    MIN_HEIGHT: int
    MAX_HEIGHT: int
    MIN_PALITRA_VALUE: int
    AGE_TOLERANCE: int
    SIMILARITY_THRESHOLD: float
    BG_COLOR_THRESHOLD: int

    # Rasm saqlash
    UPLOADS_PHOTO_DIR: str
    UPLOADS_FACE_DIR: str
    THUMBNAIL_SIZE: int
    WEBP_QUALITY: int

    # ML Inference
    MAX_CONCURRENT_INFERENCE: int
    INFERENCE_TIMEOUT_SECONDS: float
    FACE_DET_SIZE: int = 320
    FACE_DET_THRESH: float = 0.3

    # Celery / Redis
    REDIS_URL: str
    TASK_RESULT_TTL: int

    # CORS
    CORS_ORIGINS: list[str]

    class Config:
        env_file = ".env"


settings = Settings()
