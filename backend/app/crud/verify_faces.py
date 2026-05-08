from datetime import datetime, timedelta, timezone

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.verify_faces import VerifyFaces


def get_face_logs_paginated(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    user_id: int | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> tuple[list[dict], int]:
    """Yuz solishtirish loglarini sahifalab olish."""
    base_filters = []
    if user_id is not None:
        base_filters.append(VerifyFaces.user_id == user_id)
    if date_from is not None:
        base_filters.append(VerifyFaces.timestamp >= date_from)
    if date_to is not None:
        base_filters.append(VerifyFaces.timestamp <= date_to)

    query = (
        select(VerifyFaces, User.username)
        .join(User, VerifyFaces.user_id == User.id)
    )
    for f in base_filters:
        query = query.where(f)
    query = query.order_by(VerifyFaces.timestamp.desc())

    count_query = select(func.count()).select_from(VerifyFaces)
    for f in base_filters:
        count_query = count_query.where(f)
    total = db.execute(count_query).scalar() or 0

    offset = (page - 1) * per_page
    rows = db.execute(query.offset(offset).limit(per_page)).all()

    items = []
    for log, username in rows:
        items.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": username,
            "timestamp": log.timestamp.isoformat(),
            "ps_img": log.ps_img,
            "lv_img": log.lv_img,
            "ps_file_size": log.ps_file_size,
            "lv_file_size": log.lv_file_size,
            "ps_width": log.ps_width,
            "ps_height": log.ps_height,
            "lv_width": log.lv_width,
            "lv_height": log.lv_height,
            "ps_detection": log.ps_detection,
            "lv_detection": log.lv_detection,
            "detection": log.detection,
            "response_time": log.response_time,
            "score": log.score,
            "thresh_score": log.thresh_score,
            "verified": log.verified,
            "error_message": log.error_message,
        })

    return items, total


def get_face_log_by_id(db: Session, log_id: int) -> dict | None:
    """Bitta yuz solishtirish logini olish."""
    row = db.execute(
        select(VerifyFaces, User.username)
        .join(User, VerifyFaces.user_id == User.id)
        .where(VerifyFaces.id == log_id)
    ).first()
    if not row:
        return None
    log, username = row
    return {
        "id": log.id,
        "user_id": log.user_id,
        "username": username,
        "timestamp": log.timestamp.isoformat(),
        "ps_img": log.ps_img,
        "lv_img": log.lv_img,
        "ps_file_size": log.ps_file_size,
        "lv_file_size": log.lv_file_size,
        "ps_width": log.ps_width,
        "ps_height": log.ps_height,
        "lv_width": log.lv_width,
        "lv_height": log.lv_height,
        "ps_detection": log.ps_detection,
        "lv_detection": log.lv_detection,
        "detection": log.detection,
        "response_time": log.response_time,
        "score": log.score,
        "thresh_score": log.thresh_score,
        "verified": log.verified,
        "error_message": log.error_message,
    }


def get_face_dashboard_stats(db: Session) -> dict:
    """Yuz solishtirish statistikasi.

    Performance: ilgari 30 kunlik chart har kun uchun alohida COUNT query
    chaqirardi (30 roundtrip). Endi total/today/week/verified/unique 1 ta
    conditional aggregate query, daily chart 1 ta GROUP BY query — jami 2 ta.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    chart_start = today_start - timedelta(days=29)

    aggregate = db.execute(
        select(
            func.count().label("total"),
            func.count(case((VerifyFaces.timestamp >= today_start, 1))).label("today"),
            func.count(case((VerifyFaces.timestamp >= week_start, 1))).label("week"),
            func.count(case((VerifyFaces.verified == True, 1))).label("verified"),  # noqa: E712
            func.count(func.distinct(VerifyFaces.user_id)).label("unique_users"),
        )
    ).one()

    total = aggregate.total or 0
    today_count = aggregate.today or 0
    week_count = aggregate.week or 0
    verified_count = aggregate.verified or 0
    unique_users = aggregate.unique_users or 0

    success_rate = (verified_count / total * 100) if total > 0 else 0.0

    day_col = func.date_trunc("day", VerifyFaces.timestamp).label("day")
    grouped = db.execute(
        select(day_col, func.count().label("cnt"))
        .where(VerifyFaces.timestamp >= chart_start)
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
