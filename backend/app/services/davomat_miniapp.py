"""Davomat Mini App'ga xos yordamchilar.

Bot kanalida ishonchli server (bot jarayoni) Face ID natijasi va selfie'ni
o'zida saqlab, keyin `mark-attendance` ga yuborardi. Mini App'da klient —
foydalanuvchi qurilmasi, unga ishonib bo'lmaydi. Shuning uchun:

  - **Verify ticket** — `face-verify` muvaffaqiyatli bo'lsa backend imzolangan
    chipta beradi: kim (telegram_id), qaysi talabgor/smena/region, o'xshashlik
    foizi va selfie'ning SHA-256 xeshi. `mark-attendance` faqat shu chipta
    bilan ishlaydi — klient talabgorni, balni yoki selfie'ni almashtira olmaydi
    va Face ID'siz davomatga qo'sha olmaydi.
  - **Pasport QR** — ID-karta orqasidagi QR matnini (Telegram native skaneri)
    yoki QR rasmini (zxing-cpp) pasport maydonlariga ajratish.
  - **Telegram sendDocument** — kelmaganlar Excel'i foydalanuvchi chatiga
    yuboriladi (webview ichida fayl yuklab olish platformalarda ishonchsiz).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import re
import time
from collections.abc import Callable
from dataclasses import dataclass

import cv2
import httpx
import numpy as np

from app.config import settings
from app.core.logging import install_bot_token_redaction

logger = logging.getLogger("faceid.services.davomat_miniapp")
# sendDocument URL'ida bot tokeni bor — httpx uni INFO log'ga yozadi.
install_bot_token_redaction()


# ============================================================
# Verify ticket
# ============================================================

_TICKET_VERSION = "v1"
# SECRET_KEY'dan maqsadga bog'langan alohida kalit — JWT yoki boshqa imzolar
# bilan chalkashib ketmasligi uchun (domain separation).
_TICKET_KEY_LABEL = b"davomat-miniapp:verify-ticket:v1"


class TicketError(ValueError):
    """Chipta yaroqsiz yoki muddati o'tgan."""


@dataclass(frozen=True)
class VerifyTicket:
    telegram_id: int
    student_id: int
    session_smena_id: int
    region_id: int | None
    score: int
    selfie_sha256: str
    expires_at: int


def _ticket_key() -> bytes:
    return hmac.new(
        settings.SECRET_KEY.encode(), _TICKET_KEY_LABEL, hashlib.sha256
    ).digest()


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def selfie_digest(selfie_bytes: bytes) -> str:
    return hashlib.sha256(selfie_bytes).hexdigest()


def issue_verify_ticket(
    *,
    telegram_id: int,
    student_id: int,
    session_smena_id: int,
    region_id: int | None,
    score: int,
    selfie_sha256: str,
    now: float | None = None,
) -> str:
    current = int(time.time() if now is None else now)
    payload = {
        "tid": int(telegram_id),
        "sid": int(student_id),
        "ssid": int(session_smena_id),
        "rid": int(region_id) if region_id is not None else None,
        "sc": int(score),
        "sh": selfie_sha256,
        "exp": current + int(settings.DAVOMAT_MINIAPP_VERIFY_TTL),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode())
    signing_input = f"{_TICKET_VERSION}.{body}"
    sig = _b64url(hmac.new(_ticket_key(), signing_input.encode(), hashlib.sha256).digest())
    return f"{signing_input}.{sig}"


