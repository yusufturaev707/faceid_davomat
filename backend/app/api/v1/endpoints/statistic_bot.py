"""Telegram `statistic_bot` uchun endpointlar + Qabul-2026 dashboard.

Bot backend ga `X-API-Key` orqali kiradi (boshqa endpointlar bilan bir xil
autentifikatsiya). Quyidagi flow:
  1. `/check/{telegram_id}` — ruxsat va rol (DB dan).
  2. `/statistics` — backend tashqi APIdan statistikani oladi (kesh bilan)
     va xom hudud ro'yxatini qaytaradi. Bot uni o'z formatteri bilan
     chiroyli matnga aylantiradi.
  3. `/qabul` — aggregatlangan statistika (frontend dashboard uchun,
     `qabul:read` permission talab qilinadi). Joriy yil dinamik aniqlanadi.

Avval bot tashqi APIdan to'g'ridan-to'g'ri olardi — endi yagona manba shu
backend (`app.services.statistic_bot_stats`).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.crud.statistic_bot import get_bot_by_telegram_id
from app.dependencies import PermissionChecker, get_current_active_user, get_db
from app.models.statistic_bot import StatisticBot
from app.models.user import User
from app.schemas.statistic_bot import (
    QabulStats,
    StatBotAccessResponse,
    StatBotStatisticsResponse,
    StatBotUserResponse,
)
from app.services.statistic_bot_stats import (
    StatisticBotApiError,
    aggregate,
    fetch_statistics,
)

logger = logging.getLogger("faceid.api.statistic_bot")
router = APIRouter()


def _to_user_response(bot: StatisticBot) -> StatBotUserResponse:
    return StatBotUserResponse(
        id=int(bot.id),
        fio=bot.fio,
        telegram_id=int(bot.telegram_id),
        role=int(bot.role),
        role_name=bot.role_name,
        status=bool(bot.status),
        can_see_payment=bot.can_see_payment,
        can_see_prev_year=bot.can_see_prev_year,
    )


@router.get("/check/{telegram_id}", response_model=StatBotAccessResponse)
def check_access(
    telegram_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Telegram ID bo'yicha botga dostup va rolni tekshirish."""
    bot = get_bot_by_telegram_id(db, telegram_id)
    if bot is None:
        return StatBotAccessResponse(
            allowed=False,
            message="Siz ro'yxatda yo'qsiz yoki bloklangansiz",
        )
    return StatBotAccessResponse(allowed=True, user=_to_user_response(bot))


@router.get("/statistics", response_model=StatBotStatisticsResponse)
def get_statistics(
    force: bool = Query(default=False, description="Keshni e'tiborsiz qoldirib qayta olish"),
    _user: User = Depends(get_current_active_user),
):
    """Tashqi APIdan xom statistikani olish (bot uchun)."""
    try:
        data, fetched_at = fetch_statistics(force=force)
    except StatisticBotApiError as e:
        logger.warning("Statistika olishda xatolik: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    return StatBotStatisticsResponse(data=data, fetched_at=fetched_at)


@router.get("/qabul", response_model=QabulStats)
def get_qabul(
    force: bool = Query(default=False, description="Keshni e'tiborsiz qoldirib qayta olish"),
    _user: User = Depends(PermissionChecker(P.QABUL_READ.code)),
):
    """Qabul dashboard uchun aggregatlangan realtime statistika.

    Joriy yil ma'lumotdan dinamik aniqlanadi (`year`/`prev_year` javobda).
    """
    try:
        data, fetched_at = fetch_statistics(force=force)
    except StatisticBotApiError as e:
        logger.warning("Qabul statistikasi olishda xatolik: %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    return aggregate(data, fetched_at=fetched_at)
