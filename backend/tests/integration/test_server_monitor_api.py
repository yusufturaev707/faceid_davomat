"""`/admin/server-monitor` — faqat superadmin, API kalit bilan emas."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.dependencies import get_current_active_user
from app.main import app
from app.services import server_monitor as mon

BASE = "/api/v1/admin/server-monitor"


def _user(super_admin=True, role_key=1):
    return SimpleNamespace(
        id=1 if super_admin else 2,
        role_key=role_key,
        is_active=True,
        is_super_admin=super_admin,
        has_perm=lambda c: True,
        has_any_perm=lambda *c: True,
    )


@pytest.fixture
def client(tmp_path, monkeypatch):
    logs = tmp_path / "backend" / "logs"
    logs.mkdir(parents=True)
    (logs / "error.log").write_text(
        "INFO start\nERROR boom token=abc123\nINFO ok\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "MONITOR_LOG_DIRS", str(logs))
    monkeypatch.setattr(mon, "collect_overview", lambda: {"alerts": [], "generated_at": "x"})

    state = {"user": _user()}
    app.dependency_overrides[get_current_active_user] = lambda: state["user"]
    yield TestClient(app), state
    app.dependency_overrides.clear()


@pytest.mark.parametrize(
    "path",
    ["/overview", "/history", "/logs", "/logs/tail?file=backend/error.log",
     "/logs/download?file=backend/error.log", "/journal?unit=nginx.service"],
)
def test_admin_role_without_super_admin_is_forbidden(client, path):
    c, state = client
    # Admin roli (barcha permissionlar bilan) ham kira olmaydi.
    state["user"] = _user(super_admin=False, role_key=1)
    r = c.get(BASE + path)
    assert r.status_code == 403
    assert r.json()["detail"] == "Bu bo'lim faqat superadmin uchun"


def test_api_key_is_rejected_even_for_super_admin(client):
    c, _ = client
    r = c.get(BASE + "/overview", headers={"X-API-Key": "sk-anything"})
    assert r.status_code == 403


def test_overview(client):
    c, _ = client
    r = c.get(BASE + "/overview")
    assert r.status_code == 200
    assert r.json()["generated_at"] == "x"
    assert r.headers["cache-control"] == "no-store"


def test_history_bounds(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr(mon, "read_history", lambda minutes: [{"t": "x"}])
    assert c.get(BASE + "/history?minutes=60").json()["points"] == [{"t": "x"}]
    assert c.get(BASE + "/history?minutes=1").status_code == 422
    assert c.get(BASE + f"/history?minutes={mon.HISTORY_MAX + 1}").status_code == 422


def test_history_redis_down(client, monkeypatch):
    c, _ = client

    def boom(minutes):
        raise ConnectionError("redis")

    monkeypatch.setattr(mon, "read_history", boom)
    assert c.get(BASE + "/history").status_code == 503


def test_log_sources(client):
    c, _ = client
    body = c.get(BASE + "/logs").json()
    assert [f["key"] for f in body["files"]] == ["backend/error.log"]
    assert "faceid-api.service" in body["units"]


def test_tail(client):
    c, _ = client
    r = c.get(BASE + "/logs/tail", params={"file": "backend/error.log", "level": "error"})
    assert r.status_code == 200
    assert r.json()["lines"] == ["ERROR boom token=***"]


def test_tail_unknown_file(client):
    c, _ = client
    for f in ("backend/../../etc/passwd", "backend/missing.log"):
        assert c.get(BASE + "/logs/tail", params={"file": f}).status_code == 404
    assert c.get(BASE + "/logs/tail", params={"file": "backend/error.log", "level": "debug"}).status_code == 422


def test_download_is_redacted(client):
    c, _ = client
    r = c.get(BASE + "/logs/download", params={"file": "backend/error.log"})
    assert r.status_code == 200
    assert "abc123" not in r.text
    assert "token=***" in r.text
    assert 'filename="backend_error.log"' in r.headers["content-disposition"]


def test_journal_only_configured_units(client, monkeypatch):
    c, _ = client
    assert c.get(BASE + "/journal", params={"unit": "ssh.service"}).status_code == 404
    monkeypatch.setattr(
        mon, "journal_tail", lambda unit, lines, q, level: {"available": True, "lines": [unit]}
    )
    r = c.get(BASE + "/journal", params={"unit": "nginx.service"})
    assert r.json()["lines"] == ["nginx.service"]
