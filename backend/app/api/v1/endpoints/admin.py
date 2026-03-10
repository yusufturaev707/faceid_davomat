import math
import os
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import require_admin
from app.crud.api_key import create_api_key, get_all_api_keys, revoke_api_key
from app.crud.user import create_user, get_all_users, get_user_by_username
from app.crud.verification_log import get_dashboard_stats, get_log_by_id, get_logs_paginated
from app.crud.verify_faces import get_face_dashboard_stats, get_face_log_by_id, get_face_logs_paginated
from app.db.session import get_db
from app.models.user import User
from app.schemas.admin import DashboardStats, FaceLogResponse, PaginatedFaceLogs, PaginatedLogs, VerificationLogResponse
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from app.schemas.auth import CreateUserRequest, UserResponse

router = APIRouter()


@router.get("/logs", response_model=PaginatedLogs, summary="Tekshiruv loglari")
def get_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> PaginatedLogs:
    """Barcha tekshiruv loglarini sahifalab ko'rish (faqat admin)."""
    items, total = get_logs_paginated(db, page, per_page, user_id, date_from, date_to)
    pages = math.ceil(total / per_page) if total > 0 else 1
    return PaginatedLogs(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/logs/{log_id}", response_model=VerificationLogResponse, summary="Bitta log")
def get_single_log(
    log_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> VerificationLogResponse:
    """Bitta tekshiruv logini ko'rish (faqat admin)."""
    log = get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log topilmadi",
        )
    return log


@router.get("/logs/{log_id}/image", summary="Log rasmi (original)")
def get_log_image(
    log_id: int,
    thumb: bool = Query(False),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Tekshiruv logidagi rasmni olish. thumb=true bo'lsa thumbnail qaytaradi."""
    log = get_log_by_id(db, log_id)
    if not log or not log.get("image_path"):
        raise HTTPException(status_code=404, detail="Rasm topilmadi")
    filename = log["image_path"]
    suffix = "_thumb" if thumb else ""
    file_path = os.path.join(settings.UPLOADS_PHOTO_DIR, f"{filename}{suffix}.webp")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Rasm fayli topilmadi")
    return FileResponse(file_path, media_type="image/webp")


@router.get("/stats", response_model=DashboardStats, summary="Dashboard statistikasi")
def get_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> DashboardStats:
    """Dashboard uchun umumiy statistika (faqat admin)."""
    return get_dashboard_stats(db)


@router.get("/users", response_model=list[UserResponse], summary="Foydalanuvchilar ro'yxati")
def list_users(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[UserResponse]:
    """Barcha foydalanuvchilarni ko'rish (faqat admin)."""
    return get_all_users(db)


@router.post("/users", response_model=UserResponse, status_code=201, summary="Yangi foydalanuvchi")
def create_new_user(
    data: CreateUserRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """Yangi foydalanuvchi yaratish (faqat admin)."""
    existing = get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu username allaqachon band",
        )
    return create_user(db, data)


# === Yuz solishtirish loglari ===


@router.get("/face-logs", response_model=PaginatedFaceLogs, summary="Yuz solishtirish loglari")
def get_face_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> PaginatedFaceLogs:
    """Yuz solishtirish loglarini sahifalab ko'rish (faqat admin)."""
    items, total = get_face_logs_paginated(db, page, per_page, user_id, date_from, date_to)
    pages = math.ceil(total / per_page) if total > 0 else 1
    return PaginatedFaceLogs(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.get("/face-logs/{log_id}", response_model=FaceLogResponse, summary="Bitta yuz solishtirish logi")
def get_single_face_log(
    log_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> FaceLogResponse:
    """Bitta yuz solishtirish logini ko'rish (faqat admin)."""
    log = get_face_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log topilmadi",
        )
    return log


@router.get("/face-logs/{log_id}/image/{img_type}", summary="Yuz solishtirish rasmi")
def get_face_log_image(
    log_id: int,
    img_type: str,
    thumb: bool = Query(False),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Yuz solishtirish logidagi rasmni olish. img_type: ps yoki lv."""
    if img_type not in ("ps", "lv"):
        raise HTTPException(status_code=400, detail="img_type 'ps' yoki 'lv' bo'lishi kerak")
    log = get_face_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    filename = log.get("ps_img") if img_type == "ps" else log.get("lv_img")
    if not filename:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")
    suffix = "_thumb" if thumb else ""
    file_path = os.path.join(settings.UPLOADS_FACE_DIR, f"{filename}{suffix}.webp")
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Rasm fayli topilmadi")
    return FileResponse(file_path, media_type="image/webp")


@router.get("/face-stats", response_model=DashboardStats, summary="Yuz solishtirish statistikasi")
def get_face_stats(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> DashboardStats:
    """Yuz solishtirish uchun dashboard statistikasi (faqat admin)."""
    return get_face_dashboard_stats(db)


# === API Key boshqarish ===


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=201,
    summary="Yangi API kalit yaratish",
)
def create_new_api_key(
    data: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> ApiKeyCreateResponse:
    """Yangi API kalit yaratish. raw_key faqat bir marta ko'rsatiladi!"""
    api_key, raw_key = create_api_key(db, user_id=admin.id, name=data.name)
    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        raw_key=raw_key,
        created_at=api_key.created_at,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse], summary="API kalitlar ro'yxati")
def list_api_keys(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[ApiKeyResponse]:
    """Barcha API kalitlarni ko'rish (faqat admin)."""
    return get_all_api_keys(db)


@router.delete("/api-keys/{key_id}", summary="API kalitni bekor qilish")
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """API kalitni bekor qilish (o'chirilmaydi, is_active=false bo'ladi)."""
    api_key = revoke_api_key(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API kalit topilmadi",
        )
    return {"detail": "API kalit bekor qilindi"}
