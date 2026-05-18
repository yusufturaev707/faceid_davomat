"""Umumiy handlerlar: /start, /menu, "Bosh menyu" tugmasi, region tanlash,
orqaga qaytishlar.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import main_menu_kb, region_pick_kb
from services.api_client import ApiError, api_client
from services.user_state import clear_region, get_region, set_region
from utils.callbacks import BackCB, MainMenuCB, RegionPickCB
from utils.formatters import format_user_greeting

logger = logging.getLogger(__name__)
router = Router(name="common")


def _allowed_regions(user_payload: dict) -> list[dict]:
    """Bot profil javobidan barcha biriktirilgan regionlarni `[{id, name, number}, ...]`
    ko'rinishida qaytarish.
    """
    regions = user_payload.get("regions") or []
    out: list[dict] = []
    seen: set[int] = set()
    for r in regions:
        rid = int(r.get("id") or 0)
        if rid and rid not in seen:
            out.append(
                {
                    "id": rid,
                    "name": r.get("name") or "",
                    "number": int(r.get("number") or 0),
                }
            )
            seen.add(rid)
    return out


async def _fetch_profile(message: Message, telegram_id: int) -> dict | None:
    """Bot profilini olib qaytarish. Ruxsat yo'q yoki xatolik → None."""
    try:
        resp = await api_client.check_access(telegram_id)
    except ApiError as e:
        logger.error("check_access error: %s %s", e.status, e.detail)
        await message.answer(
            "⚠️ Server bilan bog'lanib bo'lmadi. Keyinroq urinib ko'ring."
        )
        return None
    except Exception as e:
        logger.exception("check_access unexpected: %s", e)
        await message.answer("⚠️ Kutilmagan xatolik. Keyinroq urinib ko'ring.")
        return None

    if not resp.get("allowed"):
        msg = resp.get("message") or "Sizga botdan foydalanish ruxsati berilmagan."
        await message.answer(f"⛔ {msg}")
        # Eski region tanlovini tozalash — boshqa user uchun bo'lishi mumkin emas,
        # lekin xavfsizlik uchun.
        clear_region(telegram_id)
        return None

    return resp.get("user") or {}


def _region_name(profile: dict, region_id: int | None) -> str:
    """Tanlangan region nomini topish (ko'rsatish uchun)."""
    if not region_id:
        return ""
    for r in profile.get("regions") or []:
        if int(r.get("id") or 0) == int(region_id):
            return r.get("name") or ""
    return ""


async def _send_main_menu(
    target: Message, profile: dict, telegram_id: int
) -> None:
    """Bosh menyuni yuborish — tanlangan region badge va kerakli tugmalar bilan."""
    fio = profile.get("fio") or "Foydalanuvchi"
    all_regions = _allowed_regions(profile)
    selected = get_region(telegram_id)
    selected_name = _region_name(profile, selected)

    text = format_user_greeting(fio, [r["name"] for r in all_regions])
    if selected_name:
        text += (
            f"📍 <b>Joriy region:</b> {selected_name}\n\n"
            "Endi <b>davomat amallari</b> tanlangan region kesimida bajariladi."
        )

    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_kb(can_change_region=len(all_regions) > 1),
    )


async def _ask_region(target: Message, profile: dict) -> None:
    """Region tanlash sahifasini yuborish (2+ region biriktirilgan holatda)."""
    fio = profile.get("fio") or "Foydalanuvchi"
    regions = _allowed_regions(profile)
    text = (
        f"👋 <b>Assalomu alaykum, {fio}!</b>\n\n"
        f"🌍 <b>Sizga biriktirilgan viloyatlar:</b> "
        f"{', '.join(r['name'] for r in regions)}\n\n"
        "📍 <b>Iltimos, qaysi region bo'yicha ishlamoqchi ekanligingizni "
        "tanlang:</b>\n\n"
        "<i>Tanlangan region kesimida davomat, statistika, Face ID va "
        "kelmaganlar ro'yxati ishlaydi. Keyin bosh menyudan istalgan vaqtda "
        "almashtirishingiz mumkin.</i>"
    )
    await target.answer(
        text,
        parse_mode="HTML",
        reply_markup=region_pick_kb(regions),
    )


