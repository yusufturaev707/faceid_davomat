from celery import Celery
from celery.signals import worker_init, worker_process_init

from app.config import settings

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
    worker_cancel_long_running_tasks_on_connection_loss=True,
    # Task STARTED holatini kuzatish
    task_track_started=True,
)


def _load_model():
    """InsightFace modelini yuklash."""
    from app.services.face_service import init_face_app
    init_face_app()


@worker_init.connect
def on_worker_init(sender, **kwargs):
    """Worker ishga tushganda modelni yuklash (solo/threads pool uchun)."""
    _load_model()


@worker_process_init.connect
def on_worker_process_init(sender, **kwargs):
    """Har bir prefork subprocess ishga tushganda modelni yuklash."""
    _load_model()
