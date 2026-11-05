"""`.xlsx` xavfsizligi: yuklangan fayllarni openpyxl'ga berishdan oldingi himoya
va eksportda formula injection'ga qarshi `text_cell`.

`.xlsx` — ZIP arxiv ichidagi XML. 16 MB fayl ochilganda gigabaytlab XML bo'lishi
mumkin (zip-bomba), XML esa entity kengaytirish hujumlarini (billion laughs)
tashishi mumkin. Shuning uchun:

- arxiv ochilmasdan oldin e'lon qilingan (header) hajmlar yig'indisi tekshiriladi —
  Python `zipfile` e'lon qilingan hajmdan ortiq o'qimaydi, shuning uchun bu
  ishonchli yuqori chegara;
- openpyxl `defusedxml` bilan ishlashi shart (requirements.txt), busiz parse
  qilishdan bosh tortamiz;
- ma'lumot qatorlari soni cheklanadi — ro'yxat va xatolar xotirada saqlanadi.
"""

from __future__ import annotations

import logging
import zipfile
from collections.abc import Iterator
from io import BytesIO
from typing import Any

logger = logging.getLogger(__name__)

# Oddiy ro'yxat XML'i ~10-20 marta siqiladi: 16 MB fayl → bir necha yuz MB.
MAX_XLSX_UNCOMPRESSED_BYTES = 512 * 1024 * 1024
MAX_XLSX_ENTRIES = 10_000
# Sarlavhadan keyingi ma'lumot qatorlari (bo'sh qatorlar ham hisoblanadi).
MAX_XLSX_DATA_ROWS = 500_000


class XlsxRejected(ValueError):
    """Fayl xavfsizlik tekshiruvidan o'tmadi — xabar foydalanuvchiga ko'rsatiladi."""


def check_xlsx_archive(content: bytes) -> None:
    """ZIP tuzilishini va ochilgandagi hajmni tekshirish (fayl ochilmaydi).

    Raises:
        XlsxRejected: `.xlsx` emas, buzilgan yoki ochilganda juda katta.
    """
    if not content.startswith(b"PK\x03\x04"):
        raise XlsxRejected("Fayl `.xlsx` formatida emas")
    try:
        with zipfile.ZipFile(BytesIO(content)) as zf:
            infos = zf.infolist()
    except (zipfile.BadZipFile, ValueError) as exc:
        raise XlsxRejected("Excel fayl buzilgan") from exc

    if len(infos) > MAX_XLSX_ENTRIES:
        raise XlsxRejected("Excel fayl tuzilishi yaroqsiz (juda ko'p ichki fayl)")
    total = sum(info.file_size for info in infos)
    if total > MAX_XLSX_UNCOMPRESSED_BYTES:
        logger.warning(
            "XLSX rad etildi: ochilgandagi hajm %d bayt (siqilgan %d bayt)",
            total, len(content),
        )
        raise XlsxRejected(
            "Excel fayl ochilganda juda katta — faylni bo'lib yuklang"
        )


def open_xlsx(content: bytes) -> Any:
    """Tekshirilgan `.xlsx` ni openpyxl bilan read-only ochish.

    Raises:
        XlsxRejected: tekshiruvdan o'tmadi yoki server `defusedxml` siz.
    """
    import openpyxl.xml
    from openpyxl import load_workbook

    if not openpyxl.xml.DEFUSEDXML:
        logger.error("defusedxml o'rnatilmagan — Excel yuklash o'chirilgan (pip install -r requirements.txt)")
        raise XlsxRejected("Server sozlanmagan: Excel yuklash vaqtincha mavjud emas")

    check_xlsx_archive(content)
    try:
        return load_workbook(BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # noqa: BLE001 — openpyxl turli xatolar tashlaydi
        logger.warning("Excel o'qishda xato: %s", exc)
        raise XlsxRejected(
            "Excel faylni o'qib bo'lmadi — fayl buzilgan yoki noto'g'ri formatda"
        ) from exc


def limit_rows(rows: Iterator[Any], max_rows: int = MAX_XLSX_DATA_ROWS) -> Iterator[Any]:
    """`ws.iter_rows()` ni `max_rows` qator bilan cheklash.

    Read-only rejimda varaq XML'i shu iteratsiya paytida parse qilinadi —
    defusedxml rad etgan (DTD/entity) yoki buzilgan XML xatosi ham shu yerda
    chiqadi va `XlsxRejected` ga aylanadi (500 emas, 400).

    Raises:
        XlsxRejected: qatorlar chegaradan oshsa yoki varaq o'qilmasa.
    """
    it = iter(rows)
    n = 0
    while True:
        try:
            row = next(it)
        except StopIteration:
            return
        except Exception as exc:  # noqa: BLE001 — defusedxml / XML parse xatolari
            logger.warning("Excel varag'ini o'qishda xato: %s", exc)
            raise XlsxRejected(
                "Excel faylni o'qib bo'lmadi — fayl buzilgan yoki noto'g'ri formatda"
            ) from exc
        n += 1
        if n > max_rows:
            raise XlsxRejected(
                f"Excel'da qatorlar {max_rows} tadan oshmasin — faylni bo'lib yuklang"
            )
        yield row


def text_cell(cell: Any) -> Any:
    """Eksportdagi ma'lumot katagi: `=` bilan boshlangan satr formula emas, matn bo'lib yoziladi.

    openpyxl `=` bilan boshlangan har qanday satrni formula qiladi. Ism, bino nomi
    va h.k. tashqi API yoki yuklangan Excel'dan keladi — `=HYPERLINK(...)` kabi
    qiymat admin faylni ochganda ishlab ketmasligi kerak (formula injection).
    Ataylab qo'yilgan formulali kataklarga (session_stats_excel) ishlatilmaydi.
    """
    if cell.data_type == "f":
        cell.data_type = "s"
    return cell
