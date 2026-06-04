"""Bot konfiguratsiyasi. Barcha sozlamalar .env faylidan o'qiladi."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_admin_ids(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.replace(" ", "").split(","):
        if part:
            try:
                ids.add(int(part))
            except ValueError:
                continue
    return ids


@dataclass
class Config:
    bot_token: str = os.getenv("BOT_TOKEN", "")
    api_url: str = os.getenv("API_URL", "")
    api_token: str = os.getenv("API_TOKEN", "")
    cache_ttl: int = int(os.getenv("CACHE_TTL", "60"))
    admin_ids: set[int] = field(
        default_factory=lambda: _parse_admin_ids(
            os.getenv("ADMIN_IDS", "811104615")
        )
    )


config = Config()
