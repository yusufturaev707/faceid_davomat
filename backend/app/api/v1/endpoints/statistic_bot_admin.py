"""Admin paneli — `statistic_bots` (Telegram statistika bot foydalanuvchilari) CRUD.

Rollar (`role` butun son):
  - 1 → Admin  (cheklov yo'q)
  - 2 → Rahbar (to'lov + 2025)
  - 3 → Xodim  (to'lov va 2025 yashiriladi)

Permissionlar: STATISTIC_BOT_*.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.crud import statistic_bot as crud
from app.crud.statistic_bot import StatisticBotError
from app.dependencies import PermissionChecker, get_db
from app.models.statistic_bot import StatisticBot
from app.models.user import User
from app.schemas.statistic_bot import (
    StatisticBotAdminResponse,
    StatisticBotCreateRequest,
    StatisticBotUpdateRequest,
)

router = APIRouter()

_READ = PermissionChecker(P.STATISTIC_BOT_READ.code)
_CREATE = PermissionChecker(P.STATISTIC_BOT_CREATE.code)
_UPDATE = PermissionChecker(P.STATISTIC_BOT_UPDATE.code)
_DELETE = PermissionChecker(P.STATISTIC_BOT_DELETE.code)


def _to_response(bot: StatisticBot) -> StatisticBotAdminResponse:
    return StatisticBotAdminResponse(
        id=int(bot.id),
        fio=bot.fio,
        telegram_id=int(bot.telegram_id),
        role=int(bot.role),
        role_name=bot.role_name,
        status=bool(bot.status),
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


@router.get("", response_model=list[StatisticBotAdminResponse])
def list_statistic_bots(
    db: Session = Depends(get_db),
    _user: User = Depends(_READ),
):
    """Barcha bot foydalanuvchilari ro'yxati."""
    return [_to_response(b) for b in crud.list_bots(db)]


@router.post("", response_model=StatisticBotAdminResponse, status_code=201)
def create_statistic_bot(
    body: StatisticBotCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_CREATE),
):
    """Yangi bot foydalanuvchisi yaratish."""
    try:
        bot = crud.create_bot(db, body)
    except StatisticBotError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(bot)


@router.patch("/{bot_id}", response_model=StatisticBotAdminResponse)
def update_statistic_bot(
    bot_id: int,
    body: StatisticBotUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_UPDATE),
):
    """Bot foydalanuvchisi yozuvini yangilash (qisman update)."""
    try:
        bot = crud.update_bot(db, bot_id, body)
    except StatisticBotError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if bot is None:
        raise HTTPException(status_code=404, detail="Bot foydalanuvchisi topilmadi")
    return _to_response(bot)


@router.delete("/{bot_id}", status_code=204)
def delete_statistic_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_DELETE),
):
    """Bot foydalanuvchisini o'chirish."""
    ok = crud.delete_bot(db, bot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bot foydalanuvchisi topilmadi")
