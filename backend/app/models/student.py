from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Index, String, false, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (
        # Bitta smenada, bitta binoda bitta kompyuter — bitta nomzodga.
        # Faqat BIRIKTIRILGAN raqamlar (`proctoring_schedule_id` bor):
        # loaderlar `sp_n` ga manba API'dagi o'rin raqamini yozadi va u
        # takrorlanadi (OTM'da hammasi `1`) — oddiy `WHERE sp_n > 0`
        # loaderlarni yiqitardi.
        Index(
            "uq_students_smena_zone_pc",
            "session_smena_id", "zone_id", "sp_n",
            unique=True,
            postgresql_where=text("proctoring_schedule_id IS NOT NULL"),
            # Testlar SQLite'da: usiz u TO'LIQ unikal indeks bo'lib qolardi.
            sqlite_where=text("proctoring_schedule_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, index=True)
    session_smena_id: Mapped[int] = mapped_column(ForeignKey("test_session_smena.id"))
    zone_id: Mapped[int] = mapped_column(ForeignKey("zone.id"))

    # api
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    middle_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    imei: Mapped[str | None] = mapped_column(String(14), index=True)
    gr_n: Mapped[int] = mapped_column(default=0)
    # O'tirish o'rni. Loader manba qiymatini yozadi; "Kompyuterlarni
    # biriktirish" uni Proctoring'dagi KOMPYUTER RAQAMI bilan almashtiradi
    # (`services/seat_assignment.py`) va `proctoring_schedule_id` ni yozadi.
    sp_n: Mapped[int] = mapped_column(default=0)
    s_code: Mapped[int] = mapped_column(BigInteger, default=0)
    e_date: Mapped[date] = mapped_column(Date)

    # ms
    subject_id: Mapped[int] = mapped_column(default=0)
    subject_name: Mapped[str | None] = mapped_column(String(100))

    # cefr
    lang_id: Mapped[int] = mapped_column(default=1)
    level_id: Mapped[int] = mapped_column(default=8)

    # state
    is_ready: Mapped[bool] = mapped_column(default=False)  # Talabgor test uchun tayyor
    is_face: Mapped[bool] = mapped_column(default=False)
    is_image: Mapped[bool] = mapped_column(default=False)
    is_cheating: Mapped[bool] = mapped_column(default=False)
    is_blacklist: Mapped[bool] = mapped_column(default=False)
    is_entered: Mapped[bool] = mapped_column(default=False)
    # Proctoring'dagi test sessiyasi (`ExamSchedule.id`), unga `sp_n`
    # KOMPYUTER RAQAMI sifatida biriktirilgan. NULL — `sp_n` manba (loader)
    # qiymati, bron yuborilmaydi. Smenada emas, qatorda: Proctoring
    # sessiyasi bitta binoga ham tegishli bo'lishi mumkin, ya'ni bitta
    # smenaning binolari turli sessiyalarga tushadi. Nomzod Face ID'dan
    # o'tganda bron AYNAN shu sessiyaga ketadi.
    #
    # Bir JShShIR smenada bir necha qatorda bo'lsa (turli fan) — kompyuter
    # bitta va ustun faqat BIRINCHI qatorda: qolganlarida raqam ko'rinadi,
    # lekin index uni ikkinchi marta "egallamaydi".
    proctoring_schedule_id: Mapped[int | None] = mapped_column(
        nullable=True, default=None
    )
    is_applied: Mapped[bool] = mapped_column(
        default=False, server_default=false()
    )  # Ariza bergan pulni qaytarib olishga
    desc_apply: Mapped[str | None] = mapped_column(String(255), nullable=True)
