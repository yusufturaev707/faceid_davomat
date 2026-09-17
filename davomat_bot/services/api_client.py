"""Backend FastAPI bilan ishlash uchun HTTP client.

Bot so'rovlarni `X-API-Key` headeri orqali yuboradi — admin tomonidan
yaratilgan API key. Bot faqat `/start` da ruxsatni tekshiradi; qolgan barcha
amallarni Mini App o'zi backendga (`/davomat-miniapp`) yuboradi.
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class ApiClient:
    """Backend uchun yengil wrapper — bitta `aiohttp.ClientSession` qayta ishlatiladi."""

    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        # aiohttp `base_url` faqat origin (scheme+host+port) ni qabul qiladi.
        # Shuning uchun `/api/v1` kabi path qismni alohida ushlab turamiz.
        self._base_url: str = settings.API_BASE_URL.rstrip("/")

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=settings.REQUEST_TIMEOUT)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={"X-API-Key": settings.API_KEY},
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, path: str) -> Any:
        if self._session is None:
            await self.start()
        assert self._session is not None

        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._session.request(method, url) as resp:
            text = await resp.text()
            if resp.status >= 400:
                logger.warning("API %s %s → %d: %s", method, url, resp.status, text[:300])
                raise ApiError(resp.status, text)
            if not text:
                return None
            try:
                return await resp.json(content_type=None)
            except Exception:
                return text

    async def check_access(self, telegram_id: int) -> dict:
        return await self._request("GET", f"davomat-bot/check/{telegram_id}")


api_client = ApiClient()
