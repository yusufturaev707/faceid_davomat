"""Bot kirish nuqtasi (entry point)."""
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import config
from handlers import setup_routers
from services.backend_client import backend

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    """Telegram buyruqlar menyusini (ko'k 'Menu' tugmasi) sozlaydi."""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="stat", description="📊 Statistikani ko'rsatish"),
        BotCommand(command="refresh", description="🔄 Ma'lumotlarni yangilash"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    if not config.bot_token:
        raise RuntimeError("BOT_TOKEN .env faylida ko'rsatilmagan!")
    if not config.api_key:
        logger.warning(
            "API_KEY .env da ko'rsatilmagan — backend so'rovlari 401 qaytarishi mumkin!"
        )

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    setup_routers(dp)

    # Backend HTTP klientini ishga tushirish (bot ishlash davomida qayta ishlatiladi).
    await backend.start()

    await set_commands(bot)
    logger.info("Bot ishga tushdi. Backend: %s", config.api_base_url)
    await bot.delete_webhook(drop_pending_updates=True)
    try:
        await dp.start_polling(bot)
    finally:
        await backend.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi")
