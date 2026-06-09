from datetime import datetime

from sqlalchemy import BigInteger, SmallInteger, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Rol kalitlari (statistik bot foydalanuvchilari uchun).
#   1 → Admin  — cheklov yo'q, hamma ma'lumotni ko'radi.
#   2 → Rahbar — to'lov holati + o'tgan yilgi (2025) ma'lumotlarni ko'radi.
#   3 → Xodim  — to'lov holati va 2025-yil ma'lumotlari KO'RINMAYDI.
ROLE_ADMIN = 1
ROLE_RAHBAR = 2
ROLE_XODIM = 3

ROLE_NAMES: dict[int, str] = {
    ROLE_ADMIN: "Admin",
    ROLE_RAHBAR: "Rahbar",
    ROLE_XODIM: "Xodim",
}


class StatisticBot(Base):
    """Statistika telegram bot foydalanuvchisi.

    `telegram_id` orqali botga dostup beriladi. `role` — to'g'ridan-to'g'ri
    butun son (1/2/3), `roles` jadvaliga FK emas (DavomatBot'dan farqli —
    bu jadval hech qanday tashqi bog'lanishga muhtoj emas).

    Ruxsat qoidalari (bot tomonida qo'llaniladi):
      - role=1 (Admin)  → hamma narsa.
      - role=2 (Rahbar) → to'lov + 2025.
      - role=3 (Xodim)  → to'lov va 2025 yashiriladi.
    """

    __tablename__ = "statistic_bots"
    __table_args__ = (
        UniqueConstraint("telegram_id", name="uq_statistic_bots_telegram_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fio: Mapped[str] = mapped_column(String(150))
    role: Mapped[int] = mapped_column(SmallInteger, default=ROLE_XODIM)
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    status: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )

    @hybrid_property
    def role_name(self) -> str:
        """Rol nomi: 1→'Admin', 2→'Rahbar', 3→'Xodim'."""
        return ROLE_NAMES.get(int(self.role or 0), "")

    @property
    def can_see_payment(self) -> bool:
        """To'lov holatini ko'rish huquqi (Admin yoki Rahbar)."""
        return int(self.role or 0) in (ROLE_ADMIN, ROLE_RAHBAR)

    @property
    def can_see_prev_year(self) -> bool:
        """O'tgan yil (2025) ma'lumotlarini ko'rish huquqi (Admin yoki Rahbar)."""
        return int(self.role or 0) in (ROLE_ADMIN, ROLE_RAHBAR)
