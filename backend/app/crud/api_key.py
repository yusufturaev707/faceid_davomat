import hashlib
import secrets

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.api_key import ApiKey

PREFIX = "sk-"


def _hash_key(raw_key: str) -> str:
    """API kalitni SHA-256 bilan hashlash."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def create_api_key(db: Session, user_id: int, name: str) -> tuple[ApiKey, str]:
    """Yangi API kalit yaratish. DB ga hash saqlanadi.
    Returns: (api_key_record, raw_key) — raw_key faqat bir marta ko'rsatiladi.
    """
    random_part = secrets.token_urlsafe(48)
    raw_key = f"{PREFIX}{random_part}"
    key_hash = _hash_key(raw_key)
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
    """Raw kalitni hashlab DB dan topish."""
    key_hash = _hash_key(raw_key)
    return db.execute(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.is_active == True,  # noqa: E712
        )
    ).scalar_one_or_none()


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
