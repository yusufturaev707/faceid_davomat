"""HTTP middleware: request-id, access log, light metrics."""
import time
import uuid
from collections import defaultdict
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import logger, request_id_ctx


class RequestIdMiddleware(BaseHTTPMiddleware):
    """X-Request-ID header'ni qabul qiladi yoki yangi UUID yaratadi."""

    async def dispatch(self, request: Request, call_next) -> Response:
        req_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:16]
        token = request_id_ctx.set(req_id)
        start = time.perf_counter()
        try:
            response = await call_next(request)
            elapsed_ms = (time.perf_counter() - start) * 1000
            response.headers["X-Request-ID"] = req_id
            logger.info(
                "%s %s -> %d %.1fms",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
            _metrics.record(request.method, request.url.path, response.status_code, elapsed_ms)
            return response
        except Exception:
            logger.exception("Unhandled: %s %s", request.method, request.url.path)
            raise
        finally:
            request_id_ctx.reset(token)


class _Metrics:
    """Juda oddiy in-process counter. Prometheus middleware'ni keyin qo'shish mumkin."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.requests_total: dict[tuple[str, int], int] = defaultdict(int)
        self.latency_sum_ms: dict[str, float] = defaultdict(float)
        self.latency_count: dict[str, int] = defaultdict(int)

    def record(self, method: str, path: str, status: int, ms: float) -> None:
        with self._lock:
            self.requests_total[(method, status)] += 1
            key = f"{method} {path}"
            self.latency_sum_ms[key] += ms
            self.latency_count[key] += 1

    def render(self) -> str:
        """Oddiy Prometheus text format."""
        lines = ["# HELP http_requests_total Total HTTP requests",
                 "# TYPE http_requests_total counter"]
        with self._lock:
            for (method, status), count in self.requests_total.items():
                lines.append(
                    f'http_requests_total{{method="{method}",status="{status}"}} {count}'
                )
            lines.append("# HELP http_request_latency_ms_avg Average latency ms")
            lines.append("# TYPE http_request_latency_ms_avg gauge")
            for key, total in self.latency_sum_ms.items():
                count = self.latency_count[key] or 1
                method, path = key.split(" ", 1)
                avg = total / count
                lines.append(
                    f'http_request_latency_ms_avg{{method="{method}",path="{path}"}} {avg:.2f}'
                )
        return "\n".join(lines) + "\n"


_metrics = _Metrics()


def get_metrics_text() -> str:
    return _metrics.render()
