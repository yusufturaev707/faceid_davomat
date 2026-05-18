"""Backend FastAPI bilan ishlash uchun HTTP client.

Bot kerakli barcha so'rovlarni `X-API-Key` headeri orqali yuboradi —
admin tomonidan yaratilgan API key. Bunda backend tomonida bot uchun
maxsus login/parol kerak emas.
"""

from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import unquote

import aiohttp

from config import settings

logger = logging.getLogger(__name__)


def _parse_filename(content_disposition: str) -> str | None:
    """`Content-Disposition` headeridan filename qiymatini olib qaytarish.

    `filename*=UTF-8''<urlencoded>` (RFC 5987) ustun ko'riladi — agar bor bo'lsa.
    Aks holda oddiy `filename="..."` ishlatiladi.
    """
    if not content_disposition:
        return None
    # RFC 5987 (utf-8 encoded)
    m = re.search(r"filename\*\s*=\s*([^;]+)", content_disposition, re.IGNORECASE)
    if m:
        val = m.group(1).strip()
        if "''" in val:
            _, _, raw = val.partition("''")
            return unquote(raw)
        return unquote(val)
    m = re.search(
        r'filename\s*=\s*"?([^";]+)"?', content_disposition, re.IGNORECASE
    )
    if m:
        return m.group(1).strip()
    return None


class ApiError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


