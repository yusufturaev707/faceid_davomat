"""Bot konfiguratsiyasi. Barcha sozlamalar .env faylidan o'qiladi.

Bot endi tashqi APIdan to'g'ridan-to'g'ri emas, FaceID backend (FastAPI)
orqali ishlaydi:
  - Foydalanuvchi dostupi/roli — backend DB dan (`/statistic-bot/check/...`).
  - Statistika — backend tashqi APIdan oladi (`/statistic-bot/statistics`).

Backendga `X-API-Key` orqali ulanadi (davomat_bot bilan bir xil pattern).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    # FaceID backend manzili (masalan: https://face-id.uzbmb.uz/api/v1).
    api_base_url: str = os.getenv(
        "API_BASE_URL", "http://localhost:8000/api/v1"
    ).rstrip("/")
    # Admin panelda yaratilgan API kalit (X-API-Key headerida yuboriladi).
    api_key: str = os.getenv("API_KEY", "")
    request_timeout: float = float(os.getenv("REQUEST_TIMEOUT", "30"))


config = Config()
