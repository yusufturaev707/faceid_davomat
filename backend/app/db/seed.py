"""Admin foydalanuvchi + RBAC (rollar va permissionlar) seed script.

Ishlatish: cd backend && python -m app.db.seed

Idempotent: qayta-qayta ishga tushirsa ham dublikat yaratmaydi.
Har safar `app.core.permissions.ALL_PERMISSIONS` ichida yangi permission
paydo bo'lsa — DB ga qo'shib qo'yadi va admin roliga biriktiradi.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_PERMISSIONS, P
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


ADMIN_ROLE_KEY = 1
OPERATOR_ROLE_KEY = 2

DEFAULT_ROLES = [
    {"key": ADMIN_ROLE_KEY, "name": "admin"},
    {"key": OPERATOR_ROLE_KEY, "name": "operator"},
]


def _sync_permissions(db: Session) -> dict[str, Permission]:
    """`ALL_PERMISSIONS` ro'yxatini DB bilan sinxronlash. Mavjudini update qiladi."""
    existing = {p.codename: p for p in db.execute(select(Permission)).scalars().all()}
    for perm in ALL_PERMISSIONS:
        current = existing.get(perm.code)
        if current is None:
            current = Permission(codename=perm.code, name=perm.name, group=perm.group)
            db.add(current)
            existing[perm.code] = current
        else:
            # name/group o'zgargan bo'lsa yangilaymiz (codename o'zgarmaydi)
            if current.name != perm.name or current.group != perm.group:
                current.name = perm.name
                current.group = perm.group
    db.flush()
    return existing


def _sync_roles(db: Session) -> dict[int, Role]:
    existing = {r.key: r for r in db.execute(select(Role)).scalars().all()}
    for data in DEFAULT_ROLES:
        if data["key"] not in existing:
            role = Role(name=data["name"], key=data["key"], is_active=True)
            db.add(role)
            existing[data["key"]] = role
    db.flush()
    return existing


def _grant_all_permissions_to_admin(
    admin_role: Role, perm_map: dict[str, Permission]
) -> None:
    """Admin roliga barcha permission'larni biriktirish (always in sync)."""
    admin_role.permissions = list(perm_map.values())


def _ensure_admin_user(db: Session, admin_role: Role) -> None:
    existing = db.execute(
        select(User).where(User.username == "admin")
    ).scalar_one_or_none()
    if existing:
        # Role biriktirilmagan bo'lsa tuzatib qo'yamiz
        if existing.role_id != admin_role.id:
            existing.role_id = admin_role.id
        print("Admin foydalanuvchi allaqachon mavjud.")
        return

    admin = User(
        username="admin",
        hashed_password=hash_password("123"),
        full_name="Administrator",
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(admin)
    print("Admin foydalanuvchi yaratildi: admin / 123")


def seed() -> None:
    db: Session = SessionLocal()
    try:
        perm_map = _sync_permissions(db)
        role_map = _sync_roles(db)
        admin_role = role_map[ADMIN_ROLE_KEY]
        _grant_all_permissions_to_admin(admin_role, perm_map)
        db.flush()
        _ensure_admin_user(db, admin_role)
        db.commit()
        print(
            f"Seed tugadi: {len(perm_map)} permission, {len(role_map)} rol, "
            f"admin rolida {len(admin_role.permissions)} permission."
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Backward compatibility
seed_admin = seed


if __name__ == "__main__":
    seed()
