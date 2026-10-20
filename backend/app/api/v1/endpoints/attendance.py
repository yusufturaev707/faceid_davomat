"""Davomat holati — tashqi tizimlar uchun (`X-API-Key`).

Uch endpoint: test sessiyalari va smenalari ro'yxati (ID larni topish
uchun), nomzodlarning keldi/kelmadi holati (keyset sahifalash bilan) va
umumiy sonlar. Faqat o'qish; hech narsa yozilmaydi.

Kirish — `attendance:read`, qamrov — `student:all_regions` (yo'q bo'lsa
API kalit egasining o'z viloyati). Shartnoma `API_DOCS.md` da — maydon
qo'shish/o'zgartirishda uni ham yangilang.

Diqqat: `@limiter.limit` bilan bezatilgan endpointlar bor, shuning uchun
`from __future__ import annotations` ishlatilmaydi.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.core.rate_limit import limiter
from app.core.region_scope import resolve_region_id
from app.dependencies import PermissionChecker, get_db
from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_log import StudentLog
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.user import User
from app.models.zone import Zone
from app.schemas.attendance import (
    AttendanceSessionItem,
    AttendanceSessionsResponse,
    AttendanceSmenaItem,
    AttendanceStatus,
    AttendanceStudentItem,
    AttendanceStudentsResponse,
    AttendanceSummaryResponse,
)

router = APIRouter()

_MAX_LIMIT = 1000


def _ensure_session(db: Session, test_session_id: int) -> None:
    if db.get(TestSession, test_session_id) is None:
        raise HTTPException(status_code=404, detail="Test sessiya topilmadi")


def _filters(
    *,
    test_session_id: int,
    session_smena_id: int | None,
    exam_date: date | None,
    region_id: int | None,
    zone_id: int | None,
) -> list:
    """`/students` va `/summary` uchun umumiy filtrlar.

    So'rov `TestSessionSmena` va `Zone` bilan JOIN qilingan bo'lishi shart.
    """
    conds = [TestSessionSmena.test_session_id == test_session_id]
    if session_smena_id is not None:
        conds.append(Student.session_smena_id == session_smena_id)
    if exam_date is not None:
        conds.append(Student.e_date == exam_date)
    if region_id is not None:
        conds.append(Zone.region_id == region_id)
    if zone_id is not None:
        conds.append(Student.zone_id == zone_id)
    return conds


_STATUS_FILTER = {
    AttendanceStatus.ENTERED: and_(
        Student.is_entered.is_(True), Student.is_cheating.is_(False)
    ),
    AttendanceStatus.CHEATING: Student.is_cheating.is_(True),
    AttendanceStatus.NOT_ENTERED: and_(
        Student.is_entered.is_(False), Student.is_cheating.is_(False)
    ),
}


def _status_of(is_entered: bool, is_cheating: bool) -> AttendanceStatus:
    # Chetlatilgan nomzod binoga kelgan hisoblanadi (`is_entered=True` ham
    # bo'ladi), lekin tashqi tizimga alohida holat sifatida beriladi.
    if is_cheating:
        return AttendanceStatus.CHEATING
    if is_entered:
        return AttendanceStatus.ENTERED
    return AttendanceStatus.NOT_ENTERED


@router.get(
    "/sessions",
    response_model=AttendanceSessionsResponse,
    summary="Test sessiyalari va smenalari",
)
@limiter.limit("60/minute")
def list_attendance_sessions(
    request: Request,
    date_from: date | None = Query(
        None, description="Shu sanadan keyin tugaydigan sessiyalar (YYYY-MM-DD)"
    ),
    date_to: date | None = Query(
        None, description="Shu sanagacha boshlanadigan sessiyalar (YYYY-MM-DD)"
    ),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.ATTENDANCE_READ.code)),
):
    """Test sessiyalari (eng yangisi birinchi) va ularning kun+smenalari.

    `test_session_id` va `session_smena_id` qiymatlarini shu yerdan olasiz.
    """
    # Qamrovsiz kalit (viloyat ham, `student:all_regions` ham yo'q) bu yerda
    # ham 403 oladi — keyingi so'rovlar baribir rad etiladi.
    resolve_region_id(current_user)

    stmt = select(TestSession)
    if date_from is not None:
        stmt = stmt.where(TestSession.finish_date >= date_from)
    if date_to is not None:
        stmt = stmt.where(TestSession.start_date <= date_to)
    stmt = stmt.order_by(TestSession.start_date.desc(), TestSession.id.desc()).limit(
        limit
    )
    sessions = db.execute(stmt).scalars().all()

    items = [
        AttendanceSessionItem(
            test_session_id=s.id,
            name=s.name,
            test_name=s.test.name if s.test else None,
            start_date=s.start_date,
            finish_date=s.finish_date,
            state_key=s.test_state.key if s.test_state else None,
            state_name=s.test_state.name if s.test_state else None,
            smenas=[
                AttendanceSmenaItem(
                    session_smena_id=sm.id,
                    day=sm.day,
                    smena_name=sm.smena.name if sm.smena else None,
                    number=sm.number,
                )
                for sm in sorted(s.smenas, key=lambda x: (x.day, x.number, x.id))
            ],
        )
        for s in sessions
    ]
    return AttendanceSessionsResponse(items=items, total=len(items))


@router.get(
    "/students",
    response_model=AttendanceStudentsResponse,
    summary="Nomzodlarning keldi/kelmadi holati",
)
@limiter.limit("300/minute")
def list_attendance_students(
    request: Request,
    test_session_id: int = Query(..., description="Test sessiya ID si"),
    session_smena_id: int | None = Query(None, description="Kun+smena ID si"),
    exam_date: date | None = Query(None, description="Imtihon sanasi (YYYY-MM-DD)"),
    region_id: int | None = Query(None, description="Viloyat ID si"),
    zone_id: int | None = Query(None, description="Bino ID si"),
    status: AttendanceStatus | None = Query(None, description="Holat bo'yicha filtr"),
    jshshir: str | None = Query(
        None, min_length=14, max_length=14, pattern=r"^\d{14}$", description="JShShIR"
    ),
    after_id: int = Query(
        0, ge=0, description="Oldingi javobdagi `next_after_id` (birinchi sahifa — 0)"
    ),
    limit: int = Query(500, ge=1, le=_MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.ATTENDANCE_READ.code)),
):
    """Nomzodlar ro'yxati holati bilan, `student_id` o'sish tartibida.

    Keyset sahifalash: keyingi sahifa uchun javobdagi `next_after_id` ni
    `after_id` ga bering. Offset ishlatilmaydi — davomat yozilayotgan paytda
    ham sahifalar siljimaydi va qatorlar takrorlanmaydi.
    """
    region_id = resolve_region_id(current_user, region_id)
    _ensure_session(db, test_session_id)

    conds = _filters(
        test_session_id=test_session_id,
        session_smena_id=session_smena_id,
        exam_date=exam_date,
        region_id=region_id,
        zone_id=zone_id,
    )
    if status is not None:
        conds.append(_STATUS_FILTER[status])
    if jshshir is not None:
        conds.append(Student.imei == jshshir)

    # `StudentLog` dan faqat vaqtlar olinadi — selfi (BYTEA) ustunlariga
    # tegilmaydi.
    stmt = (
        select(
            Student.id,
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
            TestSessionSmena.test_session_id,
            Smena.name.label("smena_name"),
            Zone.name.label("zone_name"),
            Zone.region_id,
            Region.name.label("region_name"),
            StudentLog.first_enter_time,
            StudentLog.last_enter_time,
        )
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(Zone, Zone.id == Student.zone_id)
        .outerjoin(Region, Region.id == Zone.region_id)
        .outerjoin(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .outerjoin(StudentLog, StudentLog.student_id == Student.id)
        .where(*conds, Student.id > after_id)
        .order_by(Student.id)
        .limit(limit + 1)
    )
    rows = db.execute(stmt).all()
    has_more = len(rows) > limit
    rows = rows[:limit]

    items = []
    for r in rows:
        entered = bool(r.is_entered)
        items.append(
            AttendanceStudentItem(
                student_id=r.id,
                jshshir=r.imei,
                last_name=r.last_name,
                first_name=r.first_name,
                middle_name=r.middle_name,
                test_session_id=r.test_session_id,
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

    return AttendanceStudentsResponse(
        items=items,
        count=len(items),
        has_more=has_more,
        next_after_id=items[-1].student_id if has_more else None,
    )


@router.get(
    "/summary",
    response_model=AttendanceSummaryResponse,
    summary="Keldi/kelmadi sonlari",
)
@limiter.limit("120/minute")
def get_attendance_summary(
    request: Request,
    test_session_id: int = Query(..., description="Test sessiya ID si"),
    session_smena_id: int | None = Query(None, description="Kun+smena ID si"),
    exam_date: date | None = Query(None, description="Imtihon sanasi (YYYY-MM-DD)"),
    region_id: int | None = Query(None, description="Viloyat ID si"),
    zone_id: int | None = Query(None, description="Bino ID si"),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.ATTENDANCE_READ.code)),
):
    """`/students` bilan bir xil filtrlar bo'yicha sonlar.

    `entered + cheating + not_entered = total`. `applied` — ariza bergan
    (to'lovni qaytarib olgan) nomzodlar, ular `not_entered` ichida ham bor.
    """
    region_id = resolve_region_id(current_user, region_id)
    _ensure_session(db, test_session_id)

    conds = _filters(
        test_session_id=test_session_id,
        session_smena_id=session_smena_id,
        exam_date=exam_date,
        region_id=region_id,
        zone_id=zone_id,
    )
    stmt = (
        select(
            func.count(Student.id),
            func.count(Student.id).filter(_STATUS_FILTER[AttendanceStatus.ENTERED]),
            func.count(Student.id).filter(_STATUS_FILTER[AttendanceStatus.CHEATING]),
            func.count(Student.id).filter(
                _STATUS_FILTER[AttendanceStatus.NOT_ENTERED]
            ),
            func.count(Student.id).filter(Student.is_applied.is_(True)),
        )
        .select_from(Student)
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(Zone, Zone.id == Student.zone_id)
        .where(*conds)
    )
    total, entered, cheating, not_entered, applied = db.execute(stmt).one()
    return AttendanceSummaryResponse(
        test_session_id=test_session_id,
        total=total or 0,
        entered=entered or 0,
        cheating=cheating or 0,
        not_entered=not_entered or 0,
        applied=applied or 0,
    )
