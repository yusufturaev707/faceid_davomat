"""Tashqi tizimlar uchun davomat API'si (`/attendance/student`).

`Base.metadata.create_all` SQLite'da `student_logs.ip_address` (INET) sababli
yiqiladi, shuning uchun kerakli jadvallar alohida yaratiladi, `student_logs`
esa qo'lda (INET o'rniga TEXT). Shunday qilib SQL so'rovning o'zi (JOIN'lar,
`tests.key` filtri) haqiqiy bazada tekshiriladi.
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

URL = "/api/v1/attendance/student"
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
            ExamTest(id=2, name="CEFR", key="cefr"),
            SessionState(id=4, name="Faol", key=4),
            ExamSession(
                id=7, hash_key="h7", test_state_id=4, test_id=1, name="Oktabr",
                number=7, start_date=date(2026, 10, 12), finish_date=date(2026, 10, 13),
            ),
            ExamSession(
                id=8, hash_key="h8", test_state_id=4, test_id=1, name="Noyabr",
                number=8, start_date=date(2026, 11, 2), finish_date=date(2026, 11, 2),
            ),
            ExamSession(
                id=9, hash_key="h9", test_state_id=4, test_id=2, name="CEFR oktabr",
                number=9, start_date=date(2026, 10, 12), finish_date=date(2026, 10, 12),
            ),
            SessionSmena(id=70, test_session_id=7, test_smena_id=1, number=1, day=date(2026, 10, 12)),
            SessionSmena(id=80, test_session_id=8, test_smena_id=1, number=1, day=date(2026, 11, 2)),
            SessionSmena(id=90, test_session_id=9, test_smena_id=1, number=1, day=date(2026, 10, 12)),
        ]
    )
    rows = [
        # id, task_id (s_code), smena, zone, entered, cheating, applied
        (101, 5001, 70, 10, True, False, False),
        (102, 5002, 70, 10, False, False, False),  # davomati bekor qilingan
        (103, 5003, 70, 10, True, True, False),
        (104, 5004, 70, 20, False, False, True),
        (105, 5005, 70, 10, False, False, False),
        (106, 5005, 80, 10, False, False, False),  # o'sha nomzod keyingi sessiyada
        (107, 5001, 90, 10, False, False, False),  # boshqa test turida xuddi shu task_id
    ]
    for sid, code, tss, zone, entered, cheating, applied in rows:
        s.add(
            Student(
                id=sid, s_code=code, session_smena_id=tss, zone_id=zone,
                last_name=f"F{sid}", first_name="I", imei=f"{sid:014d}", gr_n=1,
                sp_n=sid - 100,
                e_date={70: date(2026, 10, 12), 80: date(2026, 11, 2), 90: date(2026, 10, 12)}[tss],
                is_entered=entered, is_cheating=cheating, is_applied=applied,
            )
        )
    s.flush()
    for sid in (101, 102, 103):
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


def _get(c, test_key, task_id):
    return c.get(URL, params={"test_key": test_key, "task_id": task_id})


def test_requires_attendance_permission(client):
    c, state = client
    state["user"] = _user(perms=(P.STUDENT_READ.code,))
    assert _get(c, "ms", 5001).status_code == 403


def test_both_params_required(client):
    c, _ = client
    assert c.get(URL, params={"test_key": "ms"}).status_code == 422
    assert c.get(URL, params={"task_id": 5001}).status_code == 422
    assert _get(c, "ms", 0).status_code == 422
    assert _get(c, "ms", "abc").status_code == 422


def test_entered_student(client):
    c, _ = client
    r = _get(c, "ms", 5001)
    assert r.status_code == 200
    body = r.json()
    assert body["test_key"] == "ms"
    assert body["task_id"] == 5001
    assert "s_code" not in body
    # cefr'dagi 107 (xuddi shu task_id) qo'shilmaydi.
    assert body["count"] == 1
    item = body["items"][0]
    assert item["student_id"] == 101
    assert item["task_id"] == 5001
    assert "s_code" not in item
    assert item["status"] == "entered"
    assert item["entered_at"] is not None
    assert item["jshshir"] == "00000000000101"
    assert item["test_key"] == "ms"
    assert item["test_name"] == "Milliy sertifikat"
    assert item["test_session_id"] == 7
    assert item["test_session_name"] == "Oktabr"
    assert item["region_name"] == "Toshkent"
    assert item["zone_name"] == "1-bino"
    assert item["smena_name"] == "1-smena"


def test_test_key_separates_students(client):
    c, _ = client
    items = _get(c, "cefr", 5001).json()["items"]
    assert [i["student_id"] for i in items] == [107]
    assert items[0]["status"] == "not_entered"


def test_statuses(client):
    c, _ = client
    assert _get(c, "ms", 5003).json()["items"][0]["status"] == "cheating"
    applied = _get(c, "ms", 5004).json()["items"][0]
    assert applied["status"] == "not_entered"
    assert applied["is_applied"] is True
    # Bekor qilingan davomat: log bor, lekin vaqt ko'rsatilmaydi.
    cancelled = _get(c, "ms", 5002).json()["items"][0]
    assert cancelled["status"] == "not_entered"
    assert cancelled["entered_at"] is None


def test_several_sessions_newest_first(client):
    c, _ = client
    body = _get(c, "ms", 5005).json()
    assert body["count"] == 2
    assert [i["test_session_id"] for i in body["items"]] == [8, 7]


def test_not_found(client):
    c, _ = client
    assert _get(c, "ms", 9999).status_code == 404
    assert _get(c, "yoq", 5001).status_code == 404


def test_region_scope_is_forced(client):
    c, state = client
    state["user"] = _user(perms=(P.ATTENDANCE_READ.code,), region_id=2)
    # 104 — Samarqandda, 101 — Toshkentda: boshqa viloyat nomzodi ko'rinmaydi.
    assert _get(c, "ms", 5004).status_code == 200
    assert _get(c, "ms", 5001).status_code == 404

    state["user"] = _user(perms=(P.ATTENDANCE_READ.code,), region_id=None)
    assert _get(c, "ms", 5004).status_code == 403
