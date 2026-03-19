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

    # Backpressure
    QUEUE_MAX_SIZE: int = 100
    BACKPRESSURE_RETRY_AFTER: int = 5

    # Celery tuning
    TASK_TIME_LIMIT: int = 30
    WORKER_MAX_TASKS_PER_CHILD: int = 500

    # Image decoder
    MAX_IMAGE_DIMENSION: int = 4096

    # Cookie
    COOKIE_SECURE: bool = True

    # CORS
    CORS_ORIGINS: list[str]

    # Tashqi API
    API_CEFR: str = ""
    API_MS: str = ""
    API_IIV: str = ""
    API_IIV_TOKEN: str = ""
    API_GTSP: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
