from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TestSessionSmena(Base):
    __tablename__ = "test_session_smena"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    test_session_id: Mapped[int] = mapped_column(
        ForeignKey("test_sessions.id"), index=True
    )
    test_smena_id: Mapped[int] = mapped_column(ForeignKey("smena.id"), index=True)
    number: Mapped[int] = mapped_column(unique=True, default=0)
    day: Mapped[date] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    test_session: Mapped["TestSession"] = relationship(
        back_populates="smenas", lazy="selectin"
    )
    smena: Mapped["Smena"] = relationship(lazy="selectin")
