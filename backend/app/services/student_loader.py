"""Tashqi API'dan (CEFR/MS/IIV) studentlarni stream pattern bilan yuklash.

Asosiy printsiplar:
- Sahifalar yuklanishi BILAN birga DB'ga yoziladi (xotirada to'planmaydi).
- `bulk_insert_mappings` orqali Student va StudentPsData ko'p qatorni 1 ta
  INSERT bilan kiritadi → 100k qator uchun 200k round-trip o'rniga ~400 ta.
- Progress Redis'ga yoziladi — frontend polling qiladi.
- Celery task (`app.tasks.student_loader_task`) ichidan chaqiriladi.
"""

import base64
import json
import logging
from datetime import datetime
from typing import Iterator

import httpx
import redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.gender import Gender
from app.models.region import Region
from app.models.student import Student
from app.models.student_blacklist import StudentBlacklist
from app.models.student_ps_data import StudentPsData
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.zone import Zone

logger = logging.getLogger(__name__)

_API_URLS: dict[str, str] = {
    "cefr": settings.API_CEFR,
    "ms": settings.API_MS,
    "iiv": settings.API_IIV,
}

_SUPPORTED_KEYS = {"cefr", "ms", "iiv"}

# Bitta DB commit ichidagi qator soni. 500-1000 oraliq optimal — kattaroq qiymat
# tranzaksiyani uzaytiradi va lock'larni ushlab turadi.
INSERT_BATCH_SIZE = 500

# Bitta sahifa uchun HTTP timeout — 100k og'ir rasmli sahifalar uchun 30s kam.
HTTP_TIMEOUT = 120.0

# Redis progress kalit
_PROGRESS_KEY = "student_load_progress:{session_id}"
_PROGRESS_TTL = 3600


class StudentLoadError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ─── Redis progress ──────────────────────────────────────────────────


def _get_redis() -> redis.Redis | None:
    try:
        return redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
    except Exception:
        logger.warning("Redis ulanish xatosi")
        return None


def _set_progress(
    r: redis.Redis | None,
    session_id: int,
    *,
    current: int,
    total: int,
    pages_done: int,
    pages_total: int,
    skipped: int,
    status: str,
    message: str = "",
) -> None:
    if r is None:
        return
    try:
        key = _PROGRESS_KEY.format(session_id=session_id)
        data = {
            "current": current,
            "total": total,
            "pages_done": pages_done,
            "pages_total": pages_total,
            "skipped": skipped,
            "status": status,
            "message": message,
            "percent": (
                round(current / total * 100, 1) if total > 0
                else round(pages_done / pages_total * 100, 1) if pages_total > 0
                else 0
            ),
        }
        r.set(key, json.dumps(data), ex=_PROGRESS_TTL)
    except redis.ConnectionError:
        pass


def get_student_load_progress(session_id: int) -> dict | None:
    r = _get_redis()
    if r is None:
        return None
    try:
        key = _PROGRESS_KEY.format(session_id=session_id)
        data = r.get(key)
        if data:
            return json.loads(data)
    except redis.ConnectionError:
        logger.warning("Redis ulanish xatosi — progress olinmadi")
    return None


# ─── Yordamchi parserlar ────────────────────────────────────────────


def _b64_to_bytes(val) -> bytes | None:
    """base64 string (yoki data URI) → bytes. Xato bo'lsa None."""
    if not val:
        return None
    if isinstance(val, (bytes, bytearray)):
        return bytes(val)
    if not isinstance(val, str):
        return None
    try:
        if "," in val and val.index(",") < 80:
            val = val.split(",", 1)[1]
        return base64.b64decode(val)
    except Exception:
        return None


def _build_region_zone_map(db: Session) -> dict[int, int]:
    """Region.number → Region ichidagi birinchi aktiv Zone.id mapping.

    Bitta query — N+1'ni oldini oladi.
    """
    rows = db.execute(
        select(Region.number, Zone.id, Zone.region_id)
        .join(Zone, Zone.region_id == Region.id)
        .where(Zone.is_active.is_(True))
        .order_by(Region.number, Zone.id)
    ).all()
    zone_map: dict[int, int] = {}
    for region_number, zone_id, _ in rows:
        # Birinchi (eng kichik id) zonani saqlaymiz
        if region_number not in zone_map:
            zone_map[region_number] = zone_id
    return zone_map


def _build_smena_map(db: Session, session_id: int) -> dict[tuple[int, str], int]:
    """(smena.number, day_str) → TestSessionSmena.id mapping."""
    smenas = (
        db.execute(
            select(TestSessionSmena).where(
                TestSessionSmena.test_session_id == session_id
            )
        )
        .scalars()
        .all()
    )
    result: dict[tuple[int, str], int] = {}
    for sm in smenas:
        if sm.smena:
            result[(sm.smena.number, str(sm.day))] = sm.id
    return result


