"""Statistika telegram bot uchun pydantic schemalari.

Ikki yo'nalish:
  - Bot tomoni (X-API-Key): `/check/{telegram_id}` va `/statistics`.
  - Admin paneli (JWT + permission): `statistic_bots` CRUD.
  - Qabul-2026 (JWT + permission): aggregatlangan realtime statistika.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.models.statistic_bot import ROLE_NAMES

VALID_ROLES = tuple(ROLE_NAMES.keys())  # (1, 2, 3)


# ============================================================
# Bot tomoni — access check
# ============================================================


class StatBotUserResponse(BaseModel):
    """Bot foydalanuvchisi (`statistic_bots` yozuvi) ma'lumotlari."""

    id: int
    fio: str
    telegram_id: int
    role: int
    role_name: str
    status: bool
    # Ruxsat bayroqlari — bot formatlash uchun shularga qaraydi.
    can_see_payment: bool
    can_see_prev_year: bool


class StatBotAccessResponse(BaseModel):
    """`telegram_id` orqali botga dostup tekshiruvi."""

    allowed: bool
    user: StatBotUserResponse | None = None
    message: str | None = None


# ============================================================
# Bot tomoni — tashqi APIdan statistika (proksi)
# ============================================================


class StatBotStatisticsResponse(BaseModel):
    """Tashqi APIdan olingan xom statistika (hududlar ro'yxati).

    `data` — har bir hudud uchun `count_2026`, `male_2026`, ... kabi
    kalitlarga ega lug'atlar ro'yxati. Bot uni o'zining formatteri bilan
    chiroyli matnga aylantiradi.
    """

    data: list[dict] = Field(default_factory=list)
    fetched_at: datetime | None = None


# ============================================================
# Qabul — aggregatlangan statistika (frontend dashboard)
# ============================================================
#
# Yil DINAMIK: hech qayerda qotib qolmagan. Tashqi API kalitlaridagi
# `count_YYYY` ichidan eng katta yil joriy yil sifatida aniqlanadi
# (`prev` esa undan oldingi). Shuning uchun keyingi mavsumda (masalan
# 2027) kod o'zgartirilmaydi — `year`/`prev_year` javobda qaytariladi.


class QabulRegionStat(BaseModel):
    region_name: str
    count: int
    male: int
    female: int
    paid: int
    share: float  # umumiydan ulush, %


class QabulStats(BaseModel):
    """Joriy yil bo'yicha aggregatlangan ko'rsatkichlar + o'tgan yil trendi.

    `year` / `prev_year` — ma'lumotdan avtomatik aniqlanadi (frontend
    sarlavhada shu qiymatni ko'rsatadi: "Qabul-{year}"). Permission
    `qabul:read` orqali himoyalangan.
    """

    # Aniqlangan yillar (dinamik)
    year: int
    prev_year: int
    # Joriy yil
    total: int
    male: int
    female: int
    graduated: int
    graduated_not: int
    paid: int
    unpaid: int
    uz: int
    ru: int
    qq: int
    lang_other: int
    # O'tgan yil (trend uchun)
    total_prev: int
    paid_prev: int
    male_prev: int
    female_prev: int
    # hududlar (count bo'yicha kamayish tartibida)
    regions: list[QabulRegionStat] = Field(default_factory=list)
    fetched_at: datetime | None = None


# ============================================================
# Admin CRUD — `statistic_bots`
# ============================================================


class StatisticBotAdminResponse(BaseModel):
    """Admin uchun bot foydalanuvchisi to'liq javobi."""

    id: int
    fio: str
    telegram_id: int
    role: int
    role_name: str
    status: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StatisticBotCreateRequest(BaseModel):
    """Yangi bot foydalanuvchisi yaratish so'rovi."""

    fio: str = Field(..., min_length=2, max_length=150)
    telegram_id: int = Field(..., gt=0)
    role: int = Field(..., description="1=Admin, 2=Rahbar, 3=Xodim")
    status: bool = True

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: int) -> int:
        if v not in VALID_ROLES:
            raise ValueError("role faqat 1 (Admin), 2 (Rahbar) yoki 3 (Xodim) bo'lishi mumkin")
        return v


class StatisticBotUpdateRequest(BaseModel):
    """Bot foydalanuvchisini tahrirlash so'rovi (qisman)."""

    fio: str | None = Field(default=None, min_length=2, max_length=150)
    telegram_id: int | None = Field(default=None, gt=0)
    role: int | None = None
    status: bool | None = None

    @field_validator("role")
    @classmethod
    def _check_role(cls, v: int | None) -> int | None:
        if v is not None and v not in VALID_ROLES:
            raise ValueError("role faqat 1 (Admin), 2 (Rahbar) yoki 3 (Xodim) bo'lishi mumkin")
        return v


# Bot statistika javobi yo'nalishi (Literal — kelajakda kengaytirish uchun)
StatBotStatus = Literal["ok", "error"]
