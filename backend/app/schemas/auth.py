from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    role_key: int
    zone_id: int | None = None
    telegram_id: str | None = None
    is_active: bool
    permissions: list[str] = []

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    role_id: int | None = None
    zone_id: int | None = None
    telegram_id: str | None = None


class UpdateUserRequest(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    password: str | None = Field(default=None, min_length=6)
    full_name: str | None = None
    role_id: int | None = None
    zone_id: int | None = None
    telegram_id: str | None = None
    is_active: bool | None = None
