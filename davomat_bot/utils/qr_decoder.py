"""ID Card orqasidagi QR koddan pasport ma'lumotlarini ajratib olish.

QR matni tipik format: `AD 1234567#XXXXXXXXXXXXXX#...` yoki shunga
o'xshash bo'lishi mumkin. Bu yerda biz quyidagilarni qidiramiz:

* `ps_ser` — 2 ta lotin harfi (yoki kirill) + 7 ta raqam → seriya+raqam
* `jshshir` — 14 ta raqam (PINFL).

QR o'qish uchun `zxing-cpp` ishlatamiz — sof Python wheel orqali keladi
(pure C++ + pybind), tizim kutubxonalari kerakmas, aniqligi yuqori va
Windows/Linux/macOS da bir xil ishlaydi.

Bir nechta separator formatlarni (`#`, `|`, bo'sh joy) qabul qilamiz va
regex orqali ajratamiz.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import zxingcpp
from PIL import Image


@dataclass(frozen=True)
class PassportFromQR:
    ps_ser: str | None
    ps_num: str | None
    jshshir: str | None


def parse_passport_text(text: str) -> PassportFromQR:
    """QR ichidan matnli regex orqali ps_ser/ps_num/jshshir ni topish."""
    ps_match = text[5:14]
    ps_ser = ps_match[:2] if ps_match else None
    ps_num = ps_match[2:] if ps_match else None

    jshshir = text[15:29]
    return PassportFromQR(ps_ser=ps_ser, ps_num=ps_num, jshshir=jshshir)


def _result_text(result) -> str:
    """zxing-cpp natijasidan matnni xavfsiz tarzda ajratib olish.

    `result.text` ko'pincha mavjud, lekin ba'zi versiyalarda faqat
    `result.bytes` bo'ladi — har ikkala variantni qo'llab-quvvatlaymiz.
    """
    text = getattr(result, "text", None)
    if text:
        return text
    raw = getattr(result, "bytes", None)
    if raw is None:
        return ""
    try:
        return bytes(raw).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def decode_qr_from_bytes(image_bytes: bytes) -> PassportFromQR | None:
    """Rasm bytes'idan QR ni topib o'qish.

    Topilmasa None qaytaradi. Topilsa har bir QR matnini parselab birinchi
    "mos" yozuvni qaytaradi (`jshshir` topilgan bo'lsa ustuvor).
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()
    except Exception:
        return None

    # ID card QR fotosi ko'pincha katta rezolyutsiyada keladi — zxing-cpp
    # to'g'ri ishlash uchun rasmni RGB ga o'tkazamiz.
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    try:
        results = zxingcpp.read_barcodes(img, formats=zxingcpp.BarcodeFormat.QRCode)
    except Exception:
        return None

    best: PassportFromQR | None = None
    for r in results:
        text = _result_text(r)
        if not text:
            continue
        parsed = parse_passport_text(text)
        if parsed.jshshir and parsed.ps_ser and parsed.ps_num:
            return parsed
        if best is None:
            best = parsed
    return best
