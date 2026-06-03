"""Talabalarning passport (ps_ser / ps_num) ma'lumotlarini ommaviy yangilash.

Foydalanish konteksti: ba'zi talabalarning passport seriyasi/raqami
eskirgan bo'ladi. Operator Excel shablon (`jshshir, ps_ser, ps_num`) yoki
Excel'dan nusxalab qo'yilgan (paste) qatorlarni yuboradi — biz `jshshir`
(= `Student.imei`) bo'yicha shu sessiyadagi talabani topib, uning
`StudentPsData` yozuvidagi `ps_ser`/`ps_num` ni yangilaymiz.

Bu jarayon yengil (faqat DB UPDATE, yuz/embedding qayta ishlash yo'q),
shuning uchun sinxron bajariladi — Celery talab qilinmaydi.
"""

from __future__ import annotations

import logging
import re
from io import BytesIO

from sqlalchemy import select as sa_select
from sqlalchemy.orm import Session

from app.models.student import Student
from app.models.student_ps_data import StudentPsData
from app.models.test_session_smena import TestSessionSmena

logger = logging.getLogger(__name__)

# Maydon uzunligi cheklovlari — DB ustun o'lchamlariga mos
# (Student.imei = String(14), StudentPsData.ps_ser = String(5), ps_num = String(10)).
_MAX_JSHSHIR = 14
_MAX_PS_SER = 5
_MAX_PS_NUM = 10

# Excel sarlavhalari uchun alias'lar — turli shablonlarni ham qabul qilamiz.
_HEADER_ALIASES: dict[str, str] = {
    "jshshir": "jshshir",
    "jshshr": "jshshir",
    "pinfl": "jshshir",
    "imei": "jshshir",
    "ps_ser": "ps_ser",
    "psser": "ps_ser",
    "seria": "ps_ser",
    "seriya": "ps_ser",
    "series": "ps_ser",
    "pasport_seriyasi": "ps_ser",
    "ps_num": "ps_num",
    "psnum": "ps_num",
    "raqam": "ps_num",
    "number": "ps_num",
    "pasport_raqami": "ps_num",
}


