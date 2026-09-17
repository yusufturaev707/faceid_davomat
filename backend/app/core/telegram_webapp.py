"""Telegram Mini App `initData` imzosini tekshirish.

Telegram Mini App ochilganda klient `Telegram.WebApp.initData` qatorini
oladi — URL-encoded maydonlar (`user`, `auth_date`, `query_id`, ...) va ular
ustidan bot tokeni bilan hisoblangan `hash`. Backend shu `hash` ni qayta
hisoblab, ma'lumot haqiqatan ham Telegram'dan kelganini va foydalanuvchi
(`user.id`) soxtalashtirilmaganini isbotlaydi.

Algoritm (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app):
  secret_key       = HMAC_SHA256(key="WebAppData", msg=bot_token)
  data_check_string = "\\n".join(sorted(f"{k}={v}" for k, v in fields if k != "hash"))
  hash             == hex(HMAC_SHA256(key=secret_key, msg=data_check_string))

Klient faqat `initData` ni yuboradi — `telegram_id` ni o'zi tanlay olmaydi.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlencode

# Telegram initData odatda ~1 KB. Kattasi — ataka yoki buzilgan so'rov.
_MAX_INIT_DATA_LEN = 8192
# Klient va server soatlari orasidagi ruxsat etilgan farq (sekund).
_CLOCK_SKEW_SECONDS = 300


class InitDataError(ValueError):
    """initData yaroqsiz. `expired=True` — imzo to'g'ri, lekin muddati o'tgan."""

    def __init__(self, message: str, *, expired: bool = False) -> None:
        super().__init__(message)
        self.expired = expired


@dataclass(frozen=True)
class TelegramWebAppUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def sign_init_data(fields: dict[str, str], bot_token: str) -> str:
    """Maydonlarni imzolab initData qatorini qaytaradi (testlar va lokal
    ishlab chiqish uchun — production'da initData'ni faqat Telegram yaratadi).
    """
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    digest = hmac.new(
        _secret_key(bot_token), data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    return urlencode({**fields, "hash": digest})


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int,
    now: float | None = None,
) -> TelegramWebAppUser:
    """initData ni tekshiradi va imzolangan foydalanuvchini qaytaradi.

    Raises:
        InitDataError: imzo mos kelmasa, format buzilgan bo'lsa yoki muddati
            o'tgan bo'lsa.
    """
    if not bot_token:
        raise InitDataError("Bot tokeni sozlanmagan")
    if not init_data or len(init_data) > _MAX_INIT_DATA_LEN:
        raise InitDataError("initData bo'sh yoki juda uzun")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError:
        raise InitDataError("initData formati buzilgan")

    fields: dict[str, str] = {}
    for key, value in pairs:
        if key in fields:
            # Dublikat kalit — imzolangan va ishlatiladigan qiymat boshqa-boshqa
            # bo'lib qolishi mumkin; bunday so'rovni umuman qabul qilmaymiz.
            raise InitDataError("initData da takroriy maydon")
        fields[key] = value

    received_hash = fields.pop("hash", "")
    if not received_hash:
        raise InitDataError("initData imzosi yo'q")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    expected_hash = hmac.new(
        _secret_key(bot_token), data_check_string.encode(), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_hash, received_hash.lower()):
        raise InitDataError("initData imzosi mos kelmadi")

    # Imzo to'g'ri — endi maydonlarga ishonsa bo'ladi.
    try:
        auth_date = int(fields.get("auth_date", ""))
    except ValueError:
        raise InitDataError("auth_date yaroqsiz")

    current = time.time() if now is None else now
    if auth_date > current + _CLOCK_SKEW_SECONDS:
        raise InitDataError("auth_date kelajakda")
    if current - auth_date > max_age_seconds:
        raise InitDataError("initData muddati tugagan", expired=True)

    try:
        raw_user = json.loads(fields.get("user", ""))
        user_id = int(raw_user["id"])
    except (ValueError, KeyError, TypeError):
        raise InitDataError("initData da foydalanuvchi yo'q")
    if user_id <= 0:
        raise InitDataError("Foydalanuvchi id yaroqsiz")

    return TelegramWebAppUser(
        id=user_id,
        first_name=str(raw_user.get("first_name") or ""),
        last_name=raw_user.get("last_name"),
        username=raw_user.get("username"),
        language_code=raw_user.get("language_code"),
    )
