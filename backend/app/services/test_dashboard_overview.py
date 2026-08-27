"""Test Dashboard (`/test-dashboard`) uchun umumiy ko'rsatkichlar.

Barchasi viloyat qamrovida hisoblanadi (`app.core.region_scope`): global
qamrovi bor foydalanuvchi butun tizimni, qolganlar faqat o'z viloyatini
ko'radi.

Ta'riflar — `session_dashboard_stats` bilan bir xil bo'lishi uchun:
  Chetlatilgan = `Student.is_cheating`
  Talabgor     = ariza bergani (`is_applied`) hisobga olinmaydi
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import Date, cast, func, select
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.student_log import StudentLog
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.zone import Zone

logger = logging.getLogger(__name__)

# Grafik oynasi — oxirgi 30 kun (bugun ham kiradi).
CHART_DAYS = 30


def _student_scope(region_id: int | None):
    """Talabgorlar uchun umumiy WHERE shartlari."""
    conditions = [Student.is_applied.is_(False)]
    if region_id is not None:
        conditions.append(Zone.region_id == int(region_id))
    return conditions


def _base_student_query(region_id: int | None):
    """Zone bilan join qilingan bazaviy so'rov (region filtri uchun kerak)."""
    stmt = select(func.count(Student.id))
    if region_id is not None:
        stmt = stmt.join(Zone, Zone.id == Student.zone_id)
    return stmt.where(*_student_scope(region_id))


def get_overview(db: Session, region_id: int | None) -> dict:
    """Dashboard uchun 4 ta ko'rsatkich + oxirgi 30 kunlik kirish grafigi.

    Args:
        region_id: `None` bo'lsa — barcha viloyatlar.

    Returns:
        {
          "total_students": int,          # jami talabgor
          "total_rejected": int,          # chetlatilganlar (is_cheating)
          "active_sessions": int,         # faol sessiyalar
          "active_session_students": int, # faol sessiyalarda qatnashishi kerak
          "daily_entered": [{"date": "YYYY-MM-DD", "count": int}, ...],
        }
    """
    # 1) Jami talabgor
    total_students = db.scalar(_base_student_query(region_id)) or 0

    # 2) Chetlatilganlar
    total_rejected = (
        db.scalar(_base_student_query(region_id).where(Student.is_cheating.is_(True)))
        or 0
    )

    # 3-4) Faol sessiyalar va ulardagi talabgorlar.
    #      Viloyat qamrovida "faol sessiya" — shu viloyatda talabgori bor faol
    #      sessiya; aks holda operator o'ziga aloqasi yo'q sessiyalarni sanardi.
    active_smena_subq = (
        select(TestSessionSmena.id)
        .join(TestSession, TestSession.id == TestSessionSmena.test_session_id)
        .where(TestSession.is_active.is_(True))
        .scalar_subquery()
    )

    active_students_stmt = _base_student_query(region_id).where(
        Student.session_smena_id.in_(active_smena_subq)
    )
    active_session_students = db.scalar(active_students_stmt) or 0

    active_sessions_stmt = select(
        func.count(func.distinct(TestSessionSmena.test_session_id))
    ).select_from(Student).join(
        TestSessionSmena, TestSessionSmena.id == Student.session_smena_id
    ).join(
        TestSession, TestSession.id == TestSessionSmena.test_session_id
    ).where(
        TestSession.is_active.is_(True),
        Student.is_applied.is_(False),
    )
    if region_id is not None:
        active_sessions_stmt = active_sessions_stmt.join(
            Zone, Zone.id == Student.zone_id
        ).where(Zone.region_id == int(region_id))
    active_sessions = db.scalar(active_sessions_stmt) or 0

    return {
        "total_students": int(total_students),
        "total_rejected": int(total_rejected),
        "active_sessions": int(active_sessions),
        "active_session_students": int(active_session_students),
        "daily_entered": get_daily_entered(db, region_id),
    }


def get_daily_entered(db: Session, region_id: int | None) -> list[dict]:
    """Oxirgi `CHART_DAYS` kun uchun kunlik kirgan talabgorlar soni.

    Manba — `StudentLog.first_enter_time` (talabgor birinchi marta binoga
    kirgan payt). `Student.is_entered` bayrog'i "kirganmi" degan savolga javob
    beradi, lekin QACHON kirganini faqat log biladi — grafik sana kesimida
    bo'lgani uchun log ishlatiladi.

    Ma'lumot yo'q kunlar ham `count: 0` bilan qaytariladi — grafikda uzilish
    bo'lmasligi uchun.
    """
    today = date.today()
    start = today - timedelta(days=CHART_DAYS - 1)

    day_col = cast(StudentLog.first_enter_time, Date).label("day")
    stmt = (
        select(day_col, func.count(StudentLog.id).label("cnt"))
        .join(Student, Student.id == StudentLog.student_id)
        .where(
            StudentLog.first_enter_time.is_not(None),
            day_col >= start,
            day_col <= today,
            Student.is_applied.is_(False),
        )
        .group_by(day_col)
        .order_by(day_col)
    )
    if region_id is not None:
        stmt = stmt.join(Zone, Zone.id == Student.zone_id).where(
            Zone.region_id == int(region_id)
        )

    counts = {row.day: int(row.cnt) for row in db.execute(stmt).all()}

    return [
        {
            "date": (start + timedelta(days=i)).isoformat(),
            "count": counts.get(start + timedelta(days=i), 0),
        }
        for i in range(CHART_DAYS)
    ]
