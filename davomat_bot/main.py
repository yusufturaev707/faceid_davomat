"""Davomat bot entrypoint (aiogram 3)."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeAllPrivateChats

from config import settings
from handlers import get_main_router
from services.api_client import api_client


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


# Telegram chat'idagi "Menu" tugmasi orqali ko'rinadigan komandalar.
# `description` matnlari bir nechta xil tilda ko'rsatilishi mumkin
# (`BotCommandScopeAllPrivateChats` faqat shaxsiy chatlar uchun).
BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Botni qayta ishga tushirish"),
    BotCommand(command="menu", description="Bosh menyuga qaytish"),
]


async def _set_bot_commands(bot: Bot) -> None:
    """Bot komandalarini Telegram tomonida o'rnatish (idempotent)."""
    await bot.set_my_commands(
        BOT_COMMANDS,
        scope=BotCommandScopeAllPrivateChats(),
    )


async def main() -> None:
    _setup_logging()
    logger = logging.getLogger("davomat_bot")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(get_main_router())

    await api_client.start()
    try:
        logger.info("Davomat bot ishga tushdi (long polling)")
        await bot.delete_webhook(drop_pending_updates=True)
        await _set_bot_commands(bot)
        await dp.start_polling(bot)
    finally:
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
