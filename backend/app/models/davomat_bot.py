from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DavomatBot(Base):
    """Telegram davomat bot foydalanuvchisi.

    `telegram_id` orqali botga dostup beriladi. Foydalanuvchining ruxsat
    etilgan barcha regionlari `davomat_bot_regions` M2M jadvali orqali
    biriktiriladi (bitta jadvalda — `region_id`/`zone_id` ustunlari
    tashlandi).

    `role_id` — `roles` jadvaliga FK (User modeli bilan bir xil pattern).
    Validatsiya qoidasi (CRUD qatlamida): `role.key == 4` bo'lsa foydalanuvchi
    aniq 1 ta region biriktirishi kerak; aks holda (1/2/3) 1 va undan ortiq
    region biriktirilishi mumkin.
    """

    __tablename__ = "davomat_bots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    fio: Mapped[str] = mapped_column(String(150))
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id", ondelete="SET NULL"), nullable=True, index=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
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

    role_ref = relationship("Role", lazy="joined")
    regions: Mapped[list["DavomatBotRegion"]] = relationship(
        back_populates="bot",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @hybrid_property
    def role(self) -> str:
        """Rol nomi (User.role pattern bilan bir xil)."""
        if self.role_ref:
            return self.role_ref.name
        return ""

    @hybrid_property
    def role_key(self) -> int:
        """Rol kaliti — validatsiya (role_key=4 → 1 region) shu qiymatga
        qarab amalga oshiriladi.
        """
        if self.role_ref:
            return int(self.role_ref.key)
        return 0

    @property
    def allowed_region_ids(self) -> set[int]:
        """Botga ruxsat etilgan barcha region id lari (M2M dan)."""
        return {int(r.region_id) for r in self.regions}


class DavomatBotRegion(Base):
    """DavomatBot ↔ Region M2M: bir foydalanuvchiga bir yoki bir necha
    region biriktirish (validatsiya `role_key` ga bog'liq).
    """

    __tablename__ = "davomat_bot_regions"
    __table_args__ = (
        UniqueConstraint(
            "davomat_bot_id", "region_id", name="uq_davomat_bot_region"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    davomat_bot_id: Mapped[int] = mapped_column(
        ForeignKey("davomat_bots.id", ondelete="CASCADE"), index=True
    )
    region_id: Mapped[int] = mapped_column(
        ForeignKey("regions.id", ondelete="CASCADE"), index=True
    )

    bot = relationship("DavomatBot", back_populates="regions")
    region = relationship("Region", lazy="joined")
