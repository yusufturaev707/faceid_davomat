"""Global dependencies: DB session, authentication, permission checking."""

from collections.abc import Generator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import verify_jwt_token
from app.crud.api_key import get_api_key_by_raw, update_last_used
from app.db.session import SessionLocal
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login",
    auto_error=False,
)

API_KEY_HEADER = "X-API-Key"


def get_db() -> Generator[Session]:
    """DB session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_user_from_jwt(token: str, db: Session) -> User:
    """JWT tokendan foydalanuvchini aniqlash."""
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


def _get_user_from_api_key(raw_key: str, db: Session) -> User:
    """API Key orqali foydalanuvchini aniqlash."""
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
) -> User:
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


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Foydalanuvchi faol ekanligini tekshirish."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Foydalanuvchi bloklangan",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Faqat admin roli uchun (role key=1)."""
    if current_user.role_key != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faqat admin huquqi bilan ruxsat beriladi",
        )
    return current_user


class PermissionChecker:
    """Granular permission tekshiruvchi dependency.

    Ishlatish:
        @router.get("/users", dependencies=[Depends(PermissionChecker("user:read"))])
        @router.post("/users", dependencies=[Depends(PermissionChecker("user:create"))])

    Bir nechta permission (kamida bittasi bo'lsa yetarli):
        @router.get("/reports", dependencies=[Depends(PermissionChecker("report:read", "report:export"))])
    """

    def __init__(self, *required_permissions: str):
        self.required_permissions = required_permissions

    def __call__(self, current_user: User = Depends(get_current_active_user)) -> User:
        # Admin (role_key=1) har doim ruxsat oladi
        if current_user.role_key == 1:
            return current_user

        if not current_user.has_any_perm(*self.required_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Huquq yetarli emas. Kerakli: {', '.join(self.required_permissions)}",
            )
        return current_user
