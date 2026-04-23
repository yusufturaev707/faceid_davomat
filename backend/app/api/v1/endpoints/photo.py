"""Rasm tekshiruv va yuz solishtirish endpointlari.

Backpressure: queue to'lganda HTTP 429 qaytaradi (Retry-After header bilan).
"""

import logging

import redis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.config import settings
from app.core.rate_limit import limiter
from app.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.photo import (
    PhotoVerifyRequest,
    PhotoVerifyResponse,
    TaskStatusResponse,
    TaskSubmitResponse,
    TwoFaceTaskStatusResponse,
    TwoFaceVerifyRequest,
    TwoFaceVerifyResponse,
)
from app.tasks.verify_task import process_verify_photo, process_verify_two_faces

logger = logging.getLogger("faceid.api.photo")

router = APIRouter()

# Redis ulanishi — backpressure tekshiruvi uchun
_redis_client: redis.Redis | None = None


def _get_redis() -> redis.Redis:
    """Redis clientni olish (singleton).

    Returns:
        Redis client instansiyasi.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=False,
            socket_connect_timeout=2,
        )
    return _redis_client


def _check_queue_backpressure(queue_name: str = "verify") -> None:
    """Queue to'lganligini tekshirish.

    Agar queue dagi tasklar soni QUEUE_MAX_SIZE dan oshsa, HTTP 429 qaytaradi.

    Args:
        queue_name: Tekshiriladigan queue nomi.

    Raises:
        HTTPException 429: Queue to'lgan bo'lsa.
    """
    try:
        r = _get_redis()
        queue_length = r.llen(queue_name)
    except redis.ConnectionError:
        logger.warning("Redis ulanish xatosi — backpressure tekshiruvi o'tkazib yuborildi")
        return

    if queue_length >= settings.QUEUE_MAX_SIZE:
        logger.warning(
            "Backpressure: queue=%s, length=%d, max=%d",
            queue_name, queue_length, settings.QUEUE_MAX_SIZE,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Server band. Iltimos, keyinroq urinib ko'ring.",
            headers={"Retry-After": str(settings.BACKPRESSURE_RETRY_AFTER)},
        )


@router.post(
    "/verify-photo",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rasmni tekshirishga yuborish",
    description="Rasmni Celery navbatiga yuboradi va task_id qaytaradi. Natijani /verify-photo/status/{task_id} orqali oling.",
)
@limiter.limit("30/minute")
def submit_verify_photo(
    request: Request,
    payload: PhotoVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    _db: Session = Depends(get_db),
) -> TaskSubmitResponse:
    """Rasm tekshiruvini navbatga qo'shish. Darhol task_id qaytaradi."""
    _check_queue_backpressure("verify")

    task = process_verify_photo.delay(
        img_b64=payload.img_b64,
        age=payload.age,
        user_id=current_user.id,
    )
    logger.info("Rasm tekshiruvi yuborildi: task_id=%s, user_id=%d", task.id, current_user.id)
    return TaskSubmitResponse(task_id=task.id)


@router.get(
    "/verify-photo/status/{task_id}",
    response_model=TaskStatusResponse,
    summary="Task natijasini olish",
    description="task_id orqali tekshiruv natijasini so'rash. status: PENDING | STARTED | SUCCESS | FAILURE",
)
def get_task_status(
    task_id: str,
    _current_user: User = Depends(get_current_active_user),
) -> TaskStatusResponse:
    """Celery task holatini va natijasini qaytarish."""
    task_result = celery_app.AsyncResult(task_id)
    task_status = task_result.status

    if task_status == "SUCCESS":
        return TaskStatusResponse(
            task_id=task_id,
            status="SUCCESS",
            result=PhotoVerifyResponse(**task_result.result),
        )

    if task_status == "FAILURE":
        return TaskStatusResponse(
            task_id=task_id,
            status="FAILURE",
            error=str(task_result.result),
        )

    # PENDING yoki STARTED
    return TaskStatusResponse(task_id=task_id, status=task_status)


# === Ikki yuzni solishtirish ===


@router.post(
    "/verify-two-face",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ikki yuzni solishtirishga yuborish",
    description="Ikki rasmni Celery navbatiga yuboradi va task_id qaytaradi.",
)
@limiter.limit("30/minute")
def submit_verify_two_face(
    request: Request,
    payload: TwoFaceVerifyRequest,
    current_user: User = Depends(get_current_active_user),
) -> TaskSubmitResponse:
    """Ikki yuzni solishtirish taskini navbatga qo'shish."""
    _check_queue_backpressure("verify")

    task = process_verify_two_faces.delay(
        ps_img_b64=payload.ps_img,
        lv_img_b64=payload.lv_img,
        user_id=current_user.id,
    )
    logger.info("Ikki yuz solishtirish yuborildi: task_id=%s, user_id=%d", task.id, current_user.id)
    return TaskSubmitResponse(task_id=task.id)


@router.get(
    "/verify-two-face/status/{task_id}",
    response_model=TwoFaceTaskStatusResponse,
    summary="Ikki yuz solishtirish natijasini olish",
    description="task_id orqali solishtirish natijasini so'rash.",
)
def get_two_face_task_status(
    task_id: str,
    _current_user: User = Depends(get_current_active_user),
) -> TwoFaceTaskStatusResponse:
    """Ikki yuz solishtirish task holatini qaytarish."""
    task_result = celery_app.AsyncResult(task_id)
    task_status = task_result.status

    if task_status == "SUCCESS":
        return TwoFaceTaskStatusResponse(
            task_id=task_id,
            status="SUCCESS",
            result=TwoFaceVerifyResponse(**task_result.result),
        )

    if task_status == "FAILURE":
        return TwoFaceTaskStatusResponse(
            task_id=task_id,
            status="FAILURE",
            error=str(task_result.result),
        )

    return TwoFaceTaskStatusResponse(task_id=task_id, status=task_status)
