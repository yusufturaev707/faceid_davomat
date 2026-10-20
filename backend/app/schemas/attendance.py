"""Tashqi tizimlar uchun davomat API'si (`/attendance`) sxemalari.

Javoblar ataylab minimal: keldi/kelmadi holati va nomzodni tanish uchun
yetarli identifikatorlar. Pasport rasmi, embedding va selfi qaytarilmaydi.
"""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel


class AttendanceStatus(str, Enum):
    """Nomzodning davomat holati.

    - `entered` — keldi va imtihonda qatnashmoqda/qatnashdi.
    - `cheating` — keldi, lekin chetlatildi (binoga kelgan hisoblanadi).
    - `not_entered` — kelmadi (yoki davomati bekor qilingan).
    """

    ENTERED = "entered"
    CHEATING = "cheating"
    NOT_ENTERED = "not_entered"


class AttendanceStudentItem(BaseModel):
    student_id: int
    # Tashqi platformadagi nomzod ID si (bazada `students.s_code`).
    task_id: int
    jshshir: str | None = None
    last_name: str
    first_name: str
    middle_name: str | None = None
    test_key: str
    test_name: str | None = None
    test_session_id: int
    test_session_name: str | None = None
    session_smena_id: int
    exam_date: date
    smena_name: str | None = None
    region_id: int
    region_name: str | None = None
    zone_id: int
    zone_name: str | None = None
    gr_n: int
    sp_n: int
    subject_name: str | None = None
    status: AttendanceStatus
    is_entered: bool
    is_cheating: bool
    is_applied: bool
    # Birinchi va oxirgi Face ID vaqti. Faqat `is_entered=True` bo'lsa
    # to'ldiriladi — davomat bekor qilinganda log tarix sifatida qoladi,
    # lekin bu yerda ko'rsatilmaydi.
    entered_at: datetime | None = None
    last_seen_at: datetime | None = None


class AttendanceLookupResponse(BaseModel):
    test_key: str
    task_id: int
    # Odatda bitta qator. Bir nechta bo'lishi mumkin — nomzod bir nechta
    # sessiyaga yuklangan bo'lsa; eng yangi imtihon sanasi birinchi.
    count: int
    items: list[AttendanceStudentItem]
