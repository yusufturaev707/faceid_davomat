"""Davomat Telegram Mini App uchun pydantic schemalari.

Bot kanali (`schemas/davomat_bot.py`) dan farqi: so'rovlarda `telegram_id`
yo'q — foydalanuvchi imzolangan `initData` dan aniqlanadi. Javob modellari
imkon qadar bot kanalinikidan qayta ishlatiladi.
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.davomat_bot import BotStudentSlot, BotUserResponse


class MiniAppMeResponse(BaseModel):
    """Mini App ochilganda — dostup va profil.

    `allowed=False` bo'lsa ham `telegram_id` qaytariladi: foydalanuvchi uni
    administratorga yuborib ro'yxatdan o'tishi mumkin.
    """

    allowed: bool
    telegram_id: int
    user: BotUserResponse | None = None
    message: str | None = None


class MiniAppAbsenteesRequest(BaseModel):
    """Kelmaganlar ro'yxati — smena, kun yoki butun sessiya kesimida."""

    session_smena_id: int | None = None
    test_day: date | None = None
    region_id: int | None = None


class MiniAppAbsenteesResponse(BaseModel):
    """`sent` — fayl chatga yuborildi; `empty` — kelmaganlar yo'q, fayl yuborilmadi."""

    status: Literal["sent", "empty"]
    count: int
    filename: str = ""
    message: str = ""


class MiniAppPassportQrRequest(BaseModel):
    """Telegram native skaner matni (`text`) yoki QR rasmi (`image_b64`)."""

    text: str | None = Field(default=None, max_length=2048)
    image_b64: str | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> MiniAppPassportQrRequest:
        if bool(self.text) == bool(self.image_b64):
            raise ValueError("`text` yoki `image_b64` dan aynan bittasi yuborilishi kerak")
        return self


class MiniAppPassportResponse(BaseModel):
    ps_ser: str
    ps_num: str
    jshshir: str


class MiniAppFaceVerifyRequest(BaseModel):
    session_id: int
    session_smena_id: int
    region_id: int | None = None
    ps_ser: str = Field(..., min_length=1, max_length=5)
    ps_num: str = Field(..., min_length=1, max_length=10)
    jshshir: str = Field(..., pattern=r"^\d{14}$")
    selfie_b64: str = Field(..., min_length=1)


class MiniAppFaceVerifyResponse(BaseModel):
    """`BotFaceVerifyResponse` bilan bir xil, farqlari:

    - `selfie_b64` qaytarilmaydi (klientda allaqachon bor — trafik tejaladi).
    - `verify_ticket` — faqat `can_attend=True` bo'lganda; `mark-attendance`
      shu chipta bilan chaqiriladi.
    """

    status: Literal[
        "in_smena",
        "wrong_slot",
        "not_in_session",
        "wrong_passport",
        "no_face",
        "applied",
        "error",
    ]
    verified: bool = False
    score: int = 0
    threshold: int = 0
    can_attend: bool = False
    fio: str | None = None
    photo_b64: str | None = None
    message: str = ""
    slot: BotStudentSlot | None = None
    verify_ticket: str | None = None


class MiniAppMarkAttendanceRequest(BaseModel):
    """Davomatga qo'shish — talabgor, smena, region va ball chiptadan olinadi.

    `selfie_b64` — Face ID'da yuborilgan aynan o'sha selfie (xeshi chiptadagi
    bilan solishtiriladi) — `StudentLog.first_captured/last_captured` ga yoziladi.
    """

    verify_ticket: str = Field(..., min_length=10, max_length=2048)
    selfie_b64: str = Field(..., min_length=1)


class MiniAppFindByJshshirRequest(BaseModel):
    session_smena_id: int
    region_id: int | None = None
    jshshir: str = Field(..., pattern=r"^\d{14}$")


class MiniAppRemoveAttendanceRequest(BaseModel):
    student_id: int
    session_smena_id: int
    region_id: int | None = None


class MiniAppFindForCheatRequest(BaseModel):
    session_id: int
    region_id: int | None = None
    jshshir: str = Field(..., pattern=r"^\d{14}$")


class MiniAppCheatRequest(BaseModel):
    student_id: int
    session_id: int
    region_id: int | None = None
    reason_id: int
