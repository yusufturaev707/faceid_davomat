from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentBlacklist(Base):
    __tablename__ = "student_blacklist"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    imei: Mapped[str | None] = mapped_column(String(14), index=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
