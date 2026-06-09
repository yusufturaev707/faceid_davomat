"""Statistika bot uchun tashqi statistika API klienti (kesh bilan).

Avval bu logika `statistic_bot` botining ichida edi — endi backendga
ko'chirildi. Bot ham, Qabul-2026 dashboard ham shu yagona manbadan
foydalanadi (bot `X-API-Key`, dashboard JWT+permission orqali).

Tashqi API javobi:
    {"success": true, "body": {"data": [ {..hudud..}, ... ]}}
Har bir hudud lug'atida `count_2026`, `male_2026`, `paid_2026`,
`count_2025`, ... kabi kalitlar bo'ladi.
"""

from __future__ import annotations

import json
import logging
import re
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

from app.config import settings
from app.schemas.statistic_bot import QabulRegionStat, QabulStats

# Tashqi API maydonlari `<field>_<yil>` ko'rinishida (masalan `count_2026`).
_YEAR_KEY_RE = re.compile(r"^count_(\d{4})$")

logger = logging.getLogger("faceid.services.statistic_bot")


class StatisticBotApiError(Exception):
    """Tashqi API javobi noto'g'ri yoki muvaffaqiyatsiz bo'lganda."""


# Oddiy process-ichi xotira keshi (TTL). Bir nechta worker bo'lsa har birida
# alohida — bu maqbul, chunki maqsad faqat tashqi API yukini kamaytirish.
_cache: dict = {"data": None, "ts": 0.0, "fetched_at": None}

# Diskdagi zaxira kesh — server qayta ishga tushganda (sovuq start) tashqi API
# vaqtinchalik mavjud bo'lmasa ham oxirgi ma'lum holatni berish uchun.
_DISK_CACHE_FILE = Path(tempfile.gettempdir()) / "faceid_statistic_bot_cache.json"


def _save_disk_cache(data: list[dict], fetched_at: datetime) -> None:
    try:
        _DISK_CACHE_FILE.write_text(
            json.dumps({"data": data, "fetched_at": fetched_at.isoformat()}),
            encoding="utf-8",
        )
    except Exception as e:  # disk xatosi kesh logikasini buzmasin
        logger.debug("Disk kesh saqlanmadi: %s", e)


def _load_disk_cache() -> tuple[list[dict], datetime] | None:
    try:
        if not _DISK_CACHE_FILE.exists():
            return None
        raw = json.loads(_DISK_CACHE_FILE.read_text(encoding="utf-8"))
        data = raw.get("data")
        if not isinstance(data, list):
            return None
        fetched_at = datetime.fromisoformat(raw["fetched_at"])
        return data, fetched_at
    except Exception as e:
        logger.debug("Disk kesh o'qilmadi: %s", e)
        return None


# Tashqi API barqaror emas (qisqa DNS TTL — vaqtinchalik `getaddrinfo failed`
# bo'lishi mumkin). Shuning uchun bir necha marta qayta urinamiz.
_MAX_ATTEMPTS = 3
_BACKOFF_SECONDS = (0.5, 1.5)  # urinishlar orasidagi kutish


def _request_once(url: str, headers: dict) -> list[dict]:
    with httpx.Client(timeout=30.0, follow_redirects=True) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        payload = resp.json()

    if not payload.get("success"):
        raise StatisticBotApiError("Tashqi API success=false qaytardi")

    body = payload.get("body") or {}
    data = body.get("data")
    if not isinstance(data, list):
        raise StatisticBotApiError("Tashqi API javobida 'data' ro'yxati topilmadi")
    return data


def _request() -> list[dict]:
    url = settings.API_STATISTIC_BOT
    if not url:
        raise StatisticBotApiError("API_STATISTIC_BOT .env da ko'rsatilmagan")

    # Server http -> https ga 301 redirect qiladi; redirect paytida ba'zi
    # klientlar Authorization header'ni tashlaydi. Shuning uchun darhol https.
    if url.startswith("http://"):
        url = "https://" + url[len("http://"):]

    headers = {"Accept": "application/json"}
    token = settings.API_STATISTIC_BOT_TOKEN
    if token:
        # API xom (raw) tokenni kutadi — "Bearer " prefiksisiz.
        headers["Authorization"] = token

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            return _request_once(url, headers)
        except httpx.HTTPError as e:
            # Tarmoq/DNS/timeout — qayta urinishga arziydi.
            last_exc = e
            logger.warning(
                "Tashqi API urinish %d/%d muvaffaqiyatsiz: %s",
                attempt, _MAX_ATTEMPTS, e,
            )
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_BACKOFF_SECONDS[min(attempt - 1, len(_BACKOFF_SECONDS) - 1)])

    raise StatisticBotApiError(
        f"Tashqi API so'rovida xatolik ({_MAX_ATTEMPTS} urinish): {last_exc}"
    )


