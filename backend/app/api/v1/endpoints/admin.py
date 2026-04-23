import math
import os
import pathlib
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.core.permissions import P
from app.core.rate_limit import limiter
from app.crud.api_key import create_api_key, get_all_api_keys, revoke_api_key
from app.crud.user import create_user, delete_user, get_all_users, get_user_by_username, update_user
from app.crud.verification_log import get_dashboard_stats, get_log_by_id, get_logs_paginated
from app.crud.verify_faces import get_face_dashboard_stats, get_face_log_by_id, get_face_logs_paginated
from app.dependencies import PermissionChecker, get_current_active_user, get_db
from app.models.user import User
from app.schemas.admin import DashboardStats, FaceLogResponse, PaginatedFaceLogs, PaginatedLogs, VerificationLogResponse
from app.schemas.api_key import ApiKeyCreateRequest, ApiKeyCreateResponse, ApiKeyResponse
from app.schemas.auth import CreateUserRequest, UpdateUserRequest, UserResponse

router = APIRouter()


def _safe_image_path(base_dir: str, filename: str, suffix: str) -> str:
    """Fayl yo'lini xavfsiz birlashtirish: base_dir tashqarisiga chiqib ketishdan himoya.

    filename DB'dan keladi (`uuid.uuid4().hex[:16]` formatida bo'lishi kutiladi),
    lekin defense-in-depth uchun har doim resolve qilib tekshiramiz.
    """
    base = pathlib.Path(base_dir).resolve()
    target = (base / f"{filename}{suffix}.webp").resolve()
    try:
        target.relative_to(base)
    except ValueError:
        raise HTTPException(status_code=400, detail="Yaroqsiz fayl yo'li")
    return str(target)


@router.get("/logs", response_model=PaginatedLogs, summary="Tekshiruv loglari")
def get_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.LOG_READ.code)),
) -> PaginatedLogs:
    """Barcha tekshiruv loglarini sahifalab ko'rish. Admin bo'lmaganlar faqat o'z loglarini ko'radi."""
    if current_user.role_key != 1:
        user_id = current_user.id
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
    current_user: User = Depends(PermissionChecker(P.LOG_READ.code)),
) -> VerificationLogResponse:
    """Bitta tekshiruv logini ko'rish."""
    log = get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log topilmadi",
        )
    if current_user.role_key != 1 and log.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log topilmadi")
    return log


@router.get("/logs/{log_id}/image", summary="Log rasmi (original)")
def get_log_image(
    log_id: int,
    thumb: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.LOG_READ.code)),
):
    """Tekshiruv logidagi rasmni olish. thumb=true bo'lsa thumbnail qaytaradi."""
    log = get_log_by_id(db, log_id)
    if not log or not log.get("image_path"):
        raise HTTPException(status_code=404, detail="Rasm topilmadi")
    if current_user.role_key != 1 and log.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")
    filename = log["image_path"]
    suffix = "_thumb" if thumb else ""
    file_path = _safe_image_path(settings.UPLOADS_PHOTO_DIR, filename, suffix)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Rasm fayli topilmadi")
    return FileResponse(file_path, media_type="image/webp")


@router.get("/stats", response_model=DashboardStats, summary="Dashboard statistikasi")
def get_stats(
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.DASHBOARD_STATS.code, P.DASHBOARD_READ.code)),
) -> DashboardStats:
    """Dashboard uchun umumiy statistika."""
    return get_dashboard_stats(db)


@router.get("/users", response_model=list[UserResponse], summary="Foydalanuvchilar ro'yxati")
def list_users(
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.USER_READ.code)),
) -> list[UserResponse]:
    """Barcha foydalanuvchilarni ko'rish."""
    return get_all_users(db)


@router.post("/users", response_model=UserResponse, status_code=201, summary="Yangi foydalanuvchi")
@limiter.limit("10/minute")
def create_new_user(
    request: Request,
    data: CreateUserRequest,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.USER_CREATE.code)),
) -> UserResponse:
    """Yangi foydalanuvchi yaratish."""
    existing = get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bu username allaqachon band",
        )
    return create_user(db, data)


