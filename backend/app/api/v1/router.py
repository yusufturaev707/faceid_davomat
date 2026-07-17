from fastapi import APIRouter

from app.api.v1.endpoints import admin, auth, davomat_bot, davomat_bot_admin, embedding, health, lookup, online_users, pasport_info, permission, photo, result_analysis, statistic_bot, statistic_bot_admin, student, test_session

api_router = APIRouter()
# Health-check — desktop tarmoq nazorati shu prefiks (/api/v1) ostida so'rov
# yuboradi. Auth talab qilmaydi, eng yuqorida turadi.
api_router.include_router(health.router, tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(photo.router, prefix="/photo", tags=["photo"])
api_router.include_router(embedding.router, prefix="/embedding", tags=["embedding"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(
    online_users.router, prefix="/admin", tags=["admin", "online-users"]
)
api_router.include_router(
    test_session.router, prefix="/test-sessions", tags=["test-sessions"]
)
api_router.include_router(
    lookup.router, prefix="/lookup", tags=["lookup"]
)
api_router.include_router(
    student.router, prefix="/students", tags=["students"]
)
api_router.include_router(
    permission.router, prefix="/permissions", tags=["permissions"]
)
api_router.include_router(
    davomat_bot.router, prefix="/davomat-bot", tags=["davomat-bot"]
)
api_router.include_router(
    davomat_bot_admin.router,
    prefix="/admin/davomat-bots",
    tags=["admin", "davomat-bot"],
)
api_router.include_router(
    pasport_info.router, prefix="/pasport-info", tags=["pasport-info"]
)
api_router.include_router(
    statistic_bot.router, prefix="/statistic-bot", tags=["statistic-bot"]
)
api_router.include_router(
    statistic_bot_admin.router,
    prefix="/admin/statistic-bots",
    tags=["admin", "statistic-bot"],
)
api_router.include_router(
    result_analysis.router,
    prefix="/result-analysis",
    tags=["result-analysis"],
)
