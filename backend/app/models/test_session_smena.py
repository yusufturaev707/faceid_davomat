from datetime import date, datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TestSessionSmena(Base):
    __tablename__ = "test_session_smena"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    test_session_id: Mapped[int] = mapped_column(
        ForeignKey("test_session.id"), index=True
    )
    test_smena_id: Mapped[int] = mapped_column(ForeignKey("test_smena.id"), index=True)
    number: Mapped[int] = mapped_column(unique=True, default=0)
    day: Mapped[date] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)
