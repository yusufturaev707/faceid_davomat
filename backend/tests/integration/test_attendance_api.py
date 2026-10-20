"""Tashqi tizimlar uchun davomat API'si (`/attendance`).

`Base.metadata.create_all` SQLite'da `student_logs.ip_address` (INET) sababli
yiqiladi, shuning uchun kerakli jadvallar alohida yaratiladi, `student_logs`
esa qo'lda (INET o'rniga TEXT). Shunday qilib SQL so'rovlarning o'zi
(JOIN, `FILTER`, keyset) haqiqiy bazada tekshiriladi.
"""

from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.permissions import P
from app.db.base import Base
from app.dependencies import get_current_active_user, get_db
from app.main import app
from app.models.region import Region
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student import Student
from app.models.test import Test as ExamTest
from app.models.test_session import TestSession as ExamSession
from app.models.test_session_smena import TestSessionSmena as SessionSmena
from app.models.zone import Zone

URL = "/api/v1/attendance"
ENTER_TIME = datetime(2026, 10, 12, 8, 15, tzinfo=timezone.utc)


def _user(perms=(P.ATTENDANCE_READ.code, P.STUDENT_ALL_REGIONS.code), region_id=None):
    codes = set(perms)
    return SimpleNamespace(
        id=1,
        role_key=5,
        is_active=True,
        region_id=region_id,
        has_perm=lambda c: c in codes,
        has_any_perm=lambda *cs: bool(codes & set(cs)),
    )


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        m.__table__
        for m in (Region, Zone, Smena, ExamTest, SessionState, ExamSession, SessionSmena, Student)
    ]
    Base.metadata.create_all(engine, tables=tables)
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE student_logs (id INTEGER PRIMARY KEY, student_id INTEGER UNIQUE,"
                " first_captured BLOB, last_captured BLOB, first_enter_time TIMESTAMP,"
                " last_enter_time TIMESTAMP, score INTEGER DEFAULT 0, max_score INTEGER DEFAULT 0,"
                " is_check_hand BOOLEAN DEFAULT 0, ip_address TEXT, mac_address TEXT)"
            )
        )
    session = sessionmaker(bind=engine)()
    _seed(session)
    yield session
    session.close()


def _seed(s):
    s.add_all(
        [
            Region(id=1, name="Toshkent", number=1, s_number=1, k_number=1),
            Region(id=2, name="Samarqand", number=2, s_number=2, k_number=2),
            Zone(id=10, region_id=1, name="1-bino", number=1),
            Zone(id=20, region_id=2, name="2-bino", number=1),
            Smena(id=1, name="1-smena", number=1),
            ExamTest(id=1, name="Milliy sertifikat", key="ms"),
            SessionState(id=4, name="Faol", key=4),
            ExamSession(
                id=7, hash_key="h7", test_state_id=4, test_id=1, name="Oktabr",
                number=7, start_date=date(2026, 10, 12), finish_date=date(2026, 10, 13),
            ),
            SessionSmena(id=70, test_session_id=7, test_smena_id=1, number=1, day=date(2026, 10, 12)),
            SessionSmena(id=71, test_session_id=7, test_smena_id=1, number=1, day=date(2026, 10, 13)),
        ]
    )
    rows = [
        # id, smena, zone, entered, cheating, applied
        (101, 70, 10, True, False, False),
        (102, 70, 10, False, False, False),
        (103, 70, 10, True, True, False),
        (104, 70, 20, False, False, True),
        (105, 71, 20, True, False, False),
    ]
    for sid, tss, zone, entered, cheating, applied in rows:
        s.add(
            Student(
                id=sid, session_smena_id=tss, zone_id=zone, last_name=f"F{sid}",
                first_name="I", imei=f"{sid:014d}", gr_n=1, sp_n=sid - 100,
                e_date=date(2026, 10, 12) if tss == 70 else date(2026, 10, 13),
                is_entered=entered, is_cheating=cheating, is_applied=applied,
            )
        )
    s.flush()
    # 101 keldi; 102 ning davomati bekor qilingan — log tarix sifatida qolgan.
    for sid in (101, 102, 103, 105):
        s.execute(
            text(
                "INSERT INTO student_logs (student_id, first_enter_time, last_enter_time)"
                " VALUES (:s, :t, :t)"
            ),
            {"s": sid, "t": ENTER_TIME},
        )
    s.commit()


