"""Tashqi statistika API bilan ishlovchi klient (kesh bilan)."""
from __future__ import annotations

import logging
import time

import aiohttp

from config import config

logger = logging.getLogger(__name__)


class StatisticsAPIError(Exception):
    """API javobi noto'g'ri yoki muvaffaqiyatsiz bo'lganda."""


# Oddiy xotira keshi: API'ni har bosishda emas, CACHE_TTL soniyada bir bor so'raymiz.
_cache: dict = {"data": None, "ts": 0.0}


async def _request() -> list[dict]:
    if not config.api_url:
        raise StatisticsAPIError("API_URL .env faylida ko'rsatilmagan")

    # Server http -> https ga 301 redirect qiladi. Redirect paytida aiohttp
    # xavfsizlik uchun Authorization header'ni tashlab yuboradi va natijada 403 keladi.
    # Shuning uchun http manzilni darhol https ga ko'taramiz (header saqlanib qoladi).
    url = config.api_url
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    headers = {"Accept": "application/json"}
    if config.api_token:
        # API xom (raw) tokenni kutadi — "Bearer " prefiksisiz.
        headers["Authorization"] = config.api_token

    timeout = aiohttp.ClientTimeout(total=30)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            payload = await resp.json()

    if not payload.get("success"):
        raise StatisticsAPIError("API success=false qaytardi")

    body = payload.get("body") or {}
    data = body.get("data")
    if not isinstance(data, list):
        raise StatisticsAPIError("API javobida 'data' ro'yxati topilmadi")

    return data


async def fetch_statistics(force: bool = False) -> list[dict]:
    """Statistikani oladi. force=False bo'lsa kesh muddati ichida keshdan beradi."""
    if not force and _cache["data"] is not None and (time.time() - _cache["ts"]) < config.cache_ttl:
        logger.debug("Statistika keshdan olindi")
        return _cache["data"]

    data = await _request()
    _cache["data"] = data
    _cache["ts"] = time.time()
    logger.info("Statistika API'dan yangilandi: %d ta hudud", len(data))
    return data


def get_cached() -> list[dict] | None:
    """Oxirgi keshlangan ma'lumotni qaytaradi (muddatidan qat'i nazar)."""
    return _cache["data"]