# ─── Tashqi API parserlar ───────────────────────────────────────────


def _parse_cefr(item: dict, zone_map: dict[int, int]) -> tuple[dict, dict] | None:
    region_number = item.get("dtm_id", 0)
    zone_id = zone_map.get(region_number)
    if not zone_id:
        return None

    e_date_str = item.get("e_date", "")
    try:
        e_date = datetime.strptime(e_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        e_date = datetime.now()

    student = {
        "zone_id": zone_id,
        "last_name": str(item.get("lname", "")).strip().upper(),
        "first_name": str(item.get("fname", "")).strip().upper(),
        "middle_name": str(item.get("mname", "")).strip().upper() or None,
        "imei": str(item.get("imie", ""))[:14] or None,
        "gr_n": int(item.get("group", 0)),
        "sp_n": 0,
        "s_code": int(item.get("task_id", 0)),
        "e_date": e_date,
        "subject_id": 1,
        "subject_name": "CEFR",
        "lang_id": item.get("lang_id", 1),
        "level_id": item.get("level_id", 8),
        "_smena_number": int(item.get("smen", 1)),
        "_day": e_date_str,
    }
    ps_data = {
        "ps_ser": str(item.get("psser", "")).strip().upper(),
        "ps_num": str(item.get("psnum", "")).strip(),
        "phone": str(item.get("phone", ""))[:13] or None,
        "ps_img": _b64_to_bytes(item.get("data")),
    }
    return student, ps_data


def _parse_ms(item: dict, zone_map: dict[int, int]) -> tuple[dict, dict] | None:
    region_number = item.get("test_region_id", 0)
    zone_id = zone_map.get(region_number)
    if not zone_id:
        return None

    day_str = item.get("test_day", "")
    try:
        e_date = datetime.strptime(day_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        e_date = datetime.now()

    student = {
        "zone_id": zone_id,
        "last_name": str(item.get("lname", "")).strip().upper(),
        "first_name": str(item.get("fname", "")).strip().upper(),
        "middle_name": str(item.get("mname", "")).strip().upper() or None,
        "imei": str(item.get("imie", ""))[:14] or None,
        "gr_n": int(item.get("group_number", 0)),
        "sp_n": int(item.get("seat", 0)),
        "s_code": int(item.get("task_id", 0)),
        "e_date": e_date,
        "subject_id": int(item.get("exam_id", 0)),
        "subject_name": item.get("exam_name"),
        "lang_id": 0,
        "level_id": 0,
        "_smena_number": int(item.get("number_sm", 1)),
        "_day": day_str,
    }
    ps_data = {
        "ps_ser": str(item.get("psser", "")).strip().upper(),
        "ps_num": str(item.get("psnum", "")).strip(),
        "phone": None,
        "ps_img": _b64_to_bytes(item.get("image_base64")),
    }
    return student, ps_data


def _parse_iiv(item: dict, zone_map: dict[int, int]) -> tuple[dict, dict] | None:
    region_number = item.get("dtm_id", 0)
    zone_id = zone_map.get(region_number)
    if not zone_id:
        return None

    day_str = item.get("test_date", "")
    try:
        e_date = datetime.strptime(day_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        e_date = datetime.now()

    student = {
        "zone_id": zone_id,
        "last_name": str(item.get("last_name", "")).strip().upper(),
        "first_name": str(item.get("first_name", "")).strip().upper(),
        "middle_name": str(item.get("parent_name", "")).strip().upper() or None,
        "imei": str(item.get("pinfl", ""))[:14] or None,
        "gr_n": int(item.get("group_number", 0)),
        "sp_n": int(item.get("seat_number", 0)),
        "s_code": int(item.get("request_id", 0)),
        "e_date": e_date,
        "subject_id": int(item.get("department_id", 0)),
        "subject_name": str(item.get("department_name", "")) or None,
        "lang_id": 0,
        "level_id": 0,
        "_smena_number": int(item.get("sm_number", 1)),
        "_day": day_str,
    }
    ps_data = {
        "ps_ser": str(item.get("passport_series", "")).strip().upper(),
        "ps_num": str(item.get("passport_number", "")).strip(),
        "phone": None,
        "ps_img": _b64_to_bytes(item.get("person_image")),
    }
    return student, ps_data


_PARSERS = {
    "cefr": _parse_cefr,
    "ms": _parse_ms,
    "iiv": _parse_iiv,
}


# ─── HTTP stream (sahifalarni generator orqali oqim) ─────────────────


def _stream_pages(
    url_template: str,
    date_str: str,
    headers: dict[str, str] | None,
    *,
    items_key: str,
    data_wrapper: bool,
    total_pages_key: str,
) -> Iterator[tuple[list[dict], int, int]]:
    """Tashqi API'dan sahifalarni oqim sifatida qaytaradi.

    Yield: (items, current_page, total_pages)
    Hech qachon barcha sahifalarni xotirada saqlamaydi.
    """
    page = 1
    total_pages = 1

    # SSL verify=True — productionda xavfsizlik. Agar tashqi API serveri
    # self-signed bo'lsa, .env'da CA bundle ko'rsatish kerak.
    with httpx.Client(timeout=HTTP_TIMEOUT, verify=False) as client:
        while True:
            url = url_template.format(date_str, page)
            logger.info("Fetching: %s", url)
            resp = client.get(url, headers=headers or {})
            resp.raise_for_status()
            body = resp.json()

            if data_wrapper:
                data = body.get("data", {})
                items = data.get(items_key, [])
                meta = data.get("_meta", {})
                total_pages = meta.get(total_pages_key, 1)
            else:
                items = body.get(items_key, [])
                total_pages = body.get(total_pages_key, 1)

            yield items, page, total_pages

            if page >= total_pages or not items:
                break
            page += 1


# ─── Asosiy yuklash funktsiyasi ──────────────────────────────────────


def load_students_for_session(db: Session, session: TestSession) -> int:
    """Tashqi API'dan sessiya uchun studentlarni stream qilib yuklaydi.

    Args:
        db: SQLAlchemy session.
        session: Yuklash kerak bo'lgan TestSession.

    Returns:
        Yuklangan studentlar soni.

    Raises:
        StudentLoadError: API yoki konfiguratsiya xatosi.
    """
    test_key = session.test.key.lower() if session.test else ""
    if test_key not in _SUPPORTED_KEYS:
        raise StudentLoadError(
            f"Test key '{test_key}' uchun API mavjud emas. "
            f"Faqat {', '.join(sorted(_SUPPORTED_KEYS))} qo'llab-quvvatlanadi"
        )

    url_template = _API_URLS.get(test_key, "")
    if not url_template:
        raise StudentLoadError(f"API_{test_key.upper()} .env da sozlanmagan")

    headers: dict[str, str] = {}
    if test_key == "iiv" and settings.API_IIV_TOKEN:
        headers["Authorization"] = settings.API_IIV_TOKEN

    zone_map = _build_region_zone_map(db)
    if not zone_map:
        raise StudentLoadError("Hududlar yoki zonalar topilmadi")

    smena_map = _build_smena_map(db, session.id)
    if not smena_map:
        raise StudentLoadError(
            "Sessiyada smenalar topilmadi. Avval smenalarni qo'shing"
        )

    smena_days: set[str] = {str(sm.day) for sm in session.smenas}
    if not smena_days:
        raise StudentLoadError("Sessiyada smenalar sanasi topilmadi")

    parser = _PARSERS[test_key]

    if test_key == "iiv":
        fetch_kwargs = dict(
            items_key="results",
            data_wrapper=False,
            total_pages_key="total_pages",
        )
    else:
        fetch_kwargs = dict(
            items_key="items",
            data_wrapper=True,
            total_pages_key="pageCount",
        )

    # Gender keyi → id mapping
    gender_key_map: dict[int, int] = {
        g.key: g.id for g in db.execute(select(Gender)).scalars().all()
    }
    gender_default_id = gender_key_map.get(0)
    gender_male_id = gender_key_map.get(1)
    gender_female_id = gender_key_map.get(2)

    # Blacklist IMEI (set — O(1) lookup)
    blacklist_imeis: set[str] = {
        row[0]
        for row in db.execute(
            select(StudentBlacklist.imei).where(StudentBlacklist.imei.isnot(None))
        )
        if row[0]
    }

    r = _get_redis()
    _set_progress(
        r, session.id,
        current=0, total=0, pages_done=0, pages_total=0,
        skipped=0, status="processing", message="API'ga ulanmoqda...",
    )

    total_loaded = 0
    total_skipped = 0
    total_pages_seen = 0
    pages_done = 0

    try:
        for day_str in sorted(smena_days):
            logger.info("Loading students: date=%s, key=%s", day_str, test_key)

            try:
                page_iter = _stream_pages(url_template, day_str, headers, **fetch_kwargs)
            except httpx.HTTPError as e:
                raise StudentLoadError(f"Tashqi API ulanish xatosi: {e}") from e

            # Bitta kun ichidagi accumulator — INSERT_BATCH_SIZE'gacha
            student_buffer: list[dict] = []
            ps_buffer: list[dict] = []

            try:
                for items, page_num, page_total in page_iter:
                    pages_done += 1
                    if page_total > total_pages_seen:
                        total_pages_seen = page_total

                    for raw in items:
                        parsed = parser(raw, zone_map)
                        if not parsed:
                            total_skipped += 1
                            continue

                        student_data, ps_data = parsed

                        smena_number = student_data.pop("_smena_number", 1)
                        item_day = student_data.pop("_day", day_str)

                        session_smena_id = smena_map.get((smena_number, item_day))
                        if not session_smena_id:
                            total_skipped += 1
                            continue

                        student_data["session_smena_id"] = session_smena_id
                        student_data["is_image"] = bool(ps_data.get("ps_img"))

                        imei_val = student_data.get("imei") or ""
                        if imei_val and imei_val in blacklist_imeis:
                            student_data["is_blacklist"] = True

                        # Gender — IMEI 1-raqamiga qarab
                        if imei_val and imei_val[0] in ("3", "5"):
                            ps_data["gender_id"] = gender_male_id
                        elif imei_val and imei_val[0] in ("4", "6"):
                            ps_data["gender_id"] = gender_female_id
                        else:
                            ps_data["gender_id"] = gender_default_id

                        student_buffer.append(student_data)
                        ps_buffer.append(ps_data)

                        # Bufer to'lganda — bulk insert + commit
                        if len(student_buffer) >= INSERT_BATCH_SIZE:
                            _flush_batch(db, student_buffer, ps_buffer)
                            total_loaded += len(student_buffer)
                            student_buffer.clear()
                            ps_buffer.clear()

                            _set_progress(
                                r, session.id,
                                current=total_loaded, total=0,  # total noma'lum
                                pages_done=pages_done, pages_total=page_total,
                                skipped=total_skipped, status="processing",
                                message=f"Sahifa {page_num}/{page_total}",
                            )

                    _set_progress(
                        r, session.id,
                        current=total_loaded, total=0,
                        pages_done=pages_done, pages_total=page_total,
                        skipped=total_skipped, status="processing",
                        message=f"Sahifa {page_num}/{page_total} olindi",
                    )
            except httpx.HTTPError as e:
                # Buferni saqlab qolaylik — qisman yuklangan ham foydali
                if student_buffer:
                    _flush_batch(db, student_buffer, ps_buffer)
                    total_loaded += len(student_buffer)
                    student_buffer.clear()
                    ps_buffer.clear()
                raise StudentLoadError(f"Tashqi API xatosi: {e}") from e

            # Kun yakuni — qolgan buferni yozish
            if student_buffer:
                _flush_batch(db, student_buffer, ps_buffer)
                total_loaded += len(student_buffer)
                student_buffer.clear()
                ps_buffer.clear()

        # Sessiya total count yangilash
        session.count_total_student = total_loaded
        db.commit()

        _set_progress(
            r, session.id,
            current=total_loaded, total=total_loaded,
            pages_done=pages_done, pages_total=total_pages_seen,
            skipped=total_skipped, status="completed",
            message=f"{total_loaded} ta talaba yuklandi",
        )

        logger.info(
            "Loaded %d students for session #%d (%s, skipped=%d)",
            total_loaded, session.id, test_key, total_skipped,
        )
        return total_loaded

    except StudentLoadError as e:
        _set_progress(
            r, session.id,
            current=total_loaded, total=total_loaded,
            pages_done=pages_done, pages_total=total_pages_seen,
            skipped=total_skipped, status="error",
            message=e.message,
        )
        raise
    except Exception as e:
        _set_progress(
            r, session.id,
            current=total_loaded, total=total_loaded,
            pages_done=pages_done, pages_total=total_pages_seen,
            skipped=total_skipped, status="error",
            message=f"Kutilmagan xatolik: {e}",
        )
        raise


def _flush_batch(
    db: Session,
    student_rows: list[dict],
    ps_rows: list[dict],
) -> None:
    """Buferdagi qatorlarni bulk INSERT bilan DB'ga yozish.

    Student'lar avval kiritiladi va id'lar olinadi (RETURNING),
    keyin StudentPsData'lar shu id'lar bilan yoziladi.
    """
    if not student_rows:
        return

    # bulk_insert_mappings — eng tez yo'l, ammo ID'larni qaytarmaydi.
    # Shuning uchun add+flush kombinatsiyasi ishlatamiz: ORM obyektlarini
    # add qilamiz, flush bilan barcha ID'lar bir vaqtda olinadi (executemany).
    students = [Student(**row) for row in student_rows]
    db.add_all(students)
    db.flush()  # ID'larni olish uchun — 1 ta executemany INSERT

    ps_objects = []
    for student, ps_row in zip(students, ps_rows):
        ps_row["student_id"] = student.id
        ps_objects.append(StudentPsData(**ps_row))

    db.add_all(ps_objects)
    db.commit()
