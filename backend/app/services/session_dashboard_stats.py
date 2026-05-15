"""Test sessiya statistika dashboard hisoblash xizmati.

Bir bloklangan tarzda (single function) `(session, session_smena)` uchun
4 ta asosiy summa va har bir region bo'yicha taqsimotni hisoblaydi.

Tezlik: 2 ta SELECT (studentlar + cheating loglari). Python tarafida
agregatsiya — ming-o'n minglab qatordan ortiq bo'lsa SQL `GROUP BY` ga
ko'chirish kerak (kelajakda).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cheating_log import CheatingLog
from app.models.gender import Gender
from app.models.reason import Reason
from app.models.reason_type import ReasonType
from app.models.region import Region
from app.models.session_state import SessionState
from app.models.student import Student
from app.models.student_ps_data import StudentPsData
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.zone import Zone
from app.schemas.dashboard_stats import (
    CheatingStat,
    DashboardStatsResponse,
    GenderStat,
    RegionStatItem,
    StatGroup,
)

logger = logging.getLogger("faceid.services.dashboard_stats")

# === Konfiguratsiya — admin DB seed orqali boshqa qiymatlarni qo'yganda
# shu konstantalarni moslang. ReasonType.key qiymatlari domain-bog'liq.
ENTRY_REASON_TYPE_KEY = 1     # "Binoga kirishda" chetlatish
TEST_REASON_TYPE_KEY = 2      # "Test jarayonida" chetlatish

# Session ready bo'lganda (real-time mode) frontend polling boshlaydi
STATE_KEY_ACTIVE = 4

# Gender.key qiymatlari
GENDER_MALE = 1
GENDER_FEMALE = 2


class DashboardStatsError(Exception):
    """Sessiya yoki smena topilmadi / mos kelmaydi."""


@dataclass
class _Tally:
    """Bitta scope (umumiy yoki bitta region) bo'yicha hisoblagichlar."""

    total: int = 0
    total_male: int = 0
    total_female: int = 0
    total_unknown: int = 0

    attended: int = 0
    attended_male: int = 0
    attended_female: int = 0
    attended_unknown: int = 0

    not_attended: int = 0
    not_attended_male: int = 0
    not_attended_female: int = 0
    not_attended_unknown: int = 0

    cheating_total: int = 0
    cheating_at_entry: int = 0
    cheating_during_test: int = 0
    cheating_other: int = 0
    cheating_male: int = 0
    cheating_female: int = 0
    cheating_unknown: int = 0


def _gender_bucket(gender_key: int | None) -> str:
    """gender_key → 'male' | 'female' | 'unknown'."""
    if gender_key == GENDER_MALE:
        return "male"
    if gender_key == GENDER_FEMALE:
        return "female"
    return "unknown"


def _add_student_to_tally(
    tally: _Tally,
    *,
    is_entered: bool,
    is_cheating: bool,
    gender_key: int | None,
    cheating_reason_type_key: int | None,
) -> None:
    gb = _gender_bucket(gender_key)

    # Total
    tally.total += 1
    setattr(tally, f"total_{gb}", getattr(tally, f"total_{gb}") + 1)

    # Attended / not attended
    if is_entered:
        tally.attended += 1
        setattr(tally, f"attended_{gb}", getattr(tally, f"attended_{gb}") + 1)
    else:
        tally.not_attended += 1
        setattr(tally, f"not_attended_{gb}", getattr(tally, f"not_attended_{gb}") + 1)

    # Cheating
    if is_cheating:
        tally.cheating_total += 1
        setattr(tally, f"cheating_{gb}", getattr(tally, f"cheating_{gb}") + 1)
        if cheating_reason_type_key == ENTRY_REASON_TYPE_KEY:
            tally.cheating_at_entry += 1
        elif cheating_reason_type_key == TEST_REASON_TYPE_KEY:
            tally.cheating_during_test += 1
        else:
            tally.cheating_other += 1


def _tally_to_stat_group(t: _Tally) -> StatGroup:
    return StatGroup(
        total=GenderStat(
            total=t.total,
            male=t.total_male,
            female=t.total_female,
            unknown=t.total_unknown,
        ),
        attended=GenderStat(
            total=t.attended,
            male=t.attended_male,
            female=t.attended_female,
            unknown=t.attended_unknown,
        ),
        not_attended=GenderStat(
            total=t.not_attended,
            male=t.not_attended_male,
            female=t.not_attended_female,
            unknown=t.not_attended_unknown,
        ),
        cheating=CheatingStat(
            total=t.cheating_total,
            at_entry=t.cheating_at_entry,
            during_test=t.cheating_during_test,
            other=t.cheating_other,
            male=t.cheating_male,
            female=t.cheating_female,
            unknown=t.cheating_unknown,
        ),
    )


