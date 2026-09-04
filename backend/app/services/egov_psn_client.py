"""E-GOV PSN (pasport) API klienti — PINFL bo'yicha joriy hujjatni olish.

Ikki bosqichli oqim:

1. `API_GET_TOKEN_EGOV` ga POST → javobdan `{"token_type": "Bearer",
   "access_token": "...", "expires_in": 3600}` olinadi. Token ~1 soat amal
   qiladi, shuning uchun modul darajasida (protsess ichida, lock bilan)
   keshlanadi — har bir PINFL uchun qayta so'ralmaydi.
2. `API_PSN_EGOV` ga shu token bilan POST yuboriladi. Javobdagi
   `data[0].current_document` ("AD2381171") seriya va raqamga ajratiladi.

So'rov tanasidagi `birth_date` tashqaridan olinmaydi — PINFL ning o'zidan
hisoblanadi (1-belgi = asr, 2-7 belgilar = kun/oy/yil).

Klient sinxron (`httpx.Client`) — chaqiruvchi endpoint ham sinxron. Ko'p
PINFL uchun `fetch_documents()` ThreadPoolExecutor bilan parallel ishlaydi,
429 kelganda esa barcha threadlar birgalikda sekinlashadi (`_RateGate`).
"""

from __future__ import annotations

import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger("faceid.services.egov_psn")

# Bitta PINFL uchun maksimal urinish soni (429 / 5xx / tarmoq xatosi).
MAX_RETRIES = 3
# Parallel so'rovlar soni — tashqi tizim limitiga urilib qolmaslik uchun kichik.
DEFAULT_WORKERS = 5
# `Retry-After` header bo'lmasa shuncha soniya kutamiz.
DEFAULT_RETRY_AFTER = 5.0
# Header'dan olingan kutish vaqti shu oraliqqa qisiladi.
_MIN_RETRY_AFTER = 1.0
_MAX_RETRY_AFTER = 120.0
# Token muddati tugashidan shuncha soniya oldin yangilaymiz (zapas).
_TOKEN_EXPIRY_SKEW = 60.0
# Javobda `expires_in` bo'lmasa — 1 soat deb hisoblaymiz.
_DEFAULT_TOKEN_TTL = 3600.0
# Bitta HTTP so'rov uchun timeout.
_HTTP_TIMEOUT = 30.0

# So'rov tanasidagi o'zgarmas maydonlar — tashqi tizim shartnomasi.
_LANG_ID = 3
_IS_CONSENT = "Y"
_IS_PHOTO = "N"
# DIQQAT: kirillcha "М" (U+041C), lotincha "M" emas — tashqi tizim shu qiymatni kutadi.
_SENDER = "М"

# "AD2381171" / "AD 2381171" / "AD-2381171" -> ("AD", "2381171")
_DOC_RE = re.compile(r"^\s*([A-Za-z]{1,5})[\s\-]*(\d{1,10})\s*$")

# PINFL 1-belgisi -> tug'ilgan asr.
_CENTURY_BY_PREFIX: dict[str, int] = {
    "1": 1800,
    "2": 1800,
    "3": 1900,
    "4": 1900,
    "5": 2000,
    "6": 2000,
}


class EgovNotConfigured(Exception):
    """`API_GET_TOKEN_EGOV` / `API_PSN_EGOV` sozlanmagan."""


class EgovAuthError(Exception):
    """Token olishda xatolik — sozlama yoki tashqi tizim muammosi."""


class EgovError(Exception):
    """Bitta PINFL uchun so'rov muvaffaqiyatsiz tugadi."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable


@dataclass(frozen=True)
class PsnDocument:
    """PSN javobidan ajratib olingan joriy pasport."""

    pinfl: str
    ps_ser: str
    ps_num: str


# ─── Yordamchi (pure) funksiyalar ─────────────────────────────────────────


def birth_date_from_pinfl(pinfl: str) -> str | None:
    if not pinfl or len(pinfl) != 14 or not pinfl.isdigit():
        return None
    century = _CENTURY_BY_PREFIX.get(pinfl[0])
    if century is None:
        return None
    day, month, yy = int(pinfl[1:3]), int(pinfl[3:5]), int(pinfl[5:7])
    try:
        return date(century + yy, month, day).isoformat()
    except ValueError:
        return None


def split_document(doc: str) -> tuple[str, str] | None:
    m = _DOC_RE.match(doc or "")
    return (m.group(1).upper(), m.group(2)) if m else None


def parse_retry_after(resp: httpx.Response) -> float:
    """429 javobidan kutish vaqtini (soniya) ajratadi."""
    for header in ("Retry-After", "X-RateLimit-Reset", "RateLimit-Reset"):
        value = resp.headers.get(header)
        if not value:
            continue
        try:
            return min(max(float(value), _MIN_RETRY_AFTER), _MAX_RETRY_AFTER)
        except ValueError:
            continue
    return DEFAULT_RETRY_AFTER


def _backoff(attempt: int) -> float:
    """Eksponensial kutish + tasodifiy qo'shimcha (thundering herd'ga qarshi)."""
    return min(2**attempt, 30.0) + random.uniform(0, 1.0)


class _RateGate:
    """429 kelganda barcha threadlarni birgalikda sekinlashtiruvchi darvoza."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._blocked_until = 0.0

    def wait(self) -> None:
        while True:
            with self._lock:
                delay = self._blocked_until - time.monotonic()
            if delay <= 0:
                return
            time.sleep(min(delay, 5.0))

    def penalize(self, seconds: float) -> None:
        with self._lock:
            self._blocked_until = max(
                self._blocked_until, time.monotonic() + seconds
            )


