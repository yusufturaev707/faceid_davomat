from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
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
    base_filters = []
    if user_id is not None:
        base_filters.append(VerificationLog.user_id == user_id)
    if date_from is not None:
        base_filters.append(VerificationLog.timestamp >= date_from)
    if date_to is not None:
        base_filters.append(VerificationLog.timestamp <= date_to)

    query = (
        select(VerificationLog, User.username)
        .join(User, VerificationLog.user_id == User.id)
    )
    for f in base_filters:
        query = query.where(f)
    query = query.order_by(VerificationLog.timestamp.desc())

    # Umumiy son — order_by'siz, JOIN'siz, faqat asosiy jadvalda WHERE.
    count_query = select(func.count()).select_from(VerificationLog)
    for f in base_filters:
        count_query = count_query.where(f)
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
    """Dashboard uchun statistika.

    Performance: ilgari 30 kunlik chart har kun uchun alohida COUNT query
    chaqirardi (30 roundtrip). Endi total/today/week/success/unique 1 ta
    conditional aggregate query, daily chart 1 ta GROUP BY query — jami 2 ta.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    chart_start = today_start - timedelta(days=29)

    aggregate = db.execute(
        select(
            func.count().label("total"),
            func.count(case((VerificationLog.timestamp >= today_start, 1))).label("today"),
            func.count(case((VerificationLog.timestamp >= week_start, 1))).label("week"),
            func.count(case((VerificationLog.success == True, 1))).label("success"),  # noqa: E712
            func.count(func.distinct(VerificationLog.user_id)).label("unique_users"),
        )
    ).one()

    total = aggregate.total or 0
    today_count = aggregate.today or 0
    week_count = aggregate.week or 0
    success_count = aggregate.success or 0
    unique_users = aggregate.unique_users or 0

    success_rate = (success_count / total * 100) if total > 0 else 0.0

    # 30 kunlik chart — bitta GROUP BY query, default 0 bilan kunlar to'ldiriladi
    day_col = func.date_trunc("day", VerificationLog.timestamp).label("day")
    grouped = db.execute(
        select(day_col, func.count().label("cnt"))
        .where(VerificationLog.timestamp >= chart_start)
        .group_by(day_col)
    ).all()
    counts_by_date = {row.day.date(): row.cnt for row in grouped}

    daily_data = []
    for i in range(29, -1, -1):
        day = (today_start - timedelta(days=i)).date()
        daily_data.append(
            {"date": day.strftime("%Y-%m-%d"), "count": counts_by_date.get(day, 0)}
        )

    return {
        "total_verifications": total,
        "today_verifications": today_count,
        "week_verifications": week_count,
        "success_rate": round(success_rate, 1),
        "unique_users": unique_users,
        "daily_chart": daily_data,
    }
