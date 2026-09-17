"""Davomat bot entrypoint (aiogram 3).

Bot — Davomat Mini App'ga kirish nuqtasi: barcha amallar ilova ichida.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllPrivateChats,
    MenuButtonWebApp,
    WebAppInfo,
)

from config import settings
from handlers import get_main_router
from services.api_client import api_client


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    )


# Telegram chat'idagi "Menu" tugmasi orqali ko'rinadigan komandalar.
BOT_COMMANDS: list[BotCommand] = [
    BotCommand(command="start", description="Davomat ilovasini ochish"),
]


async def _setup_bot_ui(bot: Bot) -> None:
    """Komandalar va chat pastidagi menyu tugmasi (idempotent).

    Menyu tugmasi barcha foydalanuvchilar uchun Mini App'ni ochadi — ruxsat
    ilova ichida (`/davomat-miniapp/me`) tekshiriladi, ruxsatsiz foydalanuvchi
    o'z Telegram ID'sini ko'radi.
    """
    await bot.set_my_commands(BOT_COMMANDS, scope=BotCommandScopeAllPrivateChats())
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(
            text="Davomat",
            web_app=WebAppInfo(url=settings.WEBAPP_URL),
        )
    )


async def main() -> None:
    _setup_logging()
    logger = logging.getLogger("davomat_bot")

    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(get_main_router())

    await api_client.start()
    try:
        logger.info("Davomat bot ishga tushdi (long polling), Mini App: %s", settings.WEBAPP_URL)
        await bot.delete_webhook(drop_pending_updates=True)
        await _setup_bot_ui(bot)
        await dp.start_polling(bot)
    finally:
        await api_client.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
