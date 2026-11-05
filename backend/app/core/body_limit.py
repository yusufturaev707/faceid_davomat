"""So'rov tanasi (body) hajmi chegarasi — ASGI darajasida, endpoint'dan oldin.

Starlette/FastAPI'da umumiy body chegarasi yo'q: Pydantic JSON'ni to'liq o'qib
parse qiladi, multipart esa diskka yoziladi — hajm tekshiruvi (MAX_BASE64_SIZE,
`_MAX_EXCEL_BYTES`) faqat shundan KEYIN ishlaydi. Bu middleware:

- `Content-Length` chegaradan katta bo'lsa — tanani o'qimasdan 413;
- `Content-Length` siz (chunked) so'rovda o'qilgan baytlarni sanaydi va
  chegaradan oshgach to'xtatadi (413).

nginx'dagi `client_max_body_size` birinchi qatlam, bu — ikkinchisi (nginx
sozlamasi repoda yo'q va unutilishi mumkin).
"""

from __future__ import annotations

from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


def _too_large_detail(limit: int) -> str:
    return f"So'rov hajmi {limit // (1024 * 1024)}MB dan oshmasligi kerak"


class BodySizeLimitMiddleware:
    """Har so'rov tanasini `default_limit` (yoki yo'l prefiksi bo'yicha) bilan cheklash."""

    def __init__(
        self,
        app: ASGIApp,
        *,
        default_limit: int,
        path_limits: dict[str, int] | None = None,
    ) -> None:
        self.app = app
        self.default_limit = default_limit
        # Uzunroq prefiks birinchi — eng aniq moslik ustun.
        self.path_limits = sorted(
            (path_limits or {}).items(), key=lambda kv: len(kv[0]), reverse=True
        )

    def _limit_for(self, path: str) -> int:
        for prefix, limit in self.path_limits:
            if path.startswith(prefix):
                return limit
        return self.default_limit

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self._limit_for(scope.get("path", ""))

        for name, value in scope.get("headers", []):
            if name == b"content-length":
                try:
                    declared = int(value)
                except ValueError:
                    declared = 0  # yaroqsiz qiymatni uvicorn/h11 o'zi rad etadi
                if declared > limit:
                    response = JSONResponse(
                        {"detail": _too_large_detail(limit)}, status_code=413
                    )
                    await response(scope, receive, send)
                    return
                break

        received = 0

        async def limited_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Endpoint tanani o'qiyotgan paytda chiqadi — ExceptionMiddleware 413 qaytaradi.
                    raise HTTPException(status_code=413, detail=_too_large_detail(limit))
            return message

        await self.app(scope, limited_receive, send)