async def _entry(message: Message, telegram_id: int) -> None:
    """Asosiy kirish nuqtasi — /start, /menu, "Bosh menyu" tugmasi.

    Logika:
      - check_access → ruxsat yo'q bo'lsa to'xtaymiz.
      - 0 region biriktirilgan → xato xabar.
      - 1 region → avtomatik tanlanadi, bosh menyu.
      - 2+ region → region tanlash sahifasi. Agar oldindan tanlangan va u
        joriy ruxsat etilgan ro'yxatda bor bo'lsa, to'g'ridan-to'g'ri bosh
        menyu (qulaylik uchun).
    """
    profile = await _fetch_profile(message, telegram_id)
    if profile is None:
        return

    regions = _allowed_regions(profile)
    if not regions:
        clear_region(telegram_id)
        await message.answer(
            "⛔ Sizga biriktirilgan region yo'q. Iltimos, administrator bilan "
            "bog'laning."
        )
        return

    region_ids = {r["id"] for r in regions}
    if len(regions) == 1:
        # Yagona region — avtomatik tanlanadi
        set_region(telegram_id, regions[0]["id"])
        await _send_main_menu(message, profile, telegram_id)
        return

    # 2+ region
    current = get_region(telegram_id)
    if current and current in region_ids:
        # Avval tanlagan, hali ham ruxsat etilgan — to'g'ridan-to'g'ri menyu
        await _send_main_menu(message, profile, telegram_id)
        return

    # Tanlanmagan yoki tanlovi endi ruxsat etilmagan — qayta tanlash
    clear_region(telegram_id)
    await _ask_region(message, profile)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is None:
        return
    await _entry(message, message.from_user.id)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    if message.from_user is None:
        return
    await _entry(message, message.from_user.id)


@router.callback_query(BackCB.filter(F.to == "main"))
async def back_to_main(cb: CallbackQuery, state: FSMContext) -> None:
    """Inline 'Bosh menyu' tugmasi — FSM tozalanadi, menyu yoki region pick yuboriladi."""
    await state.clear()
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    await _entry(cb.message, cb.from_user.id)  # type: ignore[arg-type]


@router.callback_query(MainMenuCB.filter(F.action == "change_region"))
async def change_region(cb: CallbackQuery, state: FSMContext) -> None:
    """Bosh menyudagi "Regionni almashtirish" tugmasi — yana tanlash sahifasi."""
    await state.clear()
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return
    profile = await _fetch_profile(cb.message, cb.from_user.id)  # type: ignore[arg-type]
    if profile is None:
        return
    regions = _allowed_regions(profile)
    if len(regions) <= 1:
        # Yagona region — almashtirish mantiqsiz, bosh menyu
        if regions:
            set_region(cb.from_user.id, regions[0]["id"])
        await _send_main_menu(cb.message, profile, cb.from_user.id)  # type: ignore[arg-type]
        return
    await _ask_region(cb.message, profile)  # type: ignore[arg-type]


@router.callback_query(RegionPickCB.filter())
async def region_picked(
    cb: CallbackQuery, callback_data: RegionPickCB, state: FSMContext
) -> None:
    """Region tanlandi — saqlaymiz, bosh menyu ko'rsatamiz."""
    await state.clear()
    await cb.answer()
    if cb.from_user is None or cb.message is None:
        return

    profile = await _fetch_profile(cb.message, cb.from_user.id)  # type: ignore[arg-type]
    if profile is None:
        return

    region_ids = {r["id"] for r in _allowed_regions(profile)}
    if callback_data.region_id not in region_ids:
        await cb.message.answer(  # type: ignore[union-attr]
            "⚠️ Tanlangan region sizga ruxsat etilmagan. Qayta urinib ko'ring."
        )
        await _ask_region(cb.message, profile)  # type: ignore[arg-type]
        return

    set_region(cb.from_user.id, callback_data.region_id)
    await _send_main_menu(cb.message, profile, cb.from_user.id)  # type: ignore[arg-type]
