import time
from concurrent.futures import ThreadPoolExecutor

from app.celery_app import celery_app
from app.config import settings
from app.db.session import SessionLocal
from app.models.verification_log import VerificationLog
from app.models.verify_faces import VerifyFaces
from app.services.face_service import compare_two_faces, save_image_webp, verify_photo

_save_pool = ThreadPoolExecutor(max_workers=2)


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_verify_photo",
)
def process_verify_photo(self, img_b64: str, age: int, user_id: int) -> dict:
    """InsightFace inference + disk saqlash + DB log — worker processsida bajariladi."""
    result, img_bgr = verify_photo(img_b64=img_b64, age=age)
    image_filename = save_image_webp(img_bgr)

    db = SessionLocal()
    try:
        log = VerificationLog(
            user_id=user_id,
            success=result.success,
            detection=result.detection,
            image_width=result.size.width,
            image_height=result.size.height,
            file_size_bytes=result.file_size_byte,
            input_age=age,
            back_color=str(result.back_color),
            error_message="\n".join(result.error_messages) if result.error_messages else None,
            image_path=image_filename,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

    return result.model_dump()


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_verify_two_faces",
)
def process_verify_two_faces(self, ps_img_b64: str, lv_img_b64: str, user_id: int) -> dict:
    """Ikki yuzni solishtirish — worker processida bajariladi."""
    start_time = time.time()

    result, ps_img_bgr, lv_img_bgr = compare_two_faces(
        ps_img_b64=ps_img_b64,
        lv_img_b64=lv_img_b64,
    )

    ps_future = _save_pool.submit(save_image_webp, ps_img_bgr, settings.UPLOADS_FACE_DIR)
    lv_future = _save_pool.submit(save_image_webp, lv_img_bgr, settings.UPLOADS_FACE_DIR)
    ps_filename = ps_future.result()
    lv_filename = lv_future.result()

    response_time = round(time.time() - start_time, 3)

    db = SessionLocal()
    try:
        log = VerifyFaces(
            user_id=user_id,
            ps_img=ps_filename,
            lv_img=lv_filename,
            ps_file_size=result.ps_file_size,
            lv_file_size=result.lv_file_size,
            ps_width=result.ps_width,
            ps_height=result.ps_height,
            lv_width=result.lv_width,
            lv_height=result.lv_height,
            ps_detection=result.ps_detection,
            lv_detection=result.lv_detection,
            detection=result.ps_detection and result.lv_detection,
            response_time=response_time,
            score=result.score,
            thresh_score=result.thresh_score,
            verified=result.verified,
            error_message="\n".join(result.error_messages) if result.error_messages else None,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()

    return result.model_dump()
