"""CRUD operations for Permission and Role-Permission assignment."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.permission import Permission
from app.models.role import Role


# ---- Permission CRUD ----

def get_all_permissions(db: Session) -> list[Permission]:
    stmt = select(Permission).order_by(Permission.group, Permission.codename)
    return list(db.execute(stmt).scalars().all())


def get_permission_by_id(db: Session, perm_id: int) -> Permission | None:
    return db.get(Permission, perm_id)


def get_permission_by_codename(db: Session, codename: str) -> Permission | None:
    stmt = select(Permission).where(Permission.codename == codename)
    return db.execute(stmt).scalars().first()


def create_permission(db: Session, data: dict) -> Permission:
    perm = Permission(**data)
    db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


def update_permission(db: Session, perm_id: int, data: dict) -> Permission | None:
    perm = db.get(Permission, perm_id)
    if not perm:
        return None
    for k, v in data.items():
        if v is not None:
            setattr(perm, k, v)
    db.commit()
    db.refresh(perm)
    return perm


def delete_permission(db: Session, perm_id: int) -> bool:
    perm = db.get(Permission, perm_id)
    if not perm:
        return False
    db.delete(perm)
    db.commit()
    return True


# ---- Role-Permission assignment ----

def get_role_with_permissions(db: Session, role_id: int) -> Role | None:
    return db.get(Role, role_id)


def get_all_roles_with_permissions(db: Session) -> list[Role]:
    stmt = select(Role).order_by(Role.key)
    return list(db.execute(stmt).unique().scalars().all())


def assign_permissions_to_role(
    db: Session, role_id: int, permission_ids: list[int]
) -> Role | None:
    role = db.get(Role, role_id)
    if not role:
        return None
    # Barcha berilgan permission IDlarini olish
    stmt = select(Permission).where(Permission.id.in_(permission_ids))
    permissions = list(db.execute(stmt).scalars().all())
    # To'liq almashtirish (replace)
    role.permissions = permissions
    db.commit()
    db.refresh(role)
    return role
