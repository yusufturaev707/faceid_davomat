"""Davomat telegram bot uchun pydantic schemalari."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


# === Access check / profile ===


class BotRegionInfo(BaseModel):
    id: int
    name: str
    number: int


class BotZoneInfo(BaseModel):
    id: int
    name: str
    number: int
    region_id: int


class BotRoleInfo(BaseModel):
    """Bot foydalanuvchisiga biriktirilgan rol."""

    id: int
    name: str
    key: int


class BotUserResponse(BaseModel):
    """Bot foydalanuvchisi (`davomat_bots` yozuvi) ma'lumotlari.

    `regions` — biriktirilgan barcha regionlar (M2M). `role.key == 4` bo'lsa
    aniq 1 ta, aks holda 1+ ta region biriktirilgan bo'lishi mumkin.
    """

    id: int
    fio: str
    telegram_id: int
    is_active: bool
    role: BotRoleInfo | None = None
    regions: list[BotRegionInfo] = Field(default_factory=list)
    allowed_region_ids: list[int] = Field(default_factory=list)


class BotAccessResponse(BaseModel):
    """`telegram_id` orqali botga dostup tekshiruvi."""

    allowed: bool
    user: BotUserResponse | None = None
    message: str | None = None


# === Ready test sessions (state.key == 4 — ready/active) ===


class BotSmenaInfo(BaseModel):
    """Bitta kunlik smena (TestSessionSmena yozuvi)."""

    id: int  # TestSessionSmena.id
    smena_id: int  # Smena.id
    smena_number: int
    smena_name: str
    day: date


class BotReadySessionResponse(BaseModel):
    id: int
    name: str
    test_name: str
    start_date: date
    finish_date: date
    smenas: list[BotSmenaInfo] = Field(default_factory=list)


# === Region/zone statistika (smena bo'yicha) ===


class BotZoneStat(BaseModel):
    zone_id: int
    zone_name: str
    zone_number: int
    total: int
    entered: int
    not_entered: int
    cheating: int


class BotRegionStat(BaseModel):
    region_id: int
    region_name: str
    region_number: int
    total: int
    entered: int
    not_entered: int
    cheating: int
    zones: list[BotZoneStat] = Field(default_factory=list)


class BotSessionStatsResponse(BaseModel):
    """Tanlangan kontekst (smena / kun / butun sessiya) bo'yicha
    foydalanuvchining biriktirilgan regionlari kesimida statistika.

    `scope`:
      - `"smena"` — bitta TestSessionSmena bo'yicha (yagona kun+smena).
      - `"day"`   — bitta sananing barcha smenalari bo'yicha aggregat.
      - `"total"` — sessiyaning barcha kunlari va smenalari bo'yicha aggregat.

    `scope != "smena"` da `session_smena_id` 0 bo'lishi mumkin va
    `smena_number`/`smena_name` aggregat sarlavhasi sifatida ishlatiladi
    (masalan, "Kun yakuni" yoki "Umumiy").
    """

    session_id: int
    session_smena_id: int = 0
    test_day: date | None = None
    smena_number: int = 0
    smena_name: str = ""
    scope: Literal["smena", "day", "total"] = "smena"
    title: str = ""
    regions: list[BotRegionStat] = Field(default_factory=list)


# === Face ID — passport + selfie tekshiruv ===


class BotFaceVerifyRequest(BaseModel):
    """`ps_ser` + `ps_num` + `jshshir` (IMEI) bo'yicha GTSP'dan rasm olib
    selfie bilan solishtirish.

    Tanlangan sessiya/smena yuborilsa, backend qo'shimcha DB tekshiruvini
    bajaradi: shu jshshir tanlangan smenada bormi, yo'qmi shu sessiyaning
    boshqa smenasida bormi.

    `region_id` (ixtiyoriy) — bot 2+ regionga biriktirilgan foydalanuvchi
    `/start` da tanlagan region. Berilgan bo'lsa, talaba shu regionga
    tegishli bo'lishi shart (aks holda `wrong_slot`).
    """

    telegram_id: int = Field(..., description="Telegram foydalanuvchi id")
    session_id: int = Field(..., description="TestSession.id (statusi `active`)")
    session_smena_id: int = Field(
        ..., description="TestSessionSmena.id (tanlangan kun+smena)"
    )
    region_id: int | None = Field(default=None, description="Tanlangan region")
    ps_ser: str = Field(..., min_length=1, max_length=5)
    ps_num: str = Field(..., min_length=1, max_length=10)
    jshshir: str = Field(..., min_length=14, max_length=14)
    selfie_b64: str = Field(..., description="Selfie rasm base64 (data URI yoki sof)")


class BotStudentSlot(BaseModel):
    """Bot Face ID javobida talabaning testdagi joyi (slot) haqida ma'lumot.

    `wrong_slot` holatida — talaba aslida qaysi (kun/smena/binoda) ekanligi.
    `in_smena` holatida — tanlangan kun/smena/binodagi joyi.
    """

    student_id: int
    fio: str
    jshshir: str | None = None
    region_name: str | None = None
    zone_name: str | None = None
    test_day: str | None = None  # ISO date
    smena_number: int | None = None
    smena_name: str | None = None
    gr_n: int | None = None
    sp_n: int | None = None
    subject_name: str | None = None
    is_applied: bool = False
    is_entered: bool = False


class BotFaceVerifyResponse(BaseModel):
    """Bot Face ID javobi.

    `status`:
      - `in_smena`        — jshshir tanlangan smenada bor; GTSP+verify natijasi
                            qaytariladi va `slot` to'ldiriladi.
      - `wrong_slot`      — jshshir shu test sessiyasida bor, lekin boshqa
                            kun/smena/binoda. Davomatga qo'shib bo'lmaydi.
      - `not_in_session`  — jshshir umuman shu sessiyada topilmadi.
      - `wrong_passport`  — GTSP API ps_ser+ps_num bo'yicha rasm qaytarmadi.
      - `no_face`         — Yuz topilmadi yoki bir nechta yuz aniqlandi.
      - `applied`         — Talaba arizali (testga kiritilmaydi).
      - `error`           — Boshqa server xatoligi.

    `score` va `threshold` — yuz o'xshashligi **0-100 shkala**da, yaxlitlangan
    integer foiz (masalan, 83 = 83%). Backend ichida normalize qilinadi —
    foydalanuvchi va StudentLog uchun yagona "foiz" kontrakti.

    `can_attend=True` faqat `in_smena` + `verified=True` + `is_applied=False`
    bo'lganda qaytariladi — bot foydalanuvchiga "Davomatga qo'shish" tugmasini
    shu shartda ko'rsatadi.
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
    score: int = 0      # 0-100 foiz
    threshold: int = 0  # 0-100 foiz
    can_attend: bool = False
    fio: str | None = None
    photo_b64: str | None = None
    selfie_b64: str | None = None
    message: str = ""
    slot: BotStudentSlot | None = None


