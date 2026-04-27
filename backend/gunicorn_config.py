import multiprocessing
import os

# Server socket
bind = "unix:/var/www/faceid_davomat/backend/faceid.sock"
backlog = 2048

# Worker processes
# Formula: (2 x CPU cores) + 1 — bu CPU-bound uchun
# I/O-bound (FastAPI odatda shunday) uchun ko'proq mumkin
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
timeout = 60
keepalive = 5

# FastAPI uchun muhim: graceful shutdown
graceful_timeout = 30

# Restart workers after this many requests (memory leak oldini olish)
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "/var/www/faceid_davomat/backend/logs/access.log"
errorlog = "/var/www/faceid_davomat/backend/logs/error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s'

# Process naming
proc_name = "faceid_fastapi"

# Server mechanics
daemon = False
pidfile = "/var/www/faceid_davomat/backend/faceid.pid"
user = "root"
group = "www-data"
umask = 0o007

# Preload app — workerlar fork qilishdan oldin app yuklanadi
# Memory tejaydi, lekin DB connectionlar bilan ehtiyot bo'ling
preload_app = True
