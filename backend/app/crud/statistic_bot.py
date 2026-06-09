"""CRUD operatsiyalar — `StatisticBot` jadvali (statistika bot foydalanuvchilari).

Bot tomonida `get_bot_by_telegram_id` ishlatiladi (faqat aktiv yozuv).
Admin paneli: list/create/update/delete.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.statistic_bot import StatisticBot
from app.schemas.statistic_bot import (
    StatisticBotCreateRequest,
    StatisticBotUpdateRequest,
)


class StatisticBotError(ValueError):
    """Validatsiya yoki business-rule xatoligi (HTTP 400 ga aylanadi)."""


def get_bot_by_telegram_id(db: Session, telegram_id: int) -> StatisticBot | None:
    """Telegram ID bo'yicha aktiv (status=True) bot foydalanuvchisini olish."""
    stmt = select(StatisticBot).where(
        StatisticBot.telegram_id == telegram_id,
        StatisticBot.status.is_(True),
    )
    return db.execute(stmt).scalar_one_or_none()


def list_bots(db: Session) -> list[StatisticBot]:
    stmt = select(StatisticBot).order_by(StatisticBot.id.desc())
    return list(db.execute(stmt).scalars().all())


def create_bot(db: Session, body: StatisticBotCreateRequest) -> StatisticBot:
    existing = db.execute(
        select(StatisticBot.id).where(StatisticBot.telegram_id == body.telegram_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise StatisticBotError("Bu Telegram ID allaqachon ro'yxatdan o'tgan")

    bot = StatisticBot(
        fio=body.fio.strip(),
        telegram_id=int(body.telegram_id),
        role=int(body.role),
        status=bool(body.status),
    )
    db.add(bot)
    db.commit()
    db.refresh(bot)
    return bot


def update_bot(
    db: Session, bot_id: int, body: StatisticBotUpdateRequest
) -> StatisticBot | None:
    bot = db.get(StatisticBot, bot_id)
    if bot is None:
        return None

    if body.telegram_id is not None and int(body.telegram_id) != int(bot.telegram_id):
        existing = db.execute(
            select(StatisticBot.id).where(
                StatisticBot.telegram_id == body.telegram_id,
                StatisticBot.id != bot.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise StatisticBotError("Bu Telegram ID boshqa foydalanuvchida bor")
        bot.telegram_id = int(body.telegram_id)

    if body.fio is not None:
        bot.fio = body.fio.strip()
    if body.role is not None:
        bot.role = int(body.role)
    if body.status is not None:
        bot.status = bool(body.status)

    db.commit()
    db.refresh(bot)
    return bot


def delete_bot(db: Session, bot_id: int) -> bool:
    bot = db.get(StatisticBot, bot_id)
    if bot is None:
        return False
    db.delete(bot)
    db.commit()
    return True
