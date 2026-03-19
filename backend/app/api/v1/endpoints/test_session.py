"""Test Session CRUD endpoints."""

import logging
import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.crud.lookup import DuplicateError
from app.crud.student import get_students_by_session_and_zone
from app.crud.test_session import (
    STATE_KEY_ACTIVE,
    STATE_KEY_EMBEDDING,
    STATE_KEY_LOADING,
    add_smena_to_session,
    change_session_state,
    count_students_by_session_and_zone,
    count_students_per_smena_by_zone,
    create_test_session,
    delete_test_session,
    get_active_test_sessions,
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
from app.models.test_session import TestSession
from app.models.user import User
from app.schemas.student import StudentResponse
from app.schemas.test_session import (
    ActiveSmenaResponse,
    ActiveTestSessionResponse,
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
from app.services.embedding_extractor import get_embedding_progress
from app.services.student_loader import StudentLoadError, load_students_for_session
from app.tasks.verify_task import process_embeddings, process_retry_embeddings

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


@router.get("/active", response_model=list[ActiveTestSessionResponse])
def list_active_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Barcha aktiv test sessiyalar ro'yxati (is_active=True).

    Har bir sessiya uchun joriy foydalanuvchi zonasidagi student soni va zona nomi qaytariladi.
    """
    sessions = get_active_test_sessions(db)
    zone_id = current_user.zone_id
    zone_name = current_user.zone_name if zone_id else ""

    result = []
    for session in sessions:
        data = ActiveTestSessionResponse.model_validate(session)
        data.zone_name = zone_name
        if zone_id:
            data.zone_student_count = count_students_by_session_and_zone(
                db, test_session_id=session.id, zone_id=zone_id
            )
            smena_counts = count_students_per_smena_by_zone(
                db, test_session_id=session.id, zone_id=zone_id
            )
            for smena in data.smenas:
                smena.sm_student_count = smena_counts.get(smena.id, 0)
        result.append(data)
    return result


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


@router.get("/{session_id}/students", response_model=list[StudentResponse])
def list_session_students(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sessiyaga tegishli studentlar ro'yxati (faqat userni zonasidagi studentlar).

    Joriy foydalanuvchining zone_id si orqali filtrlaydi.
    """
    if not current_user.zone_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga zona biriktirilmagan",
        )

    session = get_test_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    return get_students_by_session_and_zone(
        db, test_session_id=session_id, zone_id=current_user.zone_id
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

    Agar tashqi API xatolik bersa, holat eski holatiga qaytariladi.
    """
    # Eski holatni eslab qolish (rollback uchun)
    old_session = db.get(TestSession, session_id)
    if not old_session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")
    previous_state_id = old_session.test_state_id

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
            _rollback_state(db, session_id, previous_state_id)
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            logger.error("Session #%d: kutilmagan xatolik: %s", session_id, e)
            _rollback_state(db, session_id, previous_state_id)
            raise HTTPException(
                status_code=500,
                detail="Tashqi API dan ma'lumot olishda kutilmagan xatolik yuz berdi",
            )

    # key=3 → face embedding chiqarish (Celery task)
    if new_state and new_state.key == STATE_KEY_EMBEDDING:
        process_embeddings.delay(session_id)
        logger.info("Session #%d: embedding Celery task boshlandi", session_id)

    # key=4 → sessiya faollashtirish — barcha studentlar is_ready=True bo'lishi kerak
    if new_state and new_state.key == STATE_KEY_ACTIVE:
        from sqlalchemy import func, select as sa_select
        from app.models.student import Student
        from app.models.test_session_smena import TestSessionSmena as TSSmena

        smena_ids = [
            row[0]
            for row in db.execute(
                sa_select(TSSmena.id).where(TSSmena.test_session_id == session_id)
            )
        ]
        not_ready_count = 0
        if smena_ids:
            not_ready_count = db.scalar(
                sa_select(func.count(Student.id)).where(
                    Student.session_smena_id.in_(smena_ids),
                    Student.is_ready.is_(False),
                )
            ) or 0

        if not_ready_count > 0:
            # Batafsil ma'lumot olish
            no_image_count = db.scalar(
                sa_select(func.count(Student.id)).where(
                    Student.session_smena_id.in_(smena_ids),
                    Student.is_image.is_(False),
                )
            ) or 0
            no_face_count = db.scalar(
                sa_select(func.count(Student.id)).where(
                    Student.session_smena_id.in_(smena_ids),
                    Student.is_image.is_(True),
                    Student.is_face.is_(False),
                )
            ) or 0

            parts: list[str] = []
            if no_image_count > 0:
                parts.append(f"{no_image_count} ta studentda rasm topilmadi")
            if no_face_count > 0:
                parts.append(f"{no_face_count} ta studentda yuz aniqlanmadi")
            remaining = not_ready_count - no_image_count - no_face_count
            if remaining > 0:
                parts.append(f"{remaining} ta student tayyor emas")
            detail = "Sessiyani faollashtirish mumkin emas: " + ", ".join(parts)
            _rollback_state(db, session_id, previous_state_id)
            raise HTTPException(status_code=400, detail=detail)

    return session


def _rollback_state(db: Session, session_id: int, previous_state_id: int) -> None:
    """Xatolik bo'lganda holatni eski holatiga qaytarish."""
    try:
        change_session_state(
            db,
            session_id=session_id,
            new_state_id=previous_state_id,
        )
    except Exception:
        logger.error(
            "Session #%d: holatni qaytarishda xatolik", session_id
        )


@router.get("/{session_id}/embedding-progress")
def embedding_progress(
    session_id: int,
    _: User = Depends(get_current_active_user),
):
    """Embedding jarayoni progressini olish (Redis dan)."""
    progress = get_embedding_progress(session_id)
    if not progress:
        return {
            "current": 0, "total": 0, "success": 0,
            "no_image": 0, "no_face": 0, "errors": 0, "failed": 0,
            "percent": 0, "status": "idle",
        }
    return progress


@router.get("/{session_id}/student-stats")
def session_student_stats(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    """Sessiya studentlari statistikasi: jami, tayyor, rasmsiz, yuzsiz."""
    from sqlalchemy import func, select as sa_select
    from app.models.student import Student
    from app.models.test_session_smena import TestSessionSmena as TSSmena

    smena_ids = [
        row[0]
        for row in db.execute(
            sa_select(TSSmena.id).where(TSSmena.test_session_id == session_id)
        )
    ]
    if not smena_ids:
        return {"total": 0, "ready": 0, "not_ready": 0, "no_image": 0, "no_face": 0}

    base = Student.session_smena_id.in_(smena_ids)
    total = db.scalar(sa_select(func.count(Student.id)).where(base)) or 0
    ready = db.scalar(
        sa_select(func.count(Student.id)).where(base, Student.is_ready.is_(True))
    ) or 0
    no_image = db.scalar(
        sa_select(func.count(Student.id)).where(base, Student.is_image.is_(False))
    ) or 0
    no_face = db.scalar(
        sa_select(func.count(Student.id)).where(
            base, Student.is_image.is_(True), Student.is_face.is_(False)
        )
    ) or 0

    return {
        "total": total,
        "ready": ready,
        "not_ready": total - ready,
        "no_image": no_image,
        "no_face": no_face,
    }


@router.post("/{session_id}/retry-embedding")
def retry_embedding(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Faqat is_ready=False bo'lgan studentlar uchun qayta embedding olish.

    Celery task ga yuboriladi.
    """
    session = get_test_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    # is_ready=False studentlar borligini tekshirish
    from sqlalchemy import func, select as sa_select
    from app.models.student import Student
    from app.models.test_session_smena import TestSessionSmena as TSSmena

    smena_ids = [
        row[0]
        for row in db.execute(
            sa_select(TSSmena.id).where(TSSmena.test_session_id == session_id)
        )
    ]
    not_ready = 0
    if smena_ids:
        not_ready = db.scalar(
            sa_select(func.count(Student.id)).where(
                Student.session_smena_id.in_(smena_ids),
                Student.is_ready.is_(False),
            )
        ) or 0

    if not_ready == 0:
        raise HTTPException(
            status_code=400,
            detail="Barcha studentlar tayyor — qayta embedding kerak emas",
        )

    process_retry_embeddings.delay(session_id)
    logger.info("Session #%d: qayta embedding Celery task boshlandi (%d student)", session_id, not_ready)

    return {"message": f"{not_ready} ta student uchun qayta embedding boshlandi", "not_ready": not_ready}


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
