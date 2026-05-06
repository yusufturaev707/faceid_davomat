"""JWT va password utility funksiyalari.

JWT claims:
- sub: foydalanuvchi ID (string)
- jti: JWT ID (uuid4 hex) — blacklist va audit uchun
- iat: issued-at (UTC timestamp)
- nbf: not-before (= iat)
- exp: expiry
- iss: issuer (multi-app bo'lsa har biri o'z iss bilan ishlaydi)
- role / role_key: ma'lumot uchun (authorization DB'dan tekshiriladi)

Eslatma: parol o'zgarganda yoki bloklanganda DB tekshiruvi orqali JWT
darhol kuchsizlanadi (`get_current_user` user'ni DB'dan oladi). Lekin
explicit revoke (logout) uchun Redis-based blacklist mavjud.
"""

import re
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, status
from jose import JWTError, jwt

from app.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except (ValueError, TypeError):
        return False


# Username enumeration timing fix uchun. Real bcrypt qiymati shaklida.
_DUMMY_HASH = bcrypt.hashpw(b"dummy_password_for_timing_safety", bcrypt.gensalt(rounds=12)).decode()


def dummy_verify_password() -> None:
    """User mavjud bo'lmasa ham bcrypt'ni ishga tushirib, login latency'ni
    deyarli teng qilamiz (timing-based username enumeration himoyasi)."""
    bcrypt.checkpw(b"x", _DUMMY_HASH.encode())


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> tuple[str, str]:
    """JWT access token yaratish.

    Returns: (token, jti) — jti'ni logout/blacklist'da ishlatish uchun.
    """
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    jti = uuid.uuid4().hex
    to_encode.update(
        {
            "iat": int(now.timestamp()),
            "nbf": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "iss": settings.JWT_ISSUER,
            "jti": jti,
        }
    )
    token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, jti


def verify_jwt_token(token: str) -> dict:
    """JWT'ni dekod qilib, claims qaytarish.

    iss/exp/nbf/iat avtomatik tekshiriladi (jose).
    Blacklist (jti) tekshiruvi `dependencies.get_current_user`da bajariladi.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "jti"]},
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token yaroqsiz yoki muddati tugagan",
        )


# === Password policy ===

_PASSWORD_MIN_LEN = 8
_PASSWORD_MAX_LEN = 128
_LOWER_RE = re.compile(r"[a-z]")
_UPPER_RE = re.compile(r"[A-Z]")
_DIGIT_RE = re.compile(r"\d")


def validate_password_strength(password: str) -> str:
    """Password policy: 8–128 belgi, kamida bitta katta+kichik+raqam.

    Pydantic field_validator orqali ishlatiladi. Xatolik bo'lsa ValueError.
    """
    if not isinstance(password, str):
        raise ValueError("Parol matn bo'lishi kerak")
    if len(password) < _PASSWORD_MIN_LEN:
        raise ValueError(f"Parol kamida {_PASSWORD_MIN_LEN} belgidan iborat bo'lsin")
    if len(password) > _PASSWORD_MAX_LEN:
        raise ValueError(f"Parol {_PASSWORD_MAX_LEN} belgidan oshmasin")
    if not _LOWER_RE.search(password):
        raise ValueError("Parolda kamida bitta kichik harf bo'lsin")
    if not _UPPER_RE.search(password):
        raise ValueError("Parolda kamida bitta katta harf bo'lsin")
    if not _DIGIT_RE.search(password):
        raise ValueError("Parolda kamida bitta raqam bo'lsin")
    return password
