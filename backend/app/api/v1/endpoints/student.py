"""Student, StudentLog, CheatingLog endpoints (CRUD)."""

import base64
import logging
import math

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


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


from app.core.permissions import P
from app.crud.student import (
    bulk_create_student_logs,
    create_cheating_log,
    create_student,
    create_student_log,
    delete_cheating_log,
    delete_student,
    delete_student_log,
    get_cheating_logs_paginated,
    get_student,
    get_student_log_detail,
    get_student_logs_paginated,
    get_students_paginated,
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
    CheatingLogCreate,
    CheatingLogListResponse,
    CheatingLogResponse,
    CheatingLogUpdate,
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

router = APIRouter()


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
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    first_enter_from: str | None = None,
    first_enter_to: str | None = None,
    last_enter_from: str | None = None,
    last_enter_to: str | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_LOG_READ.code)),
):
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
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        first_enter_from=first_enter_from,
        first_enter_to=first_enter_to,
        last_enter_from=last_enter_from,
        last_enter_to=last_enter_to,
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
    _: User = Depends(PermissionChecker(P.STUDENT_LOG_READ.code)),
):
    """Bitta StudentLog — first_captured/last_captured rasmlari bilan."""
    log = get_student_log_detail(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
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
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.CHEATING_LOG_READ.code)),
):
    items, total = get_cheating_logs_paginated(
        db, page=page, per_page=per_page, student_id=student_id
    )
    return CheatingLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
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


@router.get("", response_model=StudentListResponse)
def list_students(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.STUDENT_READ.code)),
):
    items, total = get_students_paginated(
        db,
        page=page,
        per_page=per_page,
        session_smena_id=session_smena_id,
        zone_id=zone_id,
        test_id=test_id,
        region_id=region_id,
        smena_id=smena_id,
        gr_n=gr_n,
        e_date_from=e_date_from,
        e_date_to=e_date_to,
        is_entered=is_entered,
        is_cheating=is_cheating,
        is_blacklist=is_blacklist,
        is_face=is_face,
        is_image=is_image,
        is_ready=is_ready,
        search=search,
    )
    return StudentListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
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
    _: User = Depends(PermissionChecker(P.STUDENT_READ.code)),
):
    student = get_student(db, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
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

    from app.config import settings
    from app.models.student import Student as StudentModel
    from app.models.student_ps_data import StudentPsData

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

    ps_value = f"{ps_data.ps_ser}{ps_data.ps_num}"
    imei_value = student_obj.imei or ""

    if not settings.API_GTSP:
        raise HTTPException(status_code=500, detail="API_GTSP sozlamasi topilmadi")

    url = settings.API_GTSP.format(imei_value, ps_value)
    logger.info("GTSP API chaqirilmoqda: student_id=%d, ps=%s", student_id, ps_value)

    try:
        with httpx.Client(timeout=30, verify=False) as client:
            resp = client.get(url)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("GTSP API HTTP xatolik: %s", e)
        raise HTTPException(
            status_code=502, detail=f"GTSP API xatolik: {e.response.status_code}"
        )
    except Exception as e:
        logger.error("GTSP API ulanish xatolik: %s", e)
        raise HTTPException(status_code=502, detail="GTSP API ga ulanib bo'lmadi")

    if result.get("status") != 1:
        msg = result.get("data", {}).get("message", "Noma'lum xatolik")
        raise HTTPException(status_code=400, detail=f"GTSP: {msg}")

    data = result["data"]

    # Student ma'lumotlarini yangilash
    student_obj.last_name = data.get("sname", student_obj.last_name)
    student_obj.first_name = data.get("fname", student_obj.first_name)
    student_obj.middle_name = data.get("mname", student_obj.middle_name)
    student_obj.is_image = True

    # StudentPsData yangilash
    photo = data.get("photo")
    if photo:
        ps_data.ps_img = _b64_to_bytes(photo)

    # Gender ni key orqali topish: sex=1 → key=1 (erkak), sex=2 → key=2 (ayol), boshqa → key=0
    from app.models.gender import Gender

    sex = data.get("sex")
    if sex == 1:
        gender_key = 1
    elif sex == 2:
        gender_key = 2
    else:
        gender_key = 0
    gender = db.execute(select(Gender).where(Gender.key == gender_key)).scalar()
    if gender:
        ps_data.gender_id = gender.id

    db.commit()
    logger.info("GTSP: student_id=%d muvaffaqiyatli yangilandi", student_id)
    return get_student(db, student_id)


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
