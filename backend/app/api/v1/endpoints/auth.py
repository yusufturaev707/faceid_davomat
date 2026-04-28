from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import limiter
from app.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.auth import TokenPairResponse, UserResponse
from app.services.auth_service import (
    authenticate_user,
    create_token_pair,
    logout_user,
    rotate_refresh_token,
)

router = APIRouter()

REFRESH_COOKIE_KEY = "refresh_token"
REFRESH_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_MAX_AGE,
        path=f"{settings.API_V1_PREFIX}/auth",
    )


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_KEY,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path=f"{settings.API_V1_PREFIX}/auth",
    )


@router.post("/login", response_model=TokenPairResponse, summary="Tizimga kirish")
@limiter.limit("50/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    user = authenticate_user(db, form_data.username, form_data.password)
    access_token, refresh_token = create_token_pair(db, user)

    _set_refresh_cookie(response, refresh_token)

    return TokenPairResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenPairResponse, summary="Tokenni yangilash")
@limiter.limit("30/minute")
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    token_str = request.cookies.get(REFRESH_COOKIE_KEY)
    if not token_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token topilmadi",
        )

    try:
        token_pair, new_refresh_token = rotate_refresh_token(db, token_str)
    except HTTPException:
        _delete_refresh_cookie(response)
        raise

    _set_refresh_cookie(response, new_refresh_token)
    return token_pair


@router.post("/logout", summary="Tizimdan chiqish")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token_str = request.cookies.get(REFRESH_COOKIE_KEY)
    logout_user(db, token_str)
    _delete_refresh_cookie(response)
    return {"detail": "Muvaffaqiyatli chiqildi"}


@router.get("/me", response_model=UserResponse, summary="Joriy foydalanuvchi")
def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    return current_user
