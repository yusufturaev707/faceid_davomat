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
from app.core.permissions import P
from app.dependencies import PermissionChecker, get_current_active_user, get_db
from app.models.session_state import SessionState
from app.models.test_session import TestSession
from app.models.user import User
from app.models.zone import Zone
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


def _resolve_effective_zone(
    db: Session, current_user: User, requested_zone_id: int | None
) -> tuple[int, str]:
    """Client tomonidan uzatilgan `zone_id`ni tekshirib, effective
    (zone_id, zone_name) juftligini qaytaradi.

    Xatti-harakat:
    - `requested_zone_id` None bo'lsa — foydalanuvchining o'z zonasi ishlatiladi
      (eski xulq-atvor saqlanadi).
    - Aks holda — berilgan zona user region'iga tegishliligi tekshiriladi.
      Tegishli emas bo'lsa 403 qaytadi. Shu bilan bir userning boshqa
      region zonalariga ma'lumot so'rashi bloklanadi.
    """
    user_zone_id = current_user.zone_id
    user_region_id = current_user.region_id
    user_zone_name = current_user.zone_name or ""

    if requested_zone_id is None or requested_zone_id == user_zone_id:
        return int(user_zone_id) if user_zone_id else 0, user_zone_name

    if not user_region_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga region biriktirilmagan",
        )

    zone = db.get(Zone, int(requested_zone_id))
    if not zone:
        raise HTTPException(status_code=404, detail="Zone topilmadi")
    if int(zone.region_id) != int(user_region_id):
        raise HTTPException(
            status_code=403,
            detail="Tanlangan zone foydalanuvchi regioniga tegishli emas",
        )
    return int(zone.id), zone.name


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
    zone_id: int | None = Query(
        default=None,
        description=(
            "Ixtiyoriy: boshqa zonaga (bino) bog'liq statistikani olish uchun. "
            "Bo'sh bo'lsa — foydalanuvchining o'z zonasi ishlatiladi. "
            "Berilgan zona user region'iga tegishli bo'lishi shart."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Barcha aktiv test sessiyalar ro'yxati (is_active=True).

    Har bir sessiya uchun `zone_id` (yoki user zonasi) bo'yicha student soni
    va zona nomi qaytariladi. Desktop tomonidan region ichidagi har qanday
    zone tanlash uchun ishlatiladi.
    """
    sessions = get_active_test_sessions(db)
    effective_zone_id, effective_zone_name = _resolve_effective_zone(
        db, current_user, zone_id
    )

    result = []
    for session in sessions:
        data = ActiveTestSessionResponse.model_validate(session)
        data.zone_name = effective_zone_name
        if effective_zone_id:
            data.zone_student_count = count_students_by_session_and_zone(
                db, test_session_id=session.id, zone_id=effective_zone_id
            )
            smena_counts = count_students_per_smena_by_zone(
                db, test_session_id=session.id, zone_id=effective_zone_id
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_READ.code)),
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
    zone_id: int | None = Query(
        default=None,
        description=(
            "Ixtiyoriy: boshqa zonaga (bino) bog'liq studentlarni olish uchun. "
            "Bo'sh bo'lsa — foydalanuvchining o'z zonasi ishlatiladi. "
            "Berilgan zona user region'iga tegishli bo'lishi shart."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Sessiyaga tegishli studentlar ro'yxati (tanlangan zona bo'yicha).

    Agar `zone_id` berilgan bo'lsa va u user region'iga tegishli bo'lsa —
    shu zona studentlarini qaytaradi. Aks holda user o'zining zonasidagi
    studentlarni oladi."""
    effective_zone_id, _name = _resolve_effective_zone(db, current_user, zone_id)
    if not effective_zone_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga zona biriktirilmagan",
        )

    session = get_test_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessiya topilmadi")

    return get_students_by_session_and_zone(
        db, test_session_id=session_id, zone_id=effective_zone_id
    )


@router.get("/{session_id}", response_model=TestSessionResponse)
def get_session(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.TEST_SESSION_READ.code)),
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_CREATE.code)),
):
    """Yangi test sessiya yaratish.

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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_UPDATE.code)),
):
    """Test sessiyani yangilash. Holatni o'zgartirish uchun /state endpointdan foydalaning."""
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_UPDATE.code)),
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_READ.code)),
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_READ.code)),
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


