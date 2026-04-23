"""Load students from external APIs (CEFR, MS, IIV) into DB."""

import base64
import logging
from datetime import date, datetime

import httpx
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

# API URL templates — {0}=date, {1}=page
_API_URLS: dict[str, str] = {
    "cefr": settings.API_CEFR,
    "ms": settings.API_MS,
    "iiv": settings.API_IIV,
}

_SUPPORTED_KEYS = {"cefr", "ms", "iiv"}

BATCH_SIZE = 500
HTTP_TIMEOUT = 30.0


class StudentLoadError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


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


# ── region → zone mapping cache ──────────────────────────────────────


def _build_region_zone_map(db: Session) -> dict[int, int]:
    """Region.number → first Zone.id mapping."""
    regions = db.execute(select(Region)).scalars().all()
    zone_map: dict[int, int] = {}
    for region in regions:
        first_zone = db.execute(
            select(Zone)
            .where(Zone.region_id == region.id, Zone.is_active.is_(True))
            .order_by(Zone.id)
            .limit(1)
        ).scalar()
        if first_zone:
            zone_map[region.number] = first_zone.id
    return zone_map


# ── smena mapping ────────────────────────────────────────────────────


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


# ── HTTP fetch all pages ─────────────────────────────────────────────


def _fetch_all_pages(
    url_template: str,
    date_str: str,
    headers: dict[str, str] | None = None,
    *,
    items_key: str = "items",
    data_wrapper: bool = True,
    total_pages_key: str = "pageCount",
) -> list[dict]:
    """Fetch all pages from paginated API. Returns merged items list."""
    all_items: list[dict] = []
    page = 1

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
                # IIV format — items at top level
                items = body.get(items_key, [])
                total_pages = body.get(total_pages_key, 1)

            all_items.extend(items)
            logger.info(
                "Page %d/%d — got %d items (total so far: %d)",
                page,
                total_pages,
                len(items),
                len(all_items),
            )

            if page >= total_pages or not items:
                break
            page += 1

    return all_items


# ── Parsers: external API → (Student fields, PsData fields) ─────────


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


# ── Main loader ──────────────────────────────────────────────────────


def load_students_for_session(db: Session, session: TestSession) -> int:
    """Load students from external API into DB for the given session.

    Returns the number of students loaded.
    Raises StudentLoadError on failure.
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

    # Headers (faqat IIV uchun token kerak)
    headers: dict[str, str] = {}
    if test_key == "iiv" and settings.API_IIV_TOKEN:
        headers["Authorization"] = settings.API_IIV_TOKEN

    # Build zone map
    zone_map = _build_region_zone_map(db)
    if not zone_map:
        raise StudentLoadError("Hududlar yoki zonalar topilmadi")

    # Build smena map
    smena_map = _build_smena_map(db, session.id)
    if not smena_map:
        raise StudentLoadError(
            "Sessiyada smenalar topilmadi. Avval smenalarni qo'shing"
        )

    # Determine date(s) — use smena days from the session
    smena_days: set[str] = set()
    for sm in session.smenas:
        smena_days.add(str(sm.day))

    if not smena_days:
        raise StudentLoadError("Sessiyada smenalar sanasi topilmadi")

    parser = _PARSERS[test_key]

    # Fetch params based on key type
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

    # Gender key → id mapping
    gender_key_map: dict[int, int] = {}
    for g in db.execute(select(Gender)).scalars().all():
        gender_key_map[g.key] = g.id

    # Blacklist IMEI lari to'plami
    blacklist_imeis: set[str] = set(
        row[0]
        for row in db.execute(
            select(StudentBlacklist.imei).where(StudentBlacklist.imei.isnot(None))
        )
        if row[0]
    )

    total_loaded = 0

    for day_str in sorted(smena_days):
        logger.info("Loading students for date=%s, key=%s", day_str, test_key)

        try:
            raw_items = _fetch_all_pages(url_template, day_str, headers, **fetch_kwargs)
        except httpx.HTTPError as e:
            logger.error("API error for %s date=%s: %s", test_key, day_str, e)
            raise StudentLoadError(
                f"Tashqi API dan ma'lumot olishda xatolik: {e}"
            ) from e

        if not raw_items:
            logger.info("No items returned for date=%s", day_str)
            continue

        # Parse and batch insert
        batch_students: list[tuple[dict, dict]] = []
        skipped = 0

        for raw in raw_items:
            parsed = parser(raw, zone_map)
            if not parsed:
                skipped += 1
                continue
            batch_students.append(parsed)

        if skipped:
            logger.warning("Skipped %d items (no matching zone)", skipped)

        # Insert in batches
        for i in range(0, len(batch_students), BATCH_SIZE):
            chunk = batch_students[i : i + BATCH_SIZE]
            for student_data, ps_data in chunk:
                smena_number = student_data.pop("_smena_number", 1)
                item_day = student_data.pop("_day", day_str)

                # Find matching session_smena
                session_smena_id = smena_map.get((smena_number, item_day))
                if not session_smena_id:
                    skipped += 1
                    continue

                student_data["session_smena_id"] = session_smena_id
                student_data["is_image"] = bool(ps_data.get("ps_img"))

                # Blacklist tekshirish
                imei_val = student_data.get("imei") or ""
                if imei_val and imei_val in blacklist_imeis:
                    student_data["is_blacklist"] = True

                student = Student(**student_data)
                db.add(student)
                db.flush()

                # Gender aniqlash: imei ning birinchi raqami 3/5 → key=1, 4/6 → key=2, boshqa → key=0
                imei_val = student_data.get("imei") or ""
                if imei_val and imei_val[0] in ("3", "5"):
                    ps_data["gender_id"] = gender_key_map.get(1)
                elif imei_val and imei_val[0] in ("4", "6"):
                    ps_data["gender_id"] = gender_key_map.get(2)
                else:
                    ps_data["gender_id"] = gender_key_map.get(0)

                ps_data["student_id"] = student.id
                db.add(StudentPsData(**ps_data))

            db.commit()
            total_loaded += len(chunk)
            logger.info("Committed batch %d-%d", i, i + len(chunk))

    # Update total count
    session.count_total_student = total_loaded
    db.commit()

    logger.info(
        "Loaded %d students for session #%d (%s)",
        total_loaded,
        session.id,
        test_key,
    )
    return total_loaded