def read_verify_ticket(ticket: str, *, now: float | None = None) -> VerifyTicket:
    """Chipta imzosini va muddatini tekshirib, ichidagi ma'lumotni qaytaradi."""
    parts = (ticket or "").split(".")
    if len(parts) != 3 or parts[0] != _TICKET_VERSION:
        raise TicketError("Face ID tasdig'i yaroqsiz")

    signing_input = f"{parts[0]}.{parts[1]}"
    expected = _b64url(
        hmac.new(_ticket_key(), signing_input.encode(), hashlib.sha256).digest()
    )
    if not hmac.compare_digest(expected, parts[2]):
        raise TicketError("Face ID tasdig'i yaroqsiz")

    try:
        payload = json.loads(_b64url_decode(parts[1]))
        result = VerifyTicket(
            telegram_id=int(payload["tid"]),
            student_id=int(payload["sid"]),
            session_smena_id=int(payload["ssid"]),
            region_id=int(payload["rid"]) if payload["rid"] is not None else None,
            score=int(payload["sc"]),
            selfie_sha256=str(payload["sh"]),
            expires_at=int(payload["exp"]),
        )
    except (ValueError, KeyError, TypeError):
        raise TicketError("Face ID tasdig'i yaroqsiz")

    current = time.time() if now is None else now
    if current > result.expires_at:
        raise TicketError(
            "Face ID tasdig'i muddati tugagan. Talabgorni qaytadan tekshiring."
        )
    return result


# ============================================================
# Pasport QR (ID-karta orqasi)
# ============================================================

_PS_SER_RE = re.compile(r"^[A-Z]{2}$")
_PS_NUM_RE = re.compile(r"^\d{7}$")
_JSHSHIR_RE = re.compile(r"^\d{14}$")


class PassportQrError(ValueError):
    pass


@dataclass(frozen=True)
class PassportData:
    ps_ser: str
    ps_num: str
    jshshir: str


def parse_passport_qr_text(text: str) -> PassportData:
    """ID-karta QR matnidan pasport ma'lumotlarini ajratish.

    QR ichida MRZ (TD1) ning 1-qatori turadi:
      `IU` (hujjat turi) + `UZB` (davlat) + `AD1234567` (seriya+raqam, 9)
      + nazorat raqami (1) + JShShIR (14) + to'ldiruvchi `<`.
    Shuning uchun maydonlar qat'iy pozitsiyada: [5:14] va [15:29] — bot
    (`davomat_bot/utils/qr_decoder.py`) ishlatgan formula bilan bir xil.
    Bot'dan farqli — natija formatga tekshiriladi, xato QR GTSP'ga ketmaydi.
    """
    cleaned = (text or "").strip().upper()
    passport = cleaned[5:14]
    data = PassportData(
        ps_ser=passport[:2],
        ps_num=passport[2:],
        jshshir=cleaned[15:29],
    )
    if not (
        _PS_SER_RE.match(data.ps_ser)
        and _PS_NUM_RE.match(data.ps_num)
        and _JSHSHIR_RE.match(data.jshshir)
    ):
        raise PassportQrError(
            "QR koddan pasport ma'lumotlari o'qilmadi. ID-karta orqa tomonidagi "
            "QR kodni skanerlang yoki ma'lumotlarni qo'lda kiriting."
        )
    return data


def _read_qr_texts(gray: np.ndarray) -> list[str]:
    """Kadrdagi barcha QR matnlari. Dekoder xatosi — bo'sh ro'yxat.

    `import` atayin `try` dan tashqarida: zxing-cpp o'rnatilmagan bo'lsa
    `ImportError` endpointga chiqib, 503 + tushunarli xabar beradi.
    """
    import zxingcpp

    try:
        results = zxingcpp.read_barcodes(gray, formats=zxingcpp.BarcodeFormat.QRCode)
    except Exception:
        logger.exception("zxing-cpp QR o'qishda xatolik")
        return []
    return [result.text or "" for result in results]


def _unsharp(gray: np.ndarray, sigma: float, amount: float) -> np.ndarray:
    """Fokusi ketgan kadrni o'tkirlashtirish (unsharp mask)."""
    return cv2.addWeighted(gray, 1 + amount, cv2.GaussianBlur(gray, (0, 0), sigma), -amount, 0)


# QR o'qish urinishlari. zxing-cpp QR'ni har qanday burchakda va perspektiv
# qiyshiqlikda o'zi to'g'rilaydi (uchta burchak marker + alignment pattern) —
# sinovda tiniq kadrda 0–180° burilish va 65° gacha qiyshiqlik 100% o'qildi.
# Haqiqiy yiqilish sabablari: fokus ketishi va kadrda QR juda kichik bo'lishi.
# Shu ikkisiga qarshi bosqichlar (tartib va koeffitsientlar o'lchov asosida:
# har biri faqat oldingisi yiqilganda ishlaydi, eng yomon holat ~65 ms):
_QR_ATTEMPTS: tuple[tuple[str, Callable[[np.ndarray], np.ndarray]], ...] = (
    ("asl", lambda gray: gray),
    ("unsharp-2.5", lambda gray: _unsharp(gray, 2.5, 2.0)),
    ("unsharp-1.2", lambda gray: _unsharp(gray, 1.2, 1.2)),
    ("2x", lambda gray: cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)),
)


