import hashlib
import hmac
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models.api_key import ApiKey

PREFIX = "sk-"
HASH_VERSION = "v2"  # HMAC-SHA256 versiyasi


def _pepper() -> bytes:
    """Server-side pepper. API_KEY_PEPPER majburiy — config.py darajasida validatsiya."""
    if not settings.API_KEY_PEPPER:
        raise RuntimeError("API_KEY_PEPPER bo'sh — .env da qiymat kiriting")
    return settings.API_KEY_PEPPER.encode()


def _hash_v2(raw_key: str) -> str:
    """HMAC-SHA256 bilan hashlash (server-side pepper)."""
    digest = hmac.new(_pepper(), raw_key.encode(), hashlib.sha256).hexdigest()
    return f"{HASH_VERSION}:{digest}"


def _hash_legacy(raw_key: str) -> str:
    """Eski API kalitlari uchun: oddiy SHA-256 (peppersiz)."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _verify(raw_key: str, stored_hash: str) -> bool:
    """Timing-safe tekshirish. v2 yoki legacy hashni qo'llaydi."""
    if stored_hash.startswith(f"{HASH_VERSION}:"):
        return hmac.compare_digest(stored_hash, _hash_v2(raw_key))
    return hmac.compare_digest(stored_hash, _hash_legacy(raw_key))


def create_api_key(db: Session, user_id: int, name: str) -> tuple[ApiKey, str]:
    """Yangi API kalit yaratish. DB ga HMAC-SHA256 hash saqlanadi.
    Returns: (api_key_record, raw_key) — raw_key faqat bir marta ko'rsatiladi.
    """
    random_part = secrets.token_urlsafe(48)
    raw_key = f"{PREFIX}{random_part}"
    key_hash = _hash_v2(raw_key)
    prefix = raw_key[:12]

    api_key = ApiKey(
        user_id=user_id,
        key_hash=key_hash,
        prefix=prefix,
        name=name,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def get_api_key_by_raw(db: Session, raw_key: str) -> ApiKey | None:
    """Raw kalitni hashlab DB dan topish. v2 va legacy hashlarni qo'llaydi."""
    v2_hash = _hash_v2(raw_key)
    legacy_hash = _hash_legacy(raw_key)
    row = db.execute(
        select(ApiKey).where(
            ApiKey.key_hash.in_([v2_hash, legacy_hash]),
            ApiKey.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    # Constant-time tekshirish (SQL IN filter kifoya emas, DB-ga teng emas).
    if _verify(raw_key, row.key_hash):
        return row
    return None


def update_last_used(db: Session, api_key: ApiKey) -> None:
    """Oxirgi ishlatilgan vaqtni yangilash."""
    from datetime import datetime, timezone

    db.execute(
        update(ApiKey)
        .where(ApiKey.id == api_key.id)
        .values(last_used_at=datetime.now(timezone.utc))
    )
    db.commit()


def revoke_api_key(db: Session, key_id: int) -> ApiKey | None:
    """API kalitni bekor qilish."""
    api_key = db.get(ApiKey, key_id)
    if api_key:
        api_key.is_active = False
        db.commit()
        db.refresh(api_key)
    return api_key


def get_api_keys_by_user(db: Session, user_id: int) -> list[ApiKey]:
    """Foydalanuvchining barcha API kalitlarini olish."""
    return list(
        db.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        ).scalars().all()
    )


def get_all_api_keys(db: Session) -> list[ApiKey]:
    """Barcha API kalitlarni olish (admin uchun)."""
    return list(
        db.execute(
            select(ApiKey).order_by(ApiKey.created_at.desc())
        ).scalars().all()
    )
