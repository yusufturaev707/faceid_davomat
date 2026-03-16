"""Student, StudentLog, CheatingLog endpoints (CRUD)."""

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

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