def decode_passport_qr_image(image_b64: str) -> PassportData:
    """QR rasmidan (base64) pasport ma'lumotlarini o'qish.

    Kadr xira yoki QR kichik bo'lsa bitta urinish yetmaydi — `_QR_ATTEMPTS`
    bo'yicha bosqichma-bosqich qayta o'qiladi. Rasmda boshqa QR ham bo'lishi
    mumkin (plakat, havola), shuning uchun har bir bosqichda topilgan barcha
    matnlar MRZ sifatida tekshiriladi.
    """
    from app.services.image_decoder import decode_base64_image

    img_bgr, _size = decode_base64_image(image_b64)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

    parse_error: PassportQrError | None = None
    for name, transform in _QR_ATTEMPTS:
        for text in _read_qr_texts(transform(gray)):
            try:
                data = parse_passport_qr_text(text)
            except PassportQrError as e:
                # QR bor, lekin ID-karta MRZ'i emas — keyingi matn/bosqichda
                # haqiqiy ID-karta topilishi mumkin.
                parse_error = e
                continue
            if name != "asl":
                logger.info("Pasport QR faqat `%s` bosqichida o'qildi — kadr xira yoki QR kichik", name)
            return data

    if parse_error is not None:
        raise parse_error
    raise PassportQrError(
        "Rasmda QR kod topilmadi. ID-kartani kadrni to'ldiradigan qilib, "
        "qimirlatmasdan va yorug' joyda suratga oling."
    )


# ============================================================
# Telegram Bot API — fayl yuborish
# ============================================================


class TelegramSendError(RuntimeError):
    def __init__(self, message: str, *, user_fixable: bool = False) -> None:
        super().__init__(message)
        self.user_fixable = user_fixable


def send_document_to_chat(
    *,
    chat_id: int,
    file_bytes: bytes,
    filename: str,
    caption: str,
    content_type: str,
) -> None:
    """Faylni bot nomidan foydalanuvchi chatiga yuborish.

    URL tarkibida bot tokeni bor: bu yerda URL ham, httpx istisnosining matni
    ham log qilinmaydi, httpx'ning o'z so'rov logi esa `BotTokenRedactFilter`
    orqali yashiriladi.
    """
    url = f"{settings.TELEGRAM_API_BASE.rstrip('/')}/bot{settings.DAVOMAT_BOT_TOKEN}/sendDocument"
    try:
        resp = httpx.post(
            url,
            data={"chat_id": str(chat_id), "caption": caption, "parse_mode": "HTML"},
            files={"document": (filename, file_bytes, content_type)},
            timeout=60,
        )
        payload = resp.json()
    except Exception as e:
        logger.error(
            "Telegram sendDocument ulanish xatoligi: %s (chat_id=%s)",
            type(e).__name__,
            chat_id,
        )
        raise TelegramSendError("Telegram serveriga ulanib bo'lmadi")

    if payload.get("ok"):
        return

    code = payload.get("error_code")
    description = str(payload.get("description") or "")
    logger.warning(
        "Telegram sendDocument rad etildi: code=%s description=%s chat_id=%s",
        code,
        description,
        chat_id,
    )
    if code in (400, 403):
        # "bot was blocked by the user" / "chat not found" — foydalanuvchi botni
        # to'xtatgan yoki hech qachon /start bosmagan.
        raise TelegramSendError(
            "Faylni chatga yuborib bo'lmadi. Botni oching, /start bosing va "
            "qayta urinib ko'ring.",
            user_fixable=True,
        )
    raise TelegramSendError("Telegram faylni qabul qilmadi. Keyinroq urinib ko'ring.")
