"""Test sessiya statistika dashboard hisoblash xizmati.

Bir bloklangan tarzda (single function) `(session, session_smena)` uchun
4 ta asosiy summa va har bir region bo'yicha taqsimotni hisoblaydi.

Asosiy hisoblash qoidasi (Jami = Keldi + Kelmadi):
  Keldi (attended)         = is_entered OR is_cheating           — binoga kelganlar
                                                                   (kirishda yoki test ichida
                                                                   chetlatilganlar ham qo'shiladi)
  Kelmadi (not_attended)   = NOT is_entered AND NOT is_cheating  — umuman kelmagan
  Chetlatish (cheating)    = is_cheating                         — barcha chetlatilganlar
                                                                   (Keldi'ning bir qismi, info)

CheatingStat.at_entry/during_test/other — reason_type bo'yicha breakdown
(cheating.total ga teng: at_entry + during_test + other).

Tezlik: 2 ta SELECT (studentlar + cheating loglari). Python tarafida
agregatsiya — ming-o'n minglab qatordan ortiq bo'lsa SQL `GROUP BY` ga
ko'chirish kerak (kelajakda).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import func, select
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
    ZoneStatItem,
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

# Statistika ko'lami (scope) — bitta smena, bitta kun yoki butun sessiya
SCOPE_SMENA = "smena"      # bitta kun + smena (session_smena_id majburiy)
SCOPE_DAY = "day"          # bitta kunning barcha smenalari (day majburiy)
SCOPE_OVERALL = "overall"  # sessiyaning barcha kun va smenalari
VALID_SCOPES = (SCOPE_SMENA, SCOPE_DAY, SCOPE_OVERALL)


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
    # Tenglik: total = attended + not_attended
    #   attended      = is_entered OR is_cheating               (Keldi — binoga kelgan,
    #                                                            kirishda yoki testda
    #                                                            chetlatilgan bo'lsa ham)
    #   not_attended  = NOT is_entered AND NOT is_cheating      (Kelmadi — umuman kelmagan)
    #   cheating_total= is_cheating                             (Chetlatish — Keldi'ning info qismi)
    gb = _gender_bucket(gender_key)

    # Total
    tally.total += 1
    setattr(tally, f"total_{gb}", getattr(tally, f"total_{gb}") + 1)

    # Attended (Keldi) — kelganlar (verifydan o'tgan yoki chetlatilgan)
    if is_entered or is_cheating:
        tally.attended += 1
        setattr(tally, f"attended_{gb}", getattr(tally, f"attended_{gb}") + 1)

    # Not attended (Kelmadi) — umuman kelmagan, chetlatilmagan
    if not is_entered and not is_cheating:
        tally.not_attended += 1
        setattr(tally, f"not_attended_{gb}", getattr(tally, f"not_attended_{gb}") + 1)

    # Cheating total — barcha chetlatilganlar (Keldi'ning bir qismi, info)
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
    db: Session,
    *,
    session_id: int,
    session_smena_id: int | None = None,
    day: date | None = None,
    scope: str = SCOPE_SMENA,
) -> DashboardStatsResponse:
    """(session, scope) uchun dashboard statistikasini qaytarish.

    scope:
      - ``"smena"``   — bitta kun + smena (`session_smena_id` majburiy)
      - ``"day"``     — bitta kunning barcha smenalari (`day` majburiy)
      - ``"overall"`` — sessiyaning barcha kun va smenalari

    Tezlik: scope qanday bo'lishidan qat'i nazar 2 ta asosiy SELECT
    (studentlar + cheating loglari) — filtr `TestSessionSmena` join orqali
    qo'yiladi, shuning uchun katta IN-ro'yxatlardan qochiladi.

    Raises:
        DashboardStatsError: sessiya/smena topilmadi yoki parametr yetishmaydi.
    """
    if scope not in VALID_SCOPES:
        raise DashboardStatsError(f"Noma'lum scope: {scope}")

    session = db.get(TestSession, session_id)
    if session is None:
        raise DashboardStatsError("Sessiya topilmadi")

    smena = None
    if scope == SCOPE_SMENA:
        if session_smena_id is None:
            raise DashboardStatsError("session_smena_id majburiy (scope=smena)")
        smena = db.get(TestSessionSmena, session_smena_id)
        if smena is None:
            raise DashboardStatsError("Smena topilmadi")
        if smena.test_session_id != session_id:
            raise DashboardStatsError("Tanlangan smena bu sessiyaga tegishli emas")
    elif scope == SCOPE_DAY and day is None:
        raise DashboardStatsError("day majburiy (scope=day)")

    state = db.get(SessionState, session.test_state_id) if session.test_state_id else None
    state_key = int(state.key) if state else 0

    def _apply_scope(stmt):
        """Tanlangan ko'lam (scope) bo'yicha WHERE filtrlarini qo'shadi.

        `stmt` allaqachon `Student` va `TestSessionSmena` ni join qilgan
        bo'lishi shart.
        """
        stmt = stmt.where(TestSessionSmena.test_session_id == session_id)
        if scope == SCOPE_SMENA:
            stmt = stmt.where(Student.session_smena_id == session_smena_id)
        elif scope == SCOPE_DAY:
            stmt = stmt.where(TestSessionSmena.day == day)
        return stmt

    # 1) Studentlar — region/zone/gender bilan birga
    student_rows = db.execute(
        _apply_scope(
            select(
                Student.id,
                Student.is_entered,
                Student.is_cheating,
                Student.zone_id,
                Zone.region_id,
                Zone.number.label("zone_number"),
                Zone.name.label("zone_name"),
                Zone.is_part.label("zone_is_part"),
                Region.number.label("region_number"),
                Region.name.label("region_name"),
                Region.s_number.label("region_s_number"),
                Region.k_number.label("region_k_number"),
                Region.is_have_part.label("region_is_have_part"),
                Gender.key.label("gender_key"),
            )
            .select_from(Student)
            .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
            .join(Zone, Zone.id == Student.zone_id)
            .join(Region, Region.id == Zone.region_id)
            .outerjoin(StudentPsData, StudentPsData.student_id == Student.id)
            .outerjoin(Gender, Gender.id == StudentPsData.gender_id)
        )
    ).all()

    # 2) Chetlatish loglari — reason_type bo'yicha guruhlash uchun.
    #    IN-ro'yxat o'rniga scope filtri join orqali qo'yiladi (overall'da
    #    student_ids o'n minglab bo'lishi mumkin).
    cheating_map: dict[int, int | None] = {}
    cheating_rows = db.execute(
        _apply_scope(
            select(
                CheatingLog.student_id,
                ReasonType.key.label("rt_key"),
            )
            .select_from(CheatingLog)
            .join(Student, Student.id == CheatingLog.student_id)
            .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
            .join(Reason, Reason.id == CheatingLog.reason_id)
            .outerjoin(ReasonType, ReasonType.id == Reason.reason_type_id)
        )
    ).all()
    for sid, rt_key in cheating_rows:
        # Bitta studentda CheatingLog.student_id unique — kichik xavfsizlik
        cheating_map[int(sid)] = int(rt_key) if rt_key is not None else None

    # Agregatsiya
    summary = _Tally()
    by_region: dict[int, _Tally] = defaultdict(_Tally)
    by_zone: dict[int, _Tally] = defaultdict(_Tally)
    # region_id → (number, name, s_number, k_number, is_have_part)
    region_meta: dict[int, tuple[int, str, int, int, bool]] = {}
    # zone_id → (number, name, is_part)
    zone_meta: dict[int, tuple[int, str, bool]] = {}
    # Region → ichidagi zone ID'lari ro'yxati (unique, kelishi tartibida).
    zones_by_region: dict[int, list[int]] = defaultdict(list)
    seen_zones: set[int] = set()

    for row in student_rows:
        region_id = int(row.region_id)
        zone_id = int(row.zone_id)
        region_meta.setdefault(
            region_id,
            (
                int(row.region_number or 0),
                str(row.region_name or ""),
                int(row.region_s_number or 0),
                int(row.region_k_number or 0),
                bool(row.region_is_have_part),
            ),
        )
        zone_meta.setdefault(
            zone_id,
            (
                int(row.zone_number or 0),
                str(row.zone_name or ""),
                bool(row.zone_is_part),
            ),
        )
        if zone_id not in seen_zones:
            seen_zones.add(zone_id)
            zones_by_region[region_id].append(zone_id)
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
        _add_student_to_tally(
            by_zone[zone_id],
            is_entered=bool(row.is_entered),
            is_cheating=bool(row.is_cheating),
            gender_key=row.gender_key,
            cheating_reason_type_key=rt_key,
        )

    # Region cardlari — region.number bo'yicha tartiblangan; har bir
    # region ichidagi zonalar zone.number bo'yicha.
    region_items = sorted(
        by_region.items(),
        key=lambda kv: region_meta.get(kv[0], (0, "", 0, 0, False))[0],
    )
    regions: list[RegionStatItem] = []
    for region_id, tally in region_items:
        num, name, s_num, k_num, is_have_part = region_meta.get(
            region_id, (0, "", 0, 0, False)
        )
        zone_ids = sorted(
            zones_by_region.get(region_id, []),
            key=lambda zid: zone_meta.get(zid, (0, "", False))[0],
        )
        zones_list = [
            ZoneStatItem(
                zone_id=zid,
                zone_number=zone_meta.get(zid, (0, "", False))[0],
                zone_name=zone_meta.get(zid, (0, "", False))[1],
                is_part=zone_meta.get(zid, (0, "", False))[2],
                stats=_tally_to_stat_group(by_zone[zid]),
            )
            for zid in zone_ids
        ]
        regions.append(
            RegionStatItem(
                region_id=region_id,
                region_number=num,
                region_name=name,
                region_s_number=s_num,
                region_k_number=k_num,
                is_have_part=is_have_part,
                stats=_tally_to_stat_group(tally),
                zones=zones_list,
            )
        )

    # Scope bo'yicha meta — sarlavha va smenalar soni
    resp_smena_id: int | None = None
    resp_day: date | None = None
    resp_smena_number: int | None = None
    resp_smena_name: str | None = None
    smena_count = 1

    if scope == SCOPE_SMENA:
        resp_smena_id = session_smena_id
        resp_day = smena.day
        if smena.smena is not None:
            resp_smena_name = smena.smena.name or ""
            resp_smena_number = int(smena.smena.number)
    elif scope == SCOPE_DAY:
        resp_day = day
        smena_count = int(
            db.execute(
                select(func.count())
                .select_from(TestSessionSmena)
                .where(
                    TestSessionSmena.test_session_id == session_id,
                    TestSessionSmena.day == day,
                )
            ).scalar_one()
        )
    else:  # SCOPE_OVERALL
        smena_count = int(
            db.execute(
                select(func.count())
                .select_from(TestSessionSmena)
                .where(TestSessionSmena.test_session_id == session_id)
            ).scalar_one()
        )

    return DashboardStatsResponse(
        session_id=session_id,
        scope=scope,
        session_smena_id=resp_smena_id,
        day=resp_day,
        smena_number=resp_smena_number,
        smena_name=resp_smena_name,
        smena_count=smena_count,
        session_state_key=state_key,
        is_realtime=(state_key == STATE_KEY_ACTIVE),
        summary=_tally_to_stat_group(summary),
        regions=regions,
    )
