from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, String, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(100))
    role_id: Mapped[int | None] = mapped_column(
        ForeignKey("roles.id"), index=True, nullable=True
    )
    zone_id: Mapped[int | None] = mapped_column(ForeignKey("zone.id"), nullable=True)
    telegram_id: Mapped[str | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    role_ref = relationship("Role", lazy="joined")
    zone = relationship("Zone", lazy="joined")
    verification_logs: Mapped[list["VerificationLog"]] = relationship(
        back_populates="user"
    )  # noqa: F821
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(back_populates="user")  # noqa: F821
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")  # noqa: F821

    @hybrid_property
    def role(self) -> str:
        """Role name from roles table."""
        if self.role_ref:
            return self.role_ref.name
        return ""

    @hybrid_property
    def role_key(self) -> int:
        """Role key from roles table."""
        if self.role_ref:
            return self.role_ref.key
        return 0

    @hybrid_property
    def zone_name(self) -> str:
        """Zone name from zone table."""
        if self.zone:
            return self.zone.name
        return ""

    @hybrid_property
    def region_name(self) -> str:
        """Region name from zone → region."""
        if self.zone and self.zone.region:
            return self.zone.region.name
        return ""

    @property
    def permissions(self) -> list[str]:
        """Pydantic serialization uchun permission codename lari (list)."""
        return sorted(self.permission_codes)

    @property
    def permission_codes(self) -> set[str]:
        """Foydalanuvchining barcha permission codename lari."""
        if self.role_ref and self.role_ref.permissions:
            return {p.codename for p in self.role_ref.permissions}
        return set()

    def has_perm(self, codename: str) -> bool:
        """Bitta permissionni tekshirish."""
        return codename in self.permission_codes

    def has_any_perm(self, *codenames: str) -> bool:
        """Kamida bitta permissionni tekshirish."""
        return bool(self.permission_codes & set(codenames))
