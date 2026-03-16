from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import CreateUserRequest, UpdateUserRequest


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(
        select(User).where(User.username == username)
    ).unique().scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: CreateUserRequest) -> User:
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
    user = db.get(User, user_id)
    if not user:
        return None
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data:
        update_data["hashed_password"] = hash_password(update_data.pop("password"))
    for key, val in update_data.items():
        setattr(user, key, val)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = db.get(User, user_id)
    if not user:
        return False
    db.delete(user)
    db.commit()
    return True


def get_all_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.id)).unique().scalars().all())
