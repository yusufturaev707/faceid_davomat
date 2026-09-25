"""Nomzod Face ID'dan o'tdi — kompyuterini Proctoring'da bron qilish.

Davomat yo'lida (desktop sinxronizatsiyasi, Mini App) HTTP so'rov YO'Q:
Proctoring sekin javob bersa yoki o'chiq bo'lsa ham davomat darhol
yoziladi, bron esa shu yerda qayta urinishlar bilan yetkaziladi.

`storage` navbatida — I/O ish, `verify` dagi CPU'li yuz tekshiruvini
kutib turmasligi kerak.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.region import Region
from app.models.student import Student
from app.models.zone import Zone
from app.services import proctoring_client

logger = logging.getLogger("faceid.tasks.proctoring")

#: Qayta urinishlar: 10, 20, 40 ... 300 s (jami ~25 daqiqa) — Proctoring
#: qayta ishga tushirilishi yoki tarmoq uzilishini qoplaydi. Nomzod shu
#: vaqt ichida kompyuter oldiga borib ulguradi.
MAX_RETRIES = 8


def _seat_of(db, student_id: int):
    """Nomzodning biriktirilgan joyi: `(schedule, pinfl, region, zone, raqam)` yoki `None`.

    Bir JShShIR smenada bir necha qatorda bo'lishi mumkin va "egalik"
    (`proctoring_schedule_id`) faqat birinchisida — Face ID esa istalgan
    qatorini aniqlashi mumkin. Shuning uchun egasi JShShIR bo'yicha izlanadi.
    """
    student = db.get(Student, student_id)
    if student is None or student.is_cheating or not student.imei:
        return None
    owner = student
    if owner.proctoring_schedule_id is None:
        owner = db.execute(
            select(Student).where(
                Student.session_smena_id == student.session_smena_id,
                Student.imei == student.imei,
                Student.proctoring_schedule_id.is_not(None),
            )
        ).scalar()
    if owner is None or not owner.sp_n:
        return None
    zone_number, region_number = db.execute(
        select(Zone.number, Region.number)
        .join(Region, Region.id == Zone.region_id)
        .where(Zone.id == owner.zone_id)
    ).one()
    return owner.proctoring_schedule_id, owner.imei, region_number, zone_number, owner.sp_n


@celery_app.task(
    name="tasks.proctoring_book_seat",
    queue="storage",
    bind=True,
    ignore_result=True,
    max_retries=MAX_RETRIES,
)
def book_seat(self, student_id: int) -> None:
    # DB ulanishi HTTP so'rovdan OLDIN yopiladi — Proctoring kutilayotganda
    # pool'dagi ulanish band turmasligi kerak.
    db = SessionLocal()
    try:
        seat = _seat_of(db, student_id)
    finally:
        db.close()
    if seat is None:
        return
    schedule_id, pinfl, region_number, zone_number, number = seat

    try:
        proctoring_client.book(
            schedule_id=schedule_id,
            pinfl=pinfl,
            region_number=region_number,
            zone_number=zone_number,
            computer_number=number,
        )
    except proctoring_client.ProctoringNotConfigured:
        return
    except proctoring_client.ProctoringError as exc:
        if exc.retryable and self.request.retries < MAX_RETRIES:
            raise self.retry(countdown=min(300, 10 * 2 ** self.request.retries))
        # Joy band, kompyuter topilmadi, nomzod imtihonda... — qayta urish
        # natijani o'zgartirmaydi. Nomzod Proctoring client'da
        # `seat_not_booked` oladi va administrator panelda hal qiladi.
        logger.warning(
            "Proctoring broni rad etildi: student=%s joy=%s-%s/№%s (%s) %s",
            student_id, region_number, zone_number, number, exc.code or exc.status, exc.message,
        )
        return
    logger.info(
        "Proctoring broni: student=%s joy=%s-%s/№%s", student_id, region_number, zone_number, number
    )
