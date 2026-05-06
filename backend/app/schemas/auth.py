from pydantic import BaseModel, Field, field_validator

from app.core.security import validate_password_strength


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    role_key: int
    zone_id: int | None = None
    zone_name: str = ""
    region_id: int | None = None
    region_name: str = ""
    telegram_id: str | None = None
    is_active: bool
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.\-]+$")
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)
    role_id: int | None = None
    zone_id: int | None = None
    telegram_id: str | None = Field(default=None, max_length=64)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str) -> str:
        return validate_password_strength(v)


class UpdateUserRequest(BaseModel):
    username: str | None = Field(
        default=None, min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.\-]+$"
    )
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=100)
    role_id: int | None = None
    zone_id: int | None = None
    telegram_id: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def _password_policy(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return validate_password_strength(v)
