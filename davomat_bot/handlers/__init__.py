"""Bot handler routerlarini yig'ish."""

from aiogram import Router

from handlers import common


def get_main_router() -> Router:
    """Barcha handler routerlarni bitta umumiy `Router`ga ulash."""
    router = Router(name="main")
    router.include_router(common.router)
    return router
