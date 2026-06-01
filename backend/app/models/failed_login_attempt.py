from datetime import datetime

from sqlalchemy import String, TIMESTAMP, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FailedLoginAttempt(Base):
    """Login muvaffaqiyatsizligi audit yozuvi.

    Forensic / compliance maqsadida saqlanadi. Lockout logikasi Redis'da,
    bu jadval esa tarixiy tahlil uchun (kim, qachon, qayerdan, nima sababga).
    """

    __tablename__ = "failed_login_attempts"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    ip_address: Mapped[str] = mapped_column(String(45), index=True)  # IPv6 ham sig'adi
    user_agent: Mapped[str | None] = mapped_column(String(500), default=None)
    # Sabab: 'no_user', 'wrong_password', 'inactive', 'locked'
    reason: Mapped[str] = mapped_column(String(20), index=True)
    attempted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), index=True
    )
