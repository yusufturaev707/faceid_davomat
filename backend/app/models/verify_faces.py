from datetime import datetime

from sqlalchemy import BigInteger, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VerifyFaces(Base):
    __tablename__ = "verify_faces"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(server_default=func.now(), index=True)

    # Rasmlar
    ps_img: Mapped[str | None] = mapped_column(String(255))
    lv_img: Mapped[str | None] = mapped_column(String(255))

    # Rasm ma'lumotlari
    ps_file_size: Mapped[int] = mapped_column()
    lv_file_size: Mapped[int] = mapped_column()
    ps_width: Mapped[int] = mapped_column()
    ps_height: Mapped[int] = mapped_column()
    lv_width: Mapped[int] = mapped_column()
    lv_height: Mapped[int] = mapped_column()

    # Yuz aniqlash
    ps_detection: Mapped[bool] = mapped_column()
    lv_detection: Mapped[bool] = mapped_column()
    detection: Mapped[bool] = mapped_column()

    # Natija
    response_time: Mapped[float] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float)
    thresh_score: Mapped[float] = mapped_column(Float)
    verified: Mapped[bool] = mapped_column()
    error_message: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship()  # noqa: F821