# === Davomatga qo'shish (mark attendance) ===


class BotMarkAttendanceRequest(BaseModel):
    """Bot orqali talabani davomatga qo'shish."""

    telegram_id: int
    student_id: int
    session_smena_id: int = Field(
        ..., description="Tanlangan smena — qo'shimcha xavfsizlik validatsiyasi"
    )
    region_id: int | None = Field(
        default=None, description="Tanlangan region (bot /start da tanlagan)"
    )
    selfie_b64: str | None = Field(
        default=None,
        description="Tasdiqlangan selfie — StudentLog.first_captured/last_captured ga yoziladi",
    )
    verify_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description=(
            "Bot Face ID o'xshashligi (0-100 foiz). StudentLog.score ga yoziladi."
            " Bot identification uchun ishlatiladi; max_score 0 qoldiriladi."
        ),
    )


class BotMarkAttendanceResponse(BaseModel):
    status: Literal["ok", "already_entered", "applied", "not_found", "error"]
    student_id: int | None = None
    log_id: int | None = None
    message: str = ""


# === Davomatdan olib tashlash (remove attendance) ===


class BotFindByJshshirRequest(BaseModel):
    """JShShIR bo'yicha tanlangan smenadagi talabgorlarni topish.

    Davomatdan olib tashlash flow'i uchun: agar bir nechta yozuv chiqsa,
    foydalanuvchi qaysi birini olib tashlashni tanlaydi.
    """

    telegram_id: int
    session_smena_id: int
    region_id: int | None = Field(
        default=None, description="Tanlangan region kesimi"
    )
    jshshir: str = Field(..., min_length=14, max_length=14)
    # True bo'lsa — faqat hozir davomatda turgan (is_entered=True) talabgorlar.
    # Bot remove flow uchun shu default ishlatiladi.
    only_entered: bool = True


