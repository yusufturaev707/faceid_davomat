from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.crud.refresh_token import revoke_all_user_tokens
from app.models.user import User
from app.schemas.auth import CreateUserRequest, UpdateUserRequest


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(
        select(User).where(User.username == username)
    ).unique().scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: CreateUserRequest) -> User:
    if get_user_by_username(db, data.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu username allaqachon band",
        )
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role_id=data.role_id,
        zone_id=data.zone_id,
        telegram_id=data.telegram_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, data: UpdateUserRequest) -> User | None:
    """Foydalanuvchini tahrirlash.

    Xavfsizlik:
    - Username unikalligi DB'ga emas, app darajasida tekshiriladi (#21).
    - Parol o'zgarsa yoki user bloklansa — barcha refresh tokenlar revoke qilinadi (#6).
      Access token (qisqa TTL) DB'dan user'ni o'qigani uchun darhol kuchsizlanadi.
    """
    user = db.get(User, user_id)
    if not user:
        return None

    update_data = data.model_dump(exclude_unset=True)

    new_username = update_data.get("username")
    if new_username and new_username != user.username:
        existing = get_user_by_username(db, new_username)
        if existing is not None and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bu username allaqachon band",
            )

    revoke_tokens = False
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
        revoke_tokens = True
    if update_data.get("is_active") is False:
        revoke_tokens = True

    for key, val in update_data.items():
        setattr(user, key, val)
    db.commit()
    db.refresh(user)

    if revoke_tokens:
        revoke_all_user_tokens(db, user_id)

    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    revoke_all_user_tokens(db, user_id)
    db.delete(user)
    db.commit()
    return True


def get_all_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.id)).unique().scalars().all())
