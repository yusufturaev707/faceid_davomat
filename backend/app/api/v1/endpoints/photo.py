from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.celery_app import celery_app
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

router = APIRouter()


@router.post(
    "/verify-photo",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Rasmni tekshirishga yuborish",
    description="Rasmni Celery navbatiga yuboradi va task_id qaytaradi. Natijani /verify-photo/status/{task_id} orqali oling.",
)
def submit_verify_photo(
    request: PhotoVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    _db: Session = Depends(get_db),
) -> TaskSubmitResponse:
    """Rasm tekshiruvini navbatga qo'shish. Darhol task_id qaytaradi."""
    task = process_verify_photo.delay(
        img_b64=request.img_b64,
        age=request.age,
        user_id=current_user.id,
    )
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
def submit_verify_two_face(
    request: TwoFaceVerifyRequest,
    current_user: User = Depends(get_current_active_user),
) -> TaskSubmitResponse:
    """Ikki yuzni solishtirish taskini navbatga qo'shish."""
    task = process_verify_two_faces.delay(
        ps_img_b64=request.ps_img,
        lv_img_b64=request.lv_img,
        user_id=current_user.id,
    )
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
