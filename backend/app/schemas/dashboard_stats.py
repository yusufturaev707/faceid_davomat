"""Test session statistika dashboard schemas."""

from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class GenderStat(BaseModel):
    """Gender breakdown — male/female/unknown va total.

    `unknown` — gender.key 1/2 dan tashqari yoki student_ps_data.gender_id NULL.
    """

    total: int
    male: int
    female: int
    unknown: int


class CheatingStat(BaseModel):
    """Chetlatilganlar — joy bo'yicha va gender bo'yicha bo'linish.

    at_entry — `reason_type.key == 1` (binoga kirishda)
    during_test — `reason_type.key == 2` (test jarayonida)
    other — boshqa yoki reason_type biriktirilmagan
    """

    total: int
    at_entry: int
    during_test: int
    other: int
    male: int
    female: int
    unknown: int


class StatGroup(BaseModel):
    """4 ta dashboard cardini qoplaydigan to'plamlash."""

    total: GenderStat
    attended: GenderStat       # is_entered = True
    not_attended: GenderStat   # is_entered = False
    cheating: CheatingStat


class RegionStatItem(BaseModel):
    region_id: int
    region_number: int
    region_name: str
    stats: StatGroup


class DashboardStatsResponse(BaseModel):
    session_id: int
    session_smena_id: int
    day: date
    smena_number: int
    smena_name: str
    # Front'da real-time polling boshlash uchun: 4 = ACTIVE/ready
    session_state_key: int
    is_realtime: bool
    summary: StatGroup
    regions: list[RegionStatItem]
