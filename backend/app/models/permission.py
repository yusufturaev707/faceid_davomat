"""Permission model and Role-Permission many-to-many association."""

from sqlalchemy import ForeignKey, String, Table, Column, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Many-to-Many association table: roles <-> permissions
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    codename: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    group: Mapped[str] = mapped_column(String(50), index=True)
