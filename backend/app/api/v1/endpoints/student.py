"""Student, StudentLog, CheatingLog endpoints (CRUD)."""

import base64
import logging
import math
from io import BytesIO

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


from app.core.permissions import P
from app.crud.student import (
    bulk_create_student_logs,
    bulk_reassign_zone,
    create_cheating_log,
    create_student,
    create_student_log,
    delete_cheating_log,
    delete_student,
    delete_student_log,
    get_cheating_logs_for_export,
    get_cheating_logs_paginated,
    get_filtered_students,
    get_student,
    get_student_log_detail,
    get_student_logs_paginated,
    get_students_paginated,
    remove_student_attendance,
    update_cheating_log,
    update_student,
    update_student_log,
)
from app.dependencies import (
    PermissionChecker,
    get_current_active_user,
    get_db,
)
from app.models.user import User
from app.schemas.student import (
    AppliedStudentItem,
    AppliedStudentsResponse,
    CheatingLogCreate,
    CheatingLogListResponse,
    CheatingLogResponse,
    CheatingLogUpdate,
    NotEnteredGroup,
    NotEnteredGroupStudent,
    NotEnteredGroupedResponse,
    NotEnteredStudentItem,
    NotEnteredStudentsResponse,
    RejectedStudentItem,
    RejectedStudentsResponse,
    StudentCreate,
    StudentListResponse,
    StudentLogBulkRequest,
    StudentLogBulkResponse,
    StudentLogCreate,
    StudentLogDetailResponse,
    StudentLogListResponse,
    StudentLogResponse,
    StudentLogUpdate,
    StudentResponse,
    StudentUpdate,
)
from app.services.student_export import build_students_pdf, build_students_xlsx

router = APIRouter()


def _b64_to_bytes(val: str | None) -> bytes | None:
    """base64 string (data URL yoki sof base64) → bytes."""
    if not val:
        return None
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    try:
        if "," in val and val.index(",") < 80:
            val = val.split(",", 1)[1]
        return base64.b64decode(val)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Base64 dekodlash xatosi: {exc}")


# === Ro'yxatlar (Student / StudentLog / CheatingLog) uchun region qamrovi ===
#
# Role.key asosidagi ko'rish siyosati:
#   key 1, 2, 3 → butun tizim bo'yicha barcha ma'lumot (region filtri ixtiyoriy).
#   key 4       → faqat foydalanuvchiga biriktirilgan region'ga tegishli ma'lumot.
#   boshqa key  → bu ro'yxatlar umuman ko'rinmaydi (403).
_GLOBAL_SCOPE_ROLE_KEYS = frozenset({1, 2, 3})
_REGION_SCOPE_ROLE_KEY = 4


def _scoped_region_id(user: User, requested_region_id: int | None) -> int | None:
    """Foydalanuvchi roli asosida amaldagi `region_id` filtrini qaytaradi.

    - key 1/2/3: global — mijoz bergan ixtiyoriy `requested_region_id` saqlanadi.
    - key 4: majburan foydalanuvchi region'i (mijoz boshqa region so'rasa ham
      almashtiriladi — boshqa region ma'lumoti chiqmaydi). Region biriktirilmagan
      bo'lsa 403.
    - boshqa key: 403 (bu ro'yxatlarni ko'rish huquqi yo'q).
    """
    role_key = user.role_key
    if role_key in _GLOBAL_SCOPE_ROLE_KEYS:
        return requested_region_id
    if role_key == _REGION_SCOPE_ROLE_KEY:
        if not user.region_id:
            raise HTTPException(
                status_code=403,
                detail="Foydalanuvchiga region biriktirilmagan",
            )
        return int(user.region_id)
    raise HTTPException(
        status_code=403,
        detail="Bu ma'lumotlarni ko'rish uchun ruxsat yo'q",
    )


def _student_region_id(db: Session, student_id: int) -> int | None:
    """Talabaning region_id'si (Student.zone → Zone.region_id). Yo'q bo'lsa None."""
    from sqlalchemy import select as sa_select

    from app.models.student import Student as StudentModel
    from app.models.zone import Zone

    return db.execute(
        sa_select(Zone.region_id)
        .join(StudentModel, StudentModel.zone_id == Zone.id)
        .where(StudentModel.id == student_id)
    ).scalar()


def _assert_region_access(user: User, item_region_id: int | None) -> None:
    """Bitta yozuv (detail) ko'rish uchun region ruxsatini tekshiradi.

    - key 1/2/3: ruxsat (butun tizim).
    - key 4: faqat foydalanuvchi region'idagi yozuv. Boshqa region yozuvi
      so'ralsa 404 (yozuv mavjudligini oshkor qilmaslik uchun). Region
      biriktirilmagan bo'lsa 403.
    - boshqa key: 403 (ko'rish huquqi yo'q).
    """
    role_key = user.role_key
    if role_key in _GLOBAL_SCOPE_ROLE_KEYS:
        return
    if role_key == _REGION_SCOPE_ROLE_KEY:
        if not user.region_id:
            raise HTTPException(
                status_code=403,
                detail="Foydalanuvchiga region biriktirilmagan",
            )
        if item_region_id is None or int(item_region_id) != int(user.region_id):
            raise HTTPException(status_code=404, detail="Ma'lumot topilmadi")
        return
    raise HTTPException(
        status_code=403,
        detail="Bu ma'lumotlarni ko'rish uchun ruxsat yo'q",
    )


# ===================== StudentLog =====================


@router.get("/logs", response_model=StudentLogListResponse)
def list_student_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    student_id: int | None = None,
    test_id: int | None = None,
    test_session_id: int | None = None,
    region_id: int | None = None,
    zone_id: int | None = None,
    smena_id: int | None = None,
    gender_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    first_enter_from: str | None = None,
    first_enter_to: str | None = None,
    last_enter_from: str | None = None,
    last_enter_to: str | None = None,
    created_at_from: str | None = None,
    created_at_to: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_LOG_READ.code)),
):
    region_id = _scoped_region_id(current_user, region_id)
    items, total = get_student_logs_paginated(
        db,
        page=page,
        per_page=per_page,
        student_id=student_id,
        test_id=test_id,
        test_session_id=test_session_id,
        region_id=region_id,
        zone_id=zone_id,
        smena_id=smena_id,
        gender_id=gender_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        first_enter_from=first_enter_from,
        first_enter_to=first_enter_to,
        last_enter_from=last_enter_from,
        last_enter_to=last_enter_to,
        created_at_from=created_at_from,
        created_at_to=created_at_to,
        search=search,
    )
    return StudentLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/logs/{log_id}", response_model=StudentLogDetailResponse)
def get_student_log_detail_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_LOG_READ.code)),
):
    """Bitta StudentLog — first_captured/last_captured rasmlari bilan."""
    log = get_student_log_detail(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    _assert_region_access(current_user, _student_region_id(db, log["student_id"]))
    return log


@router.post("/logs", response_model=StudentLogResponse)
def create_student_log_endpoint(
    data: StudentLogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_LOG_CREATE.code)),
):
    log = create_student_log(db, data)
    return log


@router.post("/logs/bulk", response_model=StudentLogBulkResponse)
def bulk_create_student_logs_endpoint(
    payload: StudentLogBulkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_LOG_CREATE.code)),
):
    """Desktop client uchun batch verify-log sync endpoint.

    Har batch ≤ 50 item. Har bir item alohida SAVEPOINT ichida qayta ishlanadi —
    bitta itemning xatosi boshqalarni bloklamaydi. Chetlatilganlar uchun
    CheatingLog ga (student_id, reason_id, user_id=current_user.id) yoziladi,
    Student.is_cheating/is_blacklist yangilanadi, StudentBlacklist ga imei +
    description insert qilinadi (insert-only).
    """
    results = bulk_create_student_logs(db, payload.items, user_id=current_user.id)
    succeeded = sum(1 for r in results if r.status == "ok")
    return StudentLogBulkResponse(
        items=results,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
    )


