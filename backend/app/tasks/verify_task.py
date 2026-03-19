"""Celery tasklari — yuz tekshirish va rasm saqlash.

verify queue — yuz aniqlash va solishtirish (CPU-intensiv).
storage queue — rasm diskka saqlash (I/O-intensiv, fire-and-forget).
"""

import logging
import time

from app.celery_app import celery_app
from app.config import settings
from app.db.session import SessionLocal
from app.models.verification_log import VerificationLog
from app.models.verify_faces import VerifyFaces
from app.services.embedding_extractor import extract_embeddings_for_not_ready, extract_embeddings_for_session
from app.services.face_service import compare_two_faces, save_image_webp, verify_photo
from app.services.image_decoder import decode_base64_image

logger = logging.getLogger("faceid.tasks")


# === Storage tasklari (fire-and-forget, alohida queue) ===


@celery_app.task(
    name="tasks.save_photo_image",
    queue="storage",
    max_retries=2,
    autoretry_for=(OSError, IOError),
    retry_backoff=True,
)
def save_photo_image(img_b64: str, uploads_dir: str, log_id: int) -> None:
    """Rasm tekshiruv natijasini diskka saqlash va DB da image_path yangilash.

    Args:
        img_b64: Base64 kodlangan rasm.
        uploads_dir: Saqlash papkasi.
        log_id: VerificationLog yozuvi ID si.
    """
    logger.info("Rasm saqlanmoqda: log_id=%d", log_id)
    img_bgr, _ = decode_base64_image(img_b64)
    filename = save_image_webp(img_bgr, uploads_dir)

    db = SessionLocal()
    try:
        log = db.get(VerificationLog, log_id)
        if log:
            log.image_path = filename
            db.commit()
            logger.info("Rasm saqlandi: log_id=%d, filename=%s", log_id, filename)
        else:
            logger.warning("VerificationLog topilmadi: log_id=%d", log_id)
    except Exception:
        db.rollback()
        logger.exception("DB yangilashda xatolik: log_id=%d", log_id)
        raise
    finally:
        db.close()


@celery_app.task(
    name="tasks.save_face_images",
    queue="storage",
    max_retries=2,
    autoretry_for=(OSError, IOError),
    retry_backoff=True,
)
def save_face_images(
    ps_img_b64: str, lv_img_b64: str, uploads_dir: str, log_id: int
) -> None:
    """Ikki yuz rasmlarini diskka saqlash va DB da ps_img/lv_img yangilash.

    Args:
        ps_img_b64: Pasport rasmi base64.
        lv_img_b64: Jonli rasm base64.
        uploads_dir: Saqlash papkasi.
        log_id: VerifyFaces yozuvi ID si.
    """
    logger.info("Yuz rasmlari saqlanmoqda: log_id=%d", log_id)

    ps_bgr, _ = decode_base64_image(ps_img_b64)
    lv_bgr, _ = decode_base64_image(lv_img_b64)

    ps_filename = save_image_webp(ps_bgr, uploads_dir)
    lv_filename = save_image_webp(lv_bgr, uploads_dir)

    db = SessionLocal()
    try:
        log = db.get(VerifyFaces, log_id)
        if log:
            log.ps_img = ps_filename
            log.lv_img = lv_filename
            db.commit()
            logger.info(
                "Yuz rasmlari saqlandi: log_id=%d, ps=%s, lv=%s",
                log_id, ps_filename, lv_filename,
            )
        else:
            logger.warning("VerifyFaces topilmadi: log_id=%d", log_id)
    except Exception:
        db.rollback()
        logger.exception("DB yangilashda xatolik: log_id=%d", log_id)
        raise
    finally:
        db.close()