class BotFindByJshshirResponse(BaseModel):
    status: Literal["ok", "not_found", "error"]
    matches: list[BotStudentSlot] = Field(default_factory=list)
    message: str = ""


class BotRemoveAttendanceRequest(BaseModel):
    """Tasdiqlangan talabgorni davomatdan olib tashlash.

    `Student.is_entered=False` qiymatiga qaytariladi. StudentLog tegilmaydi —
    tarixiy yozuv saqlanadi. Keyinchalik qayta qo'shilsa, `last_enter_time`
    yangilanadi, `first_*` o'zgarishsiz qoladi.
    """

    telegram_id: int
    student_id: int
    session_smena_id: int = Field(
        ..., description="Qo'shimcha xavfsizlik tekshiruvi uchun"
    )
    region_id: int | None = Field(
        default=None, description="Tanlangan region kesimi"
    )


class BotRemoveAttendanceResponse(BaseModel):
    status: Literal["ok", "not_entered", "not_found", "error"]
    student_id: int | None = None
    message: str = ""


# === Chetlatish (cheating) ===


class BotReasonTypeInfo(BaseModel):
    """Chetlatish turi (`reason_types` jadvali yozuvi)."""

    id: int
    name: str
    key: int


class BotReasonInfo(BaseModel):
    """Chetlatish sababi (`reasons` jadvali yozuvi). `reason_type_id` orqali
    turga biriktiriladi.
    """

    id: int
    reason_type_id: int | None = None
    name: str
    key: int


class BotFindForCheatRequest(BaseModel):
    """JShShIR bo'yicha tanlangan test sessiyasida talabgorni qidirish
    (chetlatish flow uchun).

    `remove-attendance` flow'idan farqi:
      - Smena bilan emas, butun sessiya bo'yicha qidiradi.
      - `is_entered` filtri yo'q (talabgor kelmasdan ham chetlatilishi mumkin).
      - `is_cheating=True` bo'lganlarni qaytarmaydi (allaqachon chetlatilgan).
    """

    telegram_id: int
    session_id: int
    region_id: int | None = Field(
        default=None, description="Tanlangan region kesimi"
    )
    jshshir: str = Field(..., min_length=14, max_length=14)


class BotFindForCheatResponse(BaseModel):
    status: Literal["ok", "not_found", "already_cheating", "error"]
    matches: list[BotStudentSlot] = Field(default_factory=list)
    message: str = ""


class BotCheatRequest(BaseModel):
    """Chetlatish kiritish (rasmsiz — bot uchun).

    - `Student.is_cheating=True` qilinadi.
    - `CheatingLog` yozuvi yaratiladi (`student_id` UNIQUE — qayta urinishda
      `already_exists` qaytariladi).
    """

    telegram_id: int
    student_id: int
    session_id: int = Field(
        ..., description="Qo'shimcha xavfsizlik tekshiruvi (talabgor shu sessiyadami)"
    )
    region_id: int | None = Field(
        default=None, description="Tanlangan region kesimi"
    )
    reason_id: int


