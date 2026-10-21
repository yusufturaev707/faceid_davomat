"""Server yuklamasi tarixi — Celery beat har daqiqada bitta nuqta yozadi.

Nuqtalar Redis'da (`server_monitor.HISTORY_KEY`), 24 soat saqlanadi va
superadminning «Server monitoringi» sahifasidagi grafiklarga chiqadi.
Storage worker shu serverning o'zida ishlaydi, shuning uchun o'lchov
API bilan bir xil mashinadan olinadi.
"""

import logging

from app.celery_app import celery_app
from app.services.server_monitor import record_sample

logger = logging.getLogger("faceid.tasks.monitor")


@celery_app.task(name="tasks.monitor_sample", queue="storage", ignore_result=True)
def monitor_sample() -> None:
    try:
        record_sample()
    except Exception:
        # Monitoring nuqtasi tushib qolsa hech narsa buzilmaydi — qayta urinilmaydi.
        logger.exception("Monitoring nuqtasini yozib bo'lmadi")
