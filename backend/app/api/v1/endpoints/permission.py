"""Permission CRUD and Role-Permission management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.permission import (
    assign_permissions_to_role,
    create_permission,
    delete_permission,
    get_all_permissions,
    get_all_roles_with_permissions,
    get_permission_by_codename,
    get_permission_by_id,
    get_role_with_permissions,
    update_permission,
)
from app.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.permission import (
    AssignPermissionsRequest,
    PermissionCreate,
    PermissionResponse,
    PermissionUpdate,
    RolePermissionsResponse,
)

router = APIRouter()


# ---- Permission CRUD ----

@router.get("", response_model=list[PermissionResponse], summary="Barcha permissionlar")
def list_permissions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[PermissionResponse]:
    return get_all_permissions(db)


@router.post("", response_model=PermissionResponse, status_code=201, summary="Yangi permission")
def create_new_permission(
    data: PermissionCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> PermissionResponse:
    existing = get_permission_by_codename(db, data.codename)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"'{data.codename}' codename allaqachon mavjud",
        )
    return create_permission(db, data.model_dump())


@router.patch("/{perm_id}", response_model=PermissionResponse, summary="Permissionni tahrirlash")
def update_existing_permission(
    perm_id: int,
    data: PermissionUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> PermissionResponse:
    perm = update_permission(db, perm_id, data.model_dump(exclude_unset=True))
    if not perm:
        raise HTTPException(status_code=404, detail="Permission topilmadi")
    return perm


@router.delete("/{perm_id}", status_code=204, summary="Permissionni o'chirish")
def delete_existing_permission(
    perm_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    if not delete_permission(db, perm_id):
        raise HTTPException(status_code=404, detail="Permission topilmadi")


# ---- Role-Permission management ----

@router.get(
    "/roles",
    response_model=list[RolePermissionsResponse],
    summary="Rollar va ularning permissionlari",
)
def list_roles_with_permissions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[RolePermissionsResponse]:
    return get_all_roles_with_permissions(db)


@router.get(
    "/roles/{role_id}",
    response_model=RolePermissionsResponse,
    summary="Bitta rolning permissionlari",
)
def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> RolePermissionsResponse:
    role = get_role_with_permissions(db, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rol topilmadi")
    return role


@router.put(
    "/roles/{role_id}",
    response_model=RolePermissionsResponse,
    summary="Rolga permissionlarni tayinlash",
)
def set_role_permissions(
    role_id: int,
    data: AssignPermissionsRequest,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> RolePermissionsResponse:
    role = assign_permissions_to_role(db, role_id, data.permission_ids)
    if not role:
        raise HTTPException(status_code=404, detail="Rol topilmadi")
    return role
