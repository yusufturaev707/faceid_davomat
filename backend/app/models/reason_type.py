from datetime import datetime

from sqlalchemy import String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ReasonType(Base):
    __tablename__ = "reason_types"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    key: Mapped[int] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