class BotCheatResponse(BaseModel):
    status: Literal[
        "ok",
        "already_cheating",
        "invalid_reason",
        "not_found",
        "wrong_session",
        "error",
    ]
    student_id: int | None = None
    log_id: int | None = None
    message: str = ""


# ============================================================
# Admin CRUD — `davomat_bots` (foydalanuvchilar + regionlar)
# ============================================================


# Role kalitlari (`roles.key`):
#   - SINGLE_REGION_ROLE_KEY (4) — bot foydalanuvchisi faqat 1 ta region
#     biriktirishi kerak (masalan, "Bino ma'sul").
#   - Boshqa role_key'lar (1, 2, 3) — kamida 1 ta, ko'p ham mumkin (masalan,
#     "Region rahbari" bir nechta viloyatga ma'sul).
SINGLE_REGION_ROLE_KEY = 4


def _validate_region_ids_against_role(
    region_ids: list[int], role_key: int | None
) -> list[int]:
    """`role_key` ga qarab `region_ids` ro'yxatini tekshirish.

    - Dublikatlarni olib tashlash (set), kamida 1 element bo'lishi shart.
    - `role_key == 4` bo'lsa, aniq 1 ta region.
    - Boshqa role_key'larda 1+ ta region.
    """
    uniq = sorted({int(x) for x in region_ids})
    if not uniq:
        raise ValueError("Kamida 1 ta region tanlanishi kerak")
    if role_key == SINGLE_REGION_ROLE_KEY and len(uniq) != 1:
        raise ValueError(
            "Bu rol uchun faqat 1 ta region biriktirilishi mumkin"
        )
    return uniq


class DavomatBotAdminRegion(BaseModel):
    """Admin javobida region — bot biriktirilgan har bir region."""

    id: int
    name: str
    number: int


class DavomatBotAdminResponse(BaseModel):
    """Admin uchun bot foydalanuvchisi to'liq javobi."""

    id: int
    fio: str
    telegram_id: int
    role_id: int | None = None
    role: str = ""
    role_key: int = 0
    is_active: bool
    regions: list[DavomatBotAdminRegion] = Field(default_factory=list)
    region_ids: list[int] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DavomatBotCreateRequest(BaseModel):
    """Yangi bot foydalanuvchisi yaratish so'rovi.

    Validatsiya:
      - `region_ids` kamida 1 element bo'lishi shart.
      - `role.key == 4` bo'lsa, aniq 1 ta region (CRUD qatlamida tekshiriladi —
        bu yerda `role_id` orqali aniqlash uchun DB kerak).
    """

    fio: str = Field(..., min_length=2, max_length=150)
    telegram_id: int = Field(..., gt=0)
    role_id: int | None = None
    is_active: bool = True
    region_ids: list[int] = Field(..., min_length=1)

    @field_validator("region_ids")
    @classmethod
    def _dedup(cls, v: list[int]) -> list[int]:
        return sorted({int(x) for x in v})


class DavomatBotUpdateRequest(BaseModel):
    """Bot foydalanuvchisini tahrirlash so'rovi. Hamma field ixtiyoriy —
    faqat o'zgargan field'larni jo'natish mumkin.
    """

    fio: str | None = Field(default=None, min_length=2, max_length=150)
    telegram_id: int | None = Field(default=None, gt=0)
    role_id: int | None = None
    is_active: bool | None = None
    region_ids: list[int] | None = None

    @field_validator("region_ids")
    @classmethod
    def _dedup(cls, v: list[int] | None) -> list[int] | None:
        if v is None:
            return None
        out = sorted({int(x) for x in v})
        if not out:
            raise ValueError("Kamida 1 ta region tanlanishi kerak")
        return out
