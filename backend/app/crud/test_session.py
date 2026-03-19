"""CRUD operations for TestSession and related models."""

import hashlib
import logging
import math
import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.cheating_log import CheatingLog
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_log import StudentLog
from app.models.student_ps_data import StudentPsData
from app.models.test import Test
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.crud.lookup import DuplicateError, _check_unique_before_write, _parse_integrity_error

logger = logging.getLogger(__name__)

# SessionState key constants
STATE_KEY_CREATED = 1
STATE_KEY_LOADING = 2
STATE_KEY_EMBEDDING = 3
STATE_KEY_ACTIVE = 4
STATE_KEY_FINISHED = 5


# --- SessionState ---

def get_session_states(db: Session, only_active: bool = True) -> list[SessionState]:
    stmt = select(SessionState)
    if only_active:
        stmt = stmt.where(SessionState.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


# --- Test ---

def get_tests(db: Session, only_active: bool = True) -> list[Test]:
    stmt = select(Test)
    if only_active:
        stmt = stmt.where(Test.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


# --- Smena ---

def get_smenas(db: Session, only_active: bool = True) -> list[Smena]:
    stmt = select(Smena)
    if only_active:
        stmt = stmt.where(Smena.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


# --- TestSession ---

def _generate_hash_key() -> str:
    return hashlib.sha256(uuid.uuid4().bytes).hexdigest()[:32]


def _next_session_number(db: Session) -> int:
    result = db.execute(
        select(func.coalesce(func.max(TestSession.number), 0))
    ).scalar()
    return result + 1


def _next_smena_number(db: Session) -> int:
    result = db.execute(
        select(func.coalesce(func.max(TestSessionSmena.number), 0))
    ).scalar()
    return result + 1


def get_test_sessions_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    is_active: bool | None = None,
    test_id: int | None = None,
) -> tuple[list[TestSession], int]:
    stmt = select(TestSession).order_by(TestSession.id.desc())
    count_stmt = select(func.count(TestSession.id))

    if is_active is not None:
        stmt = stmt.where(TestSession.is_active == is_active)
        count_stmt = count_stmt.where(TestSession.is_active == is_active)
    if test_id is not None:
        stmt = stmt.where(TestSession.test_id == test_id)
        count_stmt = count_stmt.where(TestSession.test_id == test_id)

    total = db.execute(count_stmt).scalar() or 0
    items = list(
        db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).scalars().all()
    )
    return items, total


def get_active_test_sessions(db: Session) -> list[TestSession]:
    """Barcha aktiv sessiyalarni olish (is_active=True)."""
    stmt = (
        select(TestSession)
        .where(TestSession.is_active.is_(True))
        .order_by(TestSession.id.desc())
    )
    return list(db.execute(stmt).scalars().all())


def count_students_by_session_and_zone(
    db: Session, *, test_session_id: int, zone_id: int
) -> int:
    """Sessiyaga tegishli ma'lum zonadagi studentlar sonini olish."""
    stmt = (
        select(func.count(Student.id))
        .join(TestSessionSmena, Student.session_smena_id == TestSessionSmena.id)
        .where(
            TestSessionSmena.test_session_id == test_session_id,
            Student.zone_id == zone_id,
        )
    )
    return db.execute(stmt).scalar() or 0


def count_students_per_smena_by_zone(
    db: Session, *, test_session_id: int, zone_id: int
) -> dict[int, int]:
    """Sessiyaning har bir smenasi uchun zonadagi student sonini olish.

    Returns: {smena_id: count, ...}
    """
    stmt = (
        select(
            Student.session_smena_id,
            func.count(Student.id),
        )
        .join(TestSessionSmena, Student.session_smena_id == TestSessionSmena.id)
        .where(
            TestSessionSmena.test_session_id == test_session_id,
            Student.zone_id == zone_id,
        )
        .group_by(Student.session_smena_id)
    )
    return {smena_id: cnt for smena_id, cnt in db.execute(stmt).all()}


def get_test_session(db: Session, session_id: int) -> TestSession | None:
    return db.get(TestSession, session_id)


def create_test_session(
    db: Session,
    *,
    test_id: int,
    name: str,
    start_date: date,
    finish_date: date,
    count_sm_per_day: int = 0,
    smenas: list[dict[str, Any]] | None = None,
) -> TestSession:
    # Default state: key=1 bo'lgan SessionState
    default_state = db.execute(
        select(SessionState).where(SessionState.key == 1)
    ).scalar()
    if not default_state:
        raise DuplicateError("SessionState key=1 topilmadi. Avval holat yarating")
    test_state_id = default_state.id

    session = TestSession(
        hash_key=_generate_hash_key(),
        test_state_id=test_state_id,
        test_id=test_id,
        name=name,
        number=_next_session_number(db),
        count_sm_per_day=count_sm_per_day,
        start_date=start_date,
        finish_date=finish_date,
    )
    db.add(session)
    db.flush()

    # Smena larni qo'shish (batch ichida dublikat tekshirish)
    if smenas:
        seen: set[tuple[int, str]] = set()
        base_number = _next_smena_number(db)
        for i, smena_data in enumerate(smenas):
            key = (smena_data["test_smena_id"], str(smena_data["day"]))
            if key in seen:
                db.rollback()
                raise DuplicateError(
                    f"Bir sessiyada {smena_data['day']} sanasida bitta smena ikki marta kiritilgan"
                )
            seen.add(key)
            smena = TestSessionSmena(
                test_session_id=session.id,
                test_smena_id=smena_data["test_smena_id"],
                number=base_number + i,
                day=smena_data["day"],
            )
            db.add(smena)

    try:
        db.commit()
    except IntegrityError as e:
        logger.error("TestSession create IntegrityError: %s", e.orig or e)
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(session)
    return session


def update_test_session(
    db: Session, *, session_id: int, data: dict[str, Any]
) -> TestSession | None:
    session = db.get(TestSession, session_id)
    if not session:
        return None
    # test_state_id o'zgartirilsa change_session_state orqali boshqariladi
    # shuning uchun bu yerda state o'zgartirish bo'lmasin
    data.pop("test_state_id", None)
    if not data:
        db.refresh(session)
        return session
    # Pre-check unique fields BEFORE update → prevents sequence gap
    _check_unique_before_write(db, TestSession, data, exclude_id=session_id)
    for key, value in data.items():
        if value is not None:
            setattr(session, key, value)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(session)
    return session


def change_session_state(
    db: Session, *, session_id: int, new_state_id: int
) -> TestSession:
    """Change session state with business rules.

    - key=4 → is_active=True, boshqalarda is_active=False
    - key=2 → studentlarni tashqi API dan yuklash kerak (endpoint da bajariladi)
    """
    session = db.get(TestSession, session_id)
    if not session:
        raise DuplicateError("Sessiya topilmadi")

    new_state = db.get(SessionState, new_state_id)
    if not new_state:
        raise DuplicateError("Holat topilmadi")

    # Holatni yangilash
    session.test_state_id = new_state_id

    # key=4 → is_active=True, key=5 → is_active=False
    if new_state.key == STATE_KEY_ACTIVE:
        session.is_active = True
    elif new_state.key == STATE_KEY_FINISHED:
        session.is_active = False

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(session)
    return session


def _delete_students_by_smena_ids(db: Session, smena_ids: list[int]) -> None:
    """Berilgan smena ID larga tegishli studentlar va ularning bog'liq datalarini o'chirish."""
    if not smena_ids:
        return
    student_ids = [
        row[0]
        for row in db.execute(
            select(Student.id).where(Student.session_smena_id.in_(smena_ids))
        )
    ]
    if not student_ids:
        return
    db.execute(
        CheatingLog.__table__.delete().where(CheatingLog.student_id.in_(student_ids))
    )
    db.execute(
        StudentLog.__table__.delete().where(StudentLog.student_id.in_(student_ids))
    )
    db.execute(
        StudentPsData.__table__.delete().where(StudentPsData.student_id.in_(student_ids))
    )
    db.execute(
        Student.__table__.delete().where(Student.id.in_(student_ids))
    )


def _delete_students_by_session(db: Session, session_id: int) -> None:
    """Sessiyaga tegishli barcha studentlarni o'chirish."""
    smena_ids = [
        row[0]
        for row in db.execute(
            select(TestSessionSmena.id).where(
                TestSessionSmena.test_session_id == session_id
            )
        )
    ]
    _delete_students_by_smena_ids(db, smena_ids)


def delete_test_session(db: Session, session_id: int) -> bool:
    session = db.get(TestSession, session_id)
    if not session:
        return False

    _delete_students_by_session(db, session_id)

    # TestSessionSmena larni o'chirish
    db.execute(
        TestSessionSmena.__table__.delete().where(
            TestSessionSmena.test_session_id == session_id
        )
    )
    # TestSession ni o'chirish (ORM emas, to'g'ridan-to'g'ri SQL)
    db.execute(
        TestSession.__table__.delete().where(TestSession.id == session_id)
    )
    try:
        db.commit()
    except IntegrityError as e:
        logger.error("TestSession delete IntegrityError: %s", e.orig or e)
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    return True


# --- TestSessionSmena ---

def add_smena_to_session(
    db: Session,
    *,
    test_session_id: int,
    test_smena_id: int,
    day: date,
) -> TestSessionSmena:
    # Unique tekshirish: bir sessiyada bir smenada bir kunda faqat bitta yozuv
    existing = db.execute(
        select(TestSessionSmena).where(
            TestSessionSmena.test_session_id == test_session_id,
            TestSessionSmena.test_smena_id == test_smena_id,
            TestSessionSmena.day == day,
        )
    ).scalar()
    if existing:
        raise DuplicateError(
            f"Bu sessiyada {day} sanasida ushbu smena allaqachon mavjud"
        )

    smena = TestSessionSmena(
        test_session_id=test_session_id,
        test_smena_id=test_smena_id,
        number=_next_smena_number(db),
        day=day,
    )
    db.add(smena)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(smena)
    return smena


def remove_smena_from_session(db: Session, smena_id: int) -> bool:
    smena = db.get(TestSessionSmena, smena_id)
    if not smena:
        return False

    test_session_id = smena.test_session_id

    # Avval shu smenaga tegishli studentlar va ularning bog'liq datalarini o'chirish
    _delete_students_by_smena_ids(db, [smena_id])

    db.delete(smena)
    db.flush()

    # TestSession dagi count_total_student ni yangilash
    test_session = db.get(TestSession, test_session_id)
    if test_session:
        smena_ids = [
            row[0]
            for row in db.execute(
                select(TestSessionSmena.id).where(
                    TestSessionSmena.test_session_id == test_session_id
                )
            )
        ]
        actual_count = (
            db.scalar(
                select(func.count(Student.id)).where(
                    Student.session_smena_id.in_(smena_ids)
                )
            )
            if smena_ids
            else 0
        )
        test_session.count_total_student = actual_count

    db.commit()
    return True
