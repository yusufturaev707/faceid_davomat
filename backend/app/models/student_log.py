from datetime import date, datetime

from sqlalchemy import Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import BIGINT

from app.db.base import Base


class StudentLog(Base):
    __tablename__ = "student_logs"

    id: Mapped[BIGINT] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    first_captured: Mapped[Text] = mapped_column(nullable=True)
    last_captured: Mapped[Text] = mapped_column(nullable=True)
    first_enter_time: Mapped[datetime] = mapped_column(nullable=True)
    last_enter_time: Mapped[datetime] = mapped_column(nullable=True)
    score: Mapped[int] = mapped_column(default=0)
    max_score: Mapped[int] = mapped_column(default=0)
    is_check_hand: Mapped[bool] = mapped_column(default=False)
    ip_address: Mapped[str] = mapped_column(String(45), nullable=True)
    mac_address: Mapped[str] = mapped_column(String(17), unique=True)