# === Verify tasklari (CPU-intensiv, verify queue) ===


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_verify_photo",
    queue="verify",
)
def process_verify_photo(self, img_b64: str, age: int, user_id: int) -> dict:
    """Rasm tekshiruvi — InsightFace inference + DB log.

    Rasm saqlash alohida storage task ga yuboriladi (fire-and-forget).

    Args:
        img_b64: Base64 kodlangan rasm.
        age: Kutilgan yosh.
        user_id: Foydalanuvchi ID si.

    Returns:
        PhotoVerifyResponse dict.
    """
    logger.info("Rasm tekshiruvi boshlandi: user_id=%d, age=%d", user_id, age)

    result, _img_bgr = verify_photo(img_b64=img_b64, age=age)

    # DB log (image_path hali yo'q — storage task yangilaydi)
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
        )
        db.add(log)
        db.commit()
        log_id = log.id
    except Exception:
        db.rollback()
        logger.exception("DB log yozishda xatolik: user_id=%d", user_id)
        raise
    finally:
        db.close()

    # Fire-and-forget: rasmni storage queue ga yuborish
    save_photo_image.delay(img_b64, settings.UPLOADS_PHOTO_DIR, log_id)

    logger.info("Rasm tekshiruvi tugadi: user_id=%d, success=%s", user_id, result.success)
    return result.model_dump()


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_verify_two_faces",
    queue="verify",
)
def process_verify_two_faces(self, ps_img_b64: str, lv_img_b64: str, user_id: int) -> dict:
    """Ikki yuzni solishtirish — InsightFace inference + DB log.

    Rasm saqlash alohida storage task ga yuboriladi (fire-and-forget).

    Args:
        ps_img_b64: Pasport rasmi base64.
        lv_img_b64: Jonli rasm base64.
        user_id: Foydalanuvchi ID si.

    Returns:
        TwoFaceVerifyResponse dict.
    """
    logger.info("Ikki yuz solishtirish boshlandi: user_id=%d", user_id)
    start_time = time.time()

    result, _ps_img_bgr, _lv_img_bgr = compare_two_faces(
        ps_img_b64=ps_img_b64,
        lv_img_b64=lv_img_b64,
    )

    response_time = round(time.time() - start_time, 3)

    # DB log (ps_img/lv_img hali yo'q — storage task yangilaydi)
    db = SessionLocal()
    try:
        log = VerifyFaces(
            user_id=user_id,
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
        log_id = log.id
    except Exception:
        db.rollback()
        logger.exception("DB log yozishda xatolik: user_id=%d", user_id)
        raise
    finally:
        db.close()

    # Fire-and-forget: rasmlarni storage queue ga yuborish
    save_face_images.delay(
        ps_img_b64, lv_img_b64, settings.UPLOADS_FACE_DIR, log_id,
    )

    logger.info(
        "Ikki yuz solishtirish tugadi: user_id=%d, verified=%s, score=%.4f, time=%.3fs",
        user_id, result.verified, result.score, response_time,
    )
    return result.model_dump()


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_embeddings",
    queue="verify",
    time_limit=600,  # 10 daqiqa — ko'p studentlar uchun
)
def process_embeddings(self, session_id: int) -> dict:
    """Sessiya talabalari uchun yuz embeddinglarini chiqarish.

    Celery worker da bajariladi. Progress Redis orqali kuzatiladi.

    Args:
        session_id: TestSession ID si.

    Returns:
        Natija dict: {success, no_image, no_face, errors, total}
    """
    logger.info("Embedding jarayoni boshlandi: session_id=%d", session_id)
    result = extract_embeddings_for_session(session_id)
    logger.info(
        "Embedding jarayoni tugadi: session_id=%d, success=%d, total=%d",
        session_id, result["success"], result["total"],
    )
    return result


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.process_retry_embeddings",
    queue="verify",
    time_limit=600,
)
def process_retry_embeddings(self, session_id: int) -> dict:
    """Faqat is_ready=False bo'lgan studentlar uchun qayta embedding chiqarish.

    Args:
        session_id: TestSession ID si.

    Returns:
        Natija dict: {success, no_image, no_face, errors, total}
    """
    logger.info("Qayta embedding jarayoni boshlandi: session_id=%d", session_id)
    result = extract_embeddings_for_not_ready(session_id)
    logger.info(
        "Qayta embedding jarayoni tugadi: session_id=%d, success=%d, total=%d",
        session_id, result["success"], result["total"],
    )
    return result