def fetch_statistics(force: bool = False) -> tuple[list[dict], datetime]:
    """Statistikani oladi. `force=False` bo'lsa kesh muddati ichida keshdan.

    Tashqi API muvaffaqiyatsiz bo'lsa-yu, oldindan keshlangan ma'lumot bo'lsa —
    502 o'rniga ESKI keshni qaytaramiz (foydalanuvchi oxirgi ma'lum holatni
    ko'radi). Kesh umuman bo'lmasa, xatolik ko'tariladi.

    Returns: (data, fetched_at).
    """
    ttl = settings.STATISTIC_BOT_CACHE_TTL
    if (
        not force
        and _cache["data"] is not None
        and (time.time() - _cache["ts"]) < ttl
    ):
        return _cache["data"], _cache["fetched_at"]

    try:
        data = _request()
    except StatisticBotApiError:
        # 1) Xotira keshi (shu jarayonda oldin olingan bo'lsa)
        if _cache["data"] is not None:
            logger.warning(
                "Tashqi API olinmadi — xotira keshidan beriladi (%s)",
                _cache["fetched_at"],
            )
            return _cache["data"], _cache["fetched_at"]
        # 2) Disk keshi (sovuq start — server endi ko'tarilgan)
        disk = _load_disk_cache()
        if disk is not None:
            logger.warning(
                "Tashqi API olinmadi — disk keshidan beriladi (%s)", disk[1]
            )
            _cache["data"], _cache["fetched_at"] = disk
            _cache["ts"] = time.time()
            return disk
        raise

    now = datetime.now(timezone.utc)
    _cache["data"] = data
    _cache["ts"] = time.time()
    _cache["fetched_at"] = now
    _save_disk_cache(data, now)
    logger.info("Statistika tashqi APIdan yangilandi: %d ta hudud", len(data))
    return data, now


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _total(data: list[dict], key: str) -> int:
    return sum(_int(r.get(key)) for r in data)


def detect_years(data: list[dict]) -> tuple[int, int]:
    """Ma'lumotdan joriy va o'tgan yilni avtomatik aniqlaydi (DINAMIK).

    Tashqi API kalitlari `count_2026`, `count_2025`, ... ko'rinishida —
    ulardan eng katta yil joriy (`year`), undan oldingi mavjud yil esa
    o'tgan (`prev_year`) sifatida olinadi. Topilmasa, `QABUL_YEAR` setting
    (0 bo'lsa joriy kalendar yil) ga tushadi.

    Shu tufayli keyingi mavsumda (2027, ...) kod o'zgartirilmaydi.
    """
    years: set[int] = set()
    for row in data:
        for k in row.keys():
            m = _YEAR_KEY_RE.match(k)
            if m:
                years.add(int(m.group(1)))
    if years:
        cur = max(years)
        below = [y for y in years if y < cur]
        prev = max(below) if below else cur - 1
        return cur, prev

    # Fallback — ma'lumot bo'sh bo'lsa
    cur = settings.QABUL_YEAR or datetime.now(timezone.utc).year
    return cur, cur - 1


def aggregate(data: list[dict], fetched_at: datetime | None = None) -> QabulStats:
    """Xom hudud ro'yxatini Qabul dashboard uchun aggregatlaydi.

    Yil dinamik aniqlanadi — maydon nomlari runtime'da quriladi
    (`count_{year}`, `male_{year}`, ...).
    """
    year, prev_year = detect_years(data)
    cy, py = str(year), str(prev_year)

    total = _total(data, f"count_{cy}")
    male = _total(data, f"male_{cy}")
    female = _total(data, f"female_{cy}")
    graduated = _total(data, f"graduated_{cy}")
    graduated_not = _total(data, f"graduated_not_{cy}")
    paid = _total(data, f"paid_{cy}")
    uz = _total(data, f"uz_{cy}")
    ru = _total(data, f"ru_{cy}")
    qq = _total(data, f"qq_{cy}")
    lang_other = _total(data, f"lang_other_{cy}")

    total_prev = _total(data, f"count_{py}")
    paid_prev = _total(data, f"paid_{py}")
    male_prev = _total(data, f"male_{py}")
    female_prev = _total(data, f"female_{py}")

    regions: list[QabulRegionStat] = []
    for r in data:
        cnt = _int(r.get(f"count_{cy}"))
        regions.append(
            QabulRegionStat(
                region_name=str(r.get("region_name") or "Noma'lum"),
                count=cnt,
                male=_int(r.get(f"male_{cy}")),
                female=_int(r.get(f"female_{cy}")),
                paid=_int(r.get(f"paid_{cy}")),
                share=round(cnt / total * 100, 1) if total else 0.0,
            )
        )
    regions.sort(key=lambda x: x.count, reverse=True)

    return QabulStats(
        year=year,
        prev_year=prev_year,
        total=total,
        male=male,
        female=female,
        graduated=graduated,
        graduated_not=graduated_not,
        paid=paid,
        unpaid=max(0, total - paid),
        uz=uz,
        ru=ru,
        qq=qq,
        lang_other=lang_other,
        total_prev=total_prev,
        paid_prev=paid_prev,
        male_prev=male_prev,
        female_prev=female_prev,
        regions=regions,
        fetched_at=fetched_at,
    )
