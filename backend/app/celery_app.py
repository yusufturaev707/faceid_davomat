"""Celery konfiguratsiyasi.

Ikki queue: verify (yuz tekshirish) va storage (rasm saqlash).
InsightFace modeli har worker process uchun 1 marta yuklanadi.
"""

import logging

from celery import Celery
from celery.signals import setup_logging, worker_init, worker_process_init
from kombu import Queue

from app.config import settings

logger = logging.getLogger("faceid.celery")

celery_app = Celery(
    "faceid",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.verify_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=settings.TASK_RESULT_TTL,
    # Har bir worker bitta task oladi — InsightFace CPU ni to'liq ishlatsin
    worker_prefetch_multiplier=1,
    # Task tugagandan keyin acknowledge — crash bo'lsa navbatga qaytadi
    task_acks_late=True,
    # Worker crash bo'lsa task reject qilinadi (navbatga qaytadi)
    task_reject_on_worker_lost=True,
    # Task uchun vaqt chegarasi
    task_time_limit=settings.TASK_TIME_LIMIT,
    # Worker cancel qilish ulanish uzilganda
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Task STARTED holatini kuzatish
    task_track_started=True,
    # Memory leak oldini olish — har N taskdan keyin worker restart
    worker_max_tasks_per_child=settings.WORKER_MAX_TASKS_PER_CHILD,
)

# Ikki queue: verify (yuz tekshirish) va storage (rasm saqlash)
celery_app.conf.task_queues = [
    Queue("verify", routing_key="verify.#"),
    Queue("storage", routing_key="storage.#"),
]
celery_app.conf.task_default_queue = "verify"


@setup_logging.connect
def configure_logging(**kwargs):
    """Celery'ning default logging hijack'ini almashtirib, app loggerini ulash."""
    from app.core.logging import setup_logging as app_setup_logging
    app_setup_logging()


def _load_model() -> None:
    """InsightFace modelini yuklash."""
    from app.services.face_service import init_face_app
    init_face_app()


@worker_init.connect
def on_worker_init(sender, **kwargs):
    """Worker ishga tushganda modelni yuklash (solo/threads pool uchun)."""
    from app.core.logging import setup_logging as app_setup_logging
    app_setup_logging()
    logger.info("Worker init — model yuklanmoqda")
    _load_model()


@worker_process_init.connect
def on_worker_process_init(sender, **kwargs):
    """Har bir prefork subprocess ishga tushganda modelni yuklash."""
    from app.core.logging import setup_logging as app_setup_logging
    app_setup_logging()
    logger.info("Worker process init — model yuklanmoqda")
    _load_model()
