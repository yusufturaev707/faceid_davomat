"""Sessiya talabalari uchun yuz embeddinglarini chiqarish xizmati.

Celery task orqali ishga tushadi. Progress Redis da saqlanadi.
"""

import json
import logging

import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
import app.models  # noqa: F401 — barcha modellarni metadata ga ro'yxatdan o'tkazish
from app.models.student import Student
from app.models.student_ps_data import StudentPsData
from app.models.test_session_smena import TestSessionSmena
from app.services.face_service import detect_faces
from app.services.image_decoder import decode_base64_image

logger = logging.getLogger("faceid.embedding_extractor")

BATCH_SIZE = 50

# Redis key pattern
_PROGRESS_KEY = "embedding_progress:{session_id}"
_PROGRESS_TTL = 3600  # 1 soat


def _get_redis() -> redis.Redis:
    """Redis client olish."""
    return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _set_progress(
    r: redis.Redis,
    session_id: int,
    current: int,
    total: int,
    success: int,
    no_image: int,
    no_face: int,
    errors: int,
    status: str = "processing",
) -> None:
    """Redis da progress yangilash."""
    key = _PROGRESS_KEY.format(session_id=session_id)
    data = {
        "current": current,
        "total": total,
        "success": success,
        "no_image": no_image,
        "no_face": no_face,
        "errors": errors,
        "failed": no_image + no_face + errors,
        "status": status,
        "percent": round(current / total * 100, 1) if total > 0 else 0,
    }
    r.set(key, json.dumps(data), ex=_PROGRESS_TTL)


def get_embedding_progress(session_id: int) -> dict | None:
    """Redis dan embedding progress olish.

    Args:
        session_id: Test sessiya ID si.

    Returns:
        Progress dict yoki None (jarayon boshlanmagan).
    """
    try:
        r = _get_redis()
        key = _PROGRESS_KEY.format(session_id=session_id)
        data = r.get(key)
        if data:
            return json.loads(data)
    except redis.ConnectionError:
        logger.warning("Redis ulanish xatosi — progress olinmadi")
    return None


def extract_embeddings_for_session(session_id: int) -> dict:
    """Sessiya talabalari uchun yuz embeddinglarini chiqarish.

    Celery task ichidan chaqiriladi. O'z DB sessionini ochadi.

    Args:
        session_id: TestSession ID si.

    Returns:
        Natija dict: {success, no_image, no_face, errors, total}
    """
    from app.db.session import SessionLocal
    from app.models.test_session import TestSession

    db: Session = SessionLocal()

    try:
        session = db.get(TestSession, session_id)
        if not session:
            raise ValueError(f"TestSession #{session_id} topilmadi")

        # Sessiyaga tegishli barcha smena ID larni olish
        smena_ids = [
            row[0]
            for row in db.execute(
                select(TestSessionSmena.id).where(
                    TestSessionSmena.test_session_id == session_id
                )
            )
        ]
        if not smena_ids:
            raise ValueError("Sessiyada smenalar topilmadi")

        # Barcha studentlarni olish
        all_students: list[Student] = list(
            db.execute(
                select(Student)
                .where(Student.session_smena_id.in_(smena_ids))
                .order_by(Student.id)
            ).scalars().all()
        )

        total = len(all_students)
        if total == 0:
            logger.info("Session #%d: studentlar topilmadi", session_id)
            return {"success": 0, "no_image": 0, "no_face": 0, "errors": 0, "total": 0}

        # Student ID → StudentPsData mapping (batch qilib olish — katta listda IN xavfli)
        ps_data_map: dict[int, StudentPsData] = {}
        for i in range(0, len(all_students), 1000):
            chunk_ids = [s.id for s in all_students[i:i + 1000]]
            for ps in db.execute(
                select(StudentPsData).where(StudentPsData.student_id.in_(chunk_ids))
            ).scalars():
                ps_data_map[ps.student_id] = ps

        logger.info("Session #%d: %d ta student uchun embedding boshlanmoqda", session_id, total)

        # Redis progress
        try:
            r = _get_redis()
            _set_progress(r, session_id, 0, total, 0, 0, 0, 0, "processing")
        except redis.ConnectionError:
            logger.warning("Redis ulanish xatosi — progress saqlanmaydi")
            r = None

        success_count = 0
        no_image_count = 0
        no_face_count = 0
        error_count = 0

        for i, student in enumerate(all_students):
            ps_data = ps_data_map.get(student.id)

            # ps_data yo'q yoki ps_img bo'sh — rasmsiz
            if not ps_data or not ps_data.ps_img:
                student.is_image = False
                student.is_face = False
                student.is_ready = False
                no_image_count += 1
            else:
                student.is_image = True
                try:
                    img_bgr, _ = decode_base64_image(ps_data.ps_img)
                    faces = detect_faces(img_bgr)

                    if faces:
                        embedding = faces[0].embedding.tolist()
                        ps_data.embedding = json.dumps(embedding)
                        student.is_face = True
                        student.is_ready = True
                        success_count += 1
                    else:
                        student.is_face = False
                        student.is_ready = False
                        no_face_count += 1
                except Exception:
                    student.is_face = False
                    student.is_ready = False
                    error_count += 1
                    logger.debug("Student #%d: embedding xatosi", student.id, exc_info=True)

            # Har BATCH_SIZE da commit + progress yangilash
            current = i + 1
            if current % BATCH_SIZE == 0 or current == total:
                db.commit()
                if r:
                    try:
                        _set_progress(
                            r, session_id, current, total,
                            success_count, no_image_count, no_face_count, error_count,
                        )
                    except redis.ConnectionError:
                        pass
                logger.info(
                    "Session #%d: %d/%d (success=%d, no_image=%d, no_face=%d, errors=%d)",
                    session_id, current, total, success_count, no_image_count, no_face_count, error_count,
                )

        # Yakuniy progress
        failed = no_image_count + no_face_count + error_count
        final_status = "completed" if failed == 0 else "completed_with_errors"
        if r:
            try:
                _set_progress(
                    r, session_id, total, total,
                    success_count, no_image_count, no_face_count, error_count, final_status,
                )
            except redis.ConnectionError:
                pass

        logger.info(
            "Session #%d: embedding tugadi — success=%d, no_image=%d, no_face=%d, errors=%d",
            session_id, success_count, no_image_count, no_face_count, error_count,
        )

        return {
            "success": success_count,
            "no_image": no_image_count,
            "no_face": no_face_count,
            "errors": error_count,
            "total": total,
        }
    finally:
        db.close()