def get_dashboard_stats(
    db: Session, *, session_id: int, session_smena_id: int
) -> DashboardStatsResponse:
    """Bitta (session, smena+kun) uchun dashboard statistikasini qaytarish.

    Raises:
        DashboardStatsError: sessiya yoki smena topilmadi yoki bog'lanmagan.
    """
    session = db.get(TestSession, session_id)
    if session is None:
        raise DashboardStatsError("Sessiya topilmadi")

    smena = db.get(TestSessionSmena, session_smena_id)
    if smena is None:
        raise DashboardStatsError("Smena topilmadi")
    if smena.test_session_id != session_id:
        raise DashboardStatsError("Tanlangan smena bu sessiyaga tegishli emas")

    state = db.get(SessionState, session.test_state_id) if session.test_state_id else None
    state_key = int(state.key) if state else 0

    # 1) Studentlar — region/gender bilan birga
    student_rows = db.execute(
        select(
            Student.id,
            Student.is_entered,
            Student.is_cheating,
            Zone.region_id,
            Region.number.label("region_number"),
            Region.name.label("region_name"),
            Gender.key.label("gender_key"),
        )
        .select_from(Student)
        .join(Zone, Zone.id == Student.zone_id)
        .join(Region, Region.id == Zone.region_id)
        .outerjoin(StudentPsData, StudentPsData.student_id == Student.id)
        .outerjoin(Gender, Gender.id == StudentPsData.gender_id)
        .where(Student.session_smena_id == session_smena_id)
    ).all()

    # 2) Chetlatish loglari — reason_type bo'yicha guruhlash uchun
    student_ids = [r.id for r in student_rows]
    cheating_map: dict[int, int | None] = {}
    if student_ids:
        cheating_rows = db.execute(
            select(
                CheatingLog.student_id,
                ReasonType.key.label("rt_key"),
            )
            .select_from(CheatingLog)
            .join(Reason, Reason.id == CheatingLog.reason_id)
            .outerjoin(ReasonType, ReasonType.id == Reason.reason_type_id)
            .where(CheatingLog.student_id.in_(student_ids))
        ).all()
        for sid, rt_key in cheating_rows:
            # Bitta studentda CheatingLog.student_id unique — kichik xavfsizlik
            cheating_map[int(sid)] = int(rt_key) if rt_key is not None else None

    # Agregatsiya
    summary = _Tally()
    by_region: dict[int, _Tally] = defaultdict(_Tally)
    region_meta: dict[int, tuple[int, str]] = {}  # region_id → (number, name)

    for row in student_rows:
        region_id = int(row.region_id)
        region_meta.setdefault(
            region_id, (int(row.region_number or 0), str(row.region_name or ""))
        )
        rt_key = cheating_map.get(int(row.id)) if row.is_cheating else None

        _add_student_to_tally(
            summary,
            is_entered=bool(row.is_entered),
            is_cheating=bool(row.is_cheating),
            gender_key=row.gender_key,
            cheating_reason_type_key=rt_key,
        )
        _add_student_to_tally(
            by_region[region_id],
            is_entered=bool(row.is_entered),
            is_cheating=bool(row.is_cheating),
            gender_key=row.gender_key,
            cheating_reason_type_key=rt_key,
        )

    # Region cardlari — region.number bo'yicha tartiblangan
    region_items = sorted(
        by_region.items(),
        key=lambda kv: region_meta.get(kv[0], (0, ""))[0],
    )
    regions: list[RegionStatItem] = []
    for region_id, tally in region_items:
        num, name = region_meta.get(region_id, (0, ""))
        regions.append(
            RegionStatItem(
                region_id=region_id,
                region_number=num,
                region_name=name,
                stats=_tally_to_stat_group(tally),
            )
        )

    smena_name = ""
    smena_number = 0
    if smena.smena is not None:
        smena_name = smena.smena.name or ""
        smena_number = int(smena.smena.number)

    return DashboardStatsResponse(
        session_id=session_id,
        session_smena_id=session_smena_id,
        day=smena.day,
        smena_number=smena_number,
        smena_name=smena_name,
        session_state_key=state_key,
        is_realtime=(state_key == STATE_KEY_ACTIVE),
        summary=_tally_to_stat_group(summary),
        regions=regions,
    )
