"""Tarmoq aloqasini tekshirish uchun yengil health-check endpointlari.

Bu endpointlar `/api/v1` prefiksi ostida turadi — desktop ilova (PyQt6)
`API_BASE_URL` sifatida `.../api/v1` ni ishlatadi, shuning uchun tarmoq
nazorati `base_url + /health` yoki `base_url + /healthcheck` ga so'rov
yuboradi. Auth, DB yoki tashqi xizmat TALAB QILMAYDI — maqsad faqat
serverga tarmoq aloqasi borligini tez (minimal javob bilan) tekshirish.

Root darajadagi `/health` (app.main) monitoring/infra uchun saqlanadi;
bular esa ilovaning API prefiksi ostidagi ekvivalenti.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"], summary="Health check (API v1)")
@router.get("/healthcheck", tags=["health"], summary="Health check (alias)")
def healthcheck() -> dict:
    """Yengil sog'liqni tekshirish — {"status": "ok"} qaytaradi.

    Tezkorlik uchun hech qanday I/O bajarmaydi (DB, tashqi so'rov yo'q)."""
    return {"status": "ok"}
