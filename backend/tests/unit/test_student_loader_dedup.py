"""Tashqi API'dan yuklashda `s_code` (task_id) va dublikat tekshiruvi."""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import app.crud.test_session as crud_test_session
from app.services import student_loader as sl

DAY = "2026-11-10"
DAY2 = "2026-11-11"
REGION, ZONE_ID, SMENA_ID = 5, 50, 500


def _ms_item(task_id, imie, **extra):
    item = {
        "test_region_id": REGION,
        "test_day": DAY,
        "number_sm": 1,
        "task_id": task_id,
        "imie": imie,
        "lname": "Aliyev",
        "fname": "Vali",
        "psser": "AB",
        "psnum": "1234567",
        "exam_id": 1,
    }
    item.update(extra)
    return item


@pytest.mark.parametrize(
    "val, expected",
    [(123, 123), ("456", 456), (" 789 ", 789), (12.0, 12),
     (None, 0), ("", 0), ("abc", 0), (0, 0), (-5, 0), (True, 0)],
)
def test_clean_s_code(val, expected):
    assert sl._clean_s_code(val) == expected


@pytest.mark.parametrize(
    "val, expected",
    [("31234567890123", "31234567890123"), (31234567890123, "31234567890123"),
     (" 31234567890123 ", "31234567890123"), ("312345678901234567", "31234567890123"),
     (None, None), ("", None), ("   ", None)],
)
def test_clean_imei(val, expected):
    assert sl._clean_imei(val) == expected


def test_parsers_write_source_id_to_s_code():
    zone_map = {REGION: ZONE_ID}
    cefr = sl._parse_cefr(
        {"dtm_id": REGION, "e_date": DAY, "task_id": "77", "imie": "3123"}, zone_map, {}
    )
    ms = sl._parse_ms(_ms_item(None, None), zone_map, {})
    iiv = sl._parse_iiv(
        {"dtm_id": REGION, "test_date": DAY, "request_id": 88, "pinfl": "4123"}, zone_map, {}
    )
    otm = sl._parse_otm_dtm(
        {"region_number": REGION, "e_date": DAY, "id": "99", "imie": "5123"}, zone_map, {}
    )
    assert (cefr[0]["s_code"], cefr[0]["imei"]) == (77, "3123")
    # null task_id/imie endi sahifani yiqitmaydi va "None" yozilmaydi
    assert (ms[0]["s_code"], ms[0]["imei"]) == (0, None)
    assert (iiv[0]["s_code"], iiv[0]["imei"]) == (88, "4123")
    assert (otm[0]["s_code"], otm[0]["imei"]) == (99, "5123")


def test_dedup_key_needs_both_task_id_and_imei():
    assert sl._dedup_key({"s_code": 1, "imei": "3123"}, DAY) == (1, "3123", DAY)
    assert sl._dedup_key({"s_code": 0, "imei": "3123"}, DAY) is None
    assert sl._dedup_key({"s_code": 1, "imei": None}, DAY) is None


def _run_day(monkeypatch, items):
    inserted: list[dict] = []

    def fake_flush(db, students, ps_rows):
        inserted.extend(dict(s) for s in students)
        return []

    monkeypatch.setattr(sl, "_get_redis", lambda: None)
    monkeypatch.setattr(sl, "_fetch_page", lambda *a, **k: (items, 1, len(items)))
    monkeypatch.setattr(sl, "_flush_batch", fake_flush)
    monkeypatch.setattr(crud_test_session, "_delete_students_by_session_day", lambda *a: None)

    ctx = SimpleNamespace(
        url_template="http://x/{date}", headers={}, fetch_kwargs={},
        zone_map={REGION: ZONE_ID}, building_map={},
        smena_map={(1, DAY): SMENA_ID, (2, DAY): SMENA_ID + 1, (1, DAY2): SMENA_ID + 2},
        parser=sl._parse_ms, blacklist_imeis=set(),
        gender_default_id=None, gender_male_id=1, gender_female_id=2,
    )
    res = sl.load_students_for_day(MagicMock(), SimpleNamespace(id=1), DAY, ctx=ctx)
    assert res["status"] == "completed", res
    return res, inserted


def test_duplicate_is_same_task_id_and_imei_only(monkeypatch):
    items = [
        _ms_item(1, "31111111111111"),
        _ms_item(1, "31111111111111", exam_id=2),               # dublikat — o'tkaziladi
        _ms_item(1, "31111111111111", number_sm=2),             # boshqa smena ham — dublikat
        _ms_item(2, "31111111111111"),                          # boshqa task_id — yoziladi
        _ms_item(1, "42222222222222"),                          # boshqa JShShIR — yoziladi
        _ms_item(3, "53333333333333", psnum="1234567"),         # pasport bir xil — yoziladi
        _ms_item(None, "31111111111111"),                       # task_id yo'q — tekshirilmaydi
        _ms_item(None, "31111111111111"),
        _ms_item(1, None),                                      # JShShIR yo'q — tekshirilmaydi
        _ms_item(1, None),
    ]
    res, inserted = _run_day(monkeypatch, items)

    assert res["loaded"] == 8
    assert res["skipped"] == 2
    pairs = [(s["s_code"], s["imei"]) for s in inserted]
    assert pairs.count((1, "31111111111111")) == 1
    assert (2, "31111111111111") in pairs and (1, "42222222222222") in pairs
    assert inserted[0]["subject_id"] == 1  # birinchisi qoladi


def test_same_pair_on_another_day_is_not_duplicate(monkeypatch):
    items = [
        _ms_item(1, "31111111111111"),
        _ms_item(1, "31111111111111", test_day=DAY2),   # boshqa kun — yoziladi
        _ms_item(1, "31111111111111", test_day=DAY2),   # o'sha kunda takror — o'tkaziladi
    ]
    res, inserted = _run_day(monkeypatch, items)

    assert (res["loaded"], res["skipped"]) == (2, 1)
    assert sorted(s["session_smena_id"] for s in inserted) == [SMENA_ID, SMENA_ID + 2]
