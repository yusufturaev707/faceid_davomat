"""Rasm yuklash himoyalari: dekompressiya bombasi va DB ga yoziladigan base64 rasm."""

import base64
import os

import cv2
import numpy as np
import pytest
from fastapi import HTTPException

from app.services.image_decoder import (
    MAX_IMAGE_PIXELS,
    MAX_STORED_IMAGE_BYTES,
    decode_image_b64_raw,
    decode_image_bytes,
)


def _jpeg_bytes(w: int = 64, h: int = 64) -> bytes:
    img = np.random.default_rng(0).integers(0, 255, (h, w, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    assert ok
    return buf.tobytes()


def test_opencv_pixel_limit_set_before_cv2_import():
    # app/__init__.py cv2 import qilinishidan oldin o'rnatadi
    assert os.environ["OPENCV_IO_MAX_IMAGE_PIXELS"] == str(MAX_IMAGE_PIXELS)


def test_decompression_bomb_rejected_without_decoding():
    # 8200×8200 bir rangli PNG — bir necha yuz KB, ochilsa ~200 MB BGR bo'lardi
    side = 8200
    ok, buf = cv2.imencode(".png", np.zeros((side, side), np.uint8))
    assert ok and buf.nbytes < 1024 * 1024
    with pytest.raises(HTTPException) as exc:
        decode_image_bytes(buf.tobytes())
    assert exc.value.status_code == 400


def test_normal_image_still_decodes():
    img, size = decode_image_bytes(_jpeg_bytes())
    assert img.shape == (64, 64, 3)
    assert size > 0


def test_b64_raw_accepts_jpeg_and_data_url():
    raw = _jpeg_bytes()
    b64 = base64.b64encode(raw).decode()
    assert decode_image_b64_raw(b64) == (raw, None)
    assert decode_image_b64_raw("data:image/jpeg;base64," + b64) == (raw, None)


@pytest.mark.parametrize(
    "payload",
    [
        base64.b64encode(b"<html><script>alert(1)</script></html>" * 30).decode(),
        base64.b64encode(b"%PDF-1.7" + b"\0" * 1000).decode(),
        "bu base64 emas!!!",
        "",
    ],
)
def test_b64_raw_rejects_non_images(payload):
    raw, err = decode_image_b64_raw(payload)
    assert raw is None and err


def test_b64_raw_rejects_too_large():
    big = b"\xff\xd8\xff" + b"\0" * MAX_STORED_IMAGE_BYTES
    raw, err = decode_image_b64_raw(base64.b64encode(big).decode())
    assert raw is None and "MB" in err


# --- Talabani tahrirlash formasi (crud.update_student) ---


def _ps(ps_img=None, embedding=None):
    from types import SimpleNamespace

    return SimpleNamespace(ps_img=ps_img, embedding=embedding)


def test_ps_fields_unchanged_values_not_revalidated():
    from app.crud.student import _decode_ps_binary_fields

    # Eski yozuvdagi yaroqsiz rasm/embedding formani saqlashga to'sqinlik qilmasin
    old_img, old_emb = b"legacy-not-an-image", b"\1" * 100
    update = {
        "ps_img": base64.b64encode(old_img).decode(),
        "embedding": base64.b64encode(old_emb).decode(),
    }
    assert _decode_ps_binary_fields(_ps(old_img, old_emb), update) == (False, False)
    assert update == {"ps_img": old_img, "embedding": old_emb}


def test_ps_fields_new_non_image_rejected():
    from app.crud.student import _decode_ps_binary_fields

    update = {"ps_img": base64.b64encode(b"<svg onload=alert(1)>" * 50).decode()}
    with pytest.raises(ValueError):
        _decode_ps_binary_fields(_ps(), update)


def test_ps_fields_new_image_and_embedding():
    from app.crud.student import _decode_ps_binary_fields

    raw = _jpeg_bytes()
    update = {"ps_img": base64.b64encode(raw).decode()}
    assert _decode_ps_binary_fields(_ps(b"old"), update) == (True, False)
    assert update["ps_img"] == raw

    with pytest.raises(ValueError):
        _decode_ps_binary_fields(_ps(), {"embedding": base64.b64encode(b"\0" * 100).decode()})
    emb = np.zeros(512, np.float32).tobytes()
    update = {"embedding": base64.b64encode(emb).decode()}
    assert _decode_ps_binary_fields(_ps(), update) == (False, True)
