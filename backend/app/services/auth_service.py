"""Authentication business logic.

Xavfsizlik xususiyatlari:
- Username enumeration timing himoyasi (dummy bcrypt har holda ishlaydi).
- Per-username login lockout (Redis).
- Failed login audit DB jadvalga yoziladi (forensic).
- Refresh token rotation + reuse detection (token-family revocation).
- Bloklangan foydalanuvchi tokenlari refresh qilinmaydi.
"""

import logging
from datetime import timedelta

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.redis_client import (
    is_login_locked,
    register_login_failure,
    reset_login_failures,
)
from app.core.security import (
    create_access_token,
    dummy_verify_password,
    verify_password,
)
from app.crud.failed_login_attempt import record_failed_login
from app.crud.refresh_token import (
    create_refresh_token,
    get_refresh_token_record,
    get_valid_refresh_token,
    mark_replaced,
    revoke_refresh_token,
    revoke_token_family,
)
from app.crud.user import get_user_by_username
from app.models.user import User
from app.schemas.auth import TokenPairResponse, UserResponse

logger = logging.getLogger("faceid.services.auth")


def _access_ttl_for(user: User) -> timedelta:
    """Admin uchun qisqaroq TTL (#22)."""
    if user.role_key == 1:
        return timedelta(minutes=settings.ADMIN_ACCESS_TOKEN_EXPIRE_MINUTES)
    return timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)


def authenticate_user(
    db: Session,
    username: str,
    password: str,
    ip_address: str = "unknown",
    user_agent: str | None = None,
) -> User:
    """Username + parol tekshiruvi.

    - Per-username lockout: brute-force limit oshsa 401.
    - Username enumeration timing fix: user yo'q bo'lsa ham bcrypt ishlatiladi.
    - Failed urinish DB'ga audit sifatida yoziladi (username, IP, UA, reason).
    """
    if is_login_locked(username):
        record_failed_login(db, username, ip_address, user_agent, reason="locked")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Hisob vaqtincha bloklangan. Bir oz vaqtdan so'ng urinib ko'ring.",
        )

    user = get_user_by_username(db, username)

    if user is None:
        # Timing-safe: bcrypt har holda ishga tushadi
        dummy_verify_password()
        register_login_failure(username)
        record_failed_login(db, username, ip_address, user_agent, reason="no_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not verify_password(password, user.hashed_password):
        register_login_failure(username)
        record_failed_login(
            db, username, ip_address, user_agent, reason="wrong_password"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not user.is_active:
        register_login_failure(username)
        record_failed_login(db, username, ip_address, user_agent, reason="inactive")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    reset_login_failures(username)
    return user


def create_token_pair(
    db: Session,
    user: User,
    family_id: str | None = None,
) -> tuple[str, str, str]:
    """Access token + refresh token juftligini yaratish.

    Returns: (access_token, refresh_token_str, jti)
    """
    access_token, jti = create_access_token(
        data={"sub": str(user.id), "role": user.role, "role_key": user.role_key},
        expires_delta=_access_ttl_for(user),
    )
    refresh_token = create_refresh_token(db, user.id, family_id=family_id)
    return access_token, refresh_token, jti


def rotate_refresh_token(
    db: Session, token_str: str
) -> tuple[TokenPairResponse, str]:
    """Eski refresh tokenni rotate qilib, yangi token juftligi qaytarish.

    Reuse detection (RFC 6819):
    - Agar revoke qilingan token kelsa va u allaqachon `replaced_by_hash`
      bilan zanjirlangan bo'lsa — bu token theft signali. Butun oilani
      bekor qilamiz va 401 qaytaramiz.
    """
    record = get_valid_refresh_token(db, token_str)

    if record is None:
        stale = get_refresh_token_record(db, token_str)
        if stale is not None and stale.replaced_by_hash is not None:
            revoke_token_family(db, stale.family_id, reason="reuse")
            logger.warning(
                "Refresh token reuse: user_id=%d, family=%s",
                stale.user_id,
                stale.family_id,
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan",
        )

    user = record.user
    if not user.is_active:
        revoke_token_family(db, record.family_id, reason="user_inactive")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )

    family_id = record.family_id
    access_token, new_refresh_token, _jti = create_token_pair(
        db, user, family_id=family_id
    )

    mark_replaced(db, token_str, new_refresh_token)

    response = TokenPairResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )
    return response, new_refresh_token


def logout_user(db: Session, token_str: str | None) -> None:
    """Joriy device refresh tokenini bekor qilish (boshqa sessiyalar saqlanadi)."""
    if not token_str:
        return
    record = get_refresh_token_record(db, token_str)
    if record:
        revoke_refresh_token(db, token_str)
