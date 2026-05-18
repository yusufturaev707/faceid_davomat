"""Aiogram3 `CallbackData` schemalari — inline tugmalar uchun.

Telegram callback_data 64 byte cheklovi bor — barcha sxemalar qisqa
prefixlar va minimal payload bilan tuzilgan.
"""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData


class MainMenuCB(CallbackData, prefix="mm"):
    """Bosh menyu tugmalari."""

    action: str  # "davomat" | "change_region"


class RegionPickCB(CallbackData, prefix="rgn"):
    """`/start` (yoki "Regionni almashtirish") da region tanlash.

    Bot foydalanuvchisi bir nechta regionga biriktirilgan bo'lsa, qaysi
    region kesimida ishlashini tanlaydi. Tanlangan region keyingi barcha
    so'rovlarga filtri sifatida uzatiladi.
    """

    region_id: int


class SessionCB(CallbackData, prefix="sess"):
    """Tayyor sessiyalar ro'yxatidan bittasini tanlash."""

    session_id: int


class SmenaCB(CallbackData, prefix="sm"):
    """Sessiya ichidan kun+smena tanlash."""

    session_id: int
    smena_id: int  # TestSessionSmena.id


class ActionCB(CallbackData, prefix="act"):
    """Smena tanlangandan keyingi amallar.

    `session_id` va `smena_id` keyingi qadamlarga olib o'tiladi.
    """

    action: str  # "stats" | "absent" | "faceid" | "remove"
    session_id: int
    smena_id: int


class AggrCB(CallbackData, prefix="agr"):
    """Aggregat tanlov: bitta kun (barcha smenalar) yoki butun sessiya.

    `scope`:
      - `"day"`  — `day` (YYYY-MM-DD) bo'yicha shu kun ichidagi barcha smenalar.
      - `"total"`— butun sessiya; `day` = `"-"` (sentinel).

    `day` ni hech qachon bo'sh string qilmaymiz: aiogram CallbackData
    pack qilinganda trailing `:` qo'yadi, Telegram esa transport qatlamida
    trailing bo'sh fragmentni saqlamasligi mumkin va unpack TypeError
    bilan tushadi. Shuning uchun "yo'q" qiymati uchun `"-"` ishlatamiz.
    """

    scope: str  # "day" | "total"
    session_id: int
    day: str  # YYYY-MM-DD yoki "-"


class AggrActionCB(CallbackData, prefix="aac"):
    """Aggregat (kun/sessiya) tanlovidan keyingi amallar.

    Faqat `"stats"` yoki `"absent"` — Face ID va olib tashlash yo'q.
    `day` = `"-"` total scope uchun (bo'sh string ishlatmaymiz, qarang
    `AggrCB`).
    """

    action: str  # "stats" | "absent"
    scope: str   # "day" | "total"
    session_id: int
    day: str


class FaceIDMethodCB(CallbackData, prefix="fid"):
    """Face ID — pasportni qanday kiritish usuli."""

    method: str  # "manual" | "qr"
    session_id: int
    smena_id: int


class AttendanceCB(CallbackData, prefix="att"):
    """Verify natijasidan keyin "Davomatga qo'shish" tugmasi.

    `decision`: "yes" — qo'shish, "no" — bekor qilish.
    """

    decision: str
    student_id: int
    session_id: int
    smena_id: int


class RemovePickCB(CallbackData, prefix="rmp"):
    """JShShIR bo'yicha bir nechta yozuv chiqqanda — qaysi birini olib
    tashlashni tanlash."""

    student_id: int
    session_id: int
    smena_id: int


class RemoveConfirmCB(CallbackData, prefix="rmc"):
    """Davomatdan olib tashlashni yakuniy tasdiqlash.

    `decision`: "yes" — olib tashlash, "no" — bekor qilish.
    """

    decision: str
    student_id: int
    session_id: int
    smena_id: int


class CheatPickCB(CallbackData, prefix="chp"):
    """JShShIR bo'yicha bir nechta yozuv chiqqanda — qaysi birini
    chetlatishni tanlash.
    """

    student_id: int
    session_id: int
    smena_id: int


class CheatTypeCB(CallbackData, prefix="cht"):
    """Chetlatish turini tanlash (reason_type)."""

    type_id: int
    student_id: int
    session_id: int
    smena_id: int


class CheatReasonCB(CallbackData, prefix="chr"):
    """Tanlangan tur ichida sababni tanlash (reason)."""

    reason_id: int
    student_id: int
    session_id: int
    smena_id: int


class CheatConfirmCB(CallbackData, prefix="chc"):
    """Chetlatishni yakuniy tasdiqlash.

    `decision`: "yes" — chetlatish, "no" — bekor qilish.
    """

    decision: str
    student_id: int
    reason_id: int
    session_id: int
    smena_id: int


class BackCB(CallbackData, prefix="back"):
    """Orqaga qaytish — `to` qiymati qaysi sahifaga qaytishni belgilaydi."""

    to: str  # "main" | "sessions" | "smenas" | "actions"
    session_id: int = 0
    smena_id: int = 0
