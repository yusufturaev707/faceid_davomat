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

    total = barcha `is_cheating` (kirishda + test jarayonida).
    Chetlatilganlar `attended` (Keldi) ichida ham hisoblanadi — bu yerda
    alohida informativ ko'rinishda chiqariladi.

    Reason_type breakdown:
      at_entry    — `reason_type.key == 1` (binoga kirishda)
      during_test — `reason_type.key == 2` (test jarayonida)
      other       — boshqa yoki reason_type biriktirilmagan
    Tenglik: `total == at_entry + during_test + other`.
    """

    total: int
    at_entry: int
    during_test: int
    other: int
    male: int
    female: int
    unknown: int


class StatGroup(BaseModel):
    """4 ta dashboard cardini qoplaydigan to'plamlash.

    Tenglik: `total.total == attended.total + not_attended.total`
    (cheating — attended ichidagi informativ qism)
    """

    total: GenderStat
    attended: GenderStat       # Keldi — is_entered OR is_cheating (chetlatilganlar ham)
    not_attended: GenderStat   # Kelmadi — NOT is_entered AND NOT is_cheating
    cheating: CheatingStat     # Chetlatish — is_cheating (attended ichidagi qism, info)


class ZoneStatItem(BaseModel):
    """Bitta bino (zone) bo'yicha statistika — Region card bosilganda
    modal ichida ko'rsatish uchun."""

    zone_id: int
    zone_number: int
    zone_name: str
    stats: StatGroup


class RegionStatItem(BaseModel):
    region_id: int
    region_number: int
    region_name: str
    # Muqobil tartiblash identifikatorlari (DTM=number, VM=k_number, IIV=s_number).
    # Front kartalarni va Excel hisobotini bir xil kalit bo'yicha tartiblaydi.
    region_s_number: int = 0
    region_k_number: int = 0
    stats: StatGroup
    # Region ichidagi binolar — modal'da ko'rsatiladi (lozim bo'lganda).
    # Tartibi: zone.number bo'yicha.
    zones: list[ZoneStatItem] = []


class DashboardStatsResponse(BaseModel):
    session_id: int
    # Statistika ko'lami: "smena" (bitta kun+smena) | "day" (bitta kun) |
    # "overall" (butun sessiya).
    scope: str = "smena"
    # smena/day/overall ga qarab to'ldiriladi (overall'da day=None, smena
    # maydonlari faqat scope="smena" da bo'ladi).
    session_smena_id: int | None = None
    day: date | None = None
    smena_number: int | None = None
    smena_name: str | None = None
    # Nechta smena agregatsiya qilindi (smena=1, day=shu kun smenalari,
    # overall=sessiyaning barcha smenalari).
    smena_count: int = 1
    # Front'da real-time polling boshlash uchun: 4 = ACTIVE/ready
    session_state_key: int
    is_realtime: bool
    summary: StatGroup
    regions: list[RegionStatItem]
