"""Admin paneli — `davomat_bots` (Telegram bot foydalanuvchilari) CRUD.

Validatsiya qoidasi (`role.key`):
  - `key == 4` → aniq 1 ta region biriktirilishi mumkin.
  - Boshqa key (1/2/3) → 1+ ta region biriktirilishi mumkin.

Permissionlar: USER_* (foydalanuvchilarni boshqarish bilan teng huquq).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.permissions import P
from app.crud import davomat_bot as crud
from app.crud.davomat_bot import DavomatBotError
from app.dependencies import PermissionChecker, get_db
from app.models.davomat_bot import DavomatBot
from app.models.user import User
from app.schemas.davomat_bot import (
    DavomatBotAdminRegion,
    DavomatBotAdminResponse,
    DavomatBotCreateRequest,
    DavomatBotUpdateRequest,
)


router = APIRouter()


_READ = PermissionChecker(P.DAVOMAT_BOT_READ.code)
_CREATE = PermissionChecker(P.DAVOMAT_BOT_CREATE.code)
_UPDATE = PermissionChecker(P.DAVOMAT_BOT_UPDATE.code)
_DELETE = PermissionChecker(P.DAVOMAT_BOT_DELETE.code)


def _to_response(bot: DavomatBot) -> DavomatBotAdminResponse:
    regions: list[DavomatBotAdminRegion] = []
    region_ids: list[int] = []
    for r in bot.regions:
        if r.region:
            regions.append(
                DavomatBotAdminRegion(
                    id=int(r.region.id),
                    name=r.region.name or "",
                    number=int(r.region.number or 0),
                )
            )
            region_ids.append(int(r.region.id))
    return DavomatBotAdminResponse(
        id=int(bot.id),
        fio=bot.fio,
        telegram_id=int(bot.telegram_id),
        role_id=int(bot.role_id) if bot.role_id else None,
        role=bot.role_ref.name if bot.role_ref else "",
        role_key=int(bot.role_ref.key or 0) if bot.role_ref else 0,
        is_active=bool(bot.is_active),
        regions=regions,
        region_ids=sorted(region_ids),
        created_at=bot.created_at,
        updated_at=bot.updated_at,
    )


@router.get("", response_model=list[DavomatBotAdminResponse])
def list_davomat_bots(
    db: Session = Depends(get_db),
    _user: User = Depends(_READ),
):
    """Barcha bot foydalanuvchilari ro'yxati."""
    return [_to_response(b) for b in crud.list_bots(db)]


@router.post("", response_model=DavomatBotAdminResponse, status_code=201)
def create_davomat_bot(
    body: DavomatBotCreateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_CREATE),
):
    """Yangi bot foydalanuvchisi yaratish + regionlar biriktirish.

    Validatsiya:
      - Telegram ID unique.
      - `role.key == 4` → aniq 1 ta region.
      - Boshqa rollar → 1+ ta region.
    """
    try:
        bot = crud.create_bot(db, body)
    except DavomatBotError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return _to_response(bot)


@router.patch("/{bot_id}", response_model=DavomatBotAdminResponse)
def update_davomat_bot(
    bot_id: int,
    body: DavomatBotUpdateRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(_UPDATE),
):
    """Bot foydalanuvchisi yozuvini yangilash (qisman update)."""
    try:
        bot = crud.update_bot(db, bot_id, body)
    except DavomatBotError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if bot is None:
        raise HTTPException(status_code=404, detail="Bot foydalanuvchisi topilmadi")
    return _to_response(bot)


@router.delete("/{bot_id}", status_code=204)
def delete_davomat_bot(
    bot_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(_DELETE),
):
    """Bot foydalanuvchisini o'chirish (regionlar cascade orqali tushadi)."""
    ok = crud.delete_bot(db, bot_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Bot foydalanuvchisi topilmadi")
