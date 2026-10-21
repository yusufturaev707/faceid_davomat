"""Server monitoringi — faqat superadmin (`require_super_admin`).

Server holati (CPU/RAM/disk/tarmoq), FaceID komponentlari (API, Celery,
PostgreSQL, Redis, botlar, systemd unitlari), yuklama tarixi va loglar.
Permission orqali berilmaydi: admin roliga ham ochiq emas, faqat
superadmin va faqat interaktiv login (API kalit bilan — 403).

Hammasi faqat o'qish. Yig'ish mantig'i `services/server_monitor.py` da.
Log o'qish/yuklab olish audit uchun logga yoziladi.
"""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse

from app.core.logging import logger
from app.dependencies import require_super_admin
from app.models.user import User
from app.services import server_monitor as mon

router = APIRouter(dependencies=[Depends(require_super_admin)])

LogLevel = Literal["error", "warning"]


def _no_store(response: Response) -> None:
    # Server ichki ma'lumoti brauzer/proksi keshida qolmasin.
    response.headers["Cache-Control"] = "no-store"


@router.get("/overview", summary="Server va FaceID tizimi holati")
def get_overview(response: Response) -> dict:
    _no_store(response)
    return mon.collect_overview()


@router.get("/history", summary="Yuklama tarixi (har daqiqalik nuqtalar)")
def get_history(
    response: Response,
    minutes: int = Query(60, ge=5, le=mon.HISTORY_MAX, description="Oxirgi necha daqiqa"),
) -> dict:
    _no_store(response)
    try:
        points = mon.read_history(minutes)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Redis bilan aloqa yo'q — tarixni o'qib bo'lmadi") from exc
    return {
        "minutes": minutes,
        "interval_seconds": mon.SAMPLE_INTERVAL_SECONDS,
        "points": points,
    }


@router.get("/logs", summary="Log fayllari va journal unitlari ro'yxati")
def get_log_sources(response: Response) -> dict:
    _no_store(response)
    return {"files": mon.list_log_files(), "units": mon.configured_units()}


def _log_path(file: str):
    path = mon.resolve_log_file(file)
    if path is None:
        raise HTTPException(status_code=404, detail="Log fayli topilmadi")
    return path


@router.get("/logs/tail", summary="Log faylining oxirgi qatorlari")
def tail_log(
    response: Response,
    file: str = Query(..., max_length=300, description="`/logs` ro'yxatidagi `key`"),
    lines: int = Query(300, ge=10, le=2000),
    q: str | None = Query(None, max_length=200, description="Matn bo'yicha filtr"),
    level: LogLevel | None = Query(None, description="error — faqat xatolar, warning — ogohlantirish va xatolar"),
    current_user: User = Depends(require_super_admin),
) -> dict:
    _no_store(response)
    path = _log_path(file)
    logger.info("Server monitoring: log o'qildi user=%s file=%s", current_user.id, file)
    try:
        data = mon.tail_file(path, lines, q, level)
    except OSError as exc:
        raise HTTPException(
            status_code=422, detail=f"Faylni o'qib bo'lmadi: {exc.strerror or exc}"
        ) from exc
    return {"file": file, **data}


@router.get("/logs/download", summary="Log faylini yuklab olish (maxfiy qiymatlar yashirilgan)")
def download_log(
    file: str = Query(..., max_length=300),
    current_user: User = Depends(require_super_admin),
) -> StreamingResponse:
    path = _log_path(file)
    try:
        path.open("rb").close()
    except OSError as exc:
        raise HTTPException(
            status_code=422, detail=f"Faylni o'qib bo'lmadi: {exc.strerror or exc}"
        ) from exc
    logger.info("Server monitoring: log yuklab olindi user=%s file=%s", current_user.id, file)
    filename = file.replace("/", "_")
    return StreamingResponse(
        mon.iter_redacted_file(path),
        media_type="text/plain; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/journal", summary="systemd unit journali (journalctl)")
def get_journal(
    response: Response,
    unit: str = Query(..., max_length=100),
    lines: int = Query(300, ge=10, le=2000),
    q: str | None = Query(None, max_length=200),
    level: LogLevel | None = Query(None),
    current_user: User = Depends(require_super_admin),
) -> dict:
    _no_store(response)
    # Faqat sozlamadagi unitlar — ixtiyoriy unit nomi berib bo'lmaydi.
    if unit not in mon.configured_units():
        raise HTTPException(status_code=404, detail="Unit monitoring ro'yxatida yo'q")
    logger.info("Server monitoring: journal o'qildi user=%s unit=%s", current_user.id, unit)
    try:
        data = mon.journal_tail(unit, lines, q, level)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"journalctl xatosi: {exc}") from exc
    return {"unit": unit, **data}
