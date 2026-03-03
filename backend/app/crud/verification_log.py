from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.verification_log import VerificationLog


def get_logs_paginated(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[dict], int]:
    """Loglarni sahifalab olish. (items, total) qaytaradi."""
    query = (
        select(VerificationLog, User.username)
        .join(User, VerificationLog.user_id == User.id)
        .order_by(VerificationLog.timestamp.desc())
    )

    if user_id is not None:
        query = query.where(VerificationLog.user_id == user_id)
    if date_from is not None:
        query = query.where(VerificationLog.timestamp >= date_from)
    if date_to is not None:
        query = query.where(VerificationLog.timestamp <= date_to)

    # Umumiy son
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0

    # Sahifalash
    offset = (page - 1) * per_page
    rows = db.execute(query.offset(offset).limit(per_page)).all()

    items = []
    for log, username in rows:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "timestamp": log.timestamp.isoformat(),
            "success": log.success,
            "detection": log.detection,
            "image_width": log.image_width,
            "image_height": log.image_height,
            "file_size_bytes": log.file_size_bytes,
            "input_age": log.input_age,
            "back_color": log.back_color,
            "error_message": log.error_message,
            "image_path": log.image_path,
        })

    return items, total


def get_log_by_id(db: Session, log_id: int) -> dict | None:
    """Bitta logni ID bo'yicha olish."""
    row = db.execute(
        select(VerificationLog, User.username)
        .join(User, VerificationLog.user_id == User.id)
        .where(VerificationLog.id == log_id)
    ).first()
    if not row:
        return None
    log, username = row
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": username,
        "timestamp": log.timestamp.isoformat(),
        "success": log.success,
        "detection": log.detection,
        "image_width": log.image_width,
        "image_height": log.image_height,
        "file_size_bytes": log.file_size_bytes,
        "input_age": log.input_age,
        "back_color": log.back_color,
        "error_message": log.error_message,
        "image_path": log.image_path,
    }


def get_dashboard_stats(db: Session) -> dict:
    """Dashboard uchun statistika."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)

    total = db.execute(
        select(func.count()).select_from(VerificationLog)
    ).scalar() or 0

    today_count = db.execute(
        select(func.count()).select_from(VerificationLog)
        .where(VerificationLog.timestamp >= today_start)
    ).scalar() or 0

    week_count = db.execute(
        select(func.count()).select_from(VerificationLog)
        .where(VerificationLog.timestamp >= week_start)
    ).scalar() or 0

    success_count = db.execute(
        select(func.count()).select_from(VerificationLog)
        .where(VerificationLog.success == True)  # noqa: E712
    ).scalar() or 0

    success_rate = (success_count / total * 100) if total > 0 else 0.0

    unique_users = db.execute(
        select(func.count(func.distinct(VerificationLog.user_id)))
    ).scalar() or 0

    # Oxirgi 30 kunlik chart data
    daily_data = []
    for i in range(29, -1, -1):
        day = today_start - timedelta(days=i)
        next_day = day + timedelta(days=1)
        count = db.execute(
            select(func.count()).select_from(VerificationLog)
            .where(
                VerificationLog.timestamp >= day,
                VerificationLog.timestamp < next_day,
            )
        ).scalar() or 0
        daily_data.append({"date": day.strftime("%Y-%m-%d"), "count": count})

    return {
        "total_verifications": total,
        "today_verifications": today_count,
        "week_verifications": week_count,
        "success_rate": round(success_rate, 1),
        "unique_users": unique_users,
        "daily_chart": daily_data,
    }
