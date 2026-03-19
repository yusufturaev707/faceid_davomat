"""Pydantic schemas for Student, StudentLog, CheatingLog."""

from datetime import datetime

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
    e_date: datetime
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
    e_date: datetime | None = None
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
    e_date: datetime
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
    ps_data: StudentPsDataResponse | None = None

    model_config = {"from_attributes": True}


class StudentListResponse(BaseModel):
    """Talabalar ro'yxati (pagination bilan)."""

    items: list[StudentResponse]
    total: int
    page: int
    per_page: int
    pages: int


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
    """Talaba log yozuvi."""

    id: int
    student_id: int
    first_captured: str | None = None
    last_captured: str | None = None
    first_enter_time: datetime | None = None
    last_enter_time: datetime | None = None
    score: int
    max_score: int
    is_check_hand: bool
    ip_address: str | None = None
    mac_address: str | None = None
    student_full_name: str | None = None

    model_config = {"from_attributes": True}


class StudentLogListResponse(BaseModel):
    """Talaba loglar ro'yxati (pagination bilan)."""

    items: list[StudentLogResponse]
    total: int
    page: int
    per_page: int
    pages: int


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
    """Cheating log yozuvi."""

    id: int
    student_id: int
    reason_id: int
    user_id: int
    image_path: str | None = None
    student_full_name: str | None = None
    reason_name: str | None = None
    username: str | None = None

    model_config = {"from_attributes": True}


class CheatingLogListResponse(BaseModel):
    """Cheating loglar ro'yxati (pagination bilan)."""

    items: list[CheatingLogResponse]
    total: int
    page: int
    per_page: int
    pages: int
