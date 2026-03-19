"""Lookup/reference table schemas."""

from datetime import datetime

from pydantic import BaseModel, Field


# ---- Test ----
class TestCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: str = Field(..., min_length=1, max_length=20)
    is_active: bool = True

class TestUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    key: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None

class TestResponse(BaseModel):
    id: int
    name: str
    key: str
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Smena ----
class SmenaCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=20)
    number: int
    is_active: bool = True

class SmenaUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=20)
    number: int | None = None
    is_active: bool | None = None

class SmenaResponse(BaseModel):
    id: int
    name: str
    number: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- SessionState ----
class SessionStateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: int
    is_active: bool = True

class SessionStateUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    key: int | None = None
    is_active: bool | None = None

class SessionStateResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Region ----
class RegionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    number: int
    is_active: bool = True

class RegionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    number: int | None = None
    is_active: bool | None = None

class RegionResponse(BaseModel):
    id: int
    name: str
    number: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Zone ----
class ZoneCreate(BaseModel):
    region_id: int
    name: str = Field(..., min_length=1, max_length=100)
    number: int
    is_active: bool = True

class ZoneUpdate(BaseModel):
    region_id: int | None = None
    name: str | None = Field(default=None, max_length=100)
    number: int | None = None
    is_active: bool | None = None

class ZoneResponse(BaseModel):
    id: int
    region_id: int
    name: str
    number: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Role ----
class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    key: int
    is_active: bool = True

class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    key: int | None = None
    is_active: bool | None = None

class RoleResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Reason ----
class ReasonCreate(BaseModel):
    reason_type_id: int | None = None
    name: str = Field(..., min_length=1, max_length=255)
    key: int
    is_active: bool = True

class ReasonUpdate(BaseModel):
    reason_type_id: int | None = None
    name: str | None = Field(default=None, max_length=255)
    key: int | None = None
    is_active: bool | None = None

class ReasonResponse(BaseModel):
    id: int
    reason_type_id: int | None
    name: str
    key: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- ReasonType ----
class ReasonTypeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: int
    is_active: bool = True

class ReasonTypeUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    key: int | None = None
    is_active: bool | None = None

class ReasonTypeResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- StudentBlacklist ----
class StudentBlacklistCreate(BaseModel):
    imei: str | None = Field(default=None, max_length=14)
    description: str | None = Field(default=None, max_length=255)

class StudentBlacklistUpdate(BaseModel):
    imei: str | None = Field(default=None, max_length=14)
    description: str | None = Field(default=None, max_length=255)

class StudentBlacklistResponse(BaseModel):
    id: int
    imei: str | None
    description: str | None
    created_at: datetime
    model_config = {"from_attributes": True}


# ---- Gender ----
class GenderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    key: int
    is_active: bool = True

class GenderUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    key: int | None = None
    is_active: bool | None = None

class GenderResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool
    model_config = {"from_attributes": True}
