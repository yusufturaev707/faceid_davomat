"""Test Session CRUD endpoints."""

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.lookup import DuplicateError
from app.crud.test_session import (
    STATE_KEY_LOADING,
    add_smena_to_session,
    change_session_state,
    create_test_session,
    delete_test_session,
    get_session_states,
    get_smenas,
    get_test_session,
    get_test_sessions_paginated,
    get_tests,
    remove_smena_from_session,
    update_test_session,
)
from app.dependencies import get_current_active_user, get_db, require_admin
from app.models.session_state import SessionState
from app.models.user import User
from app.schemas.test_session import (
    SessionStateResponse,
    SmenaResponse,
    TestResponse,
    TestSessionCreate,
    TestSessionListResponse,
    TestSessionResponse,
    TestSessionSmenaCreate,
    TestSessionSmenaResponse,
    TestSessionUpdate,
)
from app.services.student_loader import StudentLoadError, load_students_for_session

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Справочники (lookups) ---


@router.get("/tests", response_model=list[TestResponse])
def list_tests(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Barcha faol testlar ro'yxati."""
    return get_tests(db)


@router.get("/smenas", response_model=list[SmenaResponse])
def list_smenas(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Barcha faol smenalar ro'yxati."""
    return get_smenas(db)


@router.get("/states", response_model=list[SessionStateResponse])
def list_session_states(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Barcha faol sessiya holatlari."""
    return get_session_states(db)


# --- TestSession CRUD ---


@router.get("", response_model=TestSessionListResponse)
def list_sessions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    is_active: bool | None = None,
    test_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Test sessiyalar ro'yxati (pagination bilan)."""
    items, total = get_test_sessions_paginated(
        db, page=page, per_page=per_page, is_active=is_active, test_id=test_id
    )
    return TestSessionListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/{session_id}", response_model=TestSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Bitta test sessiyani olish."""
    session = get_test_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    return session


@router.post("", response_model=TestSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session(
    body: TestSessionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Yangi test sessiya yaratish (faqat admin).

    - test tanlash
    - kunlar va smenalar belgilash
    """
    if body.finish_date < body.start_date:
        raise HTTPException(
            status_code=400,
            detail="Tugash sanasi boshlanish sanasidan oldin bo'lishi mumkin emas",
        )

    smenas_data = [s.model_dump() for s in body.smenas] if body.smenas else None

    try:
        session = create_test_session(
            db,
            test_id=body.test_id,
            name=body.name,
            start_date=body.start_date,
            finish_date=body.finish_date,
            count_sm_per_day=body.count_sm_per_day,
            smenas=smenas_data,
        )
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return session


@router.patch("/{session_id}", response_model=TestSessionResponse)
def update_session(
    session_id: int,
    body: TestSessionUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Test sessiyani yangilash (faqat admin). Holatni o'zgartirish uchun /state endpointdan foydalaning."""
    data = body.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="O'zgartirish uchun maydon berilmadi")

    try:
        session = update_test_session(db, session_id=session_id, data=data)
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    return session


class ChangeStateRequest(BaseModel):
    test_state_id: int


@router.patch("/{session_id}/state", response_model=TestSessionResponse)
def change_state(
    session_id: int,
    body: ChangeStateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Sessiya holatini o'zgartirish.

    - key=2 ga o'tganda tashqi API dan studentlar yuklanadi
    - key=4 ga o'tganda is_active=True bo'ladi
    """
    try:
        session = change_session_state(
            db, session_id=session_id, new_state_id=body.test_state_id
        )
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)

    # key=2 → studentlarni yuklash
    new_state = db.get(SessionState, body.test_state_id)
    if new_state and new_state.key == STATE_KEY_LOADING:
        try:
            count = load_students_for_session(db, session)
            logger.info(
                "Session #%d: %d student yuklandi", session_id, count
            )
            # Refresh session after student loading (count_total_student updated)
            db.refresh(session)
        except StudentLoadError as e:
            logger.error("Student load error: %s", e.message)
            raise HTTPException(status_code=400, detail=e.message)

    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Test sessiyani o'chirish (faqat admin)."""
    try:
        if not delete_test_session(db, session_id):
            raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)


# --- Smena management ---


@router.post(
    "/{session_id}/smenas",
    response_model=TestSessionSmenaResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_smena(
    session_id: int,
    body: TestSessionSmenaCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Sessiyaga smena qo'shish."""
    session = get_test_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    try:
        smena = add_smena_to_session(
            db,
            test_session_id=session_id,
            test_smena_id=body.test_smena_id,
            day=body.day,
        )
    except DuplicateError as e:
        raise HTTPException(status_code=409, detail=e.message)
    return smena


@router.delete("/{session_id}/smenas/{smena_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_smena(
    session_id: int,
    smena_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Sessiyadan smena olib tashlash."""
    if not remove_smena_from_session(db, smena_id):
        raise HTTPException(status_code=404, detail="Smena topilmadi")