@router.patch("/logs/{log_id}", response_model=StudentLogResponse)
def update_student_log_endpoint(
    log_id: int,
    data: StudentLogUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_LOG_UPDATE.code)),
):
    log = update_student_log(db, log_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    return log


@router.delete("/logs/{log_id}", status_code=204)
def delete_student_log_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_LOG_DELETE.code)),
):
    if not delete_student_log(db, log_id):
        raise HTTPException(status_code=404, detail="Log topilmadi")


# ===================== CheatingLog =====================


@router.get("/cheating-logs", response_model=CheatingLogListResponse)
def list_cheating_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    student_id: int | None = None,
    search: str | None = Query(
        None,
        description="FIO yoki JShShIR (imei) bo'yicha qidiruv (case-insensitive).",
    ),
    test_id: int | None = None,
    region_id: int | None = None,
    zone_id: int | None = None,
    smena_id: int | None = Query(
        None,
        description="Smena.id (TestSessionSmena.test_smena_id bo'yicha filter).",
    ),
    reason_id: int | None = None,
    reason_type_id: int | None = None,
    date_from: str | None = Query(
        None, description="Smena sanasi (YYYY-MM-DD) — boshlanish."
    ),
    date_to: str | None = Query(
        None, description="Smena sanasi (YYYY-MM-DD) — tugash (inclusive)."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.CHEATING_LOG_READ.code)),
):
    region_id = _scoped_region_id(current_user, region_id)
    items, total = get_cheating_logs_paginated(
        db,
        page=page,
        per_page=per_page,
        student_id=student_id,
        search=search,
        test_id=test_id,
        region_id=region_id,
        zone_id=zone_id,
        smena_id=smena_id,
        reason_id=reason_id,
        reason_type_id=reason_type_id,
        date_from=date_from,
        date_to=date_to,
    )
    return CheatingLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.get("/cheating-logs/export")
def export_cheating_logs(
    student_id: int | None = None,
    search: str | None = Query(
        None,
        description="FIO yoki JShShIR (imei) bo'yicha qidiruv (case-insensitive).",
    ),
    test_id: int | None = None,
    region_id: int | None = None,
    zone_id: int | None = None,
    smena_id: int | None = Query(
        None,
        description="Smena.id (TestSessionSmena.test_smena_id bo'yicha filter).",
    ),
    reason_id: int | None = None,
    reason_type_id: int | None = None,
    date_from: str | None = Query(
        None, description="Smena sanasi (YYYY-MM-DD) — boshlanish."
    ),
    date_to: str | None = Query(
        None, description="Smena sanasi (YYYY-MM-DD) — tugash (inclusive)."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.CHEATING_LOG_READ.code)),
):
    """Chetlatilganlar ro'yxatini joriy filtrlar bo'yicha Excel (.xlsx) ga
    eksport qilib beradi — adminka jadvalidagi ustunlar bilan bir xil."""
    from datetime import datetime

    from app.services.cheating_logs_excel import build_cheating_logs_excel

    region_id = _scoped_region_id(current_user, region_id)
    items = get_cheating_logs_for_export(
        db,
        student_id=student_id,
        search=search,
        test_id=test_id,
        region_id=region_id,
        zone_id=zone_id,
        smena_id=smena_id,
        reason_id=reason_id,
        reason_type_id=reason_type_id,
        date_from=date_from,
        date_to=date_to,
    )
    if not items:
        raise HTTPException(
            status_code=404,
            detail="Tanlangan filtr bo'yicha chetlatilgan topilmadi",
        )

    content = build_cheating_logs_excel(items, title="Chetlatilganlar ro'yxati")
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"chetlatilganlar_{stamp}.xlsx"
    return StreamingResponse(
        BytesIO(content),
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/cheating-logs", response_model=CheatingLogResponse)
def create_cheating_log_endpoint(
    data: CheatingLogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.CHEATING_LOG_CREATE.code)),
):
    log = create_cheating_log(db, data)
    return log


@router.patch("/cheating-logs/{log_id}", response_model=CheatingLogResponse)
def update_cheating_log_endpoint(
    log_id: int,
    data: CheatingLogUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.CHEATING_LOG_UPDATE.code)),
):
    log = update_cheating_log(db, log_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    return log


@router.delete("/cheating-logs/{log_id}", status_code=204)
def delete_cheating_log_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.CHEATING_LOG_DELETE.code)),
):
    if not delete_cheating_log(db, log_id):
        raise HTTPException(status_code=404, detail="Log topilmadi")


# ===================== Student =====================


