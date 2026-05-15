"""GTSP API client — reusable wrapper for fetching student photo + FIO.

GTSP returns `{"status": 1, "data": {"sname", "fname", "mname", "photo", "sex"}}`
for a successful lookup. We expose a small dataclass result so callers don't
need to deal with raw dicts, and a single timeout-aware fetch function that
both the per-student endpoint and the bulk Excel-loader task can use.
"""

from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger("faceid.services.gtsp_client")


class GtspNotConfigured(Exception):
    """`settings.API_GTSP` bo'sh — admin'ga sozlash kerakligini bildiramiz."""


class GtspError(Exception):
    """GTSP API muvaffaqiyatsiz javob qaytardi (status != 1, network, parsing)."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class GtspResult:
    last_name: str | None
    first_name: str | None
    middle_name: str | None
    photo: bytes | None
    sex: int | None  # 1=erkak, 2=ayol, boshqa=None


def _decode_photo(val: object) -> bytes | None:
    """base64 string (yoki data URI) → bytes. Xato bo'lsa None."""
    if not val:
        return None
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if not isinstance(val, str):
        return None
    try:
        if "," in val and val.index(",") < 80:
            val = val.split(",", 1)[1]
        return base64.b64decode(val)
    except Exception:
        return None


def fetch_gtsp_data(
    imei: str | None,
    ps_value: str,
    *,
    timeout: float = 10.0,
) -> GtspResult:
    """Bitta student uchun GTSP API ni chaqirish.

    Args:
        imei: Student IMEI (URL formatlash uchun, bo'sh bo'lsa "").
        ps_value: Passport bo'limi+raqami, masalan "AD1234567".
        timeout: HTTP timeout (sekund).

    Raises:
        GtspNotConfigured: API_GTSP sozlanmagan.
        GtspError: API status != 1 yoki tarmoq xatosi.

    Returns:
        GtspResult — FIO + photo bytes + sex.
    """
    if not settings.API_GTSP:
        raise GtspNotConfigured("API_GTSP sozlamasi topilmadi")

    url = settings.API_GTSP.format(imei or "", ps_value)
    try:
        with httpx.Client(timeout=timeout, verify=False) as client:
            resp = client.get(url)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        raise GtspError(
            f"GTSP HTTP xatolik: {e.response.status_code}", retryable=True
        ) from e
    except httpx.RequestError as e:
        raise GtspError(f"GTSP ulanish xatolik: {e}", retryable=True) from e
    except ValueError as e:  # JSON parse
        raise GtspError(f"GTSP javob noto'g'ri: {e}") from e

    if result.get("status") != 1:
        msg = (result.get("data") or {}).get("message") or "Noma'lum xatolik"
        raise GtspError(f"GTSP: {msg}")

    data = result.get("data") or {}
    return GtspResult(
        last_name=(data.get("sname") or None),
        first_name=(data.get("fname") or None),
        middle_name=(data.get("mname") or None),
        photo=_decode_photo(data.get("photo")),
        sex=data.get("sex") if isinstance(data.get("sex"), int) else None,
    )
