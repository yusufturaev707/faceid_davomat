"""Proctoring kompyuterlarini nomzodlarga biriktirish (admin panel).

Oqim: test sessiyasi sahifasida «Kompyuterlarni biriktirish» → forma:
kun+smena va Proctoring'dagi ochiq sessiya tanlanadi → "Tekshirish"
(`dry_run`, hech narsa yozilmaydi) → "Biriktirish". Natija `sp_n` da;
desktop client ma'lumotni SHUNDAN KEYIN yuklab olishi kerak.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.dependencies import PermissionChecker, get_db
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student import Student
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.user import User
from app.services import proctoring_client
from app.services.seat_assignment import SeatAssignmentError, assign_seats

router = APIRouter()

#: Yakunlangan sessiyada biriktirish ma'nosiz — nomzodlar allaqachon o'tirgan.
_STATE_KEY_FINISHED = 5


class ProctoringZoneRef(BaseModel):
    region_dtm_id: int
    zone_number: int
    zone_name: str
    region_name: str


class ProctoringScheduleResponse(BaseModel):
    id: int
    exam_name: str
    exam_date: date
    starts_at: datetime
    ends_at: datetime
    zone: ProctoringZoneRef | None = None  # None — barcha binolar


class SeatAssignmentRequest(BaseModel):
    session_smena_id: int
    schedule_id: int
    dry_run: bool = False


class ZoneReportResponse(BaseModel):
    zone_id: int
    zone_name: str
    region_number: int
    zone_number: int
    candidates: int
    computers: int
    kept: int
    assigned: int
    unassigned: int


class SeatAssignmentResponse(BaseModel):
    schedule_id: int
    dry_run: bool
    totals: dict[str, int]
    changed_rows: int
    zones: list[ZoneReportResponse]
    missing_zones: list[ZoneReportResponse]


class SmenaSeatSummary(BaseModel):
    session_smena_id: int
    day: date
    smena_name: str
    candidates: int
    assigned: int
    schedule_ids: list[int]


def _proctoring_call(fn, *args, **kwargs):
    """Proctoring xatosini admin tushunadigan HTTP javobga aylantiradi."""
    try:
        return fn(*args, **kwargs)
    except proctoring_client.ProctoringNotConfigured:
        raise HTTPException(503, "Proctoring API sozlanmagan (PROCTORING_API_URL/KEY)")
    except proctoring_client.ProctoringError as exc:
        raise HTTPException(502, f"Proctoring: {exc.message}")


@router.get(
    "/proctoring/schedules",
    response_model=list[ProctoringScheduleResponse],
    summary="Proctoring'dagi ochiq (tugamagan) test sessiyalari",
)
def list_proctoring_schedules(
    _: User = Depends(PermissionChecker(P.TEST_SESSION_ASSIGN_SEATS.code)),
):
    return _proctoring_call(proctoring_client.list_schedules)


@router.get(
    "/test-sessions/{session_id}/seat-assignment",
    response_model=list[SmenaSeatSummary],
    summary="Kun+smena kesimida kompyuter biriktirilganlar soni",
)
def seat_assignment_summary(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.TEST_SESSION_ASSIGN_SEATS.code)),
):
    # Bitta GROUP BY: arizalilar hisobga olinmaydi (client ularni yuklamaydi).
    assigned = Student.proctoring_schedule_id.is_not(None)
    rows = db.execute(
        select(
            TestSessionSmena.id,
            TestSessionSmena.day,
            Smena.name,
            func.count(Student.id).filter(Student.is_applied.is_(False)),
            func.count(Student.id).filter(assigned),
            func.array_agg(func.distinct(Student.proctoring_schedule_id)).filter(assigned),
        )
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .outerjoin(Student, Student.session_smena_id == TestSessionSmena.id)
        .where(TestSessionSmena.test_session_id == session_id)
        .group_by(TestSessionSmena.id, TestSessionSmena.day, Smena.name, Smena.number)
        .order_by(TestSessionSmena.day, Smena.number)
    ).all()
    return [
        SmenaSeatSummary(
            session_smena_id=row[0],
            day=row[1],
            smena_name=row[2],
            candidates=row[3] or 0,
            assigned=row[4] or 0,
            schedule_ids=sorted(value for value in (row[5] or []) if value is not None),
        )
        for row in rows
    ]


@router.post(
    "/test-sessions/{session_id}/assign-seats",
    response_model=SeatAssignmentResponse,
    summary="Proctoring kompyuterlarini nomzodlarga biriktirish (sp_n)",
)
def assign_session_seats(
    session_id: int,
    body: SeatAssignmentRequest,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.TEST_SESSION_ASSIGN_SEATS.code)),
):
    session = db.get(TestSession, session_id)
    if session is None:
        raise HTTPException(404, "Sessiya topilmadi")
    state = db.get(SessionState, session.test_state_id)
    if state is not None and state.key == _STATE_KEY_FINISHED:
        raise HTTPException(409, "Sessiya yakunlangan — kompyuter biriktirib bo'lmaydi")
    smena = db.get(TestSessionSmena, body.session_smena_id)
    if smena is None or smena.test_session_id != session_id:
        raise HTTPException(404, "Kun va smena bu sessiyaga tegishli emas")

    try:
        report = _proctoring_call(
            assign_seats,
            db,
            session_smena_id=smena.id,
            schedule_id=body.schedule_id,
            dry_run=body.dry_run,
        )
    except SeatAssignmentError as exc:
        raise HTTPException(409, str(exc))

    return SeatAssignmentResponse(
        schedule_id=report.schedule_id,
        dry_run=report.dry_run,
        totals=report.totals,
        changed_rows=report.changed_rows,
        zones=[ZoneReportResponse(**vars(z)) for z in report.zones],
        missing_zones=[ZoneReportResponse(**vars(z)) for z in report.missing_zones],
    )
