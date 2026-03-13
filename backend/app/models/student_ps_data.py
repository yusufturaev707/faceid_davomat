from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StudentPsData(Base):
    __tablename__ = "studen_ps_data"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    ps_ser = mapped_column(String(5))
    ps_num = mapped_column(String(10))
    phone: Mapped[str] = mapped_column(String(13), nullable=True)
    ps_img: Mapped[Text] = mapped_column(nullable=True)
    embedding: VectorField = mapped_column(nullable=True)