@pytest.fixture
def client(db):
    state = {"user": _user()}
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: state["user"]
    yield TestClient(app), state
    app.dependency_overrides.clear()


def test_requires_attendance_permission(client):
    c, state = client
    state["user"] = _user(perms=(P.STUDENT_READ.code,))
    r = c.get(f"{URL}/students", params={"test_session_id": 7})
    assert r.status_code == 403


def test_sessions_list_smenas(client):
    c, _ = client
    r = c.get(f"{URL}/sessions")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    session = body["items"][0]
    assert session["test_session_id"] == 7
    assert session["test_name"] == "Milliy sertifikat"
    assert session["state_key"] == 4
    assert [sm["session_smena_id"] for sm in session["smenas"]] == [70, 71]


def test_students_statuses_and_times(client):
    c, _ = client
    r = c.get(f"{URL}/students", params={"test_session_id": 7})
    assert r.status_code == 200
    items = {i["student_id"]: i for i in r.json()["items"]}
    assert set(items) == {101, 102, 103, 104, 105}
    assert items[101]["status"] == "entered"
    assert items[101]["entered_at"] is not None
    assert items[103]["status"] == "cheating"
    assert items[104]["status"] == "not_entered"
    assert items[104]["is_applied"] is True
    # Bekor qilingan davomat: log bor, lekin vaqt ko'rsatilmaydi.
    assert items[102]["status"] == "not_entered"
    assert items[102]["entered_at"] is None
    assert items[101]["jshshir"] == "00000000000101"
    assert items[101]["region_name"] == "Toshkent"
    assert items[101]["smena_name"] == "1-smena"


def test_keyset_pagination(client):
    c, _ = client
    seen, after = [], 0
    while True:
        r = c.get(
            f"{URL}/students",
            params={"test_session_id": 7, "limit": 2, "after_id": after},
        )
        body = r.json()
        seen += [i["student_id"] for i in body["items"]]
        if not body["has_more"]:
            assert body["next_after_id"] is None
            break
        after = body["next_after_id"]
    assert seen == [101, 102, 103, 104, 105]


def test_filters(client):
    c, _ = client
    r = c.get(f"{URL}/students", params={"test_session_id": 7, "status": "entered"})
    assert [i["student_id"] for i in r.json()["items"]] == [101, 105]
    r = c.get(f"{URL}/students", params={"test_session_id": 7, "session_smena_id": 71})
    assert [i["student_id"] for i in r.json()["items"]] == [105]
    r = c.get(f"{URL}/students", params={"test_session_id": 7, "jshshir": "00000000000103"})
    assert [i["student_id"] for i in r.json()["items"]] == [103]
    r = c.get(f"{URL}/students", params={"test_session_id": 7, "jshshir": "123"})
    assert r.status_code == 422


def test_region_scope_is_forced(client):
    c, state = client
    state["user"] = _user(perms=(P.ATTENDANCE_READ.code,), region_id=2)
    # Boshqa viloyat so'ralsa ham o'z viloyati qaytadi.
    r = c.get(f"{URL}/students", params={"test_session_id": 7, "region_id": 1})
    assert [i["student_id"] for i in r.json()["items"]] == [104, 105]

    state["user"] = _user(perms=(P.ATTENDANCE_READ.code,), region_id=None)
    r = c.get(f"{URL}/students", params={"test_session_id": 7})
    assert r.status_code == 403


def test_summary(client):
    c, _ = client
    r = c.get(f"{URL}/summary", params={"test_session_id": 7})
    assert r.status_code == 200
    assert r.json() == {
        "test_session_id": 7,
        "total": 5,
        "entered": 2,
        "cheating": 1,
        "not_entered": 2,
        "applied": 1,
    }
    r = c.get(f"{URL}/summary", params={"test_session_id": 7, "zone_id": 10})
    assert r.json()["total"] == 3


def test_unknown_session_is_404(client):
    c, _ = client
    assert c.get(f"{URL}/students", params={"test_session_id": 999}).status_code == 404
    assert c.get(f"{URL}/summary", params={"test_session_id": 999}).status_code == 404
