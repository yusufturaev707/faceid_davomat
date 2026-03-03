from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerificationLog(Base):
    __tablename__ = "verification_logs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)
    success: Mapped[bool] = mapped_column()
    detection: Mapped[bool] = mapped_column()
    image_width: Mapped[int] = mapped_column()
    image_height: Mapped[int] = mapped_column()
    file_size_bytes: Mapped[float] = mapped_column()
    input_age: Mapped[int] = mapped_column()
    back_color: Mapped[str | None] = mapped_column(String(30))
    error_message: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="verification_logs")  # noqa: F821
