from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)

API_KEY_HEADER = "X-API-Key"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """JWT access token yaratish."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """JWT tokenni tekshirish va payload qaytarish."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="JWT token yaroqsiz yoki muddati tugagan",
        )


def _get_user_from_jwt(token: str, db: Session):
    """JWT tokendan foydalanuvchini aniqlash."""
    from app.models.user import User

    payload = verify_jwt_token(token)
    sub = payload.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz",
        )
    try:
        user_id = int(sub)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Foydalanuvchi topilmadi",
        )
    return user


def _get_user_from_api_key(raw_key: str, db: Session):
    """API Key orqali foydalanuvchini aniqlash."""
    from app.crud.api_key import get_api_key_by_raw, update_last_used

    api_key = get_api_key_by_raw(db, raw_key)
    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API kalit yaroqsiz yoki bekor qilingan",
        )

    user = api_key.user
    update_last_used(db, api_key)
    return user


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """JWT yoki API Key orqali foydalanuvchini aniqlash."""
    # 1. API Key tekshirish
    api_key = request.headers.get(API_KEY_HEADER)
    if api_key:
        return _get_user_from_api_key(api_key, db)

    # 2. JWT tekshirish
    if token:
        return _get_user_from_jwt(token, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Autentifikatsiya talab qilinadi",
    )


def get_current_active_user(current_user=Depends(get_current_user)):
    """Foydalanuvchi faol ekanligini tekshirish."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )
    return current_user


def require_admin(current_user=Depends(get_current_active_user)):
    """Faqat admin roli uchun."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin huquqi bilan ruxsat beriladi",
        )
    return current_user
