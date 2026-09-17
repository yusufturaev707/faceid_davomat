"""Davomat Mini App endpointlari — autentifikatsiya va Face ID chiptasi.

SQLite test bazasida `student_logs` (INET) jadvali yaratilmaydi, shuning uchun
DB ga bog'liq qismlar (`get_bot_by_telegram_id`, service funksiyalar)
monkeypatch qilinadi — bu yerda HTTP/auth qatlami tekshiriladi.
"""

import base64
import json
import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints import davomat_miniapp as endpoint
from app.config import settings
from app.core.telegram_webapp import sign_init_data
from app.dependencies import get_db
from app.main import app
from app.schemas.davomat_bot import (
    BotFaceVerifyResponse,
    BotMarkAttendanceResponse,
    BotStudentSlot,
)
from app.services.davomat_miniapp import (
    issue_verify_ticket,
    read_verify_ticket,
    selfie_digest,
)

BOT_TOKEN = "123456:MINIAPP-test-token"
TELEGRAM_ID = 700100200
SELFIE = b"\xff\xd8\xff\xe0fake-jpeg-bytes"
SELFIE_B64 = base64.b64encode(SELFIE).decode()


def _init_data(telegram_id: int = TELEGRAM_ID, bot_token: str = BOT_TOKEN) -> str:
    return sign_init_data(
        {
            "auth_date": str(int(time.time())),
            "user": json.dumps({"id": telegram_id, "first_name": "Test"}),
        },
        bot_token,
    )


def _auth(telegram_id: int = TELEGRAM_ID) -> dict[str, str]:
    return {"Authorization": f"tma {_init_data(telegram_id)}"}


@pytest.fixture
def api(monkeypatch):
    monkeypatch.setattr(settings, "DAVOMAT_BOT_TOKEN", BOT_TOKEN)
    monkeypatch.setattr(settings, "DAVOMAT_MINIAPP_USER_ID", 1)
    app.dependency_overrides[get_db] = lambda: MagicMock()
    # Lifespan (DB ping, InsightFace) ishga tushmasligi uchun context manager'siz.
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def operator(monkeypatch):
    bot = SimpleNamespace(telegram_id=TELEGRAM_ID, allowed_region_ids={3})
    monkeypatch.setattr(
        endpoint,
        "get_bot_by_telegram_id",
        lambda _db, tid: bot if tid == TELEGRAM_ID else None,
    )
    return bot


def test_unconfigured_miniapp_returns_503(api, monkeypatch):
    monkeypatch.setattr(settings, "DAVOMAT_BOT_TOKEN", "")
    r = api.get("/api/v1/davomat-miniapp/me", headers=_auth())
    assert r.status_code == 503


def test_missing_authorization_returns_401(api):
    assert api.get("/api/v1/davomat-miniapp/me").status_code == 401


def test_bearer_scheme_is_not_accepted(api):
    r = api.get("/api/v1/davomat-miniapp/me", headers={"Authorization": "Bearer x"})
    assert r.status_code == 401


def test_api_key_is_rejected(api):
    headers = {**_auth(), "X-API-Key": "sk-something"}
    assert api.get("/api/v1/davomat-miniapp/me", headers=headers).status_code == 400


def test_init_data_signed_by_other_bot_returns_401(api):
    headers = {"Authorization": f"tma {_init_data(bot_token='1:other')}"}
    assert api.get("/api/v1/davomat-miniapp/me", headers=headers).status_code == 401


def test_me_for_unregistered_user_exposes_telegram_id(api, operator):
    r = api.get("/api/v1/davomat-miniapp/me", headers=_auth(telegram_id=5))
    assert r.status_code == 200
    body = r.json()
    assert body["allowed"] is False
    assert body["telegram_id"] == 5


def test_operator_endpoints_require_registered_user(api, operator):
    r = api.get("/api/v1/davomat-miniapp/sessions", headers=_auth(telegram_id=5))
    assert r.status_code == 403


def _mark(api, ticket: str, selfie_b64: str = SELFIE_B64, telegram_id: int = TELEGRAM_ID):
    return api.post(
        "/api/v1/davomat-miniapp/mark-attendance",
        headers=_auth(telegram_id),
        json={"verify_ticket": ticket, "selfie_b64": selfie_b64},
    )


def _valid_ticket(**overrides) -> str:
    params = dict(
        telegram_id=TELEGRAM_ID,
        student_id=1001,
        session_smena_id=7,
        region_id=3,
        score=91,
        selfie_sha256=selfie_digest(SELFIE),
    )
    params.update(overrides)
    return issue_verify_ticket(**params)


def test_mark_attendance_takes_student_and_score_from_ticket(api, operator, monkeypatch):
    captured = {}

    def fake_mark(_db, bot, **kwargs):
        captured.update(kwargs, bot=bot)
        return BotMarkAttendanceResponse(status="ok", student_id=kwargs["student_id"])

    monkeypatch.setattr(endpoint.svc, "mark_attendance", fake_mark)

    r = _mark(api, _valid_ticket())
    assert r.status_code == 200, r.text
    assert captured["student_id"] == 1001
    assert captured["session_smena_id"] == 7
    assert captured["region_id"] == 3
    assert captured["verify_score"] == 91
    assert captured["bot"] is operator


