"""Celery task: Excel'dan studentlarni yuklash + GTSP boyitish.

Endpoint Excel byte'larni base64'da yuboradi (Redis broker JSON serializatsiya).
Task yakunlanganda sessiyani state.key=2 ("Yuklab olindi") ga o'tkazadi.
Xatolik bo'lsa state.key=1 (Yaratilgan) ga qaytaradi va Redis'ga
xato xabarini yozadi.
"""

from __future__ import annotations

import base64
import logging

from sqlalchemy import select

from app.celery_app import celery_app
from app.crud.test_session import STATE_KEY_LOADING, change_session_state
from app.db.session import SessionLocal
from app.models.session_state import SessionState
from app.models.test_session import TestSession
from app.services.excel_student_loader import (
    ExcelLoadError,
    _get_redis,
    _set_progress,
    load_students_from_excel,
)

logger = logging.getLogger("faceid.tasks.excel_loader")


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.load_students_from_excel",
    queue="storage",
    time_limit=3600,
    soft_time_limit=3540,
)
def excel_load_and_enrich_task(
    self,
    session_id: int,
    excel_b64: str,
    previous_state_id: int,
) -> dict:
    """Excel'dan yuklash + GTSP boyitish + state transition.

    Args:
        session_id: TestSession ID.
        excel_b64: Excel fayl base64'da.
        previous_state_id: Xato bo'lsa qaytarish kerak bo'lgan state ID.

    Returns:
        {"status": "completed" | "error", "inserted": int, ...}
    """
    logger.info("Excel loader task boshlandi: session_id=%d", session_id)
    db = SessionLocal()
    try:
        session = db.get(TestSession, session_id)
        if session is None:
            logger.error("TestSession #%d topilmadi", session_id)
            return {"status": "error", "message": "Sessiya topilmadi"}

        try:
            content = base64.b64decode(excel_b64)
        except Exception as e:
            return {"status": "error", "message": f"Excel dekod xatosi: {e}"}

        try:
            result = load_students_from_excel(db, session, content)
        except ExcelLoadError as e:
            logger.error("Session #%d: Excel xatosi — %s", session_id, e.message)
            _rollback_state(db, session_id, previous_state_id)
            return {"status": "error", "message": e.message}
        except Exception as e:  # noqa: BLE001
            logger.exception("Session #%d: kutilmagan xatolik", session_id)
            _rollback_state(db, session_id, previous_state_id)
            return {"status": "error", "message": f"Kutilmagan xatolik: {e}"}

        # Muvaffaqiyat — state.key=2 (Yuklab olindi) ga o'tkazamiz.
        target_state = db.execute(
            select(SessionState).where(SessionState.key == STATE_KEY_LOADING)
        ).scalar()
        if target_state is None:
            logger.error(
                "SessionState key=%d topilmadi — state o'zgartirilmadi",
                STATE_KEY_LOADING,
            )
        else:
            try:
                change_session_state(
                    db, session_id=session_id, new_state_id=int(target_state.id)
                )
            except Exception:
                logger.exception(
                    "Session #%d: state o'zgartirishda xatolik", session_id
                )

        logger.info(
            "Session #%d: Excel yuklash yakunlandi — %d student, %d GTSP ok, %d fail",
            session_id,
            result["inserted"],
            result["enriched"],
            result["failed"],
        )
        return {
            "status": "completed",
            "inserted": result["inserted"],
            "enriched": result["enriched"],
            "failed": result["failed"],
        }
    finally:
        db.close()


def _rollback_state(db, session_id: int, previous_state_id: int) -> None:
    """Xato bo'lganda sessiyani avvalgi state'iga qaytarish."""
    try:
        db.rollback()
    except Exception:
        pass
    try:
        change_session_state(
            db, session_id=session_id, new_state_id=previous_state_id
        )
        logger.info(
            "Session #%d: state %d ga qaytarildi", session_id, previous_state_id
        )
        # Progress'ni ham xato deb belgilab qo'yamiz
        r = _get_redis()
        _set_progress(
            r,
            session_id,
            current=0,
            total=0,
            status="error",
            message="Excel yuklashda xatolik — sessiya holati qaytarildi",
        )
    except Exception:
        logger.exception("Session #%d: state qaytarishda xatolik", session_id)