@router.get("/smenas/{smena_id}/attendance-stats")
def smena_attendance_stats(
    smena_id: int,
    zone_id: int | None = Query(
        default=None,
        description=(
            "Ixtiyoriy: tanlangan zona bo'yicha davomat statistikasini olish. "
            "Bo'sh bo'lsa — user o'z zonasi. Zona user region'iga tegishli bo'lishi shart."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Smena + bino (zone) kesimida davomat statistikasi.

    Tanlangan `zone_id` (yoki user o'zining zonasi) va berilgan smena bo'yicha
    jami, kirgan, kirmagan va chetlatilgan (cheating) sonini qaytaradi.
    """
    effective_zone_id, _name = _resolve_effective_zone(db, current_user, zone_id)
    if not effective_zone_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga zona biriktirilmagan",
        )

    from sqlalchemy import func, select as sa_select
    from app.models.student import Student

    base = (
        (Student.session_smena_id == smena_id)
        & (Student.zone_id == effective_zone_id)
    )
    total = db.scalar(sa_select(func.count(Student.id)).where(base)) or 0
    entered = db.scalar(
        sa_select(func.count(Student.id)).where(base, Student.is_entered.is_(True))
    ) or 0
    cheating = db.scalar(
        sa_select(func.count(Student.id)).where(base, Student.is_cheating.is_(True))
    ) or 0

    return {
        "total": total,
        "entered": entered,
        "not_entered": max(0, total - entered),
        "cheating": cheating,
    }


@router.get("/smenas/{smena_id}/attendance-by-region")
def smena_attendance_by_region(
    smena_id: int,
    zone_id: int | None = Query(
        default=None,
        description=(
            "Tanlangan/aktiv bino. Berilmasa — user o'zining zonasi. "
            "Region shu zonadan aniqlanadi va bino bu region ichida bo'lishi shart."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Smena + region kesimida har bir bino bo'yicha davomat statistikasi.

    Qaytaradi:
      - test_day, smena_number, smena_name (test_session_smena dan);
      - region_id, region_name (aktiv zonadan kelib chiqib);
      - active_zone_id (tanlangan bino — chiroyli highlight uchun);
      - zones: shu region'dagi har bino bo'yicha
        {zone_id, zone_name, zone_number, total, entered, not_entered, cheating, is_active}.

    Bitta GROUP BY query orqali samarali ravishda olinadi.
    """
    from sqlalchemy import case, func, select as sa_select
    from app.models.region import Region
    from app.models.smena import Smena
    from app.models.student import Student
    from app.models.test_session_smena import TestSessionSmena

    effective_zone_id, _name = _resolve_effective_zone(db, current_user, zone_id)
    if not effective_zone_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga zona biriktirilmagan",
        )

    tss_row = db.execute(
        sa_select(
            TestSessionSmena.id,
            TestSessionSmena.day,
            TestSessionSmena.number,
            Smena.name,
        )
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .where(TestSessionSmena.id == smena_id)
    ).first()
    if not tss_row:
        raise HTTPException(status_code=404, detail="Smena topilmadi")

    active_zone = db.execute(
        sa_select(Zone.id, Zone.name, Zone.number, Zone.region_id).where(
            Zone.id == effective_zone_id
        )
    ).first()
    if not active_zone:
        raise HTTPException(status_code=404, detail="Bino topilmadi")

    region_id = active_zone.region_id
    region_row = db.execute(
        sa_select(Region.id, Region.name).where(Region.id == region_id)
    ).first()

    zones_in_region = db.execute(
        sa_select(Zone.id, Zone.name, Zone.number)
        .where(Zone.region_id == region_id, Zone.is_active.is_(True))
        .order_by(Zone.number, Zone.name)
    ).all()

    zone_ids = [z.id for z in zones_in_region]
    stats_by_zone: dict[int, dict] = {
        z.id: {"total": 0, "entered": 0, "cheating": 0} for z in zones_in_region
    }

    if zone_ids:
        rows = db.execute(
            sa_select(
                Student.zone_id,
                func.count(Student.id).label("total"),
                func.sum(case((Student.is_entered.is_(True), 1), else_=0)).label(
                    "entered"
                ),
                func.sum(case((Student.is_cheating.is_(True), 1), else_=0)).label(
                    "cheating"
                ),
            )
            .where(
                Student.session_smena_id == smena_id,
                Student.zone_id.in_(zone_ids),
            )
            .group_by(Student.zone_id)
        ).all()
        for row in rows:
            stats_by_zone[row.zone_id] = {
                "total": int(row.total or 0),
                "entered": int(row.entered or 0),
                "cheating": int(row.cheating or 0),
            }

    zones_payload = []
    for z in zones_in_region:
        s = stats_by_zone.get(z.id, {"total": 0, "entered": 0, "cheating": 0})
        total = s["total"]
        entered = s["entered"]
        zones_payload.append(
            {
                "zone_id": z.id,
                "zone_name": z.name,
                "zone_number": z.number,
                "total": total,
                "entered": entered,
                "not_entered": max(0, total - entered),
                "cheating": s["cheating"],
                "is_active": z.id == effective_zone_id,
            }
        )

    return {
        "test_day": tss_row.day.isoformat() if tss_row.day else None,
        "smena_number": tss_row.number,
        "smena_name": tss_row.name,
        "region_id": region_row.id if region_row else region_id,
        "region_name": region_row.name if region_row else "",
        "active_zone_id": effective_zone_id,
        "active_zone_name": active_zone.name,
        "zones": zones_payload,
    }


@router.post("/{session_id}/retry-embedding")
def retry_embedding(
    session_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.TEST_SESSION_UPDATE.code)),
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_DELETE.code)),
):
    """Test sessiyani o'chirish."""
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_UPDATE.code)),
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
    _: User = Depends(PermissionChecker(P.TEST_SESSION_UPDATE.code)),
):
    """Sessiyadan smena olib tashlash."""
    if not remove_smena_from_session(db, smena_id):
        raise HTTPException(status_code=404, detail="Smena topilmadi")