def test_mark_attendance_rejects_other_users_ticket(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint.svc, "mark_attendance", pytest.fail)
    r = _mark(api, _valid_ticket(telegram_id=TELEGRAM_ID + 1))
    assert r.status_code == 403


def test_mark_attendance_rejects_swapped_selfie(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint.svc, "mark_attendance", pytest.fail)
    other_selfie = base64.b64encode(b"another-face").decode()
    assert _mark(api, _valid_ticket(), selfie_b64=other_selfie).status_code == 400


def test_mark_attendance_rejects_forged_ticket(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint.svc, "mark_attendance", pytest.fail)
    version, body, _sig = _valid_ticket().split(".")
    assert _mark(api, f"{version}.{body}.AAAA").status_code == 400


def test_passport_qr_text_endpoint(api, operator):
    r = api.post(
        "/api/v1/davomat-miniapp/passport-qr",
        headers=_auth(),
        json={"text": "IUUZBAD12345674123456789012342<<<<"},
    )
    assert r.status_code == 200, r.text
    assert r.json() == {"ps_ser": "AD", "ps_num": "1234567", "jshshir": "12345678901234"}


def test_passport_qr_requires_exactly_one_source(api, operator):
    r = api.post("/api/v1/davomat-miniapp/passport-qr", headers=_auth(), json={})
    assert r.status_code == 422


def _face_verify(api, **overrides):
    body = {
        "session_id": 1,
        "session_smena_id": 7,
        "region_id": 3,
        "ps_ser": "AD",
        "ps_num": "1234567",
        "jshshir": "12345678901234",
        "selfie_b64": SELFIE_B64,
    }
    body.update(overrides)
    return api.post("/api/v1/davomat-miniapp/face-verify", headers=_auth(), json=body)


def _verify_result(**overrides) -> BotFaceVerifyResponse:
    params = dict(
        status="in_smena",
        verified=True,
        score=88,
        threshold=67,
        can_attend=True,
        photo_b64="cGhvdG8=",
        selfie_b64=SELFIE_B64,
        slot=BotStudentSlot(student_id=1001, fio="Aliyev Ali"),
    )
    params.update(overrides)
    return BotFaceVerifyResponse(**params)


def test_face_verify_issues_ticket_bound_to_operator_and_selfie(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint.svc, "face_verify", lambda *_a, **_k: _verify_result())

    r = _face_verify(api)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "selfie_b64" not in body
    ticket = read_verify_ticket(body["verify_ticket"])
    assert (ticket.telegram_id, ticket.student_id, ticket.session_smena_id) == (TELEGRAM_ID, 1001, 7)
    assert ticket.score == 88
    assert ticket.selfie_sha256 == selfie_digest(SELFIE)


def test_face_verify_without_can_attend_has_no_ticket(api, operator, monkeypatch):
    result = _verify_result(can_attend=False, verified=False)
    monkeypatch.setattr(endpoint.svc, "face_verify", lambda *_a, **_k: result)
    r = _face_verify(api)
    assert r.status_code == 200, r.text
    assert r.json()["verify_ticket"] is None


def test_face_verify_validates_jshshir(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint.svc, "face_verify", pytest.fail)
    assert _face_verify(api, jshshir="123").status_code == 422


def test_absentees_are_sent_to_operator_chat(api, operator, monkeypatch):
    sent = {}
    monkeypatch.setattr(
        endpoint, "build_absentees_excel", lambda *_a, **_k: (b"xlsx", "kelmaganlar.xlsx", 12)
    )
    monkeypatch.setattr(endpoint, "send_document_to_chat", lambda **kw: sent.update(kw))

    r = api.post(
        "/api/v1/davomat-miniapp/sessions/1/absentees/send",
        headers=_auth(),
        json={"test_day": "2026-09-20", "region_id": 3},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"
    assert sent["chat_id"] == TELEGRAM_ID
    assert "2026-09-20" in sent["caption"]


def test_absentees_empty_list_is_not_sent(api, operator, monkeypatch):
    monkeypatch.setattr(
        endpoint, "build_absentees_excel", lambda *_a, **_k: (b"xlsx", "kelmaganlar.xlsx", 0)
    )
    monkeypatch.setattr(endpoint, "send_document_to_chat", pytest.fail)
    r = api.post(
        "/api/v1/davomat-miniapp/sessions/1/absentees/send", headers=_auth(), json={}
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "empty"


def test_absentees_region_outside_assignment_is_forbidden(api, operator, monkeypatch):
    monkeypatch.setattr(endpoint, "build_absentees_excel", pytest.fail)
    r = api.post(
        "/api/v1/davomat-miniapp/sessions/1/absentees/send",
        headers=_auth(),
        json={"region_id": 99},
    )
    assert r.status_code == 403
