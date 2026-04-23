"""Logging configuration.

Production'da strukturaviy JSON log formati ishlatish qulay (ELK, Loki, Datadog).
LOG_FORMAT=json env'i bilan tanlash mumkin; default — human-readable.
PII'ni kamaytirish uchun log jo'natuvchi kod qo'lda mask qilishi kerak;
bu formatter qo'shimcha redaction qilmaydi.
"""

import json
import logging
import os
import sys
from contextvars import ContextVar

# Har bir so'rov uchun request_id shu ContextVar orqali ko'chadi.
request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    """request_id ni har bir LogRecord'ga qo'shadi."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get()
        return True


class JsonFormatter(logging.Formatter):
    """Structured log uchun JSON formatter."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> None:
    """Ilova uchun logging sozlamalarini o'rnatish."""
    use_json = os.getenv("LOG_FORMAT", "text").lower() == "json"
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())

    if use_json:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | req=%(request_id)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Uchinchi tomon kutubxonalar log darajasini pasaytirish
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


logger = logging.getLogger("faceid")
