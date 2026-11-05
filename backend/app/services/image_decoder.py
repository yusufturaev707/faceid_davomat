"""Markazlashtirilgan rasm dekodlash va validatsiya moduli.

Barcha base64 rasm dekodlash shu yerda — DRY printsipi.
Faqat cv2 ishlatiladi, PIL/Pillow yo'q.
"""

import base64
import binascii
import logging
import re

import cv2
import numpy as np
from fastapi import HTTPException, status

from app.config import settings

logger = logging.getLogger("faceid.image_decoder")

# Magic bytes — rasm formatini aniqlash
_MAGIC_SIGNATURES: list[tuple[str, bytes, int]] = [
    ("JPEG", b"\xff\xd8\xff", 0),
    ("PNG", b"\x89PNG", 0),
    ("BMP", b"BM", 0),
]
# Dekompressiya bomba himoyasi — kichik base64 katta pixel arrayga aylanishi mumkin
# (PNG flat-color). 64MP smartphone fotolariga yetadi. `app/__init__.py` dagi
# OPENCV_IO_MAX_IMAGE_PIXELS bilan bir xil bo'lishi kerak.
MAX_IMAGE_PIXELS = 64 * 1024 * 1024

# WebP — RIFF header, bytes[8:12] == b"WEBP"
_WEBP_RIFF_OFFSET = 8
_WEBP_MAGIC = b"WEBP"


def detect_image_format(img_bytes: bytes) -> str | None:
    """Rasm formatini magic bytes orqali aniqlash (JPEG, PNG, WebP, BMP). Rasm bo'lmasa — None."""
    for fmt, magic, offset in _MAGIC_SIGNATURES:
        if img_bytes[offset : offset + len(magic)] == magic:
            return fmt

    # WebP: RIFF....WEBP
    if (
        len(img_bytes) >= 12
        and img_bytes[:4] == b"RIFF"
        and img_bytes[_WEBP_RIFF_OFFSET:_WEBP_RIFF_OFFSET + 4] == _WEBP_MAGIC
    ):
        return "WebP"
    return None


def _validate_magic_bytes(img_bytes: bytes) -> str:
    """Rasm formatini magic bytes orqali aniqlash.

    Args:
        img_bytes: Xom rasm baytlari.

    Returns:
        Aniqlangan format nomi (JPEG, PNG, WebP, BMP).

    Raises:
        HTTPException: Format aniqlanmasa.
    """
    fmt = detect_image_format(img_bytes)
    if fmt is not None:
        return fmt

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Noto'g'ri rasm formati. Faqat JPEG, PNG, WebP, BMP qo'llab-quvvatlanadi",
    )


def decode_image_bytes(img_bytes: bytes) -> tuple[np.ndarray, int]:
    """Xom rasm baytlarini validatsiya qilib BGR numpy arrayga aylantirish.

    Args:
        img_bytes: Xom (binary) rasm baytlari.

    Returns:
        (img_bgr, file_size_bytes) — BGR numpy array va fayl hajmi.

    Raises:
        HTTPException 400: Validatsiya xatoliklari.
    """
    if not img_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasm bo'sh",
        )

    file_size = len(img_bytes)

    # Magic bytes validatsiya
    if file_size < 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasm juda kichik yoki buzilgan",
        )
    detected_format = _validate_magic_bytes(img_bytes)
    logger.debug("Rasm formati aniqlandi: %s, hajmi: %d bytes", detected_format, file_size)

    # cv2.imdecode — BGR formatda. Piksel chegarasidan oshgan rasmni OpenCV
    # xotira ajratmasdan rad etadi (`OPENCV_IO_MAX_IMAGE_PIXELS`, app/__init__.py)
    # va cv2.error tashlaydi.
    np_arr = np.frombuffer(img_bytes, np.uint8)
    try:
        img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    except cv2.error as exc:
        logger.warning("cv2.imdecode rad etdi (piksel chegarasi yoki buzilgan): %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasm o'lchami juda katta yoki rasm buzilgan",
        )

    if img_bgr is None:
        logger.warning("cv2.imdecode None qaytardi — buzilgan rasm")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmni ochishda xatolik: buzilgan yoki yaroqsiz rasm",
        )

    # Ikkinchi qatlam — env o'zgaruvchisi tashqaridan kattaroq qilib qo'yilgan bo'lsa.
    h, w = img_bgr.shape[:2]
    if h * w > MAX_IMAGE_PIXELS:
        logger.warning("Pixel chegarasidan oshgan rasm: %dx%d = %d pixel", w, h, h * w)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rasm o'lchami juda katta: {w}x{h}",
        )

    # Katta rasmni resize
    max_dim = settings.MAX_IMAGE_DIMENSION
    if max(h, w) > max_dim:
        scale = max_dim / max(h, w)
        img_bgr = cv2.resize(img_bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        logger.debug("Rasm o'lchami o'zgartirildi: %dx%d -> %dx%d", w, h, img_bgr.shape[1], img_bgr.shape[0])

    return img_bgr, file_size


def decode_base64_image(img_b64: str) -> tuple[np.ndarray, int]:
    """Base64 rasmni dekodlash, validatsiya qilish va BGR numpy arrayga aylantirish.

    Args:
        img_b64: Base64 kodlangan rasm (data URL yoki sof base64).

    Returns:
        (img_bgr, file_size_bytes) — BGR numpy array va fayl hajmi.

    Raises:
        HTTPException 400: Validatsiya xatoliklari.
    """
    # 1. Data URL prefiksini olib tashlash
    if "," in img_b64:
        img_b64 = img_b64.split(",", 1)[1]

    # 2. Base64 hajm tekshiruvi
    raw_size = len(img_b64)
    if raw_size > settings.MAX_BASE64_SIZE:
        max_mb = settings.MAX_BASE64_SIZE // (1024 * 1024)
        logger.warning("Base64 hajm chegaradan oshdi: %d bytes (max: %d MB)", raw_size, max_mb)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rasm hajmi {max_mb}MB dan oshmasligi kerak",
        )

    # 3. Base64 dekodlash
    try:
        img_bytes = base64.b64decode(img_b64)
    except (ValueError, base64.binascii.Error) as exc:
        logger.warning("Base64 dekodlash xatosi: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base64 dekodlash xatosi: yaroqsiz format",
        )

    return decode_image_bytes(img_bytes)


