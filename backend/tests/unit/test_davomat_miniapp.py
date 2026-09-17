"""Davomat Mini App yordamchilari: verify ticket, pasport QR, rate-limit kaliti."""

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
    issue_verify_ticket,
    parse_passport_qr_text,
    read_verify_ticket,
    selfie_digest,
)

NOW = 1_780_000_000


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
