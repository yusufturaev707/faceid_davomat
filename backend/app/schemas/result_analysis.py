"""Natija uchun tahlil (result analysis) schemas.

Foydalanuvchi tashqi natija tizimidan (Excel/Access) qatorlarni joylaydi;
backend ularni FaceID bazasidagi talabalar bilan `imei` bo'yicha solishtiradi.
Tanlangan ko'lam: test + sana oralig'i + smena. Natijada nomuvofiqliklar
(masalan chetlatilgan bo'lsa-yu natija chiqqan) qaytariladi.
"""

from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel, Field


class AnalysisMode(str, Enum):
    """Tahlil turi.

    - IN_FACE_NOT_EXCLUDED_NO_RESULT — "Faceda bor - chetlatilmagan - natija chiqmagan"
    - IN_FACE_EXCLUDED_HAS_RESULT    — "Faceda bor - chetlatilgan - natija chiqqan"
    - NOT_IN_FACE_HAS_RESULT         — "Faceda yo'q - natija chiqqan"
    """

    IN_FACE_NOT_EXCLUDED_NO_RESULT = "in_face_not_excluded_no_result"
    IN_FACE_EXCLUDED_HAS_RESULT = "in_face_excluded_has_result"
    NOT_IN_FACE_HAS_RESULT = "not_in_face_has_result"


class ScopeSession(BaseModel):
    """Formaning ko'lam tanlovi uchun: aktiv test sessiya + uning test kunlari."""

    id: int
    name: str
    number: int
    days: list[str]  # ISO ("YYYY-MM-DD"), o'sish tartibida


class ResultRow(BaseModel):
    """Textarea'ga joylangan bitta natija qatoridan tahlil uchun kerakli maydonlar.

    Xom qatorda `imei, abitur_id, img, common_ball, tday, deleted` ustunlari
    bo'ladi — frontend solishtiruvga kerak bo'lganlarini (imei, tday,
    common_ball, deleted) yuboradi.

    "natija chiqqan" (result produced) — imei mavjud VA `deleted` yolg'on VA
    `common_ball` bo'sh emas. Aks holda ("imei yo'q" / `deleted=-1` /
    `common_ball` null) — "natija chiqmagan".
    """

    imei: str | None = Field(default=None, max_length=64)
    abitur_id: str | None = Field(default=None, max_length=64)
    tday: str | None = Field(default=None, max_length=32)
    common_ball: str | None = Field(default=None, max_length=32)
    deleted: bool = False  # tahlil mantiqi uchun (parsed)
    deleted_raw: str | None = Field(default=None, max_length=32)  # ko'rsatish uchun


class ResultAnalysisRequest(BaseModel):
    test_session_id: int
    # None — "Umumiy" (sessiyaning barcha kunlari); aks holda bitta test kuni.
    day: date | None = None
    mode: AnalysisMode
    rows: list[ResultRow] = Field(default_factory=list, max_length=300000)


class ResultAnalysisItem(BaseModel):
    """Natija jadvalining bir qatori."""

    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    imei: str | None = None
    region_name: str | None = None
    zone_name: str | None = None
    test_day: str | None = None  # FaceID bazasidagi test kuni (TestSessionSmena.day)
    smena_name: str | None = None
    # Tashqi natija tizimidan (imei bo'yicha moslashtirilgan) qo'shimcha ustunlar:
    abitur_id: str | None = None
    tday: str | None = None  # natija tizimidagi test kuni
    deleted: str | None = None  # natija tizimidagi deleted (xom qiymat)


class ResultAnalysisResponse(BaseModel):
    mode: AnalysisMode
    count: int
    # Diagnostika — foydalanuvchi tahlilga ishonchi uchun.
    scope_total: int  # Tanlangan ko'lamdagi FaceID talabalari soni
    pasted_total: int  # Joylangan noyob imei soni
    pasted_result_count: int  # Ulardan "natija chiqqan" (o'chirilmagan) soni
    items: list[ResultAnalysisItem]