def _norm_header(value: object) -> str:
    """Sarlavha matnini kalitga aylantiradi (kichik harf, bo'shliq/nuqta → '_')."""
    text = str(value or "").strip().lower()
    for ch in (" ", ".", "-", "/"):
        text = text.replace(ch, "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


# "Seriya+raqam" bitta katakka birlashgan holat: AA1234567 / AA 1234567 / AA-1234567.
# Harflar (seriya) + ixtiyoriy bo'shliq/tire + raqamlar (raqam).
_COMBINED_PASSPORT_RE = re.compile(r"^([A-Za-z]{1,5})[\s\-]*(\d{1,10})$")


def split_combined_passport(ps_ser: str, ps_num: str) -> tuple[str, str]:
    """`ps_num` bo'sh va `ps_ser` ichida seriya+raqam birga kelgan bo'lsa, ajratadi.

    Misol: ("AA1234567", "") -> ("AA", "1234567").
    `ps_num` allaqachon to'ldirilgan bo'lsa — hech narsa o'zgartirmaydi (to'g'ri
    qatorlarga tegmaymiz). Naqshga mos kelmasa ham o'zgarishsiz qaytaradi.
    """
    if ps_num or not ps_ser:
        return ps_ser, ps_num
    m = _COMBINED_PASSPORT_RE.match(ps_ser.strip())
    if not m:
        return ps_ser, ps_num
    return m.group(1).upper(), m.group(2)


def clean_cell(value: object) -> str:
    """Yacheykadagi qiymatni tozalaydi. Excel sonlarini ('123.0') matnga keltiradi."""
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def validate_row(jshshir: str, ps_ser: str, ps_num: str) -> str | None:
    """Bitta qatorni tekshiradi. Xato bo'lsa — sabab matnini, aks holda None qaytaradi."""
    if not jshshir:
        return "JSHSHIR bo'sh"
    if len(jshshir) > _MAX_JSHSHIR:
        return f"JSHSHIR {_MAX_JSHSHIR} belgidan oshmasin"
    if not jshshir.isdigit():
        return "JSHSHIR faqat raqamlardan iborat bo'lishi kerak"
    if not ps_ser:
        return "Pasport seriyasi bo'sh"
    if len(ps_ser) > _MAX_PS_SER:
        return f"Pasport seriyasi {_MAX_PS_SER} belgidan oshmasin"
    if not ps_num:
        return "Pasport raqami bo'sh"
    if len(ps_num) > _MAX_PS_NUM:
        return f"Pasport raqami {_MAX_PS_NUM} belgidan oshmasin"
    return None


def parse_passport_excel(content: bytes) -> tuple[list[dict], list[str]]:
    """`.xlsx` baytlaridan `[{jshshir, ps_ser, ps_num}, ...]` qatorlarini ajratadi.

    Qaytaradi: (rows, errors). `errors` — fayl darajasidagi (sarlavha topilmadi va h.k.)
    muammolar; qator darajasidagi validatsiya `update_session_passports` da bo'ladi.
    """
    from openpyxl import load_workbook

    errors: list[str] = []
    try:
        wb = load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Passport Excel o'qishda xato: %s", exc)
        return [], ["Excel faylni o'qib bo'lmadi — fayl buzilgan yoki noto'g'ri formatda"]

    ws = wb.active
    if ws is None:
        return [], ["Excel'da varaq topilmadi"]

    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return [], ["Excel bo'sh"]

    col_index: dict[str, int] = {}
    for idx, raw in enumerate(header):
        key = _HEADER_ALIASES.get(_norm_header(raw))
        if key and key not in col_index:
            col_index[key] = idx

    missing = [c for c in ("jshshir", "ps_ser", "ps_num") if c not in col_index]
    if missing:
        return [], [
            "Excel'da ustunlar topilmadi: "
            + ", ".join(missing)
            + ". Kerakli sarlavhalar: jshshir, ps_ser, ps_num"
        ]

    rows: list[dict] = []
    for raw in rows_iter:
        if raw is None:
            continue

        def cell(key: str) -> str:
            i = col_index[key]
            return clean_cell(raw[i]) if i < len(raw) else ""

        jshshir = cell("jshshir")
        ps_ser = cell("ps_ser").upper()
        ps_num = cell("ps_num")
        if not (jshshir or ps_ser or ps_num):
            continue  # butunlay bo'sh qator — o'tkazib yuboramiz
        rows.append({"jshshir": jshshir, "ps_ser": ps_ser, "ps_num": ps_num})

    wb.close()
    return rows, errors


def update_session_passports(
    db: Session, session_id: int, rows: list[dict]
) -> dict:
    """`rows` ichidagi passport ma'lumotlarini sessiya talabalariga qo'llaydi.

    Moslashtirish: `Student.imei == jshshir` VA talaba shu `session_id` ga tegishli.
    Topilgan har bir talabaning `StudentPsData` yozuvi yangilanadi (yo'q bo'lsa
    yaratiladi).

    Qaytaradi:
        {
          "total": int,            # yuborilgan qatorlar soni
          "updated": int,          # yangilangan talaba yozuvlari soni
          "not_found": [jshshir],  # sessiyada topilmagan JSHSHIR'lar
          "invalid": [{"row", "jshshir", "error"}],  # validatsiyadan o'tmaganlar
        }
    """
    total = len(rows)
    invalid: list[dict] = []
    not_found: list[str] = []

    # 1) Qatorlarni tozalab/validatsiya qilamiz; yaroqlilarini jshshir bo'yicha yig'amiz.
    #    Bir xil jshshir takror kelsa — oxirgisi ustun bo'ladi.
    valid: dict[str, dict] = {}
    for idx, row in enumerate(rows, start=1):
        jshshir = clean_cell(row.get("jshshir"))
        ps_ser = clean_cell(row.get("ps_ser")).upper()
        ps_num = clean_cell(row.get("ps_num"))
        # Seriya+raqam bitta katakka birlashib kelgan bo'lsa — ajratamiz.
        ps_ser, ps_num = split_combined_passport(ps_ser, ps_num)
        err = validate_row(jshshir, ps_ser, ps_num)
        if err:
            invalid.append({"row": idx, "jshshir": jshshir, "error": err})
            continue
        valid[jshshir] = {"ps_ser": ps_ser, "ps_num": ps_num}

    if not valid:
        return {"total": total, "updated": 0, "not_found": [], "invalid": invalid}

    # 2) Shu sessiyaga tegishli, jshshir'i mos keladigan talabalarni topamiz.
    smena_subq = sa_select(TestSessionSmena.id).where(
        TestSessionSmena.test_session_id == session_id
    )
    students = (
        db.scalars(
            sa_select(Student).where(
                Student.session_smena_id.in_(smena_subq),
                Student.imei.in_(list(valid.keys())),
            )
        )
        .all()
    )

    by_imei: dict[str, list[Student]] = {}
    for st in students:
        by_imei.setdefault(st.imei or "", []).append(st)

    # 3) Mavjud ps_data yozuvlarini bitta so'rovda olib kelamiz.
    student_ids = [st.id for st in students]
    ps_by_student: dict[int, StudentPsData] = {}
    if student_ids:
        for ps in db.scalars(
            sa_select(StudentPsData).where(StudentPsData.student_id.in_(student_ids))
        ).all():
            ps_by_student[ps.student_id] = ps

    # 4) Yangilash.
    updated = 0
    for jshshir, data in valid.items():
        matched = by_imei.get(jshshir)
        if not matched:
            not_found.append(jshshir)
            continue
        for st in matched:
            ps = ps_by_student.get(st.id)
            if ps is None:
                ps = StudentPsData(
                    student_id=st.id, ps_ser=data["ps_ser"], ps_num=data["ps_num"]
                )
                db.add(ps)
                ps_by_student[st.id] = ps
            else:
                ps.ps_ser = data["ps_ser"]
                ps.ps_num = data["ps_num"]
            updated += 1

    db.commit()
    logger.info(
        "Passport yangilash: session=%d, total=%d, updated=%d, not_found=%d, invalid=%d",
        session_id, total, updated, len(not_found), len(invalid),
    )
    return {
        "total": total,
        "updated": updated,
        "not_found": not_found,
        "invalid": invalid,
    }
