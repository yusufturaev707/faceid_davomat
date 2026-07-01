"""Pydantic schemas for Student, StudentLog, CheatingLog."""

from datetime import date, datetime

from pydantic import BaseModel, Field


# --- StudentPsData ---


class StudentPsDataResponse(BaseModel):
    """Talaba passport ma'lumotlari."""

    id: int
    student_id: int
    ps_ser: str
    ps_num: str
    phone: str | None = None
    ps_img: str | None = None
    embedding: str | None = None
    gender_id: int | None = None
    gender_name: str | None = None

    model_config = {"from_attributes": True}


# --- Student ---


class StudentCreate(BaseModel):
    session_smena_id: int
    zone_id: int
    last_name: str = Field(..., max_length=50)
    first_name: str = Field(..., max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    imei: str | None = Field(default=None, max_length=14)
    gr_n: int = 0
    sp_n: int = 0
    s_code: int = 0
    e_date: date
    subject_id: int = 0
    subject_name: str | None = Field(default=None, max_length=100)
    lang_id: int = 0
    level_id: int = 0


class StudentPsDataUpdate(BaseModel):
    """Passport ma'lumotlarini yangilash."""

    ps_ser: str | None = Field(default=None, max_length=5)
    ps_num: str | None = Field(default=None, max_length=10)
    phone: str | None = Field(default=None, max_length=13)
    ps_img: str | None = None
    embedding: str | None = None
    gender_id: int | None = None


class PassportUpdateRow(BaseModel):
    """Ommaviy passport yangilash uchun bitta qator (paste yoki Excel'dan)."""

    jshshir: str = Field(..., max_length=20)
    ps_ser: str = Field(..., max_length=10)
    ps_num: str = Field(..., max_length=15)


class PassportUpdateRequest(BaseModel):
    """Paste qilingan qatorlardan passportlarni yangilash so'rovi."""

    rows: list[PassportUpdateRow] = Field(..., min_length=1, max_length=20000)


class PassportInvalidItem(BaseModel):
    row: int
    jshshir: str
    error: str


class PassportUpdateResult(BaseModel):
    """Ommaviy passport yangilash natijasi (summary)."""

    total: int
    updated: int
    not_found: list[str] = []
    invalid: list[PassportInvalidItem] = []


class StudentUpdate(BaseModel):
    session_smena_id: int | None = None
    zone_id: int | None = None
    last_name: str | None = Field(default=None, max_length=50)
    first_name: str | None = Field(default=None, max_length=50)
    middle_name: str | None = Field(default=None, max_length=50)
    imei: str | None = Field(default=None, max_length=14)
    gr_n: int | None = None
    sp_n: int | None = None
    s_code: int | None = None
    e_date: date | None = None
    subject_id: int | None = None
    subject_name: str | None = Field(default=None, max_length=100)
    lang_id: int | None = None
    level_id: int | None = None
    is_ready: bool | None = None
    is_face: bool | None = None
    is_image: bool | None = None
    is_cheating: bool | None = None
    is_blacklist: bool | None = None
    is_entered: bool | None = None
    is_applied: bool | None = None
    desc_apply: str | None = Field(default=None, max_length=255)
    ps_data: StudentPsDataUpdate | None = None


class StudentResponse(BaseModel):
    """Bitta talaba ma'lumotlari."""

    id: int
    session_smena_id: int
    test_session_id: int | None = None
    test_name: str | None = None
    zone_id: int
    zone_name: str | None = None
    region_name: str | None = None
    smena_name: str | None = None
    last_name: str
    first_name: str
    middle_name: str | None = None
    imei: str | None = None
    gr_n: int
    sp_n: int
    s_code: int
    e_date: date
    subject_id: int
    subject_name: str | None = None
    lang_id: int
    level_id: int
    is_ready: bool
    is_face: bool
    is_image: bool
    is_cheating: bool
    is_blacklist: bool
    is_entered: bool
    is_applied: bool
    desc_apply: str | None = None
    ps_data: StudentPsDataResponse | None = None

    model_config = {"from_attributes": True}


class StudentListResponse(BaseModel):
    """Talabalar ro'yxati (pagination bilan)."""

    items: list[StudentResponse]
    total: int
    page: int
    per_page: int
    pages: int


class AppliedStudentItem(BaseModel):
    """Ariza bergan talaba (`is_applied=True`) — minimal ro'yxat formati."""

    id: int
    last_name: str
    first_name: str
    middle_name: str | None = None
    imei: str | None = None
    region_name: str | None = None
    zone_name: str | None = None
    test_date: str | None = None
    smena_name: str | None = None
    gr_n: int = 0
    desc_apply: str | None = None


class AppliedStudentsResponse(BaseModel):
    """Ariza bergan talabalar ro'yxati."""

    items: list[AppliedStudentItem]
    total: int


class NotEnteredStudentItem(BaseModel):
    """Hali kelmagan (`is_entered=False`) talaba — minimal ro'yxat formati."""

    last_name: str
    first_name: str
    middle_name: str | None = None
    imei: str | None = None
    gr_n: int = 0
    # Ro'yxat region kesimida (bir nechta bino) qaytariladi — talaba qaysi
    # binoga tegishli ekani ko'rinib tursin. Desktop hozircha ko'rsatmaydi.
    zone_name: str = ""


class NotEnteredStudentsResponse(BaseModel):
    """Tanlangan test/sana/smena + region kesimida kelmagan talabalar ro'yxati."""

    items: list[NotEnteredStudentItem]
    total: int
    # roster_total — shu test/smena + region kesimidagi JAMI talaba soni.
    # Client `items` bo'sh kelganda "hammasi kirgan" (roster_total > 0) va
    # "ro'yxat umuman yo'q" (roster_total == 0) holatlarini ajratishi uchun.
    roster_total: int = 0


class RejectedStudentItem(BaseModel):
    """Chetlatilgan (`is_cheating=True`) talaba — ro'yxat formati.

    Asosiy identifikatsiya maydonlari `NotEnteredStudentItem` bilan bir xil,
    qo'shimcha sifatida `rejection_type` (ReasonType.name) va
    `rejection_reason` (Reason.name) qaytariladi — bu ma'lumotlar
    `CheatingLog` jadvalidagi `reason_id` orqali olinadi.
    """

    last_name: str
    first_name: str
    middle_name: str | None = None
    imei: str | None = None
    gr_n: int = 0
    zone_name: str = ""
    rejection_type: str = ""
    rejection_reason: str = ""


class RejectedStudentsResponse(BaseModel):
    """Tanlangan test/sana/smena + zone kesimida chetlatilgan talabalar."""

    items: list[RejectedStudentItem]
    total: int
    roster_total: int = 0


# --- StudentLog ---


class StudentLogCreate(BaseModel):
    student_id: int
    first_captured: str | None = None
    last_captured: str | None = None
    first_enter_time: datetime | None = None
    last_enter_time: datetime | None = None
    score: int = 0
    max_score: int = 0
    is_check_hand: bool = False
    ip_address: str | None = None
    mac_address: str | None = None


class StudentLogUpdate(BaseModel):
    student_id: int | None = None
    first_captured: str | None = None
    last_captured: str | None = None
    first_enter_time: datetime | None = None
    last_enter_time: datetime | None = None
    score: int | None = None
    max_score: int | None = None
    is_check_hand: bool | None = None
    ip_address: str | None = None
    mac_address: str | None = None


class StudentLogResponse(BaseModel):
    """Talaba log yozuvi (list uchun — rasmsiz, qo'shimcha filter maydonlar bilan)."""

    id: int
    student_id: int
    first_enter_time: datetime | None = None
    last_enter_time: datetime | None = None
    score: int
    max_score: int
    is_check_hand: bool
    ip_address: str | None = None
    mac_address: str | None = None
    has_first_captured: bool = False
    has_last_captured: bool = False
    student_full_name: str | None = None
    last_name: str | None = None
    first_name: str | None = None
    middle_name: str | None = None
    imei: str | None = None
    gr_n: int | None = None
    is_cheating: bool | None = None
    is_blacklist: bool | None = None
    e_date: date | None = None
    zone_id: int | None = None
    zone_name: str | None = None
    region_id: int | None = None
    region_name: str | None = None
    smena_id: int | None = None
    smena_name: str | None = None
    test_id: int | None = None
    test_name: str | None = None
    test_session_id: int | None = None

    model_config = {"from_attributes": True}


class StudentLogDetailResponse(StudentLogResponse):
    """To'liq detail (rasmlar base64)."""

    first_captured: str | None = None
    last_captured: str | None = None


class StudentLogListResponse(BaseModel):
    """Talaba loglar ro'yxati (pagination bilan)."""

    items: list[StudentLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


# --- StudentLog Bulk (desktop → server sync) ---


class StudentLogBulkItem(BaseModel):
    """Desktop clientidan keladigan bitta verify yozuv."""

    # Mijoz lokal entry_log.id — javobda qaytariladi, mijoz mark_sent qilish uchun
    client_entry_id: int | None = None
    student_id: int
    first_captured: str | None = None  # base64-encoded JPEG
    last_captured: str | None = None
    first_enter_time: datetime | None = None
    last_enter_time: datetime | None = None
    score: int = 0
    max_score: int = 0
    is_check_hand: bool = False
    ip_address: str | None = None
    mac_address: str | None = Field(default=None, max_length=17)
    # Rejection
    is_rejected: bool = False
    reject_reason_id: int | None = None
    # Blacklist uchun (chetlatilgan bo'lsa)
    imei: str | None = Field(default=None, max_length=14)


class StudentLogBulkRequest(BaseModel):
    items: list[StudentLogBulkItem] = Field(..., min_length=1, max_length=50)


class StudentLogBulkResultItem(BaseModel):
    client_entry_id: int | None = None
    student_id: int
    status: str  # "ok" | "error"
    log_id: int | None = None
    error: str | None = None


class StudentLogBulkResponse(BaseModel):
    items: list[StudentLogBulkResultItem]
    total: int
    succeeded: int
    failed: int


# --- CheatingLog ---


class CheatingLogCreate(BaseModel):
    student_id: int
    reason_id: int
    user_id: int
    image_path: str | None = None


class CheatingLogUpdate(BaseModel):
    student_id: int | None = None
    reason_id: int | None = None
    user_id: int | None = None
    image_path: str | None = None


class CheatingLogResponse(BaseModel):
    """Cheating log yozuvi.

    `reason_name` — back-compat (eski mijozlar uchun). Yangi mijozlar
    `rejection_reason`/`rejection_type`'ni ishlatishi tavsiya etiladi.
    """

    id: int
    student_id: int
    reason_id: int
    user_id: int
    image_path: str | None = None
    student_full_name: str | None = None
    reason_name: str | None = None
    username: str | None = None
    # Extended: chetlatish kontekst maydonlari
    imei: str | None = None
    rejection_type: str | None = None
    rejection_reason: str | None = None
    test_name: str | None = None
    region_name: str | None = None
    zone_name: str | None = None
    smena_date: date | None = None
    smena_name: str | None = None
    rejected_at: datetime | None = None

    model_config = {"from_attributes": True}


class CheatingLogListResponse(BaseModel):
    """Cheating loglar ro'yxati (pagination bilan)."""

    items: list[CheatingLogResponse]
    total: int
    page: int
    per_page: int
    pages: int
