from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.permission import role_permissions


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    key: Mapped[int] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    permissions = relationship(
        "Permission",
        secondary=role_permissions,
        lazy="joined",
    )
