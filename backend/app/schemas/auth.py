from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    is_active: bool

    model_config = {"from_attributes": True}


class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)
    full_name: str | None = None
    role: str = Field(default="operator", pattern="^(admin|operator)$")
