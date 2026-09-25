"""Proctoring API client — kompyuterlar ro'yxati va nomzodni bron qilish.

Proctoring (Django/DRF) javoblari konvertda keladi:
`{"success": bool, "data": ..., "error": {"code", "message", "details"}}`.
Bu modul konvertni ochadi va xatoni ikki turga ajratadi — chaqiruvchi
uchun ular BOSHQA-BOSHQA qaror:

    ProctoringError(retryable=True)   - tarmoq, timeout, 5xx: Celery qayta
                                        uradi (bron yo'qolmasligi kerak);
    ProctoringError(retryable=False)  - 4xx: joy band, kompyuter topilmadi,
                                        nomzod imtihonda — qayta urish
                                        natijani o'zgartirmaydi.

Bino ikki tizimda TASHQI raqamlar bilan bog'lanadi: FaceID `regions.number`
= Proctoring `region.dtm_id`, `zone.number` = `zone.number`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger("faceid.services.proctoring_client")


class ProctoringNotConfigured(Exception):
    """`PROCTORING_API_URL` yoki `PROCTORING_API_KEY` bo'sh."""


class ProctoringError(Exception):
    def __init__(
        self, message: str, *, code: str = "", status: int = 0, retryable: bool = False
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status = status
        self.retryable = retryable


@dataclass(frozen=True)
class ProctoringComputer:
    """Proctoring sessiyasidagi ISHCHI kompyuter (buzilgan va raqamsizlar kelmaydi)."""

    number: int
    region_number: int  # Proctoring `region.dtm_id` = FaceID `regions.number`
    zone_number: int
    zone_name: str
    is_booked: bool
    pinfl: str  # band bo'lsa kimga


def is_configured() -> bool:
    return bool(settings.PROCTORING_API_URL and settings.PROCTORING_API_KEY)


def _request(method: str, path: str, **kwargs):
    if not is_configured():
        raise ProctoringNotConfigured("Proctoring API sozlanmagan")
    url = settings.PROCTORING_API_URL.rstrip("/") + path
    headers = {"X-API-Key": settings.PROCTORING_API_KEY, "Accept": "application/json"}
    try:
        resp = httpx.request(
            method, url, headers=headers, timeout=settings.PROCTORING_TIMEOUT, **kwargs
        )
    except httpx.HTTPError as exc:
        raise ProctoringError(
            f"Proctoring bilan bog'lanib bo'lmadi: {exc.__class__.__name__}",
            retryable=True,
        ) from exc

    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400 or body.get("success") is False:
        error = body.get("error") or {}
        raise ProctoringError(
            error.get("message") or f"Proctoring xatosi (HTTP {resp.status_code})",
            code=error.get("code") or "",
            status=resp.status_code,
            # 5xx va 429 — vaqtinchalik; qolgan 4xx — qaror.
            retryable=resp.status_code >= 500 or resp.status_code == 429,
        )
    return body.get("data", body)


def list_schedules() -> list[dict]:
    """Ochiq (tugamagan) test sessiyalari — biriktirish formasidagi tanlov."""
    return _request("GET", "/integrations/faceid/schedules/")


def list_computers(schedule_id: int) -> list[ProctoringComputer]:
    data = _request("GET", f"/integrations/faceid/schedules/{int(schedule_id)}/computers/")
    return [
        ProctoringComputer(
            number=int(row["number"]),
            region_number=int(row["region_dtm_id"]),
            zone_number=int(row["zone_number"]),
            zone_name=row.get("zone_name") or "",
            is_booked=bool(row.get("is_booked")),
            pinfl=row.get("pinfl") or "",
        )
        for row in data.get("results", [])
    ]


def book(
    *, schedule_id: int, pinfl: str, region_number: int, zone_number: int, computer_number: int
) -> dict:
    """Nomzodni kompyuterga bron qiladi. Idempotent — takror so'rov o'sha bron."""
    return _request(
        "POST",
        "/integrations/faceid/book/",
        json={
            "schedule": int(schedule_id),
            "pinfl": pinfl,
            "region_dtm_id": int(region_number),
            "zone_number": int(zone_number),
            "computer_number": int(computer_number),
        },
    )