@router.patch("/users/{user_id}", response_model=UserResponse, summary="Foydalanuvchini tahrirlash")
@limiter.limit("20/minute")
def update_existing_user(
    request: Request,
    user_id: int,
    data: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.USER_UPDATE.code)),
) -> UserResponse:
    """Foydalanuvchini tahrirlash. role_id va is_active faqat admin uchun."""
    if current_user.role_key != 1:
        provided = data.model_dump(exclude_unset=True)
        if "role_id" in provided or "is_active" in provided:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="role_id va is_active faqat admin tomonidan o'zgartiriladi",
            )
    user = update_user(db, user_id, data)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi",
        )
    return user


@router.delete("/users/{user_id}", status_code=204, summary="Foydalanuvchini o'chirish")
@limiter.limit("10/minute")
def delete_existing_user(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.USER_DELETE.code)),
):
    """Foydalanuvchini o'chirish."""
    if not delete_user(db, user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foydalanuvchi topilmadi",
        )


# === Yuz solishtirish loglari ===


@router.get("/face-logs", response_model=PaginatedFaceLogs, summary="Yuz solishtirish loglari")
def get_face_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.FACE_LOG_READ.code)),
) -> PaginatedFaceLogs:
    """Yuz solishtirish loglarini sahifalab ko'rish. Admin bo'lmaganlar faqat o'z loglarini ko'radi."""
    if current_user.role_key != 1:
        user_id = current_user.id
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
    current_user: User = Depends(PermissionChecker(P.FACE_LOG_READ.code)),
) -> FaceLogResponse:
    """Bitta yuz solishtirish logini ko'rish."""
    log = get_face_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log topilmadi",
        )
    if current_user.role_key != 1 and log.get("user_id") != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Log topilmadi")
    return log


@router.get("/face-logs/{log_id}/image/{img_type}", summary="Yuz solishtirish rasmi")
def get_face_log_image(
    log_id: int,
    img_type: str,
    thumb: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.FACE_LOG_READ.code)),
):
    """Yuz solishtirish logidagi rasmni olish. img_type: ps yoki lv."""
    if img_type not in ("ps", "lv"):
        raise HTTPException(status_code=400, detail="img_type 'ps' yoki 'lv' bo'lishi kerak")
    log = get_face_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    if current_user.role_key != 1 and log.get("user_id") != current_user.id:
        raise HTTPException(status_code=404, detail="Log topilmadi")
    filename = log.get("ps_img") if img_type == "ps" else log.get("lv_img")
    if not filename:
        raise HTTPException(status_code=404, detail="Rasm topilmadi")
    suffix = "_thumb" if thumb else ""
    file_path = _safe_image_path(settings.UPLOADS_FACE_DIR, filename, suffix)
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Rasm fayli topilmadi")
    return FileResponse(file_path, media_type="image/webp")


@router.get("/face-stats", response_model=DashboardStats, summary="Yuz solishtirish statistikasi")
def get_face_stats(
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.DASHBOARD_STATS.code, P.DASHBOARD_READ.code)),
) -> DashboardStats:
    """Yuz solishtirish uchun dashboard statistikasi."""
    return get_face_dashboard_stats(db)


# === API Key boshqarish ===


@router.post(
    "/api-keys",
    response_model=ApiKeyCreateResponse,
    status_code=201,
    summary="Yangi API kalit yaratish",
)
@limiter.limit("5/minute")
def create_new_api_key(
    request: Request,
    data: ApiKeyCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(PermissionChecker(P.API_KEY_CREATE.code)),
) -> ApiKeyCreateResponse:
    """Yangi API kalit yaratish. raw_key faqat bir marta ko'rsatiladi!"""
    api_key, raw_key = create_api_key(db, user_id=current_user.id, name=data.name)
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
    _: User = Depends(PermissionChecker(P.API_KEY_READ.code)),
) -> list[ApiKeyResponse]:
    """Barcha API kalitlarni ko'rish."""
    return get_all_api_keys(db)


@router.delete("/api-keys/{key_id}", summary="API kalitni bekor qilish")
@limiter.limit("10/minute")
def delete_api_key(
    request: Request,
    key_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(PermissionChecker(P.API_KEY_DELETE.code)),
):
    """API kalitni bekor qilish (o'chirilmaydi, is_active=false bo'ladi)."""
    api_key = revoke_api_key(db, key_id)
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API kalit topilmadi",
        )
    return {"detail": "API kalit bekor qilindi"}
