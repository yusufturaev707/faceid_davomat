"""Bot handlerlari — Davomat Mini App'ga yo'naltirish.

Test tadbirlari, statistika, kelmaganlar ro'yxati, Face ID, davomatdan olib
tashlash va chetlatish — hammasi Mini App ichida (frontend `src/miniapp`,
backend `/api/v1/davomat-miniapp`). Bot vazifasi:
  - `/start`, `/menu` — ruxsatni tekshirib, ilovani ochish tugmasini berish;
  - chat tarixidagi eski inline tugmalar bosilsa — ilovaga yo'naltirish;
  - boshqa har qanday xabarga — ilovani ochish tugmasi.
"""

from __future__ import annotations

import html
import logging

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import CallbackQuery, Message

from keyboards.inline import open_app_kb
from services.api_client import ApiError, api_client

logger = logging.getLogger(__name__)
router = Router(name="common")

_APP_HINT = (
    "📱 Davomat, Face ID, davomatdan olib tashlash va chetlatish endi "
    "<b>Davomat ilovasida</b> bajariladi.\n\n"
    "Quyidagi tugmani bosing yoki chat pastidagi <b>«Davomat»</b> menyusidan oching."
)


async def _send_entry(message: Message, telegram_id: int) -> None:
    """Ruxsatni tekshirib, salomlashish + ilovani ochish tugmasini yuborish."""
    try:
        resp = await api_client.check_access(telegram_id)
    except ApiError as e:
        logger.error("check_access error: %s %s", e.status, e.detail)
        await message.answer("⚠️ Server bilan bog'lanib bo'lmadi. Keyinroq urinib ko'ring.")
        return
    except Exception as e:
        logger.exception("check_access unexpected: %s", e)
        await message.answer("⚠️ Kutilmagan xatolik. Keyinroq urinib ko'ring.")
        return

    if not resp.get("allowed"):
        msg = resp.get("message") or "Sizga botdan foydalanish ruxsati berilmagan"
        await message.answer(
            f"⛔ {html.escape(msg)}\n\n"
            f"🆔 Telegram ID: <code>{telegram_id}</code>\n"
            "Shu raqamni administratorga yuboring."
        )
        return

    user = resp.get("user") or {}
    fio = html.escape(user.get("fio") or "Foydalanuvchi")
    regions = ", ".join(
        html.escape(r.get("name") or "") for r in user.get("regions") or []
    ) or "—"
    await message.answer(
        f"👋 <b>Assalomu alaykum, {fio}!</b>\n\n"
        f"🏠 <b>Biriktirilgan viloyatlar:</b> {regions}\n\n"
        f"{_APP_HINT}",
        reply_markup=open_app_kb(),
    )


@router.message(CommandStart())
@router.message(Command("menu"))
async def cmd_start(message: Message) -> None:
    if message.from_user is None:
        return
    await _send_entry(message, message.from_user.id)


@router.callback_query()
async def legacy_button(cb: CallbackQuery) -> None:
    """Mini App'dan oldingi xabarlardagi inline tugmalar — endi ishlamaydi."""
    await cb.answer(
        "Bu tugma eskirgan. Barcha amallar endi Davomat ilovasida.",
        show_alert=True,
    )
    if cb.message is not None:
        await cb.message.answer(_APP_HINT, reply_markup=open_app_kb())


@router.message()
async def fallback(message: Message) -> None:
    await message.answer(_APP_HINT, reply_markup=open_app_kb())
