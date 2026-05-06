"""Failed login audit CRUD.

Yozish best-effort: DB xatosi auth pipeline'ni to'xtatmasligi kerak.
Cleanup Celery beat orqali (90 kundan eski yozuvlar o'chiriladi).
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.failed_login_attempt import FailedLoginAttempt

logger = logging.getLogger("faceid.crud.failed_login")

_RETENTION_DAYS = 90
_USERNAME_MAX = 50
_UA_MAX = 500


def record_failed_login(
    db: Session,
    username: str,
    ip_address: str,
    user_agent: str | None,
    reason: str,
) -> None:
    """DB ga failed urinishni yozish. Xato bo'lsa pipeline'ni buzmaymiz."""
    try:
        row = FailedLoginAttempt(
            username=(username or "")[:_USERNAME_MAX],
            ip_address=ip_address[:45] if ip_address else "unknown",
            user_agent=(user_agent or None) and user_agent[:_UA_MAX],
            reason=reason,
        )
        db.add(row)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed login audit yozish xatoligi")


def get_failed_attempts(
    db: Session,
    username: str | None = None,
    since: datetime | None = None,
    limit: int = 100,
) -> list[FailedLoginAttempt]:
    """Audit so'rovi (admin uchun)."""
    stmt = select(FailedLoginAttempt).order_by(FailedLoginAttempt.attempted_at.desc())
    if username:
        stmt = stmt.where(FailedLoginAttempt.username == username)
    if since:
        stmt = stmt.where(FailedLoginAttempt.attempted_at >= since)
    return list(db.execute(stmt.limit(limit)).scalars().all())


def count_failed_attempts(
    db: Session,
    username: str | None = None,
    since: datetime | None = None,
) -> int:
    stmt = select(func.count(FailedLoginAttempt.id))
    if username:
        stmt = stmt.where(FailedLoginAttempt.username == username)
    if since:
        stmt = stmt.where(FailedLoginAttempt.attempted_at >= since)
    return int(db.execute(stmt).scalar_one() or 0)


def cleanup_old_attempts(db: Session, retention_days: int = _RETENTION_DAYS) -> int:
    """Eski yozuvlarni o'chirish (Celery beat har kun chaqiradi)."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = db.execute(
        delete(FailedLoginAttempt).where(FailedLoginAttempt.attempted_at < cutoff)
    )
    db.commit()
    return result.rowcount or 0
