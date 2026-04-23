from datetime import datetime

from sqlalchemy import String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentBlacklist(Base):
    __tablename__ = "student_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    imei: Mapped[str | None] = mapped_column(
        String(14), unique=True, index=True, nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=False),
        server_default=func.current_timestamp(),
        nullable=False,
    )
