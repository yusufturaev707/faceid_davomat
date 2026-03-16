from datetime import date

from sqlalchemy import BigInteger, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TestSession(Base):
    __tablename__ = "test_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    hash_key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    test_state_id: Mapped[int] = mapped_column(
        ForeignKey("session_states.id"), index=True
    )
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column(unique=True, default=0)
    count_sm_per_day: Mapped[int] = mapped_column(default=0)
    count_total_student: Mapped[int] = mapped_column(default=0)
    start_date: Mapped[date] = mapped_column()
    finish_date: Mapped[date] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=False)

    # Relationships
    test_state: Mapped["SessionState"] = relationship(lazy="selectin")
    test: Mapped["Test"] = relationship(lazy="selectin")
    smenas: Mapped[list["TestSessionSmena"]] = relationship(
        back_populates="test_session", lazy="selectin"
    )