# ─── Access token (keshlanadi) ────────────────────────────────────────────

_token_lock = threading.Lock()
_token_value: str | None = None
_token_expires_at = 0.0  # time.monotonic() shkalasida


def _error_snippet(resp: httpx.Response) -> str:
    """Xato xabariga qo'shish uchun javob tanasining qisqa parchasi."""
    try:
        # split()/join() — qator uzilishlarini bitta bo'shliqqa keltiradi.
        text = " ".join(resp.text.split())
    except Exception:  # noqa: BLE001
        return ""
    return f" — {text[:200]}" if text else ""


def _request_token(timeout: float) -> tuple[str, float]:
    """Token endpointiga POST — `(access_token, ttl_seconds)` qaytaradi.

    `grant_type`/`username`/`password` `API_GET_TOKEN_EGOV` URL ning query
    qismida keladi, shuning uchun tana yuborilmaydi. Tashqi tizim shartnomasi:
    `Content-Type: application/json` va `Authorization` headerida `.env` dagi
    `API_AUTH_TOKEN` qiymati (qanday berilgan bo'lsa, o'zgartirishsiz).
    """
    url = settings.API_GET_TOKEN_EGOV
    auth = settings.API_AUTH_TOKEN_EGOV.strip()
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if auth:
        headers["Authorization"] = f"Basic {auth}"

    try:
        # verify=False — GTSP klienti bilan bir xil sabab: e-gov sertifikat
        # zanjiri to'liq emas, aks holda har bir so'rov SSL xatosiga uchraydi.
        with httpx.Client(timeout=timeout, verify=True) as client:
            resp = client.post(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        detail = _error_snippet(exc.response)
        if exc.response.status_code in (401, 403) and not auth:
            detail += (
                " | `.env` dagi API_AUTH_TOKEN bo'sh — token endpointi "
                "`Authorization` headerini talab qiladi."
            )
        raise EgovAuthError(
            f"Token olishda HTTP xatolik: {exc.response.status_code}{detail}"
        ) from exc
    except httpx.HTTPError as exc:
        raise EgovAuthError(f"Token olishda ulanish xatoligi: {exc}") from exc
    except ValueError as exc:
        raise EgovAuthError(f"Token javobi JSON emas: {exc}") from exc

    if not isinstance(data, dict):
        raise EgovAuthError("Token javobi kutilgan formatda emas")

    token = str(data.get("access_token") or "").strip()
    if not token:
        raise EgovAuthError("Token javobida `access_token` topilmadi")

    try:
        ttl = float(data.get("expires_in") or _DEFAULT_TOKEN_TTL)
    except (TypeError, ValueError):
        ttl = _DEFAULT_TOKEN_TTL

    return token, ttl


def get_access_token(
    *, force_refresh: bool = False, timeout: float = _HTTP_TIMEOUT
) -> str:
    """Keshlangan tokenni qaytaradi, muddati tugagan bo'lsa yangilaydi."""
    global _token_value, _token_expires_at

    if not settings.API_GET_TOKEN_EGOV:
        raise EgovNotConfigured("API_GET_TOKEN_EGOV sozlamasi topilmadi")

    with _token_lock:
        now = time.monotonic()
        if not force_refresh and _token_value and now < _token_expires_at:
            return _token_value

        token, ttl = _request_token(timeout)
        _token_value = token
        # Muddat tugashidan sal oldin yangilanadigan qilib qo'yamiz.
        _token_expires_at = now + max(ttl - _TOKEN_EXPIRY_SKEW, 30.0)
        logger.info("E-GOV access token yangilandi (ttl=%.0fs)", ttl)
        return token


def reset_access_token() -> None:
    """Keshlangan tokenni bekor qiladi (testlar va qo'lda yangilash uchun)."""
    global _token_value, _token_expires_at
    with _token_lock:
        _token_value = None
        _token_expires_at = 0.0


# ─── PSN so'rovi ──────────────────────────────────────────────────────────


def _request_document(
    client: httpx.Client,
    pinfl: str,
    birth_date: str,
    transaction_id: int,
    gate: _RateGate,
) -> dict:
    """PSN API ga bitta so'rov (qayta urinishlar bilan). JSON javobni qaytaradi."""
    payload = {
        "transaction_id": transaction_id,
        "is_consent": _IS_CONSENT,
        "sender_pinfl": pinfl,
        "langId": _LANG_ID,
        "pinpp": pinfl,
        "birth_date": birth_date,
        "is_photo": _IS_PHOTO,
        "Sender": _SENDER,
    }
    url = settings.API_PSN_EGOV
    auth_refreshed = False
    last_error = "Noma'lum xatolik"

    for attempt in range(1, MAX_RETRIES + 1):
        gate.wait()
        token = get_access_token()
        try:
            resp = client.post(
                url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            last_error = f"Tarmoq xatosi: {exc}"
            if attempt == MAX_RETRIES:
                break
            time.sleep(_backoff(attempt))
            continue

        if resp.status_code == 429:
            wait = parse_retry_after(resp)
            gate.penalize(wait)
            last_error = "So'rovlar limiti (429)"
            if attempt == MAX_RETRIES:
                break
            time.sleep(wait + random.uniform(0, 1.5))
            continue

        if resp.status_code in (401, 403):
            # Token muddati tugagan bo'lishi mumkin — bir marta yangilab ko'ramiz.
            if auth_refreshed:
                last_error = f"Avtorizatsiya rad etildi (HTTP {resp.status_code})"
                break
            auth_refreshed = True
            get_access_token(force_refresh=True)
            continue

        if resp.status_code >= 500:
            last_error = f"Server xatosi (HTTP {resp.status_code})"
            if attempt == MAX_RETRIES:
                break
            time.sleep(_backoff(attempt))
            continue

        if resp.status_code >= 400:
            raise EgovError(f"So'rov rad etildi (HTTP {resp.status_code})")

        try:
            return resp.json()
        except ValueError as exc:
            raise EgovError(f"Javob JSON emas (HTTP {resp.status_code})") from exc

    raise EgovError(last_error, retryable=True)


def fetch_document(
    client: httpx.Client,
    pinfl: str,
    transaction_id: int,
    gate: _RateGate,
) -> PsnDocument:
    """Bitta PINFL uchun joriy pasport seriyasi/raqamini oladi.

    Raises:
        EgovError: PINFL formati xato, PSN rad etdi yoki tarmoq/HTTP xatosi.
    """
    birth_date = birth_date_from_pinfl(pinfl)
    if birth_date is None:
        raise EgovError("PINFL formati noto'g'ri — tug'ilgan sana aniqlanmadi")

    data = _request_document(client, pinfl, birth_date, transaction_id, gate)

    if str(data.get("result")) != "1":
        comments = data.get("comments") or data.get("comment") or ""
        detail = f": {comments}" if comments else ""
        raise EgovError(f"PSN rad etdi (result={data.get('result')}){detail}")

    try:
        doc = data["data"][0]["current_document"]
    except (KeyError, IndexError, TypeError):
        raise EgovError("Javobda `current_document` topilmadi") from None

    parts = split_document(str(doc or ""))
    if parts is None:
        raise EgovError(f"Hujjat formati noma'lum: {doc!r}")

    return PsnDocument(pinfl=pinfl, ps_ser=parts[0], ps_num=parts[1])


def fetch_documents(
    pinfls: list[str], *, workers: int = DEFAULT_WORKERS
) -> tuple[dict[str, PsnDocument], dict[str, str]]:
    """Bir nechta PINFL uchun pasportlarni parallel oladi.

    Returns:
        `(ok, errors)` — `ok[pinfl] = PsnDocument`, `errors[pinfl] = "sabab"`.

    Raises:
        EgovNotConfigured: sozlamalar bo'sh.
        EgovAuthError: token umuman olinmadi (hamma so'rov behuda bo'lardi).
    """
    if not settings.API_GET_TOKEN_EGOV or not settings.API_PSN_EGOV:
        raise EgovNotConfigured(
            "API_GET_TOKEN_EGOV / API_PSN_EGOV sozlamalari topilmadi"
        )

    # Takrorlarni olib tashlaymiz, tartibni saqlaymiz.
    unique = list(dict.fromkeys(p for p in pinfls if p))
    if not unique:
        return {}, {}

    # Tokenni oldindan olamiz — sozlama xato bo'lsa darhol xato qaytsin.
    get_access_token()

    gate = _RateGate()
    ok: dict[str, PsnDocument] = {}
    errors: dict[str, str] = {}
    max_workers = max(1, min(workers, len(unique)))

    with httpx.Client(timeout=_HTTP_TIMEOUT, verify=False) as client:
        with ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="psn"
        ) as pool:
            futures = {
                pool.submit(fetch_document, client, pinfl, tx_id, gate): pinfl
                for tx_id, pinfl in enumerate(unique, start=1)
            }
            for future in as_completed(futures):
                pinfl = futures[future]
                try:
                    ok[pinfl] = future.result()
                except EgovError as exc:
                    errors[pinfl] = exc.message
                except EgovNotConfigured as exc:
                    errors[pinfl] = str(exc)
                except EgovAuthError as exc:
                    errors[pinfl] = str(exc)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("PSN kutilmagan xatolik: pinfl=%s", pinfl)
                    errors[pinfl] = f"Kutilmagan xatolik: {exc}"

    logger.info(
        "PSN so'rov yakuni: jami=%d, olindi=%d, xato=%d",
        len(unique), len(ok), len(errors),
    )
    return ok, errors
