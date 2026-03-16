from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Reason(Base):
    __tablename__ = "reasons"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    reason_type_id: Mapped[int | None] = mapped_column(
        ForeignKey("reason_types.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255))
    key: Mapped[int] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    reason_type = relationship("ReasonType", lazy="joined")
