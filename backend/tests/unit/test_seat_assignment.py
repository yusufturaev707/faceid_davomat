"""Kompyuter biriktirish (`sp_n`) va Proctoring broni.

Proctoring API chaqirilmaydi — `proctoring_client` funksiyalari almashtiriladi.
DB — faqat kerakli jadvallar bilan in-memory SQLite (to'liq `create_all`
SQLite'da `INET` ustun tufayli yiqiladi — `CLAUDE.md`).
"""

from __future__ import annotations

from datetime import date

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.models.region import Region
from app.models.student import Student
from app.models.zone import Zone
from app.services import proctoring_booking, proctoring_client, seat_assignment
from app.services.proctoring_client import ProctoringComputer, ProctoringError
from app.tasks import proctoring_task

SMENA = 7
SCHEDULE = 55


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    for table in (Region.__table__, Zone.__table__, Student.__table__):
        table.create(bind=engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    session.add(Region(id=1, name="Buxoro", number=6, s_number=6, k_number=6))
    session.add(Zone(id=10, region_id=1, name="1-bino", number=1))
    session.add(Zone(id=11, region_id=1, name="2-bino", number=2))
    session.commit()
    yield session
    session.close()


_next_id = iter(range(1, 10_000))


def add_student(db, *, imei, gr_n=1, last="A", zone_id=10, sp_n=1, **kwargs):
    student = Student(
        id=next(_next_id),
        session_smena_id=SMENA,
        zone_id=zone_id,
        last_name=last,
        first_name="X",
        imei=imei,
        gr_n=gr_n,
        sp_n=sp_n,  # loader qiymati (OTM'da hammasi 1)
        e_date=date(2026, 9, 25),
        **kwargs,
    )
    db.add(student)
    db.commit()
    return student


def pcs(*numbers, zone=1, booked=None):
    booked = booked or {}
    return [
        ProctoringComputer(
            number=n, region_number=6, zone_number=zone, zone_name="",
            is_booked=n in booked, pinfl=booked.get(n, ""),
        )
        for n in numbers
    ]


@pytest.fixture
def computers(monkeypatch):
    state = {"list": []}
    monkeypatch.setattr(proctoring_client, "list_computers", lambda schedule_id: state["list"])
    return state


def run(db, **kwargs):
    return seat_assignment.assign_seats(
        db, session_smena_id=SMENA, schedule_id=kwargs.pop("schedule_id", SCHEDULE), **kwargs
    )


def seats(db):
    db.expire_all()
    return {
        s.imei: (s.sp_n, s.proctoring_schedule_id)
        for s in db.execute(select(Student).order_by(Student.id)).scalars()
    }


# --------------------------------------------------------------- biriktirish
def test_assigns_by_group_then_surname_and_skips_unknown_zone(db, computers):
    add_student(db, imei="P3", gr_n=2, last="A")
    add_student(db, imei="P2", gr_n=1, last="B")
    add_student(db, imei="P1", gr_n=1, last="A")
    add_student(db, imei="Z2", zone_id=11)  # Proctoring'da bu bino yo'q
    computers["list"] = pcs(4, 7, 9)

    report = run(db)

    assert seats(db) == {
        "P1": (4, SCHEDULE), "P2": (7, SCHEDULE), "P3": (9, SCHEDULE),
        "Z2": (1, None),  # tegilmadi — loader qiymati joyida
    }
    assert report.totals["assigned"] == 3
    assert [z.zone_number for z in report.missing_zones] == [2]


def test_dry_run_writes_nothing(db, computers):
    add_student(db, imei="P1")
    computers["list"] = pcs(1, 2)

    report = run(db, dry_run=True)

    assert report.changed_rows == 1
    assert seats(db) == {"P1": (1, None)}


def test_rerun_keeps_valid_seats_and_moves_only_broken(db, computers):
    for imei, last in (("P1", "A"), ("P2", "B"), ("P3", "C")):
        add_student(db, imei=imei, last=last)
    computers["list"] = pcs(1, 2, 3, 4)
    run(db)

    computers["list"] = pcs(2, 3, 4)  # 1-kompyuter buzildi
    report = run(db)

    assert seats(db) == {"P1": (4, SCHEDULE), "P2": (2, SCHEDULE), "P3": (3, SCHEDULE)}
    assert (report.zones[0].kept, report.zones[0].assigned) == (2, 1)


def test_existing_proctoring_booking_wins_and_swap_passes_unique_index(db, computers):
    add_student(db, imei="P1", last="A")
    add_student(db, imei="P2", last="B")
    computers["list"] = pcs(1, 2)
    run(db)  # P1 -> 1, P2 -> 2

    # Panelda P2 qo'lda 1-kompyuterga bron qilingan.
    computers["list"] = pcs(1, 2, booked={1: "P2"})
    run(db)

    assert seats(db) == {"P1": (2, SCHEDULE), "P2": (1, SCHEDULE)}


def test_foreign_booking_is_skipped(db, computers):
    add_student(db, imei="P1")
    computers["list"] = pcs(1, 2, booked={1: "BEGONA"})

    report = run(db)

    assert seats(db) == {"P1": (2, SCHEDULE)}
    assert report.zones[0].computers == 1


def test_shortage_clears_loader_value(db, computers):
    add_student(db, imei="P1", last="A")
    add_student(db, imei="P2", last="B")
    computers["list"] = pcs(5)

    report = run(db)

    # Loader qiymati (1) qolsa client uni kompyuter raqami deb ko'rsatardi.
    assert seats(db) == {"P1": (5, SCHEDULE), "P2": (0, None)}
    assert report.totals["unassigned"] == 1


def test_one_person_one_computer_across_duplicate_rows(db, computers):
    add_student(db, imei="P1", last="A", subject_name="Fan 1")
    twin = add_student(db, imei="P1", last="A", subject_name="Fan 2")
    add_student(db, imei="P2", last="B")
    computers["list"] = pcs(1, 2, 3)

    run(db)

    rows = db.execute(select(Student).order_by(Student.id)).scalars().all()
    assert [(r.imei, r.sp_n, r.proctoring_schedule_id) for r in rows] == [
        ("P1", 1, SCHEDULE), ("P1", 1, None), ("P2", 2, SCHEDULE),
    ]
    assert twin.id == rows[1].id


def test_applied_candidate_gets_no_seat(db, computers):
    add_student(db, imei="P1", is_applied=True)
    add_student(db, imei="P2")
    computers["list"] = pcs(1)

    run(db)

    assert seats(db) == {"P1": (0, None), "P2": (1, SCHEDULE)}


def test_entered_candidates_block_switching_schedule(db, computers):
    add_student(db, imei="P1", is_entered=True)
    computers["list"] = pcs(1)
    run(db)

    with pytest.raises(seat_assignment.SeatAssignmentError):
        run(db, schedule_id=SCHEDULE + 1)


def test_database_forbids_same_computer_twice(db):
    add_student(db, imei="P1", sp_n=3, proctoring_schedule_id=SCHEDULE)
    with pytest.raises(IntegrityError):
        add_student(db, imei="P2", sp_n=3, proctoring_schedule_id=SCHEDULE)
    db.rollback()
    # Loader qiymatlari (egasiz) takrorlanishi mumkin.
    add_student(db, imei="P3", sp_n=3)
    add_student(db, imei="P4", sp_n=3)


# --------------------------------------------------------------------- bron
def test_seat_of_resolves_owner_through_duplicate_row(db, computers):
    add_student(db, imei="P1")
    twin = add_student(db, imei="P1", subject_name="Fan 2")
    computers["list"] = pcs(8)
    run(db)

    assert proctoring_task._seat_of(db, twin.id) == (SCHEDULE, "P1", 6, 1, 8)


def test_seat_of_skips_rejected_and_unassigned(db):
    cheat = add_student(db, imei="P1", sp_n=2, proctoring_schedule_id=SCHEDULE, is_cheating=True)
    plain = add_student(db, imei="P2", sp_n=1)
    assert proctoring_task._seat_of(db, cheat.id) is None
    assert proctoring_task._seat_of(db, plain.id) is None


def test_enqueue_only_assigned_candidates(db, monkeypatch):
    owner = add_student(db, imei="P1", sp_n=2, proctoring_schedule_id=SCHEDULE)
    twin = add_student(db, imei="P1", sp_n=2)
    plain = add_student(db, imei="P2", sp_n=1)
    cheat = add_student(db, imei="P3", sp_n=3, proctoring_schedule_id=SCHEDULE, is_cheating=True)
    sent = []
    monkeypatch.setattr(proctoring_client, "is_configured", lambda: True)
    monkeypatch.setattr(proctoring_task.book_seat, "delay", sent.append)

    count = proctoring_booking.enqueue_seat_booking(db, [owner.id, twin.id, plain.id, cheat.id])

    assert count == 2
    assert sorted(sent) == sorted([owner.id, twin.id])


def test_enqueue_is_noop_when_not_configured(db, monkeypatch):
    owner = add_student(db, imei="P1", sp_n=2, proctoring_schedule_id=SCHEDULE)
    monkeypatch.setattr(proctoring_client, "is_configured", lambda: False)
    assert proctoring_booking.enqueue_seat_booking(db, [owner.id]) == 0


# ------------------------------------------------------------- HTTP client
@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "PROCTORING_API_URL", "http://proctoring/api/v1/")
    monkeypatch.setattr(settings, "PROCTORING_API_KEY", "secret")


