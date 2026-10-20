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


class AttendanceSmenaItem(BaseModel):
    session_smena_id: int
    day: date
    smena_name: str | None = None
    number: int


class AttendanceSessionItem(BaseModel):
    test_session_id: int
    name: str
    test_name: str | None = None
    start_date: date
    finish_date: date
    state_key: int | None = None
    state_name: str | None = None
    smenas: list[AttendanceSmenaItem]


class AttendanceSessionsResponse(BaseModel):
    items: list[AttendanceSessionItem]
    total: int


class AttendanceStudentItem(BaseModel):
    student_id: int
    jshshir: str | None = None
    last_name: str
    first_name: str
    middle_name: str | None = None
    test_session_id: int
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


class AttendanceStudentsResponse(BaseModel):
    items: list[AttendanceStudentItem]
    count: int
    has_more: bool
    # Keyingi sahifa uchun `after_id` qiymati; oxirgi sahifada `None`.
    next_after_id: int | None = None


class AttendanceSummaryResponse(BaseModel):
    test_session_id: int
    total: int
    entered: int
    cheating: int
    not_entered: int
    applied: int
