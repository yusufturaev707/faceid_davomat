"""Authentication business logic."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password
from app.crud.refresh_token import (
    create_refresh_token,
    get_valid_refresh_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
)
from app.crud.user import get_user_by_username
from app.models.user import User
from app.schemas.auth import TokenPairResponse, UserResponse


def authenticate_user(db: Session, username: str, password: str) -> User:
    """Username va parol orqali foydalanuvchini autentifikatsiya qilish.
    Raises HTTPException agar yaroqsiz bo'lsa.
    """
    user = get_user_by_username(db, username)

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )

    return user


def create_token_pair(db: Session, user: User) -> tuple[str, str]:
    """Access token + refresh token juftligini yaratish.
    Returns: (access_token, refresh_token_str)
    """
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role}
    )
    refresh_token = create_refresh_token(db, user.id)
    return access_token, refresh_token


def rotate_refresh_token(db: Session, token_str: str) -> tuple[TokenPairResponse, str]:
    """Eski refresh tokenni bekor qilib, yangi token juftligi qaytarish.
    Returns: (token_pair_response, new_refresh_token_str)
    Raises HTTPException agar token yaroqsiz bo'lsa.
    """
    token_record = get_valid_refresh_token(db, token_str)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan",
        )

    # Eski tokenni bekor qilish (rotation)
    revoke_refresh_token(db, token_str)

    user = token_record.user
    access_token, new_refresh_token = create_token_pair(db, user)

    response = TokenPairResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )
    return response, new_refresh_token


def logout_user(db: Session, token_str: str | None) -> None:
    """Foydalanuvchining barcha refresh tokenlarini bekor qilish."""
    if not token_str:
        return
    token_record = get_valid_refresh_token(db, token_str)
    if token_record:
        revoke_all_user_tokens(db, token_record.user_id)
