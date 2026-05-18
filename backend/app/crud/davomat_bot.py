"""CRUD operatsiyalar — `DavomatBot` jadvali (telegram bot foydalanuvchilari).

Bot tomonida `get_bot_by_telegram_id` ishlatiladi (faqat aktiv yozuv).
Admin paneli: list/create/update/delete + region biriktirish.

Region biriktirish:
  - `regions` (M2M, `davomat_bot_regions` jadvali) — endi yagona manba.
  - Validatsiya `role.key` ga bog'liq: `key == 4` → aniq 1 ta region; aks
    holda 1+ ta region.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.davomat_bot import DavomatBot, DavomatBotRegion
from app.models.region import Region
from app.models.role import Role
from app.schemas.davomat_bot import (
    SINGLE_REGION_ROLE_KEY,
    DavomatBotCreateRequest,
    DavomatBotUpdateRequest,
)


class DavomatBotError(ValueError):
    """Validatsiya yoki business-rule xatoligi (HTTP 400 yoki 409 ga aylanadi)."""


def get_bot_by_telegram_id(db: Session, telegram_id: int) -> DavomatBot | None:
    """Telegram ID bo'yicha bot foydalanuvchisi yozuvini olish.

    `regions` selectin orqali bir queryda olinadi (ichida `region` joinedload).
    `unique()` zarur — collection ichida joined eager load bor (SQLAlchemy
    duplicate rows ehtimoli uchun majburlaydi). Faqat `is_active=True`.
    """
    stmt = (
        select(DavomatBot)
        .where(
            DavomatBot.telegram_id == telegram_id,
            DavomatBot.is_active.is_(True),
        )
        .options(selectinload(DavomatBot.regions).joinedload(DavomatBotRegion.region))
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def _load_full(db: Session, bot_id: int) -> DavomatBot | None:
    stmt = (
        select(DavomatBot)
        .where(DavomatBot.id == bot_id)
        .options(
            joinedload(DavomatBot.role_ref),
            selectinload(DavomatBot.regions).joinedload(DavomatBotRegion.region),
        )
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def list_bots(db: Session) -> list[DavomatBot]:
    stmt = (
        select(DavomatBot)
        .order_by(DavomatBot.id.desc())
        .options(
            joinedload(DavomatBot.role_ref),
            selectinload(DavomatBot.regions).joinedload(DavomatBotRegion.region),
        )
    )
    return list(db.execute(stmt).unique().scalars().all())


# ============================================================
# Admin: create / update / delete
# ============================================================


def _resolve_role_key(db: Session, role_id: int | None) -> int | None:
    if role_id is None:
        return None
    role = db.get(Role, role_id)
    if role is None:
        raise DavomatBotError("Rol topilmadi")
    return int(role.key or 0)


def _validate_regions(
    db: Session, region_ids: list[int], role_key: int | None
) -> list[int]:
    """`role_key` ga qarab region_ids ro'yxatini validatsiya qilish.

    Qaytadi: yagona, sortlangan ro'yxat. Xatolikda `DavomatBotError`.
    """
    if not region_ids:
        raise DavomatBotError("Kamida 1 ta region tanlanishi kerak")

    uniq = sorted({int(x) for x in region_ids})

    if role_key == SINGLE_REGION_ROLE_KEY and len(uniq) != 1:
        raise DavomatBotError(
            "Bu rol (key=4) uchun faqat 1 ta region biriktirilishi mumkin"
        )

    # Regionlar haqiqatan ham mavjudligini va aktivligini tekshirish
    existing = db.execute(
        select(Region.id).where(Region.id.in_(uniq), Region.is_active.is_(True))
    ).scalars().all()
    existing_set = set(int(x) for x in existing)
    missing = [r for r in uniq if r not in existing_set]
    if missing:
        raise DavomatBotError(
            f"Quyidagi regionlar topilmadi yoki aktiv emas: {missing}"
        )
    return uniq


def _sync_regions(
    db: Session, bot: DavomatBot, region_ids: list[int]
) -> None:
    """`bot.regions` ro'yxatini `region_ids` ga moslash (idempotent).

    Eskirgan yozuvlar `cascade=all, delete-orphan` orqali avtomatik
    o'chiriladi.
    """
    target = set(int(x) for x in region_ids)
    current = {int(r.region_id): r for r in bot.regions}

    # Yangi yo'q bo'lganlarni olib tashlash
    for rid, rec in list(current.items()):
        if rid not in target:
            bot.regions.remove(rec)

    # Yangilarni qo'shish
    for rid in target:
        if rid not in current:
            bot.regions.append(DavomatBotRegion(region_id=rid))


def create_bot(db: Session, body: DavomatBotCreateRequest) -> DavomatBot:
    # Telegram ID dublikat tekshiruvi
    existing = db.execute(
        select(DavomatBot.id).where(DavomatBot.telegram_id == body.telegram_id)
    ).scalar_one_or_none()
    if existing is not None:
        raise DavomatBotError("Bu Telegram ID allaqachon ro'yxatdan o'tgan")

    role_key = _resolve_role_key(db, body.role_id)
    region_ids = _validate_regions(db, body.region_ids, role_key)

    bot = DavomatBot(
        fio=body.fio.strip(),
        telegram_id=int(body.telegram_id),
        role_id=body.role_id,
        is_active=bool(body.is_active),
    )
    for rid in region_ids:
        bot.regions.append(DavomatBotRegion(region_id=rid))
    db.add(bot)
    db.commit()
    refreshed = _load_full(db, int(bot.id))
    assert refreshed is not None
    return refreshed


def update_bot(
    db: Session, bot_id: int, body: DavomatBotUpdateRequest
) -> DavomatBot | None:
    bot = _load_full(db, bot_id)
    if bot is None:
        return None

    # Telegram ID o'zgartirish — dublikat tekshiruvi
    if body.telegram_id is not None and int(body.telegram_id) != int(bot.telegram_id):
        existing = db.execute(
            select(DavomatBot.id).where(
                DavomatBot.telegram_id == body.telegram_id,
                DavomatBot.id != bot.id,
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise DavomatBotError("Bu Telegram ID boshqa foydalanuvchida bor")
        bot.telegram_id = int(body.telegram_id)

    if body.fio is not None:
        bot.fio = body.fio.strip()
    if body.is_active is not None:
        bot.is_active = bool(body.is_active)

    # Rol va regionlar — birga validatsiya, chunki cheklov `role_key` ga
    # bog'liq. Yangi role_id berilsa undan, aks holda joriy roldan foydalanamiz.
    new_role_id = body.role_id if "role_id" in body.model_fields_set else None
    role_changed = "role_id" in body.model_fields_set and new_role_id != bot.role_id
    if role_changed:
        # Yangi role_key — agar regionlar yuborilmagan bo'lsa, joriy
        # regionlarga qarshi validatsiya o'tkazamiz.
        future_role_key = _resolve_role_key(db, new_role_id)
    else:
        future_role_key = int(bot.role_key) if bot.role_ref else None

    if body.region_ids is not None:
        region_ids = _validate_regions(db, body.region_ids, future_role_key)
        _sync_regions(db, bot, region_ids)
    elif role_changed:
        # Rol o'zgardi-yu, regionlar yuborilmagan — joriy regionlar yangi
        # rol qoidasiga mosligini tekshiramiz.
        current_ids = sorted({int(r.region_id) for r in bot.regions})
        _validate_regions(db, current_ids, future_role_key)

    if role_changed:
        bot.role_id = new_role_id

    db.commit()
    refreshed = _load_full(db, int(bot.id))
    assert refreshed is not None
    return refreshed


def delete_bot(db: Session, bot_id: int) -> bool:
    bot = db.get(DavomatBot, bot_id)
    if bot is None:
        return False
    db.delete(bot)
    db.commit()
    return True
