"""Student, StudentLog, CheatingLog endpoints (CRUD)."""

import logging
import math

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.crud.student import (
    create_cheating_log,
    create_student,
    create_student_log,
    delete_cheating_log,
    delete_student,
    delete_student_log,
    get_cheating_logs_paginated,
    get_student,
    get_student_logs_paginated,
    get_students_paginated,
    update_cheating_log,
    update_student,
    update_student_log,
)
from app.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.schemas.student import (
    CheatingLogCreate,
    CheatingLogListResponse,
    CheatingLogResponse,
    CheatingLogUpdate,
    StudentCreate,
    StudentListResponse,
    StudentLogCreate,
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
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
):
    items, total = get_student_logs_paginated(
        db, page=page, per_page=per_page, student_id=student_id
    )
    return StudentLogListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total else 0,
    )


@router.post("/logs", response_model=StudentLogResponse)
def create_student_log_endpoint(
    data: StudentLogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    log = create_student_log(db, data)
    return log


@router.patch("/logs/{log_id}", response_model=StudentLogResponse)
def update_student_log_endpoint(
    log_id: int,
    data: StudentLogUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    log = update_student_log(db, log_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    return log


@router.delete("/logs/{log_id}", status_code=204)
def delete_student_log_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
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
    _: User = Depends(get_current_active_user),
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
    _: User = Depends(require_admin),
):
    log = create_cheating_log(db, data)
    return log


@router.patch("/cheating-logs/{log_id}", response_model=CheatingLogResponse)
def update_cheating_log_endpoint(
    log_id: int,
    data: CheatingLogUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    log = update_cheating_log(db, log_id, data)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    return log


@router.delete("/cheating-logs/{log_id}", status_code=204)
def delete_cheating_log_endpoint(
    log_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
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
    _: User = Depends(get_current_active_user),
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
    _: User = Depends(require_admin),
):
    student = create_student(db, data)
    return get_student(db, student.id)


@router.get("/{student_id}", response_model=StudentResponse)
def get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_active_user),
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
    _: User = Depends(require_admin),
):
    student = update_student(db, student_id, data)
    if not student:
        raise HTTPException(status_code=404, detail="Talaba topilmadi")
    return get_student(db, student_id)


@router.delete("/{student_id}", status_code=204)
def delete_student_endpoint(
    student_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
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
    _: User = Depends(require_admin),
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
        ps_data.ps_img = body.ps_img
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
    _: User = Depends(require_admin),
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
        ps_data.ps_img = photo

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
