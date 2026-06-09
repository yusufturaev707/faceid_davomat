"""Statistika buyruqlari va xabarlarini qayta ishlovchi handlerlar.

Dostup va rol backend DB dan olinadi (`/statistic-bot/check/...`), statistika
esa backend orqali tashqi APIdan keladi (`/statistic-bot/statistics`).

Rollar:
  - Admin (1) / Rahbar (2) → to'lov + 2025 ko'rinadi.
  - Xodim (3)              → to'lov va 2025 yashiriladi.
"""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from keyboards.menu import main_menu
from services.backend_client import BackendError, backend
from utils.formatter import format_summary, split_message

router = Router()
logger = logging.getLogger(__name__)


async def _get_access(message: Message) -> dict | None:
    """Backenddan dostupni tekshiradi. Ruxsat bo'lsa user dict, aks holda None."""
    try:
        result = await backend.check_access(message.from_user.id)
    except BackendError:
        logger.exception("Dostup tekshiruvida backend xatosi")
        await message.answer(
            "❗️ <b>Server bilan bog'lanishda xatolik.</b>\n"
            "Birozdan so'ng qayta urinib ko'ring."
        )
        return None

    if not result.get("allowed"):
        await message.answer(
            "⛔️ <b>Kechirasiz, siz ro'yxatda yo'qsiz.</b>\n\n"
            f"Sizning ID raqamingiz: <code>{message.from_user.id}</code>\n"
            "Ushbu raqamni administratorga yuboring."
        )
        return None

    return result.get("user") or {}


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    user = await _get_access(message)
    if user is None:
        return
    await message.answer(
        "👋 <b>Assalomu alaykum!</b>\n\n"
        "Bu botdan abituriyentlar ro'yxati bo'yicha statistikani olsa bo'ladi.\n"
        "Quyidagi tugma orqali eng so'nggi ma'lumotlarni oling 👇",
        reply_markup=main_menu(),
    )


@router.message(Command("stat"))
@router.message(F.text == "📊 Statistika")
async def show_statistics(message: Message) -> None:
    await _send_statistics(message, force=False)


@router.message(Command("refresh"))
@router.message(F.text == "🔄 Yangilash")
async def refresh_statistics(message: Message) -> None:
    await _send_statistics(message, force=True)


async def _send_statistics(message: Message, force: bool) -> None:
    user = await _get_access(message)
    if user is None:
        return

    status = await message.answer("⏳ <i>Ma'lumotlar yuklanmoqda...</i>")
    try:
        data = await backend.fetch_statistics(force=force)
    except BackendError:
        logger.exception("Statistikani olishda backend xatosi")
        await status.edit_text(
            "❗️ <b>Ma'lumotlarni olishda xatolik yuz berdi.</b>\n"
            "Birozdan so'ng qayta urinib ko'ring."
        )
        return

    if not data:
        await status.edit_text("📭 Hozircha statistika ma'lumotlari mavjud emas.")
        return

    # Admin/Rahbar → to'lov va o'tgan yil ko'rinadi; Xodim → yo'q.
    show_extra = bool(user.get("can_see_prev_year"))
    text = format_summary(data, show_prev=show_extra)
    chunks = split_message(text)

    await status.edit_text(chunks[0])
    for chunk in chunks[1:]:
        await message.answer(chunk)
