"""Markazlashtirilgan rasm dekodlash va validatsiya moduli.

Barcha base64 rasm dekodlash shu yerda — DRY printsipi.
Faqat cv2 ishlatiladi, PIL/Pillow yo'q.
"""

import base64
import logging

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
# WebP — RIFF header, bytes[8:12] == b"WEBP"
_WEBP_RIFF_OFFSET = 8
_WEBP_MAGIC = b"WEBP"


def _validate_magic_bytes(img_bytes: bytes) -> str:
    """Rasm formatini magic bytes orqali aniqlash.

    Args:
        img_bytes: Xom rasm baytlari.

    Returns:
        Aniqlangan format nomi (JPEG, PNG, WebP, BMP).

    Raises:
        HTTPException: Format aniqlanmasa.
    """
    for fmt, magic, offset in _MAGIC_SIGNATURES:
        if img_bytes[offset : offset + len(magic)] == magic:
            return fmt

    # WebP: RIFF....WEBP
    if len(img_bytes) >= 12 and img_bytes[_WEBP_RIFF_OFFSET:_WEBP_RIFF_OFFSET + 4] == _WEBP_MAGIC:
        return "WebP"

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

    # cv2.imdecode — BGR formatda
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    if img_bgr is None:
        logger.warning("cv2.imdecode None qaytardi — buzilgan rasm")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Rasmni ochishda xatolik: buzilgan yoki yaroqsiz rasm",
        )

    # Dekompressiya bomba himoyasi — kichik base64 katta pixel arrayga aylanishi mumkin (PNG flat-color).
    # 64MP chegarasi: smartphone fotolariga yetadi, lekin 20k×20k bomba'ni rad etadi.
    h, w = img_bgr.shape[:2]
    MAX_PIXELS = 64 * 1024 * 1024
    if h * w > MAX_PIXELS:
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
