# Server socket
bind = "unix:/var/www/faceid_davomat/backend/faceid.sock"
backlog = 2048

# Worker processes
# Formula: (2 x CPU cores) + 1 — bu CPU-bound uchun
# I/O-bound (FastAPI odatda shunday) uchun ko'proq mumkin
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 8
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 120
keepalive = 5

# FastAPI uchun muhim: graceful shutdown
graceful_timeout = 60

# Restart workers after this many requests (memory leak oldini olish)
max_requests = 20000
max_requests_jitter = 50

# Logging
accesslog = "/var/www/faceid_davomat/backend/logs/access.log"
errorlog = "/var/www/faceid_davomat/backend/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# ── Health-check'ni gunicorn access.log'idan chiqarish ──
# Desktop klientlar har 5 s'da health so'rovi yuboradi; bu yozuvlar
# access.log'ni ko'mib tashlamasligi uchun filtrlaymiz. Filtr har workerda
# `gunicorn.access` logger'iga ulanadi (post_worker_init hook orqali).
import logging as _logging

_SKIP_ACCESS_PATHS = ("/health", "/api/v1/health", "/api/v1/healthcheck")


class _HealthAccessLogFilter(_logging.Filter):
    def filter(self, record: _logging.LogRecord) -> bool:
        # gunicorn access record: args['r'] == 'GET /api/v1/healthcheck HTTP/1.1'
        args = record.args
        if not isinstance(args, dict):
            return True
        req_line = args.get("r") or ""
        parts = req_line.split(" ")
        path = parts[1].split("?", 1)[0] if len(parts) > 1 else ""
        return path not in _SKIP_ACCESS_PATHS


def post_worker_init(worker):
    _logging.getLogger("gunicorn.access").addFilter(_HealthAccessLogFilter())


# Process naming
proc_name = "faceid_fastapi"

# Server mechanics
# daemon = False
pidfile = "/var/www/faceid_davomat/backend/faceid.pid"
# user = "root"
# group = "www-data"
umask = 0o007

# Preload app — workerlar fork qilishdan oldin app yuklanadi
# Memory tejaydi, lekin DB connectionlar bilan ehtiyot bo'ling
# preload_app = True
