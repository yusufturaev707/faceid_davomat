from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Zone(Base):
    __tablename__ = "zone"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column(default=0)
    is_active: Mapped[bool] = mapped_column(default=True)
    is_part: Mapped[bool] = mapped_column(default=False)
    # Tashqi OTM API'dagi bino "id" qiymati. Zona hali biror tashqi binoga
    # bog'lanmagan bo'lsa NULL (masalan qo'lda yaratilgan qo'shimcha zonalar).
    # Bog'langanda unikal — bir tashqi bino bitta zonaga to'g'ri keladi.
    building_id: Mapped[int | None] = mapped_column(
        unique=True, index=True, nullable=True, default=None
    )
    region = relationship("Region", lazy="joined")
