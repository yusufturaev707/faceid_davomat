from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    get_current_active_user,
    verify_password,
)
from app.crud.refresh_token import (
    create_refresh_token,
    get_valid_refresh_token,
    revoke_all_user_tokens,
    revoke_refresh_token,
)
from app.crud.user import get_user_by_username
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    TokenPairResponse,
    UserResponse,
)

router = APIRouter()

REFRESH_COOKIE_KEY = "refresh_token"
REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60  # sekundlarda


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Refresh tokenni HttpOnly cookie sifatida o'rnatish."""
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        max_age=REFRESH_MAX_AGE,
        path=f"{settings.API_V1_PREFIX}/auth",
    )


def _delete_refresh_cookie(response: Response) -> None:
    """Refresh token cookie ni o'chirish."""
    response.delete_cookie(
        key=REFRESH_COOKIE_KEY,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="strict",
        path=f"{settings.API_V1_PREFIX}/auth",
    )


@router.post("/login", response_model=TokenPairResponse, summary="Tizimga kirish")
def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    user = get_user_by_username(db, form_data.username)

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    refresh_token = create_refresh_token(db, user.id)

    _set_refresh_cookie(response, refresh_token)

    return TokenPairResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenPairResponse, summary="Tokenni yangilash")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    """Cookie dagi refresh token orqali yangi access + refresh token olish (token rotation)."""
    token_str = request.cookies.get(REFRESH_COOKIE_KEY)
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token topilmadi",
        )

    token_record = get_valid_refresh_token(db, token_str)
    if not token_record:
        _delete_refresh_cookie(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan",
        )

    # Eski tokenni bekor qilish (rotation)
    revoke_refresh_token(db, token_str)

    user = token_record.user
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    new_refresh_token = create_refresh_token(db, user.id)

    _set_refresh_cookie(response, new_refresh_token)

    return TokenPairResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", summary="Tizimdan chiqish")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Refresh tokenni bekor qilish va cookie ni o'chirish."""
    token_str = request.cookies.get(REFRESH_COOKIE_KEY)
    if token_str:
        token_record = get_valid_refresh_token(db, token_str)
        if token_record:
            revoke_all_user_tokens(db, token_record.user_id)

    _delete_refresh_cookie(response)
    return {"detail": "Muvaffaqiyatli chiqildi"}


@router.get("/me", response_model=UserResponse, summary="Joriy foydalanuvchi")
def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Joriy autentifikatsiya qilingan foydalanuvchi ma'lumotlari."""
    return current_user
