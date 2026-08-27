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
    }


def month_bounds(month: date) -> tuple[date, date]:
    """Oyning birinchi va oxirgi kunini qaytaradi."""
    first = month.replace(day=1)
    if first.month == 12:
        nxt = first.replace(year=first.year + 1, month=1)
    else:
        nxt = first.replace(month=first.month + 1)
    return first, nxt - timedelta(days=1)


def get_daily_entered(db: Session, region_id: int | None, month: date) -> dict:
    """Berilgan OY uchun kunlik kirgan talabgorlar soni.

    Manba — `StudentLog.first_enter_time` (talabgor birinchi marta binoga
    kirgan payt). `Student.is_entered` bayrog'i "kirganmi" degan savolga javob
    beradi, lekin QACHON kirganini faqat log biladi.

    Oyning HAR kuni qaytariladi (ma'lumot yo'q kun ham `count: 0`) — grafikda
    uzilish bo'lmasligi va oy uzunligi ko'rinib turishi uchun.

    Returns:
        {"month": "YYYY-MM", "days": [{"date", "count"}, ...], "total": int}
    """
    first, last = month_bounds(month)

    day_col = cast(StudentLog.first_enter_time, Date).label("day")
    stmt = (
        select(day_col, func.count(StudentLog.id).label("cnt"))
        .join(Student, Student.id == StudentLog.student_id)
        .where(
            StudentLog.first_enter_time.is_not(None),
            day_col >= first,
            day_col <= last,
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
    n_days = (last - first).days + 1
    days = [
        {
            "date": (first + timedelta(days=i)).isoformat(),
            "count": counts.get(first + timedelta(days=i), 0),
        }
        for i in range(n_days)
    ]
    return {
        "month": first.strftime("%Y-%m"),
        "days": days,
        "total": sum(d["count"] for d in days),
    }


def earliest_entered_month(db: Session, region_id: int | None) -> str | None:
    """Qamrovda kirish qayd etilgan eng eski oy (`YYYY-MM`) yoki None.

    UI "oldingi oy" tugmasini shu chegarada to'xtatadi — foydalanuvchi
    cheksiz bo'sh oylarga o'tib ketmasin.
    """
    stmt = select(func.min(cast(StudentLog.first_enter_time, Date))).join(
        Student, Student.id == StudentLog.student_id
    ).where(
        StudentLog.first_enter_time.is_not(None),
        Student.is_applied.is_(False),
    )
    if region_id is not None:
        stmt = stmt.join(Zone, Zone.id == Student.zone_id).where(
            Zone.region_id == int(region_id)
        )
    earliest = db.scalar(stmt)
    return earliest.strftime("%Y-%m") if earliest else None
