from aiogram import Dispatcher

from .statistics import router as statistics_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(statistics_router)
