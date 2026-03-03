from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.schemas.auth import CreateUserRequest


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.execute(
        select(User).where(User.username == username)
    ).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def create_user(db: Session, data: CreateUserRequest) -> User:
    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_all_users(db: Session) -> list[User]:
    return list(db.execute(select(User).order_by(User.id)).scalars().all())
