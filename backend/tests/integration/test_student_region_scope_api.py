"""Talabgorlarga yozuvchi endpointlarda viloyat qamrovi.

`student:all_regions` yo'q foydalanuvchi faqat o'z viloyati talabgorlarini
o'zgartiradi va faqat o'z viloyatidagi binoga ko'chiradi.
"""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import app.crud.student as crud_student
from app.api.v1.endpoints import student as ep
from app.dependencies import get_current_active_user, get_db
from app.main import app

BASE = "/api/v1/students"
MY_REGION = 7
OTHER_REGION = 9
ZONES = {1: SimpleNamespace(id=1, name="O'z bino", region_id=MY_REGION),
         2: SimpleNamespace(id=2, name="Chet bino", region_id=OTHER_REGION)}
STUDENT_REGION = {10: MY_REGION, 20: OTHER_REGION}


class FakeDb:
    def get(self, model, pk):
        return ZONES.get(pk)


def _user(perms, all_regions=False, role_key=2):
    perms = set(perms) | ({"student:all_regions"} if all_regions else set())
    return SimpleNamespace(
        id=5, role_key=role_key, region_id=MY_REGION, is_active=True,
        is_super_admin=False,
        has_perm=lambda c: c in perms,
        has_any_perm=lambda *c: any(x in perms for x in c),
    )


@pytest.fixture
def client(monkeypatch):
    calls = []
    monkeypatch.setattr(ep, "_student_region_id", lambda db, sid: STUDENT_REGION.get(sid))
    monkeypatch.setattr(
        crud_student, "get_filtered_student_ids",
        lambda db, **kw: calls.append(kw) or [],
    )
    monkeypatch.setattr(ep, "bulk_reassign_zone", lambda db, ids, zid: 0)
    monkeypatch.setattr(ep, "delete_student", lambda db, sid: True)
    state = {"user": None}
    app.dependency_overrides[get_current_active_user] = lambda: state["user"]
    app.dependency_overrides[get_db] = lambda: FakeDb()
    yield TestClient(app), state, calls
    app.dependency_overrides.clear()


def test_bulk_gtsp_forced_to_own_region(client):
    c, state, calls = client
    state["user"] = _user({"student:fetch_gtsp"})
    r = c.post(BASE + f"/fetch-gtsp-bulk?test_id=1&region_id={OTHER_REGION}")
    assert r.status_code == 200, r.text
    assert calls[0]["region_id"] == MY_REGION


def test_bulk_gtsp_global_user_keeps_requested_region(client):
    c, state, calls = client
    state["user"] = _user({"student:fetch_gtsp"}, all_regions=True)
    c.post(BASE + f"/fetch-gtsp-bulk?test_id=1&region_id={OTHER_REGION}")
    assert calls[0]["region_id"] == OTHER_REGION


def test_reassign_forced_to_own_region(client):
    c, state, calls = client
    state["user"] = _user({"student:update"})
    r = c.post(BASE + f"/reassign-zone-bulk?target_zone_id=1&test_id=1&region_id={OTHER_REGION}")
    assert r.status_code == 200, r.text
    assert calls[0]["region_id"] == MY_REGION


def test_reassign_to_other_region_zone_forbidden(client):
    c, state, calls = client
    state["user"] = _user({"student:update"})
    r = c.post(BASE + "/reassign-zone-bulk?target_zone_id=2&test_id=1")
    assert r.status_code == 403
    assert r.json()["detail"] == "Bu bino sizning viloyatingizga tegishli emas"
    assert calls == []


def test_admin_can_reassign_anywhere(client):
    c, state, _ = client
    state["user"] = _user(set(), role_key=1)
    r = c.post(BASE + "/reassign-zone-bulk?target_zone_id=2&test_id=1")
    assert r.status_code == 200, r.text


@pytest.mark.parametrize(
    "method, path, perm",
    [
        ("delete", "/20", "student:delete"),
        ("patch", "/20", "student:update"),
        ("post", "/20/fetch-gtsp", "student:fetch_gtsp"),
        ("post", "/20/upload-image", "student:update"),
    ],
)
def test_other_region_student_is_not_found(client, method, path, perm):
    c, state, _ = client
    state["user"] = _user({perm})
    kwargs = {"json": {"ps_img": "eA=="}} if "upload" in path else (
        {"json": {}} if method == "patch" else {})
    r = getattr(c, method)(BASE + path, **kwargs)
    assert r.status_code == 404
    assert r.json()["detail"] == "Ma'lumot topilmadi"


def test_own_region_student_delete_ok(client):
    c, state, _ = client
    state["user"] = _user({"student:delete"})
    assert c.delete(BASE + "/10").status_code == 204


def test_patch_move_to_other_region_zone_forbidden(client):
    c, state, _ = client
    state["user"] = _user({"student:update"})
    r = c.patch(BASE + "/10", json={"zone_id": 2})
    assert r.status_code == 403
