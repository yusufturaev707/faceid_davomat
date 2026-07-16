"""Dashboard statistika uchun qisqa-TTL kesh + single-flight qatlami.

Muammo: `session_dashboard_stats` endpointi real-time rejimda (session.state=4)
frontend tomonidan har ~5 sekundda chaqiriladi. Bir vaqtda bir nechta admin shu
sahifani ochsa, har biri bir xil og'ir to'liq-skan hisobni takrorlaydi (kesh
yo'q edi) — bu backend'ni bo'g'ishi mumkin.

Yechim (bu modul):
  1. Qisqa-TTL kesh — `(session_id, scope, session_smena_id, day)` kaliti
     bo'yicha natija ~`_TTL_SECONDS` saqlanadi. Shu oyna ichidagi barcha
     so'rovlar bitta hisob natijasini bo'lishadi (N user → 1 hisob).
  2. Single-flight — kesh eskirganda bir vaqtda kelgan bir nechta so'rovdan
     faqat BITTASI DB'dan hisoblaydi; qolganlari o'sha natijani kutib oladi
     (thundering-herd / stampede oldini oladi).

DIQQAT: kesh worker-jarayon ichida (in-process). Gunicorn'da har worker o'z
keshiga ega — ya'ni yuk worker soniga bo'linadi (masalan 8 worker → interval
boshiga eng ko'pi 8 hisob, N emas). Barcha workerlar bo'ylab yagona hisob kerak
bo'lsa — keyinchalik Redis backend'iga ko'chirish mumkin (interfeys o'zgarmaydi).

Staleness: natija eng ko'pi `_TTL_SECONDS` eski bo'lishi mumkin — real-time
dashboard uchun (frontend baribir har 5s so'raydi) bu maqbul.
"""

from __future__ import annotations

import threading
import time
from datetime import date

from sqlalchemy.orm import Session

from app.schemas.dashboard_stats import DashboardStatsResponse
from app.services.session_dashboard_stats import get_dashboard_stats

# Kesh yashash muddati (sekund). Frontend polling ~5s; 4s TTL bir polling
# oynasidagi barcha bir vaqtli so'rovlarni bitta hisobga yig'adi, staleness
# esa <= 4s bo'lib qoladi.
_TTL_SECONDS = 4.0

# key -> (expiry_monotonic, DashboardStatsResponse)
_cache: dict[tuple, tuple[float, DashboardStatsResponse]] = {}
# Kesh dict va _key_locks ni himoya qiluvchi yengil, qisqa ushlab turiladigan qulf.
_cache_lock = threading.Lock()
# Har kalit uchun single-flight qulfi (bir kalitni bir vaqtda faqat bitta
# thread hisoblaydi).
_key_locks: dict[tuple, threading.Lock] = {}


def _make_key(
    session_id: int,
    scope: str,
    session_smena_id: int | None,
    day: date | None,
) -> tuple:
    return (
        int(session_id),
        str(scope),
        int(session_smena_id) if session_smena_id is not None else None,
        day.isoformat() if day is not None else None,
    )


def _get_key_lock(key: tuple) -> threading.Lock:
    with _cache_lock:
        lk = _key_locks.get(key)
        if lk is None:
            lk = threading.Lock()
            _key_locks[key] = lk
        return lk


def _read_fresh(key: tuple, now: float) -> DashboardStatsResponse | None:
    with _cache_lock:
        hit = _cache.get(key)
        if hit is not None and hit[0] > now:
            return hit[1]
    return None


def _store(key: tuple, value: DashboardStatsResponse) -> None:
    now = time.monotonic()
    with _cache_lock:
        _cache[key] = (now + _TTL_SECONDS, value)
        # Yengil tozalash — eskirgan yozuvlarni olib tashlaymiz (kalitlar soni
        # kichik: aktiv sessiyalar × scope, shuning uchun bu arzon).
        if len(_cache) > 64:
            expired = [k for k, (exp, _) in _cache.items() if exp <= now]
            for k in expired:
                _cache.pop(k, None)


def get_dashboard_stats_cached(
    db: Session,
    *,
    session_id: int,
    scope: str,
    session_smena_id: int | None = None,
    day: date | None = None,
) -> DashboardStatsResponse:
    """`get_dashboard_stats` ning keshli + single-flight varianti.

    Real-time polling endpointi shu funksiyani chaqiradi. Argumentlar va
    qaytish qiymati `get_dashboard_stats` bilan bir xil.
    """
    key = _make_key(session_id, scope, session_smena_id, day)

    # 1) Tez yo'l — yangi kesh bo'lsa, darhol qaytaramiz (DB'ga tegmaymiz).
    fresh = _read_fresh(key, time.monotonic())
    if fresh is not None:
        return fresh

    # 2) Kesh yo'q/eskirgan — single-flight: bu kalit uchun faqat bitta thread
    #    hisoblaydi, qolganlari qulfda kutib, natijani qayta o'qiydi.
    lock = _get_key_lock(key)
    with lock:
        # Qulfni kutib turgan vaqtda boshqa thread hisoblab qo'ygan bo'lishi
        # mumkin — qayta tekshiramiz.
        fresh = _read_fresh(key, time.monotonic())
        if fresh is not None:
            return fresh

        # Faqat bitta thread shu yergacha yetadi — DB'dan bir marta hisoblaydi.
        result = get_dashboard_stats(
            db,
            session_id=session_id,
            scope=scope,
            session_smena_id=session_smena_id,
            day=day,
        )
        _store(key, result)
        return result


def invalidate_dashboard_stats() -> None:
    """Butun keshni tozalaydi (test yoki ma'lumot o'zgarishida qo'l bilan
    chaqirish uchun). Odatda TTL o'zi yetarli."""
    with _cache_lock:
        _cache.clear()
