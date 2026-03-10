from datetime import datetime

from pydantic import BaseModel, Field


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="API kalit nomi (masalan: tashqi tizim nomi)")


class ApiKeyCreateResponse(BaseModel):
    """Faqat yaratilganda qaytariladi. raw_key boshqa ko'rsatilmaydi."""
    id: int
    name: str
    prefix: str
    raw_key: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApiKeyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    prefix: str
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
