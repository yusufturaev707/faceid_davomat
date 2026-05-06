from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Plaintext o'rniga SHA-256 hash saqlanadi. DB sizib chiqsa, raw token tiklanmaydi.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Token oilasi: rotatsiya zanjirida bir xil family_id. Reuse detection bu orqali ishlaydi.
    family_id: Mapped[str] = mapped_column(String(36), index=True)
    # Bu token rotate qilinganida — yangi tokenning hash'i shu yerda saqlanadi.
    replaced_by_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    expires_at: Mapped[datetime] = mapped_column()
    revoked: Mapped[bool] = mapped_column(default=False)
    # Reuse aniqlanganida butun oila bekor qilingan deb belgilanadi.
    reuse_detected_at: Mapped[datetime | None] = mapped_column(default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")  # noqa: F821