class ApiClient:
    """Backend uchun ozgina yengil wrapper.

    Bitta `aiohttp.ClientSession` ni qayta ishlatadi (bot ishlash davomida).
    """

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

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if self._session is None:
            await self.start()
        assert self._session is not None

        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._session.request(method, url, params=params, json=json) as resp:
            text = await resp.text()
            if resp.status >= 400:
                logger.warning(
                    "API %s %s → %d: %s", method, url, resp.status, text[:300]
                )
                raise ApiError(resp.status, text)
            if not text:
                return None
            try:
                return await resp.json(content_type=None)
            except Exception:
                return text

    async def _request_bytes(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> tuple[bytes, str | None, dict[str, str]]:
        """Faylni baytlar ko'rinishida olib qaytaradi.

        Returns: (body, filename, headers).
        Header kalitlari kichik harflarga keltiriladi — HTTP/2 va proxy'lar
        kalitlarni lowercase qilishi mumkin; bot tomonida case-sensitive
        lookup ishlamay qolmasligi uchun yagona shaklga keltiramiz.
        """
        if self._session is None:
            await self.start()
        assert self._session is not None

        url = f"{self._base_url}/{path.lstrip('/')}"
        async with self._session.request(method, url, params=params) as resp:
            body = await resp.read()
            if resp.status >= 400:
                logger.warning(
                    "API %s %s → %d: %s",
                    method,
                    url,
                    resp.status,
                    body[:300].decode("utf-8", "ignore"),
                )
                raise ApiError(resp.status, body.decode("utf-8", "ignore"))
            headers = {k.lower(): v for k, v in resp.headers.items()}
            filename = _parse_filename(headers.get("content-disposition", ""))
            return body, filename, headers

    # ---- Davomat bot ----

    async def check_access(self, telegram_id: int) -> dict:
        return await self._request("GET", f"davomat-bot/check/{telegram_id}")

    async def list_ready_sessions(self) -> list[dict]:
        return await self._request("GET", "davomat-bot/ready-sessions")

    async def get_session_stats(
        self,
        session_id: int,
        telegram_id: int,
        *,
        session_smena_id: int | None = None,
        test_day: str | None = None,
        region_id: int | None = None,
    ) -> dict:
        """Statistika so'rovi. Aniq bittasi berilishi kutiladi:
        - `session_smena_id` (bitta smena)
        - `test_day` (bitta kun barcha smenalari)
        - hech biri (butun sessiya).

        `region_id` berilsa, statistika faqat shu region kesimida (bot
        foydalanuvchi `/start` da tanlagan region).
        """
        params: dict[str, Any] = {"telegram_id": telegram_id}
        if session_smena_id is not None:
            params["session_smena_id"] = session_smena_id
        if test_day:
            params["test_day"] = test_day
        if region_id is not None:
            params["region_id"] = region_id
        return await self._request(
            "GET",
            f"davomat-bot/sessions/{session_id}/stats",
            params=params,
        )

    async def get_absentees_excel(
        self,
        session_id: int,
        telegram_id: int,
        *,
        session_smena_id: int | None = None,
        test_day: str | None = None,
        region_id: int | None = None,
    ) -> tuple[bytes, str, int]:
        """Kelmaganlar ro'yxati (.xlsx) baytlarini olib qaytaradi.

        Aniq bittasi berilishi kutiladi: smena / kun / sessiya (yuqoridagi
        `get_session_stats` bilan bir xil semantika). `region_id` ko'rib chiqing.

        Returns: (file_bytes, filename, absent_count).
        """
        params: dict[str, Any] = {"telegram_id": telegram_id}
        if session_smena_id is not None:
            params["session_smena_id"] = session_smena_id
        if test_day:
            params["test_day"] = test_day
        if region_id is not None:
            params["region_id"] = region_id
        body, filename, headers = await self._request_bytes(
            "GET",
            f"davomat-bot/sessions/{session_id}/absentees.xlsx",
            params=params,
        )
        try:
            count = int(headers.get("x-absent-count", "0"))
        except ValueError:
            count = 0
        return body, filename or "kelmaganlar.xlsx", count

    async def face_verify(
        self,
        telegram_id: int,
        session_id: int,
        session_smena_id: int,
        ps_ser: str,
        ps_num: str,
        jshshir: str,
        selfie_b64: str,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/face-verify",
            json={
                "telegram_id": telegram_id,
                "session_id": session_id,
                "session_smena_id": session_smena_id,
                "region_id": region_id,
                "ps_ser": ps_ser,
                "ps_num": ps_num,
                "jshshir": jshshir,
                "selfie_b64": selfie_b64,
            },
        )

    async def find_by_jshshir(
        self,
        telegram_id: int,
        session_smena_id: int,
        jshshir: str,
        only_entered: bool = True,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/find-by-jshshir",
            json={
                "telegram_id": telegram_id,
                "session_smena_id": session_smena_id,
                "region_id": region_id,
                "jshshir": jshshir,
                "only_entered": only_entered,
            },
        )

    async def remove_attendance(
        self,
        telegram_id: int,
        student_id: int,
        session_smena_id: int,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/remove-attendance",
            json={
                "telegram_id": telegram_id,
                "student_id": student_id,
                "session_smena_id": session_smena_id,
                "region_id": region_id,
            },
        )

    async def list_reason_types(self) -> list[dict]:
        """Chetlatish turlari (aktiv)."""
        return await self._request("GET", "davomat-bot/reason-types")

    async def list_reasons(self, reason_type_id: int | None = None) -> list[dict]:
        """Chetlatish sabablari — `reason_type_id` bo'yicha filtrlash."""
        params: dict[str, Any] = {}
        if reason_type_id is not None:
            params["reason_type_id"] = reason_type_id
        return await self._request(
            "GET", "davomat-bot/reasons", params=params or None
        )

    async def find_for_cheat(
        self,
        telegram_id: int,
        session_id: int,
        jshshir: str,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/find-for-cheat",
            json={
                "telegram_id": telegram_id,
                "session_id": session_id,
                "region_id": region_id,
                "jshshir": jshshir,
            },
        )

    async def create_cheating(
        self,
        telegram_id: int,
        student_id: int,
        session_id: int,
        reason_id: int,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/cheating",
            json={
                "telegram_id": telegram_id,
                "student_id": student_id,
                "session_id": session_id,
                "region_id": region_id,
                "reason_id": reason_id,
            },
        )

    async def mark_attendance(
        self,
        telegram_id: int,
        student_id: int,
        session_smena_id: int,
        selfie_b64: str | None,
        verify_score: int = 0,
        *,
        region_id: int | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            "davomat-bot/mark-attendance",
            json={
                "telegram_id": telegram_id,
                "student_id": student_id,
                "session_smena_id": session_smena_id,
                "region_id": region_id,
                "selfie_b64": selfie_b64,
                "verify_score": verify_score,
            },
        )


api_client = ApiClient()
