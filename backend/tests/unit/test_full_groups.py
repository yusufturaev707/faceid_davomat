"""Statistika: viloyat binolarida 100% kelgan guruhlar (`get_region_full_groups`).

DB — faqat kerakli jadvallar bilan in-memory SQLite (to'liq `create_all`
SQLite'da `INET` ustun tufayli yiqiladi — `CLAUDE.md`).
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.region import Region
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student import Student
from app.models.test import Test as ExamTest
from app.models.test_session import TestSession as ExamSession
from app.models.test_session_smena import TestSessionSmena as ExamSmena
from app.models.zone import Zone
from app.services.session_dashboard_stats import (
    DashboardStatsError,
    get_region_full_groups,
)

DAY1 = date(2026, 10, 10)
DAY2 = date(2026, 10, 11)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for model in (
        SessionState, ExamTest, ExamSession, Smena, ExamSmena,
        Region, Zone, Student,
    ):
        model.__table__.create(bind=engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(Region(id=1, name="Buxoro", number=6, s_number=6, k_number=6))
    session.add(Region(id=2, name="Navoiy", number=7, s_number=7, k_number=7))
    session.add(Zone(id=10, region_id=1, name="1-bino", number=1))
    session.add(Zone(id=11, region_id=1, name="2-bino", number=2))
    session.add(Zone(id=20, region_id=2, name="Boshqa", number=1))
    session.add(Smena(id=1, name="1-smena", number=1))
    session.add(Smena(id=2, name="2-smena", number=2))
    session.add(
        ExamSession(
            id=1, hash_key="h", test_state_id=1, test_id=1, name="S",
            start_date=DAY1, finish_date=DAY2,
        )
    )
    session.add(ExamSmena(id=100, test_session_id=1, test_smena_id=1, day=DAY1))
    session.add(ExamSmena(id=101, test_session_id=1, test_smena_id=2, day=DAY1))
    session.add(ExamSmena(id=102, test_session_id=1, test_smena_id=1, day=DAY2))
    session.commit()
    yield session
    session.close()


_next_id = iter(range(1, 10_000))


def add(db, *, smena=100, zone=10, gr_n=1, entered=False, cheating=False):
    db.add(
        Student(
            id=next(_next_id), session_smena_id=smena, zone_id=zone,
            last_name="A", first_name="B", imei=None, gr_n=gr_n, e_date=DAY1,
            is_entered=entered, is_cheating=cheating,
        )
    )


def _zone(resp, zone_id):
    return next(z for z in resp.zones if z.zone_id == zone_id)


def test_smena_scope_only_full_groups_sorted_by_gr_n(db):
    # gr 3 — hammasi keldi; gr 1 — biri kelmadi; gr 2 — biri chetlatilgan
    # (chetlatilgan ham "kelgan"); gr 0 — guruh emas.
    add(db, gr_n=3, entered=True)
    add(db, gr_n=3, entered=True)
    add(db, gr_n=1, entered=True)
    add(db, gr_n=1)
    add(db, gr_n=2, entered=True)
    add(db, gr_n=2, cheating=True)
    add(db, gr_n=0, entered=True)
    add(db, zone=11, gr_n=5)
    add(db, zone=20, gr_n=1, entered=True)  # boshqa viloyat
    add(db, smena=101, gr_n=7, entered=True)  # boshqa smena
    db.commit()

    resp = get_region_full_groups(
        db, session_id=1, region_id=1, scope="smena", session_smena_id=100
    )

    z10 = _zone(resp, 10)
    assert z10.total_groups == 3
    assert [(g.gr_n, g.total, g.cheating) for g in z10.full_groups] == [
        (2, 2, 1),
        (3, 2, 0),
    ]
    z11 = _zone(resp, 11)
    assert z11.total_groups == 1 and z11.full_groups == []
    assert {z.zone_id for z in resp.zones} == {10, 11}
    assert [s.session_smena_id for s in resp.smenas] == [100]


def test_overall_scope_same_gr_n_in_different_smenas_are_separate(db):
    add(db, smena=102, gr_n=1, entered=True)
    add(db, smena=100, gr_n=1, entered=True)
    add(db, smena=101, gr_n=1)  # 2-smena, 1-guruh — to'liq emas
    add(db, smena=101, gr_n=4, entered=True)
    db.commit()

    resp = get_region_full_groups(db, session_id=1, region_id=1, scope="overall")

    z10 = _zone(resp, 10)
    assert z10.total_groups == 4
    # Tartib: kun → smena raqami, so'ng gr_n
    assert [(g.session_smena_id, g.gr_n) for g in z10.full_groups] == [
        (100, 1),
        (101, 4),
        (102, 1),
    ]
    assert [s.session_smena_id for s in resp.smenas] == [100, 101, 102]
    assert resp.smenas[1].smena_number == 2


def test_day_scope_filters_by_day(db):
    add(db, smena=100, gr_n=1, entered=True)
    add(db, smena=102, gr_n=2, entered=True)
    db.commit()

    resp = get_region_full_groups(
        db, session_id=1, region_id=1, scope="day", day=DAY2
    )

    assert [(g.session_smena_id, g.gr_n) for g in _zone(resp, 10).full_groups] == [
        (102, 2)
    ]


def test_smena_from_other_session_rejected(db):
    db.add(
        ExamSession(
            id=2, hash_key="h2", test_state_id=1, test_id=1, name="S2",
            number=2, start_date=DAY1, finish_date=DAY1,
        )
    )
    db.add(ExamSmena(id=200, test_session_id=2, test_smena_id=1, day=DAY1))
    db.commit()

    with pytest.raises(DashboardStatsError):
        get_region_full_groups(
            db, session_id=1, region_id=1, scope="smena", session_smena_id=200
        )


def test_bot_stats_include_full_groups_per_zone(db):
    from app.services.davomat_bot_stats import compute_bot_stats

    add(db, gr_n=2, entered=True)
    add(db, gr_n=1, entered=True)
    add(db, gr_n=1)
    add(db, smena=101, gr_n=3, entered=True)
    db.commit()

    smena = compute_bot_stats(
        db, session_id=1, session_smena_id=100, allowed_region_ids={1}
    )
    z10 = next(z for z in smena.regions[0].zones if z.zone_id == 10)
    assert z10.total_groups == 2
    assert [g.gr_n for g in z10.full_groups] == [2]

    day = compute_bot_stats(db, session_id=1, test_day=DAY1, allowed_region_ids={1})
    z10 = next(z for z in day.regions[0].zones if z.zone_id == 10)
    assert [(g.session_smena_id, g.gr_n) for g in z10.full_groups] == [(100, 2), (101, 3)]


def test_stats_share_message_from_db(db):
    from datetime import datetime, timezone

    from app.services.davomat_bot_stats import BotStatsError
    from app.services.davomat_stats_message import build_stats_messages

    add(db, gr_n=1, entered=True)
    add(db, gr_n=1, entered=True)
    add(db, gr_n=2)
    db.commit()

    messages, total = build_stats_messages(
        db,
        session_id=1,
        session_smena_id=100,
        test_day=None,
        allowed_region_ids={1},
        now=datetime(2026, 10, 10, 4, 0, tzinfo=timezone.utc),
    )
    assert total == 3
    [msg] = messages
    assert "📝 <b>S</b>" in msg and "1-smena" in msg and "Yuborildi: 10.10.2026 · 09:00" in msg
    # Viloyatda faol bino bitta — faqat viloyat yakuni
    assert "Keldi: <b>2</b> · ❌ Kelmadi: <b>1</b>" in msg and "1-bino" not in msg
    assert "guruhlar" not in msg

    with pytest.raises(BotStatsError):
        build_stats_messages(
            db, session_id=999, session_smena_id=None, test_day=None,
            allowed_region_ids={1},
        )