# ─── DB ga (BYTEA) xom holda yoziladigan rasmlar ─────────────────────────
#
# Passport rasmi (`StudentPsData.ps_img`) va desktop selfie'lari
# (`StudentLog.first/last_captured`) qayta kodlanmasdan saqlanadi. Ular
# keyin embedding bosqichida ochiladi va admin panelda ko'rsatiladi — shuning
# uchun DB ga faqat rasmga o'xshagan, chegaralangan hajmdagi baytlar yoziladi.

MIN_STORED_IMAGE_BYTES = 512  # 512 B dan kichigi rasm bo'lishi mumkin emas
MAX_STORED_IMAGE_BYTES = 3 * 1024 * 1024  # 3 MB
# Base64 satr chegarasi (schema `max_length` uchun): 3 MB → ~4 MB base64 + data-URL prefiksi.
MAX_STORED_IMAGE_B64_LEN = 4_200_000

# `data:image/jpeg;base64,....` shaklidagi data-URL prefiksi.
_DATA_URL_RE = re.compile(r"^data:[^;,]*;base64,", re.IGNORECASE)


def decode_image_b64_raw(value: str) -> tuple[bytes | None, str | None]:
    """base64 satrni (data-URL yoki sof base64) DB ga yoziladigan rasm baytlariga aylantiradi.

    Piksellar ochilmaydi (arzon): faqat base64 to'g'riligi, hajm va magic bytes.
    Qaytaradi: `(raw_bytes, None)` yoki xato bo'lsa `(None, "sabab")`.
    """
    text = (value or "").strip()
    if not text:
        return None, "Rasm bo'sh"
    if len(text) > MAX_STORED_IMAGE_B64_LEN:
        return None, f"Rasm hajmi {MAX_STORED_IMAGE_BYTES // (1024 * 1024)}MB dan oshmasin"

    text = _DATA_URL_RE.sub("", text)
    # Excel/matn muharrirlaridan nusxalanganda base64 ichiga qator uzilishi va
    # bo'shliqlar tushib qolishi mumkin — ularni olib tashlaymiz.
    text = re.sub(r"\s+", "", text)
    # URL-safe base64 (`-` va `_`) ni ham qabul qilamiz.
    text = text.replace("-", "+").replace("_", "/")
    # To'ldiruvchi `=` yetishmasa — qo'shib qo'yamiz.
    if len(text) % 4:
        text += "=" * (4 - len(text) % 4)

    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError):
        return None, "Base64 formati noto'g'ri"

    if len(raw) < MIN_STORED_IMAGE_BYTES:
        return None, "Rasm juda kichik (buzilgan bo'lishi mumkin)"
    if len(raw) > MAX_STORED_IMAGE_BYTES:
        return None, f"Rasm hajmi {MAX_STORED_IMAGE_BYTES // (1024 * 1024)}MB dan oshmasin"
    if detect_image_format(raw) is None:
        return None, "Bu rasm emas (JPEG/PNG/WebP/BMP kutilgan)"
    return raw, None
