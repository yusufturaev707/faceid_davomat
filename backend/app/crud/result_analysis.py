"""Natija uchun tahlil — solishtiruv logikasi.

Tanlangan ko'lam (test + sana oralig'i + smena) bo'yicha FaceID bazasidagi
talabalar bilan tashqi natija qatorlarini `imei` bo'yicha solishtiradi.

Atamalar:
- "Faceda bor"        — talaba FaceID bazasida (tanlangan ko'lamda) mavjud.
- "chetlatilgan"      — `Student.is_cheating == True`.
- "chetlatilmagan"    — `Student.is_cheating == False`.
- "natija chiqqan"    — tashqi natijada shu imei uchun o'chirilmagan qator bor.
- "natija chiqmagan"  — imei o'chirilmagan natija qatorlari orasida yo'q
                        (umuman kelmagan yoki `deleted=True`).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.zone import Zone
from app.schemas.result_analysis import (
    AnalysisMode,
    ResultAnalysisItem,
    ResultAnalysisResponse,
    ResultRow,
)


def _norm(imei: str | None) -> str:
    return (imei or "").strip()


def _scope_item(row) -> ResultAnalysisItem:
    """FaceID talaba qatoridan natija jadvali elementini yasaydi."""
    return ResultAnalysisItem(
        last_name=row.last_name,
        first_name=row.first_name,
        middle_name=row.middle_name,
        imei=row.imei,
        region_name=row.region_name,
        zone_name=row.zone_name,
        test_day=row.test_day.isoformat() if row.test_day else None,
        smena_name=row.smena_name,
    )


def analyze_results(
    db: Session,
    *,
    test_id: int,
    smena_id: int,
    date_from: date,
    date_to: date,
    mode: AnalysisMode,
    rows: list[ResultRow],
) -> ResultAnalysisResponse:
    # 1) Tashqi natija qatorlarini imei bo'yicha indekslaymiz.
    has_result_imeis: set[str] = set()  # "natija chiqqan" (deleted=False)
    all_pasted_imeis: set[str] = set()
    tday_by_imei: dict[str, str] = {}
    for r in rows:
        imei = _norm(r.imei)
        if not imei:
            continue
        all_pasted_imeis.add(imei)
        if not r.deleted:
            has_result_imeis.add(imei)
            if imei not in tday_by_imei and r.tday:
                tday_by_imei[imei] = r.tday.strip()

    # 2) Tanlangan ko'lam bo'yicha FaceID talabalari.
    stmt = (
        select(
            Student.imei,
            Student.is_cheating,
            Student.last_name,
            Student.first_name,
            Student.middle_name,
            Region.name.label("region_name"),
            Zone.name.label("zone_name"),
            Smena.name.label("smena_name"),
            TestSessionSmena.day.label("test_day"),
        )
        .join(TestSessionSmena, Student.session_smena_id == TestSessionSmena.id)
        .join(TestSession, TestSessionSmena.test_session_id == TestSession.id)
        .outerjoin(Zone, Student.zone_id == Zone.id)
        .outerjoin(Region, Zone.region_id == Region.id)
        .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
        .where(
            TestSession.test_id == test_id,
            TestSessionSmena.test_smena_id == smena_id,
            TestSessionSmena.day >= date_from,
            TestSessionSmena.day <= date_to,
        )
    )
    scope_rows = db.execute(stmt).all()
    scope_imeis: set[str] = {_norm(r.imei) for r in scope_rows if _norm(r.imei)}

    items: list[ResultAnalysisItem] = []

    if mode == AnalysisMode.IN_FACE_NOT_EXCLUDED_NO_RESULT:
        # Faceda bor + chetlatilmagan + natija chiqmagan
        for r in scope_rows:
            if not r.is_cheating and _norm(r.imei) not in has_result_imeis:
                items.append(_scope_item(r))
    elif mode == AnalysisMode.IN_FACE_EXCLUDED_HAS_RESULT:
        # Faceda bor + chetlatilgan + natija chiqqan
        for r in scope_rows:
            if r.is_cheating and _norm(r.imei) in has_result_imeis:
                items.append(_scope_item(r))
    else:  # AnalysisMode.NOT_IN_FACE_HAS_RESULT
        # Faceda yo'q + natija chiqqan — talaba ko'lamda topilmadi, shuning uchun
        # faqat imei va natijadagi test kuni (tday) ma'lum.
        for imei in sorted(has_result_imeis - scope_imeis):
            items.append(
                ResultAnalysisItem(imei=imei, test_day=tday_by_imei.get(imei))
            )

    return ResultAnalysisResponse(
        mode=mode,
        count=len(items),
        scope_total=len(scope_rows),
        pasted_total=len(all_pasted_imeis),
        pasted_result_count=len(has_result_imeis),
        items=items,
    )
