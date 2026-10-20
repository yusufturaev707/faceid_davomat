"""Davomat holati — tashqi tizimlar uchun (`X-API-Key`).

Bitta endpoint: nomzodni test turi (`tests.key`) va tashqi platformadagi
unikal ID si (`task_id`) bo'yicha topib, keldi/kelmadi holatini
qaytaradi. Faqat o'qish; hech narsa yozilmaydi.

`task_id` — faqat shu API'dagi nom; bazada u `students.s_code` ustuni
(loaderlar manba ID sini shu yerga yozadi), model o'zgarmagan.

Kirish — `attendance:read`, qamrov — `student:all_regions` (yo'q bo'lsa
API kalit egasining o'z viloyati). Shartnoma `API_DOCS.md` da — maydon
qo'shish/o'zgartirishda uni ham yangilang.

Diqqat: `@limiter.limit` bilan bezatilgan, shuning uchun
`from __future__ import annotations` ishlatilmaydi.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.core.rate_limit import limiter
from app.core.region_scope import resolve_region_id
from app.dependencies import PermissionChecker, get_db
from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_log import StudentLog
from app.models.test import Test
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.user import User
from app.models.zone import Zone
from app.schemas.attendance import (
    AttendanceLookupResponse,
    AttendanceStatus,
    AttendanceStudentItem,
)

router = APIRouter()

# Bitta `task_id` uchun qaytariladigan qatorlar chegarasi — tasodifiy
# ommaviy takrorlanish (masalan, qayta yuklangan sessiyalar) javobni
# shishirmasin.
_MAX_ROWS = 50


def _status_of(is_entered: bool, is_cheating: bool) -> AttendanceStatus:
    # Chetlatilgan nomzod binoga kelgan hisoblanadi (`is_entered=True` ham
    # bo'ladi), lekin tashqi tizimga alohida holat sifatida beriladi.
    if is_cheating:
        return AttendanceStatus.CHEATING
    if is_entered:
        return AttendanceStatus.ENTERED
    return AttendanceStatus.NOT_ENTERED


@router.get(
    "/student",
    response_model=AttendanceLookupResponse,
    summary="Nomzodni test turi va task_id bo'yicha topish",
)
@limiter.limit("600/minute")
def find_attendance_student(
    request: Request,
    test_key: str = Query(
        ..., min_length=1, max_length=20, description="Test turi kaliti (`tests.key`)"
    ),
    task_id: int = Query(
        ..., ge=1, description="Nomzodning tashqi platformadagi unikal ID si"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.ATTENDANCE_READ.code)),
):
    """Nomzod va uning davomat holati.

    Odatda bitta qator qaytadi; nomzod bir nechta sessiyaga yuklangan
    bo'lsa — hammasi, eng yangi imtihon sanasi birinchi. Topilmasa — 404.
    """
    region_id = resolve_region_id(current_user)

    # `StudentLog` dan faqat vaqtlar olinadi — selfi (BYTEA) ustunlariga
    # tegilmaydi.
    stmt = (
        select(
            Student.id,
            Student.s_code.label("task_id"),
            Student.imei,
            Student.last_name,
            Student.first_name,
            Student.middle_name,
            Student.session_smena_id,
            Student.e_date,
            Student.zone_id,
            Student.gr_n,
            Student.sp_n,
            Student.subject_name,
            Student.is_entered,
            Student.is_cheating,
            Student.is_applied,
            Test.key.label("test_key"),
            Test.name.label("test_name"),
            TestSession.id.label("test_session_id"),
            TestSession.name.label("test_session_name"),
            Smena.name.label("smena_name"),
            Zone.name.label("zone_name"),
            Zone.region_id,
            Region.name.label("region_name"),
            StudentLog.first_enter_time,
            StudentLog.last_enter_time,
        )
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(TestSession, TestSession.id == TestSessionSmena.test_session_id)
        .join(Test, Test.id == TestSession.test_id)
        .join(Zone, Zone.id == Student.zone_id)
        .outerjoin(Region, Region.id == Zone.region_id)
        .outerjoin(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .outerjoin(StudentLog, StudentLog.student_id == Student.id)
        .where(Student.s_code == task_id, Test.key == test_key)
        .order_by(Student.e_date.desc(), Student.id.desc())
        .limit(_MAX_ROWS)
    )
    if region_id is not None:
        stmt = stmt.where(Zone.region_id == region_id)
    rows = db.execute(stmt).all()
    if not rows:
        raise HTTPException(status_code=404, detail="Nomzod topilmadi")

    items = []
    for r in rows:
        entered = bool(r.is_entered)
        items.append(
            AttendanceStudentItem(
                student_id=r.id,
                task_id=r.task_id,
                jshshir=r.imei,
                last_name=r.last_name,
                first_name=r.first_name,
                middle_name=r.middle_name,
                test_key=r.test_key,
                test_name=r.test_name,
                test_session_id=r.test_session_id,
                test_session_name=r.test_session_name,
                session_smena_id=r.session_smena_id,
                exam_date=r.e_date,
                smena_name=r.smena_name,
                region_id=r.region_id,
                region_name=r.region_name,
                zone_id=r.zone_id,
                zone_name=r.zone_name,
                gr_n=r.gr_n or 0,
                sp_n=r.sp_n or 0,
                subject_name=r.subject_name,
                status=_status_of(entered, bool(r.is_cheating)),
                is_entered=entered,
                is_cheating=bool(r.is_cheating),
                is_applied=bool(r.is_applied),
                entered_at=r.first_enter_time if entered else None,
                last_seen_at=r.last_enter_time if entered else None,
            )
        )
    return AttendanceLookupResponse(
        test_key=test_key, task_id=task_id, count=len(items), items=items
    )
