"""Davomat Mini App yordamchilari: verify ticket, pasport QR, rate-limit kaliti."""

import base64
import json
import time

import pytest
from starlette.requests import Request

from app.config import settings
from app.core.rate_limit import _identity_key
from app.core.telegram_webapp import sign_init_data
from app.services.davomat_miniapp import (
    PassportQrError,
    TicketError,
    _read_qr_texts,
    decode_passport_qr_image,
    issue_verify_ticket,
    parse_passport_qr_text,
    read_verify_ticket,
    selfie_digest,
)

NOW = 1_780_000_000
# TD1 MRZ 1-qatori: [5:14] seriya+raqam, [15:29] JShShIR.
MRZ_TEXT = "IUUZBAD12345674123456789012342<<<<"


def _ticket(**overrides) -> str:
    params = dict(
        telegram_id=42,
        student_id=1001,
        session_smena_id=7,
        region_id=3,
        score=87,
        selfie_sha256=selfie_digest(b"selfie"),
        now=NOW,
    )
    params.update(overrides)
    return issue_verify_ticket(**params)


def test_ticket_roundtrip():
    ticket = read_verify_ticket(_ticket(), now=NOW + 1)
    assert ticket.telegram_id == 42
    assert ticket.student_id == 1001
    assert ticket.session_smena_id == 7
    assert ticket.region_id == 3
    assert ticket.score == 87
    assert ticket.selfie_sha256 == selfie_digest(b"selfie")


def test_ticket_without_region_roundtrip():
    assert read_verify_ticket(_ticket(region_id=None), now=NOW).region_id is None


def test_ticket_payload_tampering_is_detected():
    version, body, sig = _ticket().split(".")
    forged = issue_verify_ticket(
        telegram_id=42,
        student_id=9999,
        session_smena_id=7,
        region_id=3,
        score=100,
        selfie_sha256="x",
        now=NOW,
    ).split(".")[1]
    with pytest.raises(TicketError):
        read_verify_ticket(f"{version}.{forged}.{sig}", now=NOW)


def test_ticket_signed_with_other_secret_is_rejected(monkeypatch):
    ticket = _ticket()
    monkeypatch.setattr(settings, "SECRET_KEY", "another-secret-key-0123456789abcdef")
    with pytest.raises(TicketError):
        read_verify_ticket(ticket, now=NOW)


def test_expired_ticket_is_rejected():
    ticket = _ticket()
    with pytest.raises(TicketError, match="muddati"):
        read_verify_ticket(ticket, now=NOW + settings.DAVOMAT_MINIAPP_VERIFY_TTL + 1)


@pytest.mark.parametrize("garbage", ["", "v1.abc", "v2.a.b", "v1.!!!.sig"])
def test_malformed_ticket_is_rejected(garbage):
    with pytest.raises(TicketError):
        read_verify_ticket(garbage, now=NOW)


def test_passport_qr_mrz_text_is_parsed():
    data = parse_passport_qr_text("IUUZBAD12345674123456789012342<<<<\n")
    assert (data.ps_ser, data.ps_num, data.jshshir) == ("AD", "1234567", "12345678901234")


@pytest.mark.parametrize(
    "text",
    ["", "https://example.com/some-qr", "IUUZBAD1234X674123456789012342", "IUUZB1234567AB12345678901234"],
)
def test_passport_qr_garbage_is_rejected(text):
    with pytest.raises(PassportQrError):
        parse_passport_qr_text(text)


# ── QR rasmidan o'qish ────────────────────────────────────────


