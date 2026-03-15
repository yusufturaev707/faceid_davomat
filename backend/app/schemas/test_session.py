from datetime import date, datetime

from pydantic import BaseModel, Field


# --- SessionState ---
class SessionStateResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool

    model_config = {"from_attributes": True}


# --- Test ---
class TestResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool

    model_config = {"from_attributes": True}


# --- Smena ---
class SmenaResponse(BaseModel):
    id: int
    name: str
    number: int
    is_active: bool

    model_config = {"from_attributes": True}


# --- TestSessionSmena ---
class TestSessionSmenaCreate(BaseModel):
    test_smena_id: int
    day: date


class TestSessionSmenaResponse(BaseModel):
    id: int
    test_session_id: int
    test_smena_id: int
    number: int
    day: date
    is_active: bool
    smena: SmenaResponse | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- TestSession ---
class TestSessionCreate(BaseModel):
    test_id: int
    name: str = Field(..., min_length=1, max_length=100)
    start_date: date
    finish_date: date
    count_sm_per_day: int = Field(default=0, ge=0)
    smenas: list[TestSessionSmenaCreate] = Field(default_factory=list)


class TestSessionUpdate(BaseModel):
    test_id: int | None = None
    name: str | None = Field(default=None, max_length=100)
    test_state_id: int | None = None
    start_date: date | None = None
    finish_date: date | None = None
    count_sm_per_day: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class TestSessionResponse(BaseModel):
    id: int
    hash_key: str
    test_state_id: int
    test_id: int
    name: str
    number: int
    count_sm_per_day: int
    count_total_student: int
    start_date: date
    finish_date: date
    is_active: bool
    test_state: SessionStateResponse | None = None
    test: TestResponse | None = None
    smenas: list[TestSessionSmenaResponse] = []
    created_at: datetime

    model_config = {"from_attributes": True}


class TestSessionListResponse(BaseModel):
    items: list[TestSessionResponse]
    total: int
    page: int
    per_page: int
    pages: int
