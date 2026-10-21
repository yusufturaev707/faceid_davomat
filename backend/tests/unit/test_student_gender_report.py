"""Jins bo'yicha hisobot: viloyat × (sana, smena) × erkak/ayol."""

from datetime import date, datetime
from io import BytesIO

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.gender import Gender
from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_ps_data import StudentPsData
from app.models.test import Test as TestModel
from app.models.test_session import TestSession as SessionModel
from app.models.test_session_smena import TestSessionSmena as SessionSmenaModel
from app.models.zone import Zone
from app.services.student_gender_report import (
    build_gender_report_xlsx,
    collect_gender_report,
    format_day_uz,
)

D1 = date(2026, 10, 12)
D2 = date(2026, 10, 13)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [
        m.__table__
        for m in (Gender, Region, Zone, Smena, TestModel, SessionModel,
                  SessionSmenaModel, Student, StudentPsData)
    ]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as s:
        s.add_all([
            Gender(id=1, name="Noma'lum", key=0),
            Gender(id=2, name="Erkak", key=1),
            Gender(id=3, name="Ayol", key=2),
            Region(id=1, name="Toshkent sh.", number=2, s_number=1, k_number=1),
            Region(id=2, name="Andijon", number=1, s_number=2, k_number=2),
            Zone(id=1, region_id=1, name="Bino A"),
            Zone(id=2, region_id=2, name="Bino B"),
            Smena(id=1, name="1-smena", number=1),
            Smena(id=2, name="2-smena", number=2),
            TestModel(id=1, name="DTM", key="dtm"),
            TestModel(id=2, name="Boshqa", key="x"),
            SessionModel(id=1, hash_key="a", test_state_id=1, test_id=1, name="S1",
                        number=1, start_date=D1, finish_date=D2),
            SessionModel(id=2, hash_key="b", test_state_id=1, test_id=2, name="S2",
                        number=2, start_date=D1, finish_date=D2),
            SessionSmenaModel(id=1, test_session_id=1, test_smena_id=1, day=D1),
            SessionSmenaModel(id=2, test_session_id=1, test_smena_id=2, day=D1),
            SessionSmenaModel(id=3, test_session_id=1, test_smena_id=1, day=D2),
            SessionSmenaModel(id=4, test_session_id=2, test_smena_id=1, day=D1),
        ])
        s.flush()
        sid = 0

        def student(ss, zone, day, imei, gender_id=None, ps=True, entered=False):
            nonlocal sid
            sid += 1
            s.add(Student(id=sid, session_smena_id=ss, zone_id=zone, last_name="F",
                          first_name="I", imei=imei, e_date=day, is_entered=entered))
            if ps:
                s.add(StudentPsData(id=sid, student_id=sid, ps_ser="AA", ps_num="1",
                                    gender_id=gender_id))

        # Toshkent, 12-oktabr 1-smena: 2 erkak (biri gender'siz, JShShIR 3...), 1 ayol
        student(1, 1, D1, "31111111111111", gender_id=2, entered=True)
        student(1, 1, D1, "51111111111111", gender_id=None)
        student(1, 1, D1, "41111111111111", gender_id=3, entered=True)
        # Toshkent, 12-oktabr 2-smena: 1 ayol (ps_data yo'q — JShShIR 6...)
        student(2, 1, D1, "61111111111111", ps=False)
        # Andijon, 13-oktabr 1-smena: 1 erkak, 1 noma'lum (key=0, JShShIR yo'q)
        student(3, 2, D2, "31111111111111", gender_id=2)
        student(3, 2, D2, None, gender_id=1)
        # Boshqa test — hisobotga kirmaydi
        student(4, 1, D1, "31111111111111", gender_id=2)
        s.commit()
        yield s


def test_columns_rows_and_totals(db):
    r = collect_gender_report(db, test_id=1, date_from=D1, date_to=D2)
    assert r.test_name == "DTM"
    assert [c.label for c in r.columns] == [
        "12-oktabr 1-smena", "12-oktabr 2-smena", "13-oktabr 1-smena",
    ]
    # Viloyatlar `regions.number` tartibida: Andijon (1), Toshkent (2)
    assert [row.region_name for row in r.rows] == ["Andijon", "Toshkent sh."]
    andijon, toshkent = r.rows
    assert toshkent.cells == [[2, 1], [0, 1], [0, 0]]
    assert andijon.cells == [[0, 0], [0, 0], [1, 0]]
    assert andijon.unknown == 1
    assert r.totals == [[2, 1], [0, 1], [1, 0]]
    assert (r.male, r.female, r.unknown) == (3, 2, 1)


def test_date_range_and_extra_filters(db):
    r = collect_gender_report(db, test_id=1, date_from=D2, date_to=D2)
    assert [c.label for c in r.columns] == ["13-oktabr 1-smena"]
    assert [row.region_name for row in r.rows] == ["Andijon"]

    r = collect_gender_report(db, test_id=1, date_from=D1, date_to=D2, region_id=1,
                              is_entered=True)
    assert [row.region_name for row in r.rows] == ["Toshkent sh."]
    assert r.rows[0].cells == [[1, 1]]


def test_empty_report(db):
    r = collect_gender_report(db, test_id=1, date_from=date(2026, 1, 1),
                              date_to=date(2026, 1, 2))
    assert r.columns == [] and r.rows == [] and r.male == 0


def test_year_shown_only_when_range_spans_years():
    assert format_day_uz(D1) == "12-oktabr"
    assert format_day_uz(D1, with_year=True) == "12-oktabr 2026"


def test_xlsx_flat_headers(db):
    from openpyxl import load_workbook

    r = collect_gender_report(db, test_id=1, date_from=D1, date_to=D2)
    ws = load_workbook(BytesIO(build_gender_report_xlsx(r, datetime(2026, 10, 21)))).active
    headers = [c.value for c in ws[3]]
    assert headers[:4] == ["№", "Viloyat", "12-oktabr 1-smena Erkak", "12-oktabr 1-smena Ayol"]
    assert headers[-3:] == ["Jami Erkak", "Jami Ayol", "Jami"]
    assert [c.value for c in ws[5]][1:5] == ["Toshkent sh.", 2, 1, 0]
    total = [c.value for c in ws[6]]
    assert total[1] == "Jami" and total[-3:] == [3, 2, 5]
