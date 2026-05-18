"""Bot handler routerlarini yig'ish."""

from aiogram import Router

from handlers import cheat, common, davomat, faceid, remove


def get_main_router() -> Router:
    """Barcha handler routerlarni bitta umumiy `Router`ga ulash."""
    router = Router(name="main")
    router.include_router(common.router)
    router.include_router(davomat.router)
    router.include_router(faceid.router)
    router.include_router(remove.router)
    router.include_router(cheat.router)
    return router
