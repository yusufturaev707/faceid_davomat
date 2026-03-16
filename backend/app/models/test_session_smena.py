from datetime import date

from sqlalchemy import BigInteger, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TestSessionSmena(Base):
    __tablename__ = "test_session_smena"
    __table_args__ = (
        UniqueConstraint(
            "test_session_id", "test_smena_id", "day",
            name="uq_session_smena_day",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    test_session_id: Mapped[int] = mapped_column(
        ForeignKey("test_sessions.id"), index=True
    )
    test_smena_id: Mapped[int] = mapped_column(ForeignKey("smena.id"), index=True)
    number: Mapped[int] = mapped_column(default=0)
    day: Mapped[date] = mapped_column()
    is_active: Mapped[bool] = mapped_column(default=True)

    # Relationships
    test_session: Mapped["TestSession"] = relationship(
        back_populates="smenas", lazy="selectin"
    )
    smena: Mapped["Smena"] = relationship(lazy="selectin")
