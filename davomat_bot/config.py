"""Davomat bot sozlamalari (env orqali).

`pydantic-settings` `.env` ni odatda CWD ga nisbatan qidiradi — biz uni
`config.py` joylashgan papkaga nisbatan absolyut qilib beramiz, shunda
bot qaysi katalogdan ishga tushirilishidan qat'i nazar topadi.
`.env` topilmasa, fallback sifatida `.env.example` ham qabul qilinadi.
"""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Tuple — pydantic-settings birinchi mavjud faylni ishlatadi,
        # `.env` ustun, topilmasa `.env.example` ga tushadi.
        env_file=(_BASE_DIR / ".env", _BASE_DIR / ".env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    BOT_TOKEN: str
    API_BASE_URL: str = "http://localhost:8000/api/v1"
    API_KEY: str

    LOG_LEVEL: str = "INFO"
    REQUEST_TIMEOUT: float = 60.0


settings = Settings()
