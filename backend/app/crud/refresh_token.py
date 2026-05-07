"""Refresh token CRUD — hashlangan saqlash + reuse detection.

Xavfsizlik prinsipi:
- DB faqat SHA-256 hash saqlaydi → DB sizib chiqsa raw token tiklanmaydi.
- Rotatsiya zanjirida `family_id` saqlanadi. Eski (replaced) tokenni qayta
  ishlatish urinishi `replaced_by_hash` orqali sezilsa, butun oila bekor
  qilinadi (RFC 6819 — token theft detection).
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import settings
from app.models.refresh_token import RefreshToken

logger = logging.getLogger("faceid.crud.refresh_token")


def _hash_token(token_str: str) -> str:
    """SHA-256 — raw token uzun random qiymat (256 bit), pepper kerak emas."""
    return hashlib.sha256(token_str.encode()).hexdigest()


def create_refresh_token(
    db: Session,
    user_id: int,
    family_id: str | None = None,
) -> str:
    """Yangi refresh token yaratish va DB ga hashlangan holda saqlash.

    Args:
        family_id: Mavjud bo'lsa zanjir davom etadi (rotatsiya), aks holda yangi oila.

    Returns:
        Raw token (faqat clientga beriladi, DB ga emas).
    """
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )
    token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id or str(uuid.uuid4()),
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    return raw_token


def get_refresh_token_record(
    db: Session, token_str: str, *, for_update: bool = False
) -> RefreshToken | None:
    """Raw tokenni hashlab DB dan topish (revoked/expired ham qaytarilishi mumkin)."""
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == _hash_token(token_str)
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def get_record_by_hash(
    db: Session, token_hash: str
) -> RefreshToken | None:
    """Hash bo'yicha to'g'ridan-to'g'ri topish (replaced_by_hash uchun)."""
    return db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    ).scalar_one_or_none()


def get_valid_refresh_token(
    db: Session, token_str: str, *, for_update: bool = False
) -> RefreshToken | None:
    """Yaroqli (revoke qilinmagan, muddati tugamagan) refresh token."""
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == _hash_token(token_str),
        RefreshToken.revoked == False,  # noqa: E712
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    if for_update:
        stmt = stmt.with_for_update()
    return db.execute(stmt).scalar_one_or_none()


def revoke_refresh_token(db: Session, token_str: str) -> None:
    """Bitta refresh tokenni bekor qilish (raw token bo'yicha)."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == _hash_token(token_str))
        .values(revoked=True)
    )
    db.commit()


def revoke_token_family(db: Session, family_id: str, reason: str = "rotation") -> int:
    """Butun token oilasini bekor qilish. Reuse aniqlanganda chaqiriladi.

    Returns: bekor qilingan tokenlar soni.
    """
    now = datetime.now(timezone.utc)
    values: dict = {"revoked": True}
    if reason == "reuse":
        values["reuse_detected_at"] = now
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
        .values(**values)
    )
    db.commit()
    count = result.rowcount or 0
    if reason == "reuse" and count > 0:
        logger.warning(
            "Refresh token REUSE aniqlandi! family_id=%s, %d token bekor qilindi",
            family_id,
            count,
        )
    return count


def mark_replaced(db: Session, old_token_str: str, new_token_str: str) -> None:
    """Eski tokenni revoked deb belgilab, yangi tokenning hash'ini saqlash."""
    mark_replaced_by_hash(db, _hash_token(old_token_str), new_token_str)


def mark_replaced_by_hash(
    db: Session, old_token_hash: str, new_token_str: str
) -> None:
    """Hash bo'yicha eski tokenni revoked deb belgilash (grace window uchun)."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == old_token_hash)
        .values(
            replaced_by_hash=_hash_token(new_token_str),
            revoked=True,
        )
    )
    db.commit()


def revoke_all_user_tokens(db: Session, user_id: int) -> int:
    """Foydalanuvchining barcha refresh tokenlarini bekor qilish.

    Parol o'zgartirilganda yoki user bloklanganda chaqiriladi.

    Returns: bekor qilingan tokenlar soni.
    """
    result = db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked == False,  # noqa: E712
        )
        .values(revoked=True)
    )
    db.commit()
    return result.rowcount or 0
