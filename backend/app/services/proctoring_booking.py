"""Davomatdan keyin Proctoring bronini navbatga qo'yish.

Ikki yo'l `is_entered=True` yozadi — desktop sinxronizatsiyasi
(`POST /students/logs/bulk`) va davomat Mini App/bot (`mark_attendance`) —
ikkalasi shu funksiyani chaqiradi. Chaqiruv COMMIT'DAN KEYIN: task
tranzaksiya hali ko'rinmagan qatorni o'qib, "biriktirilmagan" deb
chiqib ketmasligi kerak.
"""

from __future__ import annotations

import logging

from sqlalchemy import exists, select
from sqlalchemy.orm import Session, aliased

from app.models.student import Student
from app.services import proctoring_client

logger = logging.getLogger("faceid.services.proctoring_booking")


def enqueue_seat_booking(db: Session, student_ids: list[int]) -> int:
    """Kompyuter biriktirilgan nomzodlar uchun bron task'ini yuboradi.

    HAR KIRISHDA yuboriladi, faqat birinchisida emas: bron idempotent va
    nomzod qayta aniqlanganda (client yozuvni yangilaydi) oldingi
    muvaffaqiyatsiz bron o'z-o'zidan tuzaladi.

    Xato YUTILADI — broker ishlamasa ham davomat yozilgan bo'lishi kerak.
    Qaytaradi: navbatga qo'yilganlar soni.
    """
    if not student_ids or not proctoring_client.is_configured():
        return 0

    owner = aliased(Student)
    has_assigned_sibling = exists().where(
        owner.session_smena_id == Student.session_smena_id,
        owner.imei == Student.imei,
        owner.proctoring_schedule_id.is_not(None),
    )
    try:
        bookable = db.execute(
            select(Student.id).where(
                Student.id.in_(set(student_ids)),
                Student.is_cheating.is_(False),
                Student.proctoring_schedule_id.is_not(None) | has_assigned_sibling,
            )
        ).scalars().all()
    except Exception:
        logger.exception("Bron uchun nomzodlarni tanlab bo'lmadi")
        return 0

    from app.tasks.proctoring_task import book_seat

    sent = 0
    for student_id in bookable:
        try:
            book_seat.delay(student_id)
            sent += 1
        except Exception:
            logger.exception("Bron navbatga qo'yilmadi: student=%s", student_id)
    return sent
