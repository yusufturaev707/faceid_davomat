from datetime import date, datetime

from sqlalchemy import Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.sqltypes import BIGINT

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[BIGINT] = mapped_column(primary_key=True, index=True)
    session_smena_id: Mapped[int] = mapped_column(ForeignKey("test_session_smena.id"))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zones.id"))

    # api
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    middle_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(14), index=True)
    gr_n: Mapped[int] = mapped_column(default=0)
    sp_n: Mapped[int] = mapped_column(default=0)
    s_code: Mapped[BIGINT] = mapped_column(default=0)
    e_date: Mapped[datetime] = mapped_column()

    # ms
    subject_id: Mapped[int] = mapped_column(default=0)
    subject_name: Mapped[str | None] = mapped_column(String(100))

    # cefr
    lang_id: Mapped[int] = mapped_column(default=0)
    level_id: Mapped[int] = mapped_column(default=0)

    # state
    is_ready: Mapped[bool] = mapped_column(default=False)
    is_face: Mapped[bool] = mapped_column(
        default=False
    )  # is have face detection in image
    is_image: Mapped[bool] = mapped_column(default=False)  # is have image
    is_cheating: Mapped[bool] = mapped_column(default=False)
    is_blacklist: Mapped[bool] = mapped_column(default=False)
    is_entered: Mapped[bool] = mapped_column(default=False)