def _respond(monkeypatch, status, body, seen=None):
    def fake(method, url, **kwargs):
        if seen is not None:
            seen.append((method, url, kwargs))
        return httpx.Response(status, json=body, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", fake)


def test_client_unwraps_envelope_and_sends_api_key(configured, monkeypatch):
    seen = []
    _respond(monkeypatch, 200, {"success": True, "data": {"results": [
        {"number": 12, "region_dtm_id": 6, "zone_number": 1, "zone_name": "1-bino",
         "is_booked": False, "pinfl": ""},
    ]}, "error": None}, seen)

    result = proctoring_client.list_computers(5)

    assert result[0].number == 12 and result[0].region_number == 6
    method, url, kwargs = seen[0]
    assert url == "http://proctoring/api/v1/integrations/faceid/schedules/5/computers/"
    assert kwargs["headers"]["X-API-Key"] == "secret"


def test_client_business_error_is_not_retryable(configured, monkeypatch):
    _respond(monkeypatch, 409, {"success": False, "data": None, "error": {
        "code": "seat_unavailable", "message": "Kompyuter band"}})

    with pytest.raises(ProctoringError) as ctx:
        proctoring_client.book(
            schedule_id=1, pinfl="P1", region_number=6, zone_number=1, computer_number=2
        )
    assert (ctx.value.code, ctx.value.retryable, ctx.value.message) == (
        "seat_unavailable", False, "Kompyuter band")


def test_client_server_and_network_errors_are_retryable(configured, monkeypatch):
    _respond(monkeypatch, 503, {})
    with pytest.raises(ProctoringError) as ctx:
        proctoring_client.list_schedules()
    assert ctx.value.retryable

    def boom(*args, **kwargs):
        raise httpx.ConnectTimeout("timeout")

    monkeypatch.setattr(httpx, "request", boom)
    with pytest.raises(ProctoringError) as ctx:
        proctoring_client.list_schedules()
    assert ctx.value.retryable


def test_client_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "PROCTORING_API_URL", "")
    with pytest.raises(proctoring_client.ProctoringNotConfigured):
        proctoring_client.list_schedules()