def extract_embeddings_for_not_ready(session_id: int) -> dict:
    """Faqat is_ready=False bo'lgan studentlar uchun qayta embedding chiqarish.

    Qo'lda rasm yuklangandan keyin chaqiriladi.

    Args:
        session_id: TestSession ID si.

    Returns:
        Natija dict: {success, no_image, no_face, errors, total}
    """
    from app.db.session import SessionLocal
    from app.models.test_session import TestSession

    db: Session = SessionLocal()

    try:
        session = db.get(TestSession, session_id)
        if not session:
            raise ValueError(f"TestSession #{session_id} topilmadi")

        # Sessiyaga tegishli barcha smena ID larni olish
        smena_ids = [
            row[0]
            for row in db.execute(
                select(TestSessionSmena.id).where(
                    TestSessionSmena.test_session_id == session_id
                )
            )
        ]
        if not smena_ids:
            raise ValueError("Sessiyada smenalar topilmadi")

        # Faqat is_ready=False bo'lgan studentlarni olish
        not_ready_students: list[Student] = list(
            db.execute(
                select(Student)
                .where(
                    Student.session_smena_id.in_(smena_ids),
                    Student.is_ready.is_(False),
                )
                .order_by(Student.id)
            ).scalars().all()
        )

        total = len(not_ready_students)
        if total == 0:
            logger.info("Session #%d: is_ready=False studentlar topilmadi", session_id)
            return {"success": 0, "no_image": 0, "no_face": 0, "errors": 0, "total": 0}

        # Student ID → StudentPsData mapping
        ps_data_map: dict[int, StudentPsData] = {}
        for i in range(0, len(not_ready_students), 1000):
            chunk_ids = [s.id for s in not_ready_students[i:i + 1000]]
            for ps in db.execute(
                select(StudentPsData).where(StudentPsData.student_id.in_(chunk_ids))
            ).scalars():
                ps_data_map[ps.student_id] = ps

        logger.info("Session #%d: %d ta is_ready=False student uchun qayta embedding", session_id, total)

        # Redis progress
        try:
            r = _get_redis()
            _set_progress(r, session_id, 0, total, 0, 0, 0, 0, "processing")
        except redis.ConnectionError:
            logger.warning("Redis ulanish xatosi — progress saqlanmaydi")
            r = None

        success_count = 0
        no_image_count = 0
        no_face_count = 0
        error_count = 0

        for i, student in enumerate(not_ready_students):
            ps_data = ps_data_map.get(student.id)

            if not ps_data or not ps_data.ps_img:
                student.is_image = False
                student.is_face = False
                student.is_ready = False
                no_image_count += 1
            else:
                student.is_image = True
                try:
                    img_bgr, _ = decode_base64_image(ps_data.ps_img)
                    faces = detect_faces(img_bgr)

                    if faces:
                        embedding = faces[0].embedding.tolist()
                        ps_data.embedding = json.dumps(embedding)
                        student.is_face = True
                        student.is_ready = True
                        success_count += 1
                    else:
                        student.is_face = False
                        student.is_ready = False
                        no_face_count += 1
                except Exception:
                    student.is_face = False
                    student.is_ready = False
                    error_count += 1
                    logger.debug("Student #%d: embedding xatosi", student.id, exc_info=True)

            current = i + 1
            if current % BATCH_SIZE == 0 or current == total:
                db.commit()
                if r:
                    try:
                        _set_progress(
                            r, session_id, current, total,
                            success_count, no_image_count, no_face_count, error_count,
                        )
                    except redis.ConnectionError:
                        pass

        failed = no_image_count + no_face_count + error_count
        final_status = "completed" if failed == 0 else "completed_with_errors"
        if r:
            try:
                _set_progress(
                    r, session_id, total, total,
                    success_count, no_image_count, no_face_count, error_count, final_status,
                )
            except redis.ConnectionError:
                pass

        logger.info(
            "Session #%d: qayta embedding tugadi — success=%d, no_image=%d, no_face=%d, errors=%d",
            session_id, success_count, no_image_count, no_face_count, error_count,
        )

        return {
            "success": success_count,
            "no_image": no_image_count,
            "no_face": no_face_count,
            "errors": error_count,
            "total": total,
        }
    finally:
        db.close()
