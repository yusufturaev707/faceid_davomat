from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import limiter
from app.core.redis_client import blacklist_jti
from app.core.security_headers import (
    CSRF_COOKIE_KEY,
    generate_csrf_token,
    verify_csrf,
)
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
CSRF_MAX_AGE = REFRESH_MAX_AGE


def _login_rate_key(request: Request) -> str:
    """Login uchun maxsus key — IP + username (agar kelgan bo'lsa)."""
    ip = get_remote_address(request)
    # Form data preview qila olmaymiz Starlette darajasida — IP yetarli
    return f"login:ip:{ip}"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=REFRESH_MAX_AGE,
        path=f"{settings.API_V1_PREFIX}/auth",
        domain=settings.COOKIE_DOMAIN or None,
    )


def _set_csrf_cookie(response: Response) -> str:
    """CSRF token cookie (HttpOnly EMAS — JS o'qiy olishi kerak)."""
    token = generate_csrf_token()
    response.set_cookie(
        key=CSRF_COOKIE_KEY,
        value=token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        max_age=CSRF_MAX_AGE,
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )
    return token


def _delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_KEY,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path=f"{settings.API_V1_PREFIX}/auth",
        domain=settings.COOKIE_DOMAIN or None,
    )


def _delete_csrf_cookie(response: Response) -> None:
    response.delete_cookie(
        key=CSRF_COOKIE_KEY,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite="lax",
        path="/",
        domain=settings.COOKIE_DOMAIN or None,
    )


@router.post("/login", response_model=TokenPairResponse, summary="Tizimga kirish")
@limiter.limit("50/minute", key_func=_login_rate_key)
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    ip = get_remote_address(request)
    ua = request.headers.get("user-agent")
    user = authenticate_user(
        db,
        form_data.username,
        form_data.password,
        ip_address=ip,
        user_agent=ua,
    )
    access_token, refresh_token, _jti = create_token_pair(db, user)

    _set_refresh_cookie(response, refresh_token)
    _set_csrf_cookie(response)

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
    # CSRF tekshiruvi — refresh state-changing operatsiya
    verify_csrf(request)

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
        _delete_csrf_cookie(response)
        raise

    _set_refresh_cookie(response, new_refresh_token)
    _set_csrf_cookie(response)
    return token_pair


@router.post("/logout", summary="Tizimdan chiqish")
@limiter.limit("30/minute")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    # Logoutda CSRF talab qilinadi (state-changing)
    verify_csrf(request)

    token_str = request.cookies.get(REFRESH_COOKIE_KEY)
    logout_user(db, token_str)

    # Access token jti'ni blacklist'ga (qisqa TTL)
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from jose import jwt as _jwt

            payload = _jwt.decode(
                auth_header[7:],
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                issuer=settings.JWT_ISSUER,
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            exp = payload.get("exp")
            if jti and exp:
                blacklist_jti(jti, int(exp))
        except Exception:
            pass

    _delete_refresh_cookie(response)
    _delete_csrf_cookie(response)
    return {"detail": "Muvaffaqiyatli chiqildi"}


@router.get("/me", response_model=UserResponse, summary="Joriy foydalanuvchi")
def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    return current_user
