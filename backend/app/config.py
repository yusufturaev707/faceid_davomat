from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_INSECURE_SECRETS: set[str] = {
    "change-me-in-production-use-openssl-rand-hex-32",
    "CHANGE_ME__generate_with_secrets.token_urlsafe_48",
    "changeme",
    "secret",
}


class Settings(BaseSettings):
    # === Pydantic config — MUHIM, comment qilinmasin! ===
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,  # JWT_ISSUER == jwt_issuer
        extra="ignore",  # Noma'lum fieldlarni e'tiborsiz qoldirish
    )

    # Ilova nomi
    APP_NAME: str
    API_V1_PREFIX: str

    # JWT sozlamalari
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_ISSUER: str = "faceid-api"

    # API key hashlash uchun server-side pepper (SECRET_KEY'dan alohida).
    # Majburiy — bo'sh qoldirmang. Rotatsiya uchun: eski kalitlarni bekor qilib qayta yaratish.
    API_KEY_PEPPER: str

    # Refresh token
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # Login lockout
    LOGIN_LOCKOUT_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_WINDOW_SECONDS: int = 900
    LOGIN_LOCKOUT_DURATION_SECONDS: int = 900

    # CSRF
    CSRF_PROTECTION_ENABLED: bool = True

    # /metrics himoyasi
    METRICS_AUTH_TOKEN: str = ""

    # Cookie
    COOKIE_DOMAIN: str = ""

    # Database
    DATABASE_URL: str

    # DB connection pool va timeoutlar.
    # Idle ulanishlar firewall/NAT tomonidan jimgina uzilganda ("half-open"
    # socket) — keepalives ularni tirik tutadi va o'lganini tez aniqlaydi,
    # statement_timeout esa hech bir so'rov cheksiz "pending" qolmasligini
    # kafolatlaydi. Hammasi default qiymatli — .env ga qo'shish shart emas.
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    # NAT/firewall idle timeout odatda ≥5 daqiqa — undan past qiymat
    # ulanishni eskirishidan oldin yangilaydi.
    DB_POOL_RECYCLE: int = 280
    # Yangi ulanish o'rnatish uchun cap (sekund).
    DB_CONNECT_TIMEOUT: int = 10
    # Server tomonida har bir SQL statement uchun qattiq limit (millisekund).
    # Celery batch tasklari (student loader DELETE/INSERT) ham shu engine'dan
    # foydalanadi — qiymat ular uchun yetarli darajada katta.
    DB_STATEMENT_TIMEOUT_MS: int = 60000

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

    # CORS — Production'da .env orqali aniq domain ro'yxati berilishi shart.
    # Default faqat localhost dev uchun.
    # CORS_ORIGINS: list[str] = []
    CORS_ORIGINS: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins ro'yxat ko'rinishida."""
        if not self.CORS_ORIGINS:
            return []
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]

    # Tashqi API
    API_CEFR: str = ""
    API_MS: str = ""
    API_IIV: str = ""
    API_IIV_TOKEN: str = ""
    API_GTSP: str = ""

    @field_validator("SECRET_KEY", "API_KEY_PEPPER")
    @classmethod
    def _reject_insecure_secrets(cls, v: str, info) -> str:
        if not v or v.strip() in _INSECURE_SECRETS or len(v) < 32:
            raise ValueError(
                f"{info.field_name} placeholder/zaif qiymatga ega. "
                'Yangi qiymat: python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return v


settings = Settings()