def _qr_frame(*, rotate_deg: float = 0, blur_sigma: float = 0, qr_px: int = 300) -> str:
    """ID-karta QR'i tushgan kadr → base64 JPEG (klient yuboradigan ko'rinish)."""
    cv2 = pytest.importorskip("cv2")
    zxingcpp = pytest.importorskip("zxingcpp")
    np = pytest.importorskip("numpy")

    bitmap = np.array(
        zxingcpp.write_barcode(zxingcpp.BarcodeFormat.QRCode, MRZ_TEXT, quiet_zone=4)
    )
    if bitmap.ndim == 3:
        bitmap = bitmap[:, :, 0]
    qr = cv2.resize(bitmap, (qr_px, qr_px), interpolation=cv2.INTER_NEAREST)

    frame = np.full((1080, 1920), 150, np.uint8)
    y0, x0 = (1080 - qr_px) // 2, (1920 - qr_px) // 2
    frame[y0 : y0 + qr_px, x0 : x0 + qr_px] = qr
    if rotate_deg:
        m = cv2.getRotationMatrix2D((960, 540), rotate_deg, 1.0)
        frame = cv2.warpAffine(frame, m, (1920, 1080), borderValue=150)
    if blur_sigma:
        frame = cv2.GaussianBlur(frame, (0, 0), blur_sigma)

    ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    assert ok
    return base64.b64encode(buf).decode("ascii")


@pytest.mark.parametrize("rotate_deg", [0, 23, 45, 90, 180])
def test_qr_image_is_read_at_any_rotation(rotate_deg):
    """QR uchta burchak markeriga tayanadi — burilish dekodlashga xalal bermaydi."""
    data = decode_passport_qr_image(_qr_frame(rotate_deg=rotate_deg))
    assert (data.ps_ser, data.ps_num, data.jshshir) == ("AD", "1234567", "12345678901234")


def test_blurred_qr_is_recovered_by_sharpening():
    """Fokusi ketgan kadr: to'g'ridan-to'g'ri o'qib bo'lmaydi, `unsharp` qutqaradi."""
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    frame = _qr_frame(blur_sigma=3.0, qr_px=220)

    raw = cv2.cvtColor(
        cv2.imdecode(np.frombuffer(base64.b64decode(frame), np.uint8), cv2.IMREAD_COLOR),
        cv2.COLOR_BGR2GRAY,
    )
    assert _read_qr_texts(raw) == [], "kadr birinchi urinishda o'qilmasligi kerak"

    assert decode_passport_qr_image(frame).jshshir == "12345678901234"


def test_qr_image_without_barcode_is_rejected():
    cv2 = pytest.importorskip("cv2")
    np = pytest.importorskip("numpy")
    ok, buf = cv2.imencode(".jpg", np.full((400, 400), 200, np.uint8))
    assert ok
    with pytest.raises(PassportQrError, match="QR kod topilmadi"):
        decode_passport_qr_image(base64.b64encode(buf).decode("ascii"))


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "client": ("10.0.0.5", 1234),
        }
    )


def test_rate_limit_key_uses_verified_telegram_user(monkeypatch):
    monkeypatch.setattr(settings, "DAVOMAT_BOT_TOKEN", "123:token")
    fields = {"auth_date": str(int(time.time())), "user": json.dumps({"id": 555})}
    init_data = sign_init_data(fields, "123:token")
    assert _identity_key(_request({"Authorization": f"tma {init_data}"})) == "tg:555"


def test_rate_limit_key_ignores_forged_init_data(monkeypatch):
    monkeypatch.setattr(settings, "DAVOMAT_BOT_TOKEN", "123:token")
    forged = sign_init_data({"auth_date": "2000000000", "user": '{"id": 1}'}, "999:other")
    assert _identity_key(_request({"Authorization": f"tma {forged}"})) == "ip:10.0.0.5"


def test_httpx_log_does_not_leak_bot_token(caplog):
    import logging

    import app.services.davomat_miniapp  # noqa: F401 — filtrni o'rnatadi

    with caplog.at_level(logging.INFO, logger="httpx"):
        logging.getLogger("httpx").info(
            'HTTP Request: %s %s "%s"',
            "POST",
            "https://api.telegram.org/bot123456:AAF-secret_token/sendDocument",
            "HTTP/1.1 200 OK",
        )
    assert "AAF-secret_token" not in caplog.text
    assert "/bot***/sendDocument" in caplog.text
