from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.verification_log import VerificationLog
from app.schemas.photo import PhotoVerifyRequest, PhotoVerifyResponse
from app.services.face_service import save_image_webp, verify_photo

router = APIRouter()


@router.post(
    "/verify-photo",
    response_model=PhotoVerifyResponse,
    summary="Rasmni tekshirish",
    description="Base64 formatdagi rasmni qabul qilib, yuz aniqlash va sertifikat parametrlarini tekshiradi.",
)
def verify_photo_endpoint(
    request: PhotoVerifyRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
) -> PhotoVerifyResponse:
    """Rasm tekshiruv endpointi. JWT orqali himoyalangan."""
    result, img_bgr = verify_photo(img_b64=request.img_b64, age=request.age)

    # Rasmni WebP formatda diskka saqlash
    image_filename = save_image_webp(img_bgr)

    # Tekshiruv logini DB ga yozish
    log = VerificationLog(
        user_id=current_user.id,
        success=result.success,
        detection=result.detection,
        image_width=result.size.width,
        image_height=result.size.height,
        file_size_bytes=result.file_size_byte,
        input_age=request.age,
        back_color=str(result.back_color),
        error_message="\n".join(result.error_messages) if result.error_messages else None,
        image_path=image_filename,
    )
    db.add(log)
    db.commit()

    return result
