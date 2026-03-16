"""Permission schemas."""

from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: int
    codename: str
    name: str
    group: str

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    codename: str = Field(..., min_length=3, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    group: str = Field(..., min_length=1, max_length=50)


class PermissionUpdate(BaseModel):
    codename: str | None = Field(default=None, min_length=3, max_length=100)
    name: str | None = Field(default=None, max_length=200)
    group: str | None = Field(default=None, max_length=50)


class RolePermissionsResponse(BaseModel):
    id: int
    name: str
    key: int
    is_active: bool
    permissions: list[PermissionResponse]

    model_config = {"from_attributes": True}


class AssignPermissionsRequest(BaseModel):
    """Rolga permission IDlarini tayinlash."""
    permission_ids: list[int]
