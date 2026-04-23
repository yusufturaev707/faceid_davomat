from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentLog(Base):
    __tablename__ = "student_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id"), unique=True, index=True
    )
    first_captured: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    last_captured: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    first_enter_time: Mapped[datetime | None] = mapped_column(nullable=True)
    last_enter_time: Mapped[datetime | None] = mapped_column(nullable=True)
    score: Mapped[int] = mapped_column(default=0)
    max_score: Mapped[int] = mapped_column(default=0)
    is_check_hand: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[str | None] = mapped_column(INET, nullable=True)
    mac_address: Mapped[str] = mapped_column(String(17), nullable=True)
