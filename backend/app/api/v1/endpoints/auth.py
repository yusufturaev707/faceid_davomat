from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

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
    RefreshRequest,
    TokenPairResponse,
    UserResponse,
)

router = APIRouter()


@router.post("/login", response_model=TokenPairResponse, summary="Tizimga kirish")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # LoginRequest o'rniga
    db: Session = Depends(get_db),
) -> TokenPairResponse:
    # Endi 'request.username' o'rniga 'form_data.username'
    user = get_user_by_username(db, form_data.username)

    # Qolgan mantiq o'zgarishsiz qoladi...
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

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=TokenPairResponse, summary="Tokenni yangilash")
def refresh(
    request: RefreshRequest, db: Session = Depends(get_db)
) -> TokenPairResponse:
    """Refresh token orqali yangi access + refresh token olish (token rotation)."""
    token_record = get_valid_refresh_token(db, request.refresh_token)
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token yaroqsiz yoki muddati tugagan",
        )

    # Eski tokenni bekor qilish (rotation)
    revoke_refresh_token(db, request.refresh_token)

    user = token_record.user
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})
    new_refresh_token = create_refresh_token(db, user.id)

    return TokenPairResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout", summary="Tizimdan chiqish")
def logout(
    request: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Refresh tokenni bekor qilish."""
    token_record = get_valid_refresh_token(db, request.refresh_token)
    if token_record:
        revoke_all_user_tokens(db, token_record.user_id)
    return {"detail": "Muvaffaqiyatli chiqildi"}


@router.get("/me", response_model=UserResponse, summary="Joriy foydalanuvchi")
def get_me(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Joriy autentifikatsiya qilingan foydalanuvchi ma'lumotlari."""
    return current_user
