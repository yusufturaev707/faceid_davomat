"""FaceID backend (FastAPI) bilan ishlovchi HTTP klient.

Bot barcha so'rovlarni `X-API-Key` headeri orqali yuboradi — admin tomonidan
yaratilgan API kalit. Bitta `aiohttp.ClientSession` bot ishlash davomida
qayta ishlatiladi.

Endpointlar:
  - GET `/statistic-bot/check/{telegram_id}` → dostup + rol.
  - GET `/statistic-bot/statistics`          → xom statistika (hududlar).
"""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from config import config

logger = logging.getLogger(__name__)


class BackendError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class BackendClient:
    def __init__(self) -> None:
        self._session: aiohttp.ClientSession | None = None
        self._base_url = config.api_base_url

    async def start(self) -> None:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=config.request_timeout)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "X-API-Key": config.api_key,
                    "Accept": "application/json",
                },
            )

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()

    async def _get(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        if self._session is None:
            await self.start()
        assert self._session is not None

        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._session.get(url, params=params) as resp:
            text = await resp.text()
            if resp.status >= 400:
                logger.warning("Backend GET %s → %d: %s", url, resp.status, text[:300])
                raise BackendError(resp.status, text)
            try:
                return await resp.json(content_type=None)
            except Exception:
                return text

    async def check_access(self, telegram_id: int) -> dict:
        """Foydalanuvchi dostupi va roli.

        Returns: {"allowed": bool, "user": {...}|None, "message": str|None}.
        """
        return await self._get(f"/statistic-bot/check/{telegram_id}")

    async def fetch_statistics(self, force: bool = False) -> list[dict]:
        """Xom statistika (hududlar ro'yxati)."""
        data = await self._get(
            "/statistic-bot/statistics",
            params={"force": "true"} if force else None,
        )
        if isinstance(data, dict):
            rows = data.get("data")
            return rows if isinstance(rows, list) else []
        return []


# Bot ishlash davomida yagona instans (bot.py da start/close qilinadi).
backend = BackendClient()
