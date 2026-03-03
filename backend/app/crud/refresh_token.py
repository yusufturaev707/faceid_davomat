import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.refresh_token import RefreshToken


def create_refresh_token(db: Session, user_id: int) -> str:
    """Yangi refresh token yaratish va DB ga saqlash."""
    token_str = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    token = RefreshToken(
        user_id=user_id,
        token=token_str,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    return token_str


def get_valid_refresh_token(db: Session, token_str: str) -> RefreshToken | None:
    """Yaroqli (revoke qilinmagan, muddati tugamagan) refresh tokenni olish."""
    return db.execute(
        select(RefreshToken).where(
            RefreshToken.token == token_str,
            RefreshToken.revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    ).scalar_one_or_none()


def revoke_refresh_token(db: Session, token_str: str) -> None:
    """Refresh tokenni bekor qilish."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.token == token_str)
        .values(revoked=True)
    )
    db.commit()


def revoke_all_user_tokens(db: Session, user_id: int) -> None:
    """Foydalanuvchining barcha refresh tokenlarini bekor qilish."""
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)  # noqa: E712
        .values(revoked=True)
    )
    db.commit()