@router.get("/applied", response_model=AppliedStudentsResponse)
def list_applied_students(
    session_smena_id: int = Query(
        ...,
        description=(
            "Joriy test_session_smena.id — undan test_session_id aniqlanadi va "
            "shu test sessiyasidagi barcha smenalar kesimida ariza bergan "
            "talabalar qaytariladi."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Ariza bergan (`is_applied=True`) talabalar ro'yxati — joriy test
    sessiyasi va foydalanuvchi region'i kesimida.

    Foydalanuvchi region'i `current_user.zone.region_id` orqali aniqlanadi.
    Talaba `zone.region_id` shu region'ga teng bo'lgan barcha studentlar
    qaytariladi (zone foydalanuvchi zonasi bo'lishi shart emas).
    """
    from sqlalchemy import select as sa_select

    from app.models.region import Region
    from app.models.smena import Smena
    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone

    user_region_id = current_user.region_id
    if not user_region_id:
        raise HTTPException(
            status_code=400,
            detail="Foydalanuvchiga region biriktirilmagan",
        )

    current_tss = db.get(TestSessionSmena, session_smena_id)
    if current_tss is None:
        raise HTTPException(status_code=404, detail="Test sessiya smena topilmadi")

    stmt = (
        sa_select(
            StudentModel.id,
            StudentModel.last_name,
            StudentModel.first_name,
            StudentModel.middle_name,
            StudentModel.imei,
            StudentModel.gr_n,
            StudentModel.desc_apply,
            StudentModel.e_date,
            Region.name.label("region_name"),
            Zone.name.label("zone_name"),
            Smena.name.label("smena_name"),
        )
        .join(TestSessionSmena, TestSessionSmena.id == StudentModel.session_smena_id)
        .join(Zone, Zone.id == StudentModel.zone_id)
        .join(Region, Region.id == Zone.region_id)
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .where(
            TestSessionSmena.test_session_id == current_tss.test_session_id,
            Zone.region_id == int(user_region_id),
            StudentModel.is_applied.is_(True),
        )
        .order_by(StudentModel.last_name, StudentModel.first_name)
    )

    rows = db.execute(stmt).all()
    items = [
        AppliedStudentItem(
            id=r.id,
            last_name=r.last_name,
            first_name=r.first_name,
            middle_name=r.middle_name,
            imei=r.imei,
            region_name=r.region_name,
            zone_name=r.zone_name,
            test_date=r.e_date.isoformat() if r.e_date else None,
            smena_name=r.smena_name,
            gr_n=r.gr_n or 0,
            desc_apply=r.desc_apply,
        )
        for r in rows
    ]
    return AppliedStudentsResponse(items=items, total=len(items))


@router.get("/not-entered", response_model=NotEnteredStudentsResponse)
def list_not_entered_students(
    session_smena_id: int = Query(
        ...,
        description=(
            "Joriy test_session_smena.id — shu test/sana/smena kesimida "
            "hali kelmagan (is_entered=False) talabalar qaytariladi."
        ),
    ),
    zone_id: int | None = Query(
        None,
        description=(
            "Tanlangan bino (zone). Berilsa — ro'yxat aynan shu binoga "
            "tegishli talabalar bilan cheklanadi (bino foydalanuvchi "
            "region'iga tegishli bo'lishi shart). Berilmasa — ro'yxat butun "
            "region kesimida qaytariladi."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tanlangan test_session_smena kesimida hali kelmagan
    (`is_entered=False`) talabalar ro'yxati.

    `zone_id` berilsa — ro'yxat aynan shu binoga tegishli talabalar bilan
    cheklanadi (desktop yuklab olgan test sessiyasining binosi). Berilmasa —
    foydalanuvchining butun region'i (bir nechta bino) qamraladi. `is_entered`
    backend tomonida `/students/logs/bulk` sync paytida yangilanadi, ya'ni
    ro'yxat barcha operatorlar sync qilgan davomatni hisobga oladi.
    """
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone

    # Region — avval foydalanuvchiga bevosita biriktirilgan `region_id`.
    # Eski akkauntlarda (region_id hali to'ldirilmagan) zaxira sifatida
    # uzatilgan `zone_id` yoki user zonasi orqali region aniqlanadi.
    target_region_id = current_user.region_id
    if not target_region_id:
        fallback_zone = zone_id or current_user.zone_id
        if fallback_zone:
            zone = db.get(Zone, int(fallback_zone))
            target_region_id = int(zone.region_id) if zone else None
    if not target_region_id:
        raise HTTPException(status_code=400, detail="Region aniqlanmadi")

    # `zone_id` berilsa — ro'yxat shu bino bilan cheklanadi. Bino
    # foydalanuvchi region'iga tegishli ekani tekshiriladi (boshqa region
    # binosini so'rash bloklanadi).
    target_zone_id: int | None = None
    if zone_id:
        zone = db.get(Zone, int(zone_id))
        if not zone:
            raise HTTPException(status_code=404, detail="Bino topilmadi")
        if int(zone.region_id) != int(target_region_id):
            raise HTTPException(
                status_code=403,
                detail="Tanlangan bino foydalanuvchi region'iga tegishli emas",
            )
        target_zone_id = int(zone_id)

    if db.get(TestSessionSmena, session_smena_id) is None:
        raise HTTPException(status_code=404, detail="Test sessiya smena topilmadi")

    list_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
        StudentModel.is_entered.is_(False),
    ]
    if target_zone_id is not None:
        list_filters.append(StudentModel.zone_id == target_zone_id)

    stmt = (
        sa_select(
            StudentModel.last_name,
            StudentModel.first_name,
            StudentModel.middle_name,
            StudentModel.imei,
            StudentModel.gr_n,
            Zone.name.label("zone_name"),
        )
        .join(Zone, Zone.id == StudentModel.zone_id)
        .where(*list_filters)
        # Bino raqami → guruh → familiya/ism bo'yicha tartiblanadi.
        .order_by(
            Zone.number,
            Zone.name,
            StudentModel.gr_n,
            StudentModel.last_name,
            StudentModel.first_name,
        )
    )
    rows = db.execute(stmt).all()
    items = [
        NotEnteredStudentItem(
            last_name=r.last_name,
            first_name=r.first_name,
            middle_name=r.middle_name,
            imei=r.imei,
            gr_n=r.gr_n or 0,
            zone_name=r.zone_name or "",
        )
        for r in rows
    ]

    # roster_total — shu smena (+ tanlangan bino, bo'lmasa region) kesimidagi
    # JAMI talaba soni. Client bo'sh ro'yxatni "hammasi kirgan" va "roster
    # bo'sh" holatlariga ajratadi.
    roster_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
    ]
    if target_zone_id is not None:
        roster_filters.append(StudentModel.zone_id == target_zone_id)
    roster_total = (
        db.scalar(
            sa_select(func.count(StudentModel.id))
            .select_from(StudentModel)
            .join(Zone, Zone.id == StudentModel.zone_id)
            .where(*roster_filters)
        )
        or 0
    )

    return NotEnteredStudentsResponse(
        items=items, total=len(items), roster_total=int(roster_total)
    )


@router.get("/not-entered-grouped", response_model=NotEnteredGroupedResponse)
def list_not_entered_students_grouped(
    session_smena_id: int = Query(
        ...,
        description=(
            "Joriy test_session_smena.id — shu test/sana/smena kesimida hali "
            "kelmagan (is_entered=False) talabalar guruh bo'yicha guruhlanadi."
        ),
    ),
    zone_id: int | None = Query(
        None,
        description=(
            "Tanlangan bino (zone). Berilsa — ro'yxat aynan shu binoga "
            "cheklanadi (bino foydalanuvchi region'iga tegishli bo'lishi shart). "
            "Berilmasa — foydalanuvchining butun region'i qamraladi."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tanlangan test_session_smena + bino kesimida hali kelmagan
    (`is_entered=False`) talabalar, guruh (`gr_n`) bo'yicha guruhlangan holda.

    Guruhlar `gr_n` bo'yicha, har bir guruh ichidagi talabalar familiya bo'yicha
    tartiblanadi. Har bir talaba uchun familiya, ism, sharif, JShShIR (`imei`)
    va o'tirish o'rni (`sp_n`) qaytariladi.

    Region/bino aniqlash logikasi `/not-entered` bilan bir xil.
    """
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone

    # Region — avval foydalanuvchiga bevosita biriktirilgan `region_id`,
    # aks holda zaxira sifatida zone orqali aniqlanadi (`/not-entered` bilan bir xil).
    target_region_id = current_user.region_id
    if not target_region_id:
        fallback_zone = zone_id or current_user.zone_id
        if fallback_zone:
            zone = db.get(Zone, int(fallback_zone))
            target_region_id = int(zone.region_id) if zone else None
    if not target_region_id:
        raise HTTPException(status_code=400, detail="Region aniqlanmadi")

    target_zone_id: int | None = None
    if zone_id:
        zone = db.get(Zone, int(zone_id))
        if not zone:
            raise HTTPException(status_code=404, detail="Bino topilmadi")
        if int(zone.region_id) != int(target_region_id):
            raise HTTPException(
                status_code=403,
                detail="Tanlangan bino foydalanuvchi region'iga tegishli emas",
            )
        target_zone_id = int(zone_id)

    if db.get(TestSessionSmena, session_smena_id) is None:
        raise HTTPException(status_code=404, detail="Test sessiya smena topilmadi")

    list_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
        StudentModel.is_entered.is_(False),
    ]
    if target_zone_id is not None:
        list_filters.append(StudentModel.zone_id == target_zone_id)

    stmt = (
        sa_select(
            StudentModel.gr_n,
            StudentModel.last_name,
            StudentModel.first_name,
            StudentModel.middle_name,
            StudentModel.imei,
            StudentModel.sp_n,
        )
        .join(Zone, Zone.id == StudentModel.zone_id)
        .where(*list_filters)
        # Guruh → familiya → ism bo'yicha tartiblanadi. Guruhlash tartibi
        # shu order'ga tayanadi (bir gr_n uchun barcha qatorlar ketma-ket keladi).
        .order_by(
            StudentModel.gr_n,
            StudentModel.last_name,
            StudentModel.first_name,
        )
    )
    rows = db.execute(stmt).all()

    # gr_n bo'yicha guruhlash — rows allaqachon gr_n bo'yicha tartiblangan,
    # shuning uchun ketma-ket bir xil gr_n larni bitta guruhga yig'amiz.
    groups: list[NotEnteredGroup] = []
    current_gr: int | None = None
    current_students: list[NotEnteredGroupStudent] = []
    for r in rows:
        gr = r.gr_n or 0
        if gr != current_gr:
            if current_gr is not None:
                groups.append(
                    NotEnteredGroup(
                        gr_n=current_gr,
                        total=len(current_students),
                        students=current_students,
                    )
                )
            current_gr = gr
            current_students = []
        current_students.append(
            NotEnteredGroupStudent(
                last_name=r.last_name,
                first_name=r.first_name,
                middle_name=r.middle_name,
                imei=r.imei,
                sp_n=r.sp_n or 0,
            )
        )
    if current_gr is not None:
        groups.append(
            NotEnteredGroup(
                gr_n=current_gr,
                total=len(current_students),
                students=current_students,
            )
        )

    roster_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
    ]
    if target_zone_id is not None:
        roster_filters.append(StudentModel.zone_id == target_zone_id)
    roster_total = (
        db.scalar(
            sa_select(func.count(StudentModel.id))
            .select_from(StudentModel)
            .join(Zone, Zone.id == StudentModel.zone_id)
            .where(*roster_filters)
        )
        or 0
    )

    return NotEnteredGroupedResponse(
        groups=groups, total=len(rows), roster_total=int(roster_total)
    )


@router.get("/entered", response_model=NotEnteredStudentsResponse)
def list_entered_students(
    session_smena_id: int = Query(
        ...,
        description=(
            "Joriy test_session_smena.id — shu test/sana/smena kesimida "
            "kelgan (is_entered=True) talabalar qaytariladi. Chetlatilganlar "
            "ham kiradi (yangi semantika: chetlatilgan = binoga kelgan)."
        ),
    ),
    zone_id: int | None = Query(
        None,
        description=(
            "Tanlangan bino (zone). Berilsa — ro'yxat aynan shu binoga "
            "cheklanadi (bino foydalanuvchi region'iga tegishli bo'lishi shart). "
            "Berilmasa — ro'yxat butun region kesimida qaytariladi."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tanlangan test_session_smena kesimida kelgan (`is_entered=True`)
    talabalar ro'yxati. Chetlatilganlar ham kiradi (yangi semantika).

    Javob shakli `/not-entered` bilan bir xil — desktop tabli modal'da
    bir xil jadval modelini ishlatishi uchun.
    """
    from sqlalchemy import func
    from sqlalchemy import select as sa_select

    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone

    target_region_id = current_user.region_id
    if not target_region_id:
        fallback_zone = zone_id or current_user.zone_id
        if fallback_zone:
            zone = db.get(Zone, int(fallback_zone))
            target_region_id = int(zone.region_id) if zone else None
    if not target_region_id:
        raise HTTPException(status_code=400, detail="Region aniqlanmadi")

    target_zone_id: int | None = None
    if zone_id:
        zone = db.get(Zone, int(zone_id))
        if not zone:
            raise HTTPException(status_code=404, detail="Bino topilmadi")
        if int(zone.region_id) != int(target_region_id):
            raise HTTPException(
                status_code=403,
                detail="Tanlangan bino foydalanuvchi region'iga tegishli emas",
            )
        target_zone_id = int(zone_id)

    if db.get(TestSessionSmena, session_smena_id) is None:
        raise HTTPException(status_code=404, detail="Test sessiya smena topilmadi")

    list_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
        StudentModel.is_entered.is_(True),
    ]
    if target_zone_id is not None:
        list_filters.append(StudentModel.zone_id == target_zone_id)

    stmt = (
        sa_select(
            StudentModel.last_name,
            StudentModel.first_name,
            StudentModel.middle_name,
            StudentModel.imei,
            StudentModel.gr_n,
            Zone.name.label("zone_name"),
        )
        .join(Zone, Zone.id == StudentModel.zone_id)
        .where(*list_filters)
        .order_by(
            Zone.number,
            Zone.name,
            StudentModel.gr_n,
            StudentModel.last_name,
            StudentModel.first_name,
        )
    )
    rows = db.execute(stmt).all()
    items = [
        NotEnteredStudentItem(
            last_name=r.last_name,
            first_name=r.first_name,
            middle_name=r.middle_name,
            imei=r.imei,
            gr_n=r.gr_n or 0,
            zone_name=r.zone_name or "",
        )
        for r in rows
    ]

    roster_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
    ]
    if target_zone_id is not None:
        roster_filters.append(StudentModel.zone_id == target_zone_id)
    roster_total = (
        db.scalar(
            sa_select(func.count(StudentModel.id))
            .select_from(StudentModel)
            .join(Zone, Zone.id == StudentModel.zone_id)
            .where(*roster_filters)
        )
        or 0
    )

    return NotEnteredStudentsResponse(
        items=items, total=len(items), roster_total=int(roster_total)
    )


# ── Chetlatilganlar (is_cheating=True, CheatingLog ulanadi) ──
@router.get("/rejected", response_model=RejectedStudentsResponse)
def list_rejected_students(
    session_smena_id: int = Query(
        ...,
        description=(
            "Joriy test_session_smena.id — shu test/sana/smena kesimida "
            "chetlatilgan (is_cheating=True) talabalar qaytariladi."
        ),
    ),
    zone_id: int | None = Query(
        None,
        description=(
            "Tanlangan bino (zone). Berilsa — ro'yxat aynan shu binoga "
            "cheklanadi. Berilmasa — region kesimida."
        ),
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Tanlangan test_session_smena + zone kesimida chetlatilgan
    (`is_cheating=True`) talabalar ro'yxati.

    `CheatingLog → Reason → ReasonType` LEFT JOIN orqali har bir talaba uchun
    chetlatish turi (`rejection_type` = ReasonType.name) va sababi
    (`rejection_reason` = Reason.name) qaytariladi. Eski yozuvlarda
    CheatingLog yo'q bo'lsa, bu maydonlar bo'sh string bo'ladi.
    """
    from sqlalchemy import func
    from sqlalchemy import select as sa_select
    from sqlalchemy.orm import aliased

    from app.models.cheating_log import CheatingLog
    from app.models.reason import Reason
    from app.models.reason_type import ReasonType
    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone

    # Region + zone validatsiyasi /entered bilan bir xil mantiq
    target_region_id = current_user.region_id
    if not target_region_id:
        fallback_zone = zone_id or current_user.zone_id
        if fallback_zone:
            zone = db.get(Zone, int(fallback_zone))
            target_region_id = int(zone.region_id) if zone else None
    if not target_region_id:
        raise HTTPException(status_code=400, detail="Region aniqlanmadi")

    target_zone_id: int | None = None
    if zone_id:
        zone = db.get(Zone, int(zone_id))
        if not zone:
            raise HTTPException(status_code=404, detail="Bino topilmadi")
        if int(zone.region_id) != int(target_region_id):
            raise HTTPException(
                status_code=403,
                detail="Tanlangan bino foydalanuvchi region'iga tegishli emas",
            )
        target_zone_id = int(zone_id)

    if db.get(TestSessionSmena, session_smena_id) is None:
        raise HTTPException(status_code=404, detail="Test sessiya smena topilmadi")

    list_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
        StudentModel.is_cheating.is_(True),
    ]
    if target_zone_id is not None:
        list_filters.append(StudentModel.zone_id == target_zone_id)

    # LEFT OUTER JOIN — eski yozuvlarda CheatingLog yo'q bo'lishi mumkin,
    # bunday talabalar ham ro'yxatda chiqishi kerak (rejection maydonlari
    # bo'sh string).
    stmt = (
        sa_select(
            StudentModel.last_name,
            StudentModel.first_name,
            StudentModel.middle_name,
            StudentModel.imei,
            StudentModel.gr_n,
            Zone.name.label("zone_name"),
            ReasonType.name.label("rejection_type"),
            Reason.name.label("rejection_reason"),
            CheatingLog.created_at.label("rejected_at"),
        )
        .join(Zone, Zone.id == StudentModel.zone_id)
        .outerjoin(CheatingLog, CheatingLog.student_id == StudentModel.id)
        .outerjoin(Reason, Reason.id == CheatingLog.reason_id)
        .outerjoin(ReasonType, ReasonType.id == Reason.reason_type_id)
        .where(*list_filters)
        # Eng oxirgi chetlatilganlar yuqorida; CheatingLog yo'q bo'lsa
        # zone/guruh tartibida.
        .order_by(
            CheatingLog.created_at.desc().nulls_last(),
            Zone.number,
            StudentModel.gr_n,
            StudentModel.last_name,
            StudentModel.first_name,
        )
    )
    rows = db.execute(stmt).all()
    items = [
        RejectedStudentItem(
            last_name=r.last_name,
            first_name=r.first_name,
            middle_name=r.middle_name,
            imei=r.imei,
            gr_n=r.gr_n or 0,
            zone_name=r.zone_name or "",
            rejection_type=r.rejection_type or "",
            rejection_reason=r.rejection_reason or "",
        )
        for r in rows
    ]

    roster_filters = [
        StudentModel.session_smena_id == session_smena_id,
        Zone.region_id == int(target_region_id),
    ]
    if target_zone_id is not None:
        roster_filters.append(StudentModel.zone_id == target_zone_id)
    roster_total = (
        db.scalar(
            sa_select(func.count(StudentModel.id))
            .select_from(StudentModel)
            .join(Zone, Zone.id == StudentModel.zone_id)
            .where(*roster_filters)
        )
        or 0
    )

    return RejectedStudentsResponse(
        items=items, total=len(items), roster_total=int(roster_total)
    )


@router.get("", response_model=StudentListResponse)
def list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gender_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    is_applied: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_READ.code)),
):
    region_id = _scoped_region_id(current_user, region_id)
    items, total = get_students_paginated(
        db,
        page=page,
        per_page=per_page,
        session_smena_id=session_smena_id,
        zone_id=zone_id,
        test_id=test_id,
        region_id=region_id,
        smena_id=smena_id,
        gender_id=gender_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_entered=is_entered,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        is_face=is_face,
        is_image=is_image,
        is_ready=is_ready,
        is_applied=is_applied,
        search=search,
    )
    return StudentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


# Eksport uchun maksimal qator soni (xotira/hajmni cheklash uchun).
_EXPORT_MAX_XLSX = 100_000
_EXPORT_MAX_PDF = 10_000


@router.get("/export")
def export_students(
    fmt: str = Query("xlsx", description="Format: 'xlsx' yoki 'pdf'"),
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gender_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    is_applied: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_READ.code)),
):
    """Filtrlangan talabalar ro'yxatini Excel (.xlsx) yoki PDF qilib yuklab olish.

    `GET /students` bilan bir xil filtrlarni qabul qiladi (sahifalashsiz).
    Ustunlar: Test, Hudud, Familiya, Ism, Otasining ismi, JSHSHIR, Seriya,
    Raqam, Sana, Smena, Guruh.
    """
    from datetime import datetime

    fmt = (fmt or "xlsx").lower()
    if fmt not in ("xlsx", "pdf"):
        raise HTTPException(
            status_code=400, detail="Format 'xlsx' yoki 'pdf' bo'lishi kerak"
        )

    cap = _EXPORT_MAX_XLSX if fmt == "xlsx" else _EXPORT_MAX_PDF
    region_id = _scoped_region_id(current_user, region_id)
    rows = get_filtered_students(
        db,
        session_smena_id=session_smena_id,
        zone_id=zone_id,
        test_id=test_id,
        region_id=region_id,
        smena_id=smena_id,
        gender_id=gender_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_entered=is_entered,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        is_face=is_face,
        is_image=is_image,
        is_ready=is_ready,
        is_applied=is_applied,
        search=search,
        limit=cap + 1,
    )
    if not rows:
        raise HTTPException(
            status_code=404, detail="Tanlangan filtr bo'yicha talaba topilmadi"
        )
    if len(rows) > cap:
        raise HTTPException(
            status_code=413,
            detail=(
                f"Natija juda katta ({fmt.upper()} uchun {cap:,} qatordan ortiq). "
                "Iltimos, filtrni aniqlashtiring."
            ),
        )

    generated_at = datetime.now()
    stamp = generated_at.strftime("%Y%m%d_%H%M")
    if fmt == "xlsx":
        content = build_students_xlsx(rows, generated_at)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"talabalar_{stamp}.xlsx"
    else:
        content = build_students_pdf(rows, generated_at)
        media = "application/pdf"
        filename = f"talabalar_{stamp}.pdf"

    return StreamingResponse(
        BytesIO(content),
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("", response_model=StudentResponse)
def create_student_endpoint(
    data: StudentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_CREATE.code)),
):
    student = create_student(db, data)
    return get_student(db, student.id)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_READ.code)),
):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
    _assert_region_access(current_user, _student_region_id(db, student_id))
    return student


@router.patch("/{student_id}", response_model=StudentResponse)
def update_student_endpoint(
    student_id: int,
    data: StudentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_UPDATE.code)),
):
    student = update_student(db, student_id, data)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
    return get_student(db, student_id)


@router.delete("/{student_id}", status_code=204)
def delete_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_DELETE.code)),
):
    if not delete_student(db, student_id):
        raise HTTPException(status_code=404, detail="Talaba topilmadi")


@router.post("/{student_id}/remove-attendance")
def remove_student_attendance_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.STUDENT_LOG_CREATE.code)),
):
    """Davomatdan olish — talabaning `is_entered` bayrog'ini False qiladi.

    Desktop operatori (STUDENT_LOG_CREATE ruxsati — davomat loglarini
    yaratuvchi) noto'g'ri qo'shilgan davomatni bekor qilishi uchun. Faqat
    `is_entered` o'zgaradi. Talaba topilmasa 404."""
    student, was_entered = remove_student_attendance(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
    logger.info(
        "Davomatdan olindi: student_id=%s user_id=%s was_entered=%s",
        student_id,
        current_user.id,
        was_entered,
    )
    # `was_entered` — operatsiyadan OLDINgi holat. Desktop shu asosda
    # "allaqachon davomatda emas edi" degan xabarni ko'rsatadi.
    return {
        "status": "ok",
        "student_id": student_id,
        "is_entered": False,
        "was_entered": was_entered,
    }


class UploadImageRequest(BaseModel):
    ps_img: str  # base64 rasm


@router.post("/{student_id}/upload-image", response_model=StudentResponse)
def upload_student_image(
    student_id: int,
    body: UploadImageRequest,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_UPDATE.code)),
):
    """Studentga qo'lda rasm yuklash. is_image=True bo'ladi."""
    from sqlalchemy import select

    from app.models.student_ps_data import StudentPsData

    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")

    # StudentPsData ni topish yoki yaratish
    ps_data = db.execute(
        select(StudentPsData).where(StudentPsData.student_id == student_id)
    ).scalar()

    if ps_data:
        ps_data.ps_img = _b64_to_bytes(body.ps_img)
    else:
        raise HTTPException(
            status_code=404,
            detail="Talaba passport ma'lumotlari topilmadi",
        )

    # Student is_image ni yangilash
    from app.models.student import Student as StudentModel

    student_obj = db.get(StudentModel, student_id)
    if student_obj:
        student_obj.is_image = True

    db.commit()
    return get_student(db, student_id)


@router.post("/{student_id}/fetch-gtsp", response_model=StudentResponse)
def fetch_gtsp_image(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_UPDATE.code)),
):
    """GTSP API dan studentning rasmini yuklab olish.

    ps_ser + ps_num birlashtiriladi (masalan AD1234567).
    Response dan: last_name=sname, first_name=fname, middle_name=mname,
    ps_img=photo, gender=sex (1=erkak, 2=ayol, boshqa=unknown).
    """
    from sqlalchemy import select

    from app.models.gender import Gender
    from app.models.student import Student as StudentModel
    from app.models.student_ps_data import StudentPsData
    from app.services.gtsp_client import (
        GtspError,
        GtspNotConfigured,
        build_ps_value,
        fetch_gtsp_data,
    )

    student_obj = db.get(StudentModel, student_id)
    if not student_obj:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")

    ps_data = db.execute(
        select(StudentPsData).where(StudentPsData.student_id == student_id)
    ).scalar()
    if not ps_data:
        raise HTTPException(
            status_code=404, detail="Talaba passport ma'lumotlari topilmadi"
        )

    ps_value = build_ps_value(ps_data.ps_ser, ps_data.ps_num)
    logger.info("GTSP API chaqirilmoqda: student_id=%d, ps=%s", student_id, ps_value)

    try:
        result = fetch_gtsp_data(student_obj.imei, ps_value, timeout=30.0)
    except GtspNotConfigured as e:
        raise HTTPException(status_code=500, detail=str(e))
    except GtspError as e:
        # retryable=True → ulanish xatosi, boshqa hollarda — API rad etdi
        status_code = 502 if e.retryable else 400
        raise HTTPException(status_code=status_code, detail=e.message)

    # Student ma'lumotlarini yangilash
    if result.last_name:
        student_obj.last_name = result.last_name
    if result.first_name:
        student_obj.first_name = result.first_name
    if result.middle_name is not None:
        student_obj.middle_name = result.middle_name
    student_obj.is_image = True

    # StudentPsData yangilash
    if result.photo:
        ps_data.ps_img = result.photo

    # Gender ni key orqali topish: sex=1 → key=1, sex=2 → key=2, boshqa → key=0
    gender_key = result.sex if result.sex in (1, 2) else 0
    gender = db.execute(select(Gender).where(Gender.key == gender_key)).scalar()
    if gender:
        ps_data.gender_id = gender.id

    db.commit()
    logger.info("GTSP: student_id=%d muvaffaqiyatli yangilandi", student_id)
    return get_student(db, student_id)


class BulkGtspResponse(BaseModel):
    """Filtrlangan studentlar uchun GTSP rasm yuklash natijasi."""

    total: int  # filtr/qidiruvga mos jami studentlar
    succeeded: int  # GTSP'dan muvaffaqiyatli yangilandi
    failed: int  # GTSP xatosi (raqam topilmadi, tarmoq va h.k.)
    skipped: int  # passport ma'lumotlari yo'q — chetlab o'tildi


@router.post("/fetch-gtsp-bulk", response_model=BulkGtspResponse)
def fetch_gtsp_bulk(
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gender_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    is_applied: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_UPDATE.code)),
):
    """Filtr/qidiruvga mos BARCHA studentlarning rasmini GTSP'dan yuklash.

    `list_students` bilan bir xil filtr parametrlarini qabul qiladi va
    har bir student uchun imei + (ps_ser + ps_num) bo'yicha GTSP'ni
    chaqiradi. ps_num 7 xonaga 0 bilan to'ldiriladi (`build_ps_value`).
    GTSP chaqiruvlari parallel (ThreadPoolExecutor), DB yozish ketma-ket.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from sqlalchemy import select

    from app.crud.student import get_filtered_student_ids
    from app.models.student import Student as StudentModel
    from app.models.student_ps_data import StudentPsData
    from app.services.excel_student_loader import (
        GTSP_WORKERS,
        _apply_gtsp_result,
        _build_gender_lookup,
        _enrich_one,
    )

    student_ids = get_filtered_student_ids(
        db,
        session_smena_id=session_smena_id,
        zone_id=zone_id,
        test_id=test_id,
        region_id=region_id,
        smena_id=smena_id,
        gender_id=gender_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_entered=is_entered,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        is_face=is_face,
        is_image=is_image,
        is_ready=is_ready,
        is_applied=is_applied,
        search=search,
    )
    total = len(student_ids)
    if not student_ids:
        return BulkGtspResponse(total=0, succeeded=0, failed=0, skipped=0)

    # Faqat passport ma'lumotlari bor studentlar GTSP'ga yuboriladi.
    rows = db.execute(
        select(
            StudentModel.id,
            StudentModel.imei,
            StudentPsData.ps_ser,
            StudentPsData.ps_num,
        )
        .join(StudentPsData, StudentPsData.student_id == StudentModel.id)
        .where(StudentModel.id.in_(student_ids))
    ).all()
    work_items: list[tuple[int, str | None, str, str]] = [
        (int(sid), imei, ps_ser, ps_num) for sid, imei, ps_ser, ps_num in rows
    ]
    skipped = total - len(work_items)

    gender_map = _build_gender_lookup(db)
    succeeded = 0
    failed = 0
    processed = len(work_items)

    logger.info("GTSP bulk: %d student (skipped=%d) ishlanmoqda", processed, skipped)
    with ThreadPoolExecutor(max_workers=GTSP_WORKERS) as ex:
        future_map = {ex.submit(_enrich_one, item): item[0] for item in work_items}
        for i, fut in enumerate(as_completed(future_map), start=1):
            student_id, result = fut.result()
            if _apply_gtsp_result(db, student_id, result, gender_map):
                succeeded += 1
            else:
                failed += 1
            # Har 20 ta da commit — uzilib qolsa ham ishlangan qismi saqlanadi.
            if i % 20 == 0 or i == processed:
                try:
                    db.commit()
                except Exception:
                    db.rollback()
                    logger.exception("GTSP bulk commit xatosi")

    logger.info(
        "GTSP bulk yakunlandi: total=%d, ok=%d, xato=%d, skip=%d",
        total,
        succeeded,
        failed,
        skipped,
    )
    return BulkGtspResponse(
        total=total, succeeded=succeeded, failed=failed, skipped=skipped
    )


# ===================== Bulk zone reassignment =====================


class ReassignZoneResponse(BaseModel):
    """Filtrlangan studentlarni boshqa binoga (zone) biriktirish natijasi."""

    total: int  # filtr/qidiruvga mos jami studentlar
    updated: int  # zone_id yangilangan studentlar
    zone_id: int  # yangi bino id
    zone_name: str  # yangi bino nomi


@router.post("/reassign-zone-bulk", response_model=ReassignZoneResponse)
def reassign_zone_bulk(
    target_zone_id: int = Query(
        ..., description="Talabalar biriktiriladigan yangi bino (zone) id."
    ),
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gender_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    is_applied: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_UPDATE.code)),
):
    """Filtr/qidiruvga mos BARCHA studentlarni tanlangan binoga (zone) biriktirish.

    `list_students` bilan bir xil filtr parametrlarini qabul qiladi va shu
    filtrga mos har bir studentning `zone_id` sini `target_zone_id` ga
    o'zgartiradi. Xavfsizlik uchun kamida bitta filtr/qidiruv shart —
    filtr berilmasa (barcha studentlarni tasodifan ko'chirib yubormaslik
    uchun) so'rov rad etiladi.
    """
    from app.crud.student import get_filtered_student_ids
    from app.models.zone import Zone

    target_zone = db.get(Zone, target_zone_id)
    if not target_zone:
        raise HTTPException(status_code=404, detail="Bino topilmadi")

    # Kamida bitta filtr/qidiruv bo'lishi shart — bo'sh filtr barcha
    # talabalarni ko'chirib yuborishi mumkin, buni bloklaymiz.
    has_filter = any(
        v is not None
        for v in (
            session_smena_id,
            zone_id,
            test_id,
            region_id,
            smena_id,
            gender_id,
            gr_n,
            e_date_from,
            e_date_to,
            is_entered,
            is_cheating,
            is_blacklist,
            is_face,
            is_image,
            is_ready,
            is_applied,
        )
    ) or bool(search)
    if not has_filter:
        raise HTTPException(
            status_code=400,
            detail="Kamida bitta filtr yoki qidiruv shart",
        )

    student_ids = get_filtered_student_ids(
        db,
        session_smena_id=session_smena_id,
        zone_id=zone_id,
        test_id=test_id,
        region_id=region_id,
        smena_id=smena_id,
        gender_id=gender_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_entered=is_entered,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        is_face=is_face,
        is_image=is_image,
        is_ready=is_ready,
        is_applied=is_applied,
        search=search,
    )
    total = len(student_ids)
    updated = bulk_reassign_zone(db, student_ids, target_zone_id)
    logger.info(
        "Bulk zone reassign: total=%d, updated=%d, target_zone_id=%d",
        total,
        updated,
        target_zone_id,
    )
    return ReassignZoneResponse(
        total=total,
        updated=updated,
        zone_id=target_zone_id,
        zone_name=target_zone.name,
    )


# ===================== Check FaceID via GTSP =====================


class CheckFaceidGtspRequest(BaseModel):
    """Yangi pasport ma'lumotlari bo'yicha cameradan kelgan yuzni tekshirish."""

    ps_ser: str = Field(..., min_length=1, max_length=5)
    ps_num: str = Field(..., min_length=1, max_length=10)
    imei: str | None = Field(default=None, max_length=14)
    lv_img: str  # base64 — kameradan kelgan frame
    # Desktop'da tanlangan smena (test_session_smena.id) va bino (zone.id).
    # DB validatsiyasi shu ikki maydonga tayanadi: pinfl shu smena+zone'da
    # bo'lmasa — GTSP API chaqirilmaydi.
    session_smena_id: int | None = None
    zone_id: int | None = None


class MatchedSlot(BaseModel):
    """Pinfl bo'yicha topilgan student slotining ma'lumoti.

    `ok` / `wrong_passport` holatlarida — tanlangan slot (shu smena + bino).
    `wrong_slot` holatida — studentning aslida qaysi slotda ekanligi.
    """

    session_smena_id: int | None = None
    zone_id: int | None = None
    test_day: str | None = None
    sm_number: int | None = None
    region_name: str | None = None
    zone_name: str | None = None
    gr_n: int | None = None
    sp_n: int | None = None
    subject_name: str | None = None


class CheckFaceidGtspResponse(BaseModel):
    """Cameradan kelgan yuzni GTSP rasmiga solishtirish natijasi.

    status qiymatlari:
      - "ok"            → slot mos, GTSP chaqirildi, verified maydonda natija
      - "not_in_test"   → pinfl shu test sessiyasida topilmadi
      - "wrong_slot"    → pinfl shu testda bor, lekin boshqa kun/smena/binoda
                          (`matched_slot` to'ldiriladi; davomatga qo'shib bo'lmaydi)
      - "wrong_passport"→ slot mos, lekin GTSP ps_ser+ps_num bo'yicha rasm
                          qaytarmadi (pasport ma'lumoti noto'g'ri kiritilgan)
      - "applied"       → talaba ariza bergan (is_applied=True) — testga
                          kirita olmaymiz, `message` da `desc_apply` matni
    """

    status: str = "ok"
    can_attend: bool = False
    success: bool = False
    verified: bool = False
    score: float = 0.0
    threshold: float = 0.0
    message: str = ""
    sname: str | None = None
    fname: str | None = None
    mname: str | None = None
    imei: str | None = None
    photo: str | None = None  # base64 — GTSP dan kelgan passport rasmi
    matched_slot: MatchedSlot | None = None


def _call_gtsp(ps_value: str, imei_value: str) -> tuple[dict | None, str | None]:
    """GTSP API ni chaqiradi. Qaytaradi: (data, error_message).

    Network yoki API xatoligi bo'lsa — data=None, error_message to'ldiriladi.
    Chaqiruvchi error_message'ni userga ko'rsatiladigan formatda qayta
    ishlaydi (masalan `wrong_passport` statusiga o'tkazadi).
    """
    from app.config import settings

    if not settings.API_GTSP:
        return None, "API_GTSP sozlamasi topilmadi"

    url = settings.API_GTSP.format(imei_value, ps_value)
    try:
        with httpx.Client(timeout=30, verify=False) as client:
            resp = client.get(url)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("GTSP API HTTP xatolik: %s", e)
        return None, f"GTSP API xatolik: {e.response.status_code}"
    except Exception as e:
        logger.error("GTSP API ulanish xatolik: %s", e)
        return None, "GTSP API ga ulanib bo'lmadi"

    if result.get("status") != 1:
        msg = (result.get("data") or {}).get("message") or "Noma'lum xatolik"
        return None, f"GTSP: {msg}"

    data = result.get("data") or {}
    if not data.get("photo"):
        return None, "GTSP javobida rasm yo'q"
    return data, None


@router.post("/check-faceid-gtsp", response_model=CheckFaceidGtspResponse)
def check_faceid_gtsp(
    body: CheckFaceidGtspRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """GTSP dan fresh passport rasmini olib, cameradan kelgan yuz bilan solishtirish.

    Avval DB da tekshiriladi: pinfl shu test_session_smena + zone da bormi.
    Agar yo'q bo'lsa — GTSP chaqirilmaydi:
      - boshqa kun/smena/binoda topilsa → `wrong_slot` + matched_slot
      - umuman topilmasa → `not_in_test`

    Agar slot mos bo'lsa — GTSP chaqiriladi. Javob kelmasa yoki rasm
    bo'lmasa → `wrong_passport` (userga "Pasport ma'lumotlari xato"
    xabari). Aks holda kameradan kelgan lv_img bilan solishtirilib,
    verified natija qaytariladi. DB ga hech narsa saqlanmaydi — bu
    faqat tekshiruv endpoint'i.
    """
    from sqlalchemy import select

    from app.models.region import Region
    from app.models.smena import Smena
    from app.models.student import Student as StudentModel
    from app.models.test_session_smena import TestSessionSmena
    from app.models.zone import Zone
    from app.services.face_service import compare_two_faces

    def _slot_from_row(
        stu_row, tss_row, zone_row, smena_row, region_row
    ) -> MatchedSlot:
        return MatchedSlot(
            session_smena_id=tss_row.id if tss_row else None,
            zone_id=zone_row.id if zone_row else None,
            test_day=tss_row.day.isoformat() if (tss_row and tss_row.day) else None,
            sm_number=smena_row.number if smena_row else None,
            region_name=region_row.name if region_row else None,
            zone_name=zone_row.name if zone_row else None,
            gr_n=stu_row.gr_n if stu_row else None,
            sp_n=stu_row.sp_n if stu_row else None,
            subject_name=stu_row.subject_name if stu_row else None,
        )

    def _lookup_student_row(
        imei: str,
        session_smena_id: int | None = None,
        zone_id: int | None = None,
        test_session_id: int | None = None,
    ):
        """Student + to'liq slot kontekstini bitta queryda oladi.

        Agar session_smena_id + zone_id berilsa — aynan shu slotdan.
        Aks holda test_session_id bo'yicha istalgan slotdan (wrong_slot uchun).
        Qaytaradi: (stu, tss, zone, smena, region) yoki None.
        """
        q = (
            select(StudentModel, TestSessionSmena, Zone, Smena, Region)
            .join(
                TestSessionSmena, TestSessionSmena.id == StudentModel.session_smena_id
            )
            .join(Zone, Zone.id == StudentModel.zone_id)
            .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
            .join(Region, Region.id == Zone.region_id)
            .where(StudentModel.imei == imei)
        )
        if session_smena_id is not None and zone_id is not None:
            q = q.where(
                StudentModel.session_smena_id == session_smena_id,
                StudentModel.zone_id == zone_id,
            )
        elif test_session_id is not None:
            q = q.where(TestSessionSmena.test_session_id == test_session_id)
        return db.execute(q).first()

    imei_value = (body.imei or "").strip()
    ps_value = f"{body.ps_ser}{body.ps_num}"

    # Keyinchalik javobda foydalanish uchun — slot mos kelganda shu maydonlar
    # ok/wrong_passport holatlariga ham qo'shiladi.
    current_slot: MatchedSlot | None = None
    current_fio: tuple[str | None, str | None, str | None] = (None, None, None)

    # ── 1) DB validatsiya: pinfl + slot ───────────────────────────────
    if imei_value and body.session_smena_id and body.zone_id:
        # 1a) Aynan shu smena+zone da bormi
        matched = _lookup_student_row(
            imei_value,
            session_smena_id=body.session_smena_id,
            zone_id=body.zone_id,
        )

        if matched is None:
            # 1b) Shu test sessiyasining boshqa slotida bormi
            current_tss = db.get(TestSessionSmena, body.session_smena_id)
            if current_tss is None:
                return CheckFaceidGtspResponse(
                    status="not_in_test",
                    message="Talabgor - bu testdan topilmadi!",
                )

            other = _lookup_student_row(
                imei_value,
                test_session_id=current_tss.test_session_id,
            )

            if other is None:
                return CheckFaceidGtspResponse(
                    status="not_in_test",
                    message="Talabgor - bu testdan topilmadi!",
                )

            stu_row, tss_row, zone_row, smena_row, region_row = other
            return CheckFaceidGtspResponse(
                status="wrong_slot",
                can_attend=False,
                message=("Talabgor shu testda bor, lekin boshqa kun / smena / binoda."),
                sname=stu_row.last_name,
                fname=stu_row.first_name,
                mname=stu_row.middle_name,
                imei=imei_value,
                matched_slot=_slot_from_row(
                    stu_row,
                    tss_row,
                    zone_row,
                    smena_row,
                    region_row,
                ),
            )

        # slot mos — student ma'lumotini saqlab, GTSP chaqiruviga o'tamiz
        stu_row, tss_row, zone_row, smena_row, region_row = matched
        current_slot = _slot_from_row(
            stu_row,
            tss_row,
            zone_row,
            smena_row,
            region_row,
        )
        current_fio = (stu_row.last_name, stu_row.first_name, stu_row.middle_name)

        # Talaba ariza bergan bo'lsa — testga kirita olmaymiz, GTSP chaqirilmaydi.
        if stu_row.is_applied:
            return CheckFaceidGtspResponse(
                status="applied",
                can_attend=False,
                message=stu_row.desc_apply or "Talaba ariza bergan",
                sname=stu_row.last_name,
                fname=stu_row.first_name,
                mname=stu_row.middle_name,
                imei=imei_value or None,
                matched_slot=current_slot,
            )

    # ── 2) GTSP chaqiruvi ─────────────────────────────────────────────
    logger.info(
        "GTSP API chaqirilmoqda (check-faceid): ps=%s, imei=%s",
        ps_value,
        imei_value,
    )
    data, err = _call_gtsp(ps_value, imei_value)
    if err is not None or not data:
        # Pasport ma'lumotlari noto'g'ri kiritilgan yoki GTSP javob
        # bermadi — userga qaytariladigan xabar Uzbekcha. Slot ma'lumoti
        # (viloyat/bino/kun/smena/joy/subject) DB'dan aniq bor, shuni
        # ham javobga qo'shamiz — modal to'liq ko'rsatadi.
        return CheckFaceidGtspResponse(
            status="wrong_passport",
            can_attend=False,
            message=(
                "Pasport ma'lumotlari xato kiritildi. Iltimos to'g'ri ma'lumot kiriting"
            ),
            sname=current_fio[0],
            fname=current_fio[1],
            mname=current_fio[2],
            imei=imei_value or None,
            matched_slot=current_slot,
        )

    photo_b64 = data.get("photo")

    # ── 3) Yuz solishtirish ───────────────────────────────────────────
    try:
        verify_resp, _ps_bgr, _lv_bgr = compare_two_faces(photo_b64, body.lv_img)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compare_two_faces xatolik: %s", e)
        raise HTTPException(status_code=500, detail=f"Yuz solishtirishda xatolik: {e}")

    return CheckFaceidGtspResponse(
        status="ok",
        can_attend=bool(verify_resp.verified),
        success=verify_resp.verified,
        verified=verify_resp.verified,
        score=verify_resp.score,
        threshold=verify_resp.thresh_score,
        message=verify_resp.message,
        sname=data.get("sname"),
        fname=data.get("fname"),
        mname=data.get("mname"),
        imei=imei_value or None,
        photo=photo_b64,
        matched_slot=current_slot,
    )


# ===================== Check FaceID via GTSP — Self-only =====================


class CheckFaceidGtspSelfRequest(BaseModel):
    """Faqat o'zini tekshirish — DB validatsiyasiz, sof face identification.

    GTSP dan ps_ser+ps_num+imei bo'yicha rasm olinadi va cameradan kelgan
    yuz bilan solishtiriladi. Studentning testda bor-yo'qligi tekshirilmaydi.
    """

    ps_ser: str = Field(..., min_length=1, max_length=5)
    ps_num: str = Field(..., min_length=1, max_length=10)
    imei: str | None = Field(default=None, max_length=14)
    lv_img: str  # base64 — kameradan kelgan frame


@router.post("/check-faceid-gtsp-self", response_model=CheckFaceidGtspResponse)
def check_faceid_gtsp_self(
    body: CheckFaceidGtspSelfRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """GTSP dan rasm olib, cameradan kelgan yuz bilan to'g'ridan-to'g'ri
    solishtirish — DB validatsiyasi qilinmaydi.

    Pasport ma'lumotlari + JShShIR bo'yicha GTSP API chaqiriladi. Javob
    bo'lmasa → `wrong_passport`. Aks holda kameradan kelgan yuz bilan
    solishtirilib, FIO + score qaytariladi. `matched_slot` har doim None.
    DB ga hech narsa saqlanmaydi.
    """
    from app.services.face_service import compare_two_faces

    imei_value = (body.imei or "").strip()
    ps_value = f"{body.ps_ser}{body.ps_num}"

    logger.info(
        "GTSP API chaqirilmoqda (check-faceid-self): ps=%s, imei=%s",
        ps_value,
        imei_value,
    )
    data, err = _call_gtsp(ps_value, imei_value)
    if err is not None or not data:
        return CheckFaceidGtspResponse(
            status="wrong_passport",
            can_attend=False,
            message=(
                "Pasport ma'lumotlari xato kiritildi. Iltimos to'g'ri ma'lumot kiriting"
            ),
            imei=imei_value or None,
        )

    photo_b64 = data.get("photo")

    try:
        verify_resp, _ps_bgr, _lv_bgr = compare_two_faces(photo_b64, body.lv_img)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("compare_two_faces xatolik: %s", e)
        raise HTTPException(status_code=500, detail=f"Yuz solishtirishda xatolik: {e}")

    return CheckFaceidGtspResponse(
        status="ok",
        can_attend=False,
        success=verify_resp.verified,
        verified=verify_resp.verified,
        score=verify_resp.score,
        threshold=verify_resp.thresh_score,
        message=verify_resp.message,
        sname=data.get("sname"),
        fname=data.get("fname"),
        mname=data.get("mname"),
        imei=imei_value or None,
        photo=photo_b64,
        matched_slot=None,
    )
