from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentPsData(Base):
    __tablename__ = "student_ps_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    ps_ser: Mapped[str] = mapped_column(String(5))
    ps_num: Mapped[str] = mapped_column(String(10))
    phone: Mapped[str | None] = mapped_column(String(13), nullable=True)
    ps_img: Mapped[str | None] = mapped_column(Text, nullable=True)
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)
