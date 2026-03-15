"""CRUD operations for TestSession and related models."""

import hashlib
import math
import uuid
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.test import Test
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.crud.lookup import DuplicateError, _check_unique_before_write, _parse_integrity_error


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
    result = db.execute(select(func.max(TestSession.number))).scalar()
    return (result or 0) + 1


def _next_smena_number(db: Session) -> int:
    result = db.execute(select(func.max(TestSessionSmena.number))).scalar()
    return (result or 0) + 1


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
    # Default state: 1 (birinchi holat - "Yaratilgan")
    default_state = db.execute(
        select(SessionState).where(SessionState.is_active.is_(True)).limit(1)
    ).scalar()
    test_state_id = default_state.id if default_state else 1

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

    # Smena larni qo'shish
    if smenas:
        for smena_data in smenas:
            smena = TestSessionSmena(
                test_session_id=session.id,
                test_smena_id=smena_data["test_smena_id"],
                number=_next_smena_number(db),
                day=smena_data["day"],
            )
            db.add(smena)

    try:
        db.commit()
    except IntegrityError as e:
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


def delete_test_session(db: Session, session_id: int) -> bool:
    session = db.get(TestSession, session_id)
    if not session:
        return False
    # Avval bog'liq smena larni o'chiramiz
    db.execute(
        TestSessionSmena.__table__.delete().where(
            TestSessionSmena.test_session_id == session_id
        )
    )
    db.delete(session)
    db.commit()
    return True


# --- TestSessionSmena ---

def add_smena_to_session(
    db: Session,
    *,
    test_session_id: int,
    test_smena_id: int,
    day: date,
) -> TestSessionSmena:
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
    db.delete(smena)
    db.commit()
    return True
