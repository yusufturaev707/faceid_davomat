"""Sessiya talabalari uchun yuz embeddinglarini chiqarish xizmati.

Celery task orqali ishga tushadi. Progress Redis da saqlanadi.

100k+ talabada xotira to'lib ketmasligi uchun studentlar va ularning
ps_img blob'lari kichik chunk'larda DB dan o'qiladi (streaming).
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
import app.models  # noqa: F401 — barcha modellarni metadata ga ro'yxatdan o'tkazish
from app.models.student import Student
from app.models.student_ps_data import StudentPsData
from app.models.test_session_smena import TestSessionSmena
from app.services.face_service import detect_faces
from app.services.image_decoder import decode_image_bytes

logger = logging.getLogger("faceid.embedding_extractor")

# Bir chunk da DB dan o'qiladigan studentlar soni. ps_img blob ~50-500 KB
# bo'lgani uchun 500 student ≈ 25-250 MB RAM. Bu xavfsiz chegara.
CHUNK_SIZE = 500

# Progress va commit chastotasi (har N student dan keyin)
BATCH_SIZE = 50

# Redis key pattern
_PROGRESS_KEY = "embedding_progress:{session_id}"
# 6 soat — task time_limit dan kengroq, network glitch da expire bo'lib qolmasligi uchun
_PROGRESS_TTL = 6 * 3600


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
    message: str | None = None,
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
    if message:
        data["message"] = message
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


def _get_smena_ids(db: Session, session_id: int) -> list[int]:
    return [
        row[0]
        for row in db.execute(
            select(TestSessionSmena.id).where(
                TestSessionSmena.test_session_id == session_id
            )
        )
    ]


def _infer_one(img_bytes: bytes) -> tuple[bytes | None, str]:
    """Rasm bayt'laridan yuz embedding'ini chiqaradi. SOF funksiya — DB/ORM'ga
    tegmaydi, shuning uchun thread'dan xavfsiz chaqiriladi.

    decode + detect_faces CPU-bound; ONNX inference GIL'ni bo'shatgani uchun bir
    nechta thread haqiqiy parallel ishlaydi (har inference intra_op=1 → 1 yadro).

    Returns:
        (embedding_bytes | None, status) — status: "success" | "no_face" | "error"
    """
    try:
        img_bgr, _ = decode_image_bytes(img_bytes)
        faces = detect_faces(img_bgr)
        if faces:
            emb = np.asarray(faces[0].embedding, dtype=np.float32).tobytes()
            return emb, "success"
        return None, "no_face"
    except Exception:
        return None, "error"


def _process_chunk(
    db: Session, students: list[Student], executor: ThreadPoolExecutor | None
) -> tuple[int, int, int, int]:
    """Berilgan student chunk uchun embedding chiqarish.

    ps_img faqat shu chunk uchun yuklanadi — RAM ni tejash uchun. Inference
    (`_infer_one`) `executor` orqali PARALLEL bajariladi; ORM yozuvlari esa
    faqat shu (asosiy) thread'da qilinadi — SQLAlchemy Session thread-safe emas.

    Returns:
        (success, no_image, no_face, errors)
    """
    if not students:
        return 0, 0, 0, 0

    chunk_ids = [s.id for s in students]
    ps_data_map: dict[int, StudentPsData] = {
        ps.student_id: ps
        for ps in db.execute(
            select(StudentPsData).where(StudentPsData.student_id.in_(chunk_ids))
        ).scalars()
    }

    success = 0
    no_image = 0
    no_face = 0
    errors = 0

    # 1-bosqich (asosiy thread): rasmi bor studentlarni ajratamiz. ps_img yo'q
    # bo'lganlarni shu yerda belgilaymiz — inference'ga yubormaymiz.
    to_infer: list[tuple[Student, StudentPsData, bytes]] = []
    for student in students:
        ps_data = ps_data_map.get(student.id)
        if not ps_data or not ps_data.ps_img:
            student.is_image = False
            student.is_face = False
            student.is_ready = False
            no_image += 1
            continue
        student.is_image = True
        to_infer.append((student, ps_data, ps_data.ps_img))

    # 2-bosqich: inference'ni parallel bajaramiz (DB'ga tegmaydi)
    if to_infer:
        img_list = [item[2] for item in to_infer]
        mapper = executor.map if executor is not None else map
        results = list(mapper(_infer_one, img_list))

        # 3-bosqich (asosiy thread): natijalarni ORM'ga yozamiz
        for (student, ps_data, _), (emb, status) in zip(to_infer, results):
            if status == "success":
                ps_data.embedding = emb
                student.is_face = True
                student.is_ready = True
                success += 1
            elif status == "no_face":
                student.is_face = False
                student.is_ready = False
                no_face += 1
            else:  # "error"
                student.is_face = False
                student.is_ready = False
                errors += 1

    # Chunk ichidagi ps_img referencesini bo'shatish — keyingi chunk gacha xotirada turmasligi uchun
    ps_data_map.clear()
    return success, no_image, no_face, errors


def _run_embedding_job(
    session_id: int,
    only_not_ready: bool,
) -> dict:
    """Streaming embedding extractor — barcha yoki faqat is_ready=False studentlar uchun.

    Args:
        session_id: TestSession ID si.
        only_not_ready: True bo'lsa faqat is_ready=False bo'lganlarni qayta ishlaydi.

    Returns:
        {success, no_image, no_face, errors, total}
    """
    from app.db.session import SessionLocal
    from app.models.test_session import TestSession

    db: Session = SessionLocal()

    # OpenCV'ning ichki thread-pool'ini o'chiramiz: parallellik bizning thread
    # pool'imizda (har rasm alohida thread), decode esa har thread'da 1 ipda —
    # aks holda workers × cv2-threads yadrolarni ortiqcha bosadi.
    try:
        import cv2
        cv2.setNumThreads(1)
    except Exception:
        pass

    workers = settings.EMBEDDING_WORKERS
    executor: ThreadPoolExecutor | None = (
        ThreadPoolExecutor(max_workers=workers, thread_name_prefix="emb")
        if workers and workers > 1
        else None
    )
    logger.info(
        "Session #%d: embedding parallel workers=%s",
        session_id, workers if executor is not None else 1,
    )

    # Redis progress holatini boshlash — exception bo'lsa ham frontend bilsin
    try:
        r: redis.Redis | None = _get_redis()
    except redis.ConnectionError:
        logger.warning("Redis ulanish xatosi — progress saqlanmaydi")
        r = None

    success_count = 0
    no_image_count = 0
    no_face_count = 0
    error_count = 0
    total = 0

    try:
        session = db.get(TestSession, session_id)
        if not session:
            raise ValueError(f"TestSession #{session_id} topilmadi")

        smena_ids = _get_smena_ids(db, session_id)
        if not smena_ids:
            raise ValueError("Sessiyada smenalar topilmadi")

        base_filter = [Student.session_smena_id.in_(smena_ids)]
        if only_not_ready:
            base_filter.append(Student.is_ready.is_(False))

        total = db.scalar(
            select(func.count(Student.id)).where(*base_filter)
        ) or 0

        if total == 0:
            logger.info("Session #%d: studentlar topilmadi", session_id)
            if r:
                try:
                    _set_progress(r, session_id, 0, 0, 0, 0, 0, 0, "completed")
                except redis.ConnectionError:
                    pass
            return {"success": 0, "no_image": 0, "no_face": 0, "errors": 0, "total": 0}

        if r:
            try:
                _set_progress(r, session_id, 0, total, 0, 0, 0, 0, "processing")
            except redis.ConnectionError:
                pass

        logger.info(
            "Session #%d: %d ta student uchun embedding boshlanmoqda (only_not_ready=%s)",
            session_id, total, only_not_ready,
        )

        processed = 0
        last_id = 0
        # Keyset pagination — `id > last_id` orqali. limit/offset emas, chunki
        # offset katta bo'lsa indeks orqali ham sekin bo'ladi.
        while True:
            chunk: list[Student] = list(
                db.execute(
                    select(Student)
                    .where(*base_filter, Student.id > last_id)
                    .order_by(Student.id)
                    .limit(CHUNK_SIZE)
                ).scalars().all()
            )
            if not chunk:
                break

            last_id = chunk[-1].id

            # Chunk ichida BATCH_SIZE bo'lakda commit + progress yangilash
            for batch_start in range(0, len(chunk), BATCH_SIZE):
                batch = chunk[batch_start: batch_start + BATCH_SIZE]
                s, ni, nf, er = _process_chunk(db, batch, executor)
                success_count += s
                no_image_count += ni
                no_face_count += nf
                error_count += er
                processed += len(batch)

                db.commit()

                if r:
                    try:
                        _set_progress(
                            r, session_id, processed, total,
                            success_count, no_image_count, no_face_count, error_count,
                        )
                    except redis.ConnectionError:
                        pass

                logger.info(
                    "Session #%d: %d/%d (success=%d, no_image=%d, no_face=%d, errors=%d)",
                    session_id, processed, total,
                    success_count, no_image_count, no_face_count, error_count,
                )

            # Chunk objektlarini sessiondan chiqarib tashlash — RAM tejash uchun
            db.expunge_all()

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
    except Exception as e:
        # Frontend cheksiz polling qilmasin — Redis da error holatini saqlaymiz
        logger.exception("Session #%d: embedding jarayonida xatolik", session_id)
        if r:
            try:
                _set_progress(
                    r, session_id,
                    success_count + no_image_count + no_face_count + error_count,
                    total,
                    success_count, no_image_count, no_face_count, error_count,
                    status="error",
                    message=str(e)[:200],
                )
            except redis.ConnectionError:
                pass
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        if executor is not None:
            executor.shutdown(wait=True)
        db.close()


def extract_embeddings_for_session(session_id: int) -> dict:
    """Sessiya talabalari uchun yuz embeddinglarini chiqarish (streaming)."""
    return _run_embedding_job(session_id, only_not_ready=False)


def extract_embeddings_for_not_ready(session_id: int) -> dict:
    """Faqat is_ready=False bo'lgan studentlar uchun qayta embedding (streaming)."""
    return _run_embedding_job(session_id, only_not_ready=True)
