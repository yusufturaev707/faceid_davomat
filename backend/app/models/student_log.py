from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentLog(Base):
    __tablename__ = "student_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    first_captured: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_captured: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_enter_time: Mapped[datetime | None] = mapped_column(nullable=True)
    last_enter_time: Mapped[datetime | None] = mapped_column(nullable=True)
    score: Mapped[int] = mapped_column(default=0)
    max_score: Mapped[int] = mapped_column(default=0)
    is_check_hand: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True)
