"""Periodic cleanup tasklari — Celery beat orqali ishga tushadi."""

import logging
from datetime import datetime, timezone

from sqlalchemy import delete, or_

from app.celery_app import celery_app
from app.crud.failed_login_attempt import cleanup_old_attempts
from app.db.session import SessionLocal
from app.models.refresh_token import RefreshToken

logger = logging.getLogger("faceid.tasks.cleanup")


@celery_app.task(
    name="tasks.cleanup_refresh_tokens",
    queue="storage",
    ignore_result=True,
)
def cleanup_refresh_tokens() -> dict:
    """Eskirgan va revoke qilingan refresh tokenlarni DB dan o'chirish.

    Celery beat har soatda ishga tushiradi.

    Returns:
        {"deleted": int} — o'chirilgan rowlar soni.
    """
    db = SessionLocal()
    try:
        result = db.execute(
            delete(RefreshToken).where(
                or_(
                    RefreshToken.revoked.is_(True),
                    RefreshToken.expires_at < datetime.now(timezone.utc),
                )
            )
        )
        deleted = result.rowcount or 0
        db.commit()
        logger.info("Refresh token cleanup: %d row(s) deleted", deleted)
        return {"deleted": deleted}
    except Exception:
        db.rollback()
        logger.exception("Refresh token cleanup xatoligi")
        raise
    finally:
        db.close()


@celery_app.task(
    name="tasks.cleanup_failed_logins",
    queue="storage",
    ignore_result=True,
)
def cleanup_failed_logins() -> dict:
    """90 kundan eski failed login audit yozuvlarini o'chirish.

    Celery beat har kunda ishga tushiradi.
    """
    db = SessionLocal()
    try:
        deleted = cleanup_old_attempts(db, retention_days=90)
        logger.info("Failed login audit cleanup: %d row(s) deleted", deleted)
        return {"deleted": deleted}
    except Exception:
        db.rollback()
        logger.exception("Failed login cleanup xatoligi")
        raise
    finally:
        db.close()
