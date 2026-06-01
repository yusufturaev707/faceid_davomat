"""Celery task: tashqi API'dan studentlarni yuklash.

Sinxron HTTP request ichida 100k+ talaba yuklash 504 Gateway Timeout'ga
olib keladi. Shuning uchun yuklash arqaplanga (background) o'tkaziladi:

1. Endpoint state=2 ga o'tganda darhol Celery task'ga yuboradi.
2. Frontend `/student-load-progress` orqali Redis'dan progress polling qiladi.
3. Xatolik bo'lsa — sessiya state'ini avvalgi holatga qaytaradi.
"""

import logging

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.test_session import TestSession
from app.services.student_loader import (
    StudentLoadError,
    load_students_for_session,
)

logger = logging.getLogger("faceid.tasks.student_loader")


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.load_students",
    queue="storage",  # CPU-light, I/O-heavy → storage queue (verify CPU bilan band)
    time_limit=3600,  # 1 soat — 100k+ talaba uchun
    soft_time_limit=3540,
)
def load_students_task(
    self, session_id: int, previous_state_id: int
) -> dict:
    """Sessiya uchun tashqi API'dan studentlarni yuklash.

    Args:
        session_id: TestSession ID si.
        previous_state_id: Xatolik bo'lsa qaytarish kerak bo'lgan state ID.

    Returns:
        {"loaded": int, "status": "completed" | "error", "message": str}
    """
    logger.info("Student loading task boshlandi: session_id=%d", session_id)

    db = SessionLocal()
    try:
        session = db.get(TestSession, session_id)
        if not session:
            logger.error("TestSession #%d topilmadi", session_id)
            return {
                "loaded": 0,
                "status": "error",
                "message": f"Sessiya #{session_id} topilmadi",
            }

        try:
            count = load_students_for_session(db, session)
        except StudentLoadError as e:
            logger.error(
                "Session #%d: yuklash xatosi — %s. State qaytarilmoqda → %d",
                session_id, e.message, previous_state_id,
            )
            _rollback_state(db, session_id, previous_state_id)
            return {"loaded": 0, "status": "error", "message": e.message}
        except Exception as e:
            logger.exception(
                "Session #%d: kutilmagan xatolik. State qaytarilmoqda → %d",
                session_id, previous_state_id,
            )
            _rollback_state(db, session_id, previous_state_id)
            return {
                "loaded": 0,
                "status": "error",
                "message": f"Kutilmagan xatolik: {e}",
            }

        # 0 talaba bo'lsa state'ni boshlang'ich holatga qaytaramiz.
        # Endpoint state'ni allaqachon key=2 ga o'zgartirgan — uni key=1 ga
        # qaytarish foydalanuvchi konfiguratsiyani tekshirib qayta urinishi uchun.
        if count == 0:
            logger.warning(
                "Session #%d: 0 ta talaba yuklandi — state %d ga qaytarilmoqda",
                session_id, previous_state_id,
            )
            _rollback_state(db, session_id, previous_state_id)
            # Redis progress'ni xato sifatida belgilaymiz (frontend xato banner ko'rsatadi)
            try:
                from app.services.student_loader import _get_redis, _set_progress

                _set_progress(
                    _get_redis(),
                    session_id,
                    current=0,
                    total=0,
                    pages_done=0,
                    pages_total=0,
                    skipped=0,
                    status="error",
                    message=(
                        "Tashqi API'dan 0 ta talaba qaytdi — sessiya parametrlarini "
                        "(test, smena, sana, region) tekshiring"
                    ),
                )
            except Exception:
                logger.exception(
                    "Session #%d: progress yozishda xato", session_id
                )
            return {
                "loaded": 0,
                "status": "completed",
                "message": "0 ta talaba — sessiya boshlang'ich holatda qoldi",
            }

        logger.info(
            "Session #%d: %d ta talaba muvaffaqiyatli yuklandi", session_id, count
        )
        return {
            "loaded": count,
            "status": "completed",
            "message": f"{count} ta talaba yuklandi",
        }
    finally:
        db.close()


def _rollback_state(db, session_id: int, previous_state_id: int) -> None:
    """Xatolik bo'lganda sessiyani avvalgi state'iga qaytarish.

    DB sessionning o'zi xatosi bo'lsa qaytadan ochamiz.
    """
    try:
        db.rollback()
    except Exception:
        pass

    try:
        from app.crud.test_session import change_session_state

        change_session_state(
            db, session_id=session_id, new_state_id=previous_state_id
        )
        logger.info(
            "Session #%d: state %d ga qaytarildi", session_id, previous_state_id
        )
    except Exception:
        logger.exception(
            "Session #%d: state qaytarishda xatolik", session_id
        )
