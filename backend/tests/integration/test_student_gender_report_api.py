"""`/students/gender-report` va bulk amallarda test majburiyligi."""

from datetime import date
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_current_active_user, get_db
from app.main import app
from app.services import student_gender_report as sgr

BASE = "/api/v1/students"
OK = "?test_id=1&e_date_from=2026-10-12&e_date_to=2026-10-13"


def _user(perms=("student:read", "student:export_excel"), region_id=7):
    return SimpleNamespace(
        id=5,
        role_key=2,
        region_id=region_id,
        is_active=True,
        is_super_admin=False,
        has_perm=lambda c: c in perms,
        has_any_perm=lambda *c: any(x in perms for x in c),
    )


@pytest.fixture
def client(monkeypatch):
    calls = []

    def fake_collect(db, **kw):
        calls.append(kw)
        r = sgr.GenderReport(test_id=kw["test_id"], test_name="DTM",
                             date_from=kw["date_from"], date_to=kw["date_to"])
        r.columns = [sgr.GenderReportColumn(date(2026, 10, 12), 1, "1-smena",
                                            "12-oktabr 1-smena")]
        r.rows = [sgr.GenderReportRow(1, "Andijon", [[3, 4]], male=3, female=4)]
        r.totals = [[3, 4]]
        r.male, r.female = 3, 4
        return r

    monkeypatch.setattr(sgr, "collect_gender_report", fake_collect)
    state = {"user": _user()}
    app.dependency_overrides[get_current_active_user] = lambda: state["user"]
    app.dependency_overrides[get_db] = lambda: None
    yield TestClient(app), state, calls
    app.dependency_overrides.clear()


def test_report_ok_and_region_scope(client):
    c, state, calls = client
    state["user"] = _user(region_id=7)  # student:all_regions yo'q → o'z viloyati
    r = c.get(BASE + "/gender-report" + OK + "&region_id=1&is_entered=true")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["columns"][0]["label"] == "12-oktabr 1-smena"
    assert body["rows"][0]["cells"] == [[3, 4]]
    assert calls[0]["region_id"] == 7
    assert calls[0]["is_entered"] is True


@pytest.mark.parametrize(
    "query, detail",
    [
        ("?e_date_from=2026-10-12&e_date_to=2026-10-13", "Avval testni tanlang"),
        ("?test_id=1&e_date_from=2026-10-12", "Test sanasi oralig'ini (dan — gacha) tanlang"),
        ("?test_id=1&e_date_from=2026-10-14&e_date_to=2026-10-12",
         "Sana oralig'i noto'g'ri: boshlanish sanasi tugashidan keyin"),
        ("?test_id=1&e_date_from=2026-01-01&e_date_to=2026-12-31",
         "Sana oralig'i 62 kundan oshmasligi kerak"),
    ],
)
def test_report_validation(client, query, detail):
    c, _, _ = client
    r = c.get(BASE + "/gender-report" + query)
    assert r.status_code == 400
    assert r.json()["detail"] == detail


def test_report_requires_student_read(client):
    c, state, _ = client
    state["user"] = _user(perms=())
    assert c.get(BASE + "/gender-report" + OK).status_code == 403


def test_export_xlsx(client):
    c, _, _ = client
    r = c.get(BASE + "/gender-report/export" + OK)
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert "jins_hisoboti_" in r.headers["content-disposition"]


def test_export_requires_excel_permission(client):
    c, state, _ = client
    state["user"] = _user(perms=("student:read",))
    assert c.get(BASE + "/gender-report/export" + OK).status_code == 403


@pytest.mark.parametrize(
    "path, perm",
    [
        ("/fetch-gtsp-bulk?region_id=1", "student:fetch_gtsp"),
        ("/reassign-zone-bulk?target_zone_id=1&region_id=1", "student:update"),
    ],
)
def test_bulk_actions_require_test(client, path, perm):
    c, state, _ = client
    state["user"] = _user(perms=(perm,))
    r = c.post(BASE + path)
    assert r.status_code == 400
    assert r.json()["detail"] == "Avval testni tanlang"
