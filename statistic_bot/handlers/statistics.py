"""Statistika buyruqlari va xabarlarini qayta ishlovchi handlerlar."""
from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from config import config
from keyboards.menu import main_menu
from services.api_client import fetch_statistics
from utils.formatter import format_summary, split_message

router = Router()
logger = logging.getLogger(__name__)


def is_admin(user_id: int) -> bool:
    return user_id in config.admin_ids


async def _deny(message: Message) -> None:
    await message.answer(
        "⛔️ <b>Kechirasiz, siz ro'yxatda yo'qsiz.</b>\n\n"
        f"Sizning ID raqamingiz: <code>{message.from_user.id}</code>\n"
        "Ushbu raqamni administratorga yuboring."
    )


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await _deny(message)
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
    if not is_admin(message.from_user.id):
        await _deny(message)
        return

    status = await message.answer("⏳ <i>Ma'lumotlar yuklanmoqda...</i>")
    try:
        data = await fetch_statistics(force=force)
    except Exception:
        logger.exception("Statistikani olishda xatolik")
        await status.edit_text(
            "❗️ <b>Ma'lumotlarni olishda xatolik yuz berdi.</b>\n"
            "Birozdan so'ng qayta urinib ko'ring."
        )
        return

    if not data:
        await status.edit_text("📭 Hozircha statistika ma'lumotlari mavjud emas.")
        return

    text = format_summary(data)
    chunks = split_message(text)

    # Birinchi bo'lakni status xabarining o'zida yangilaymiz, qolganlarini ketma-ket yuboramiz.
    await status.edit_text(chunks[0])
    for chunk in chunks[1:]:
        await message.answer(chunk)
