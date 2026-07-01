"""Admin foydalanuvchi + rollar seed script.

Ishlatish: cd backend && python -m app.db.seed

Idempotent: qayta-qayta ishga tushirsa ham dublikat yaratmaydi.

Eslatma: Permission catalog (ALL_PERMISSIONS → permissions jadvali) auto-sync
har FastAPI startupda chaqiriladi (`app.core.permission_sync`). Shuning uchun
yangi permission qo'shilganda seed'ni qayta ishga tushirish shart emas —
serverni restart qilish kifoya.

Xavfsizlik:
- Admin paroli env'dan olinadi (`ADMIN_INITIAL_PASSWORD`).
- Env yo'q bo'lsa — random parol generatsiya qilinadi va STDOUT ga chiqariladi
  (faqat seed paytida, log fayllarda saqlanmaydi). Birinchi loginda darhol
  o'zgartiring.
- Hardcoded "123" yoki shunga o'xshash zaif parol qabul qilinmaydi.
"""

import os
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permission_sync import sync_permission_catalog
from app.core.security import hash_password, validate_password_strength
from app.db.session import SessionLocal
from app.models.role import Role
from app.models.user import User


ADMIN_ROLE_KEY = 1
OPERATOR_ROLE_KEY = 2
ADMIN_USERNAME = "admin"

DEFAULT_ROLES = [
    {"key": ADMIN_ROLE_KEY, "name": "admin"},
    {"key": OPERATOR_ROLE_KEY, "name": "operator"},
]


def _generate_admin_password() -> str:
    """Env'dan olish, bo'lmasa kuchli random parol."""
    env_value = os.environ.get("ADMIN_INITIAL_PASSWORD", "").strip()
    if env_value:
        try:
            validate_password_strength(env_value)
        except ValueError as exc:
            raise SystemExit(
                f"ADMIN_INITIAL_PASSWORD policy talabiga javob bermaydi: {exc}"
            )
        return env_value

    while True:
        candidate = secrets.token_urlsafe(16)
        try:
            return validate_password_strength(candidate)
        except ValueError:
            continue


def _sync_roles(db: Session) -> dict[int, Role]:
    # Role.permissions lazy="joined" (collection) — JOIN dublikat qatorlar
    # qaytaradi, shuning uchun .unique() majburiy.
    existing = {
        r.key: r for r in db.execute(select(Role)).unique().scalars().all()
    }
    for data in DEFAULT_ROLES:
        if data["key"] not in existing:
            role = Role(name=data["name"], key=data["key"], is_active=True)
            db.add(role)
            existing[data["key"]] = role
    db.flush()
    return existing


def _ensure_admin_user(db: Session, admin_role: Role) -> None:
    existing = db.execute(
        select(User).where(User.username == ADMIN_USERNAME)
    ).unique().scalar_one_or_none()
    if existing:
        if existing.role_id != admin_role.id:
            existing.role_id = admin_role.id
        print(f"Admin foydalanuvchi mavjud: {ADMIN_USERNAME} (parol o'zgartirilmadi)")
        return

    raw_password = _generate_admin_password()
    admin = User(
        username=ADMIN_USERNAME,
        hashed_password=hash_password(raw_password),
        full_name="Administrator",
        role_id=admin_role.id,
        is_active=True,
    )
    db.add(admin)
    print("=" * 60)
    print(f"  ADMIN FOYDALANUVCHI YARATILDI: {ADMIN_USERNAME}")
    print(f"  Boshlang'ich parol: {raw_password}")
    print("  ⚠ Birinchi loginda darhol o'zgartiring!")
    print("=" * 60)


def seed() -> None:
    """Rollar va admin user seed qilish.

    Permissionlar `sync_permission_catalog` orqali alohida sinxronlashtiriladi,
    bu funksiya har FastAPI startupda ham chaqiriladi.
    """
    # 1) Avval rollar seed
    db: Session = SessionLocal()
    try:
        role_map = _sync_roles(db)
        admin_role = role_map[ADMIN_ROLE_KEY]
        _ensure_admin_user(db, admin_role)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    # 2) Permission catalog sync (admin'ga ham biriktiradi)
    result = sync_permission_catalog()
    print(
        f"Seed tugadi: rollar OK, permissionlar +{result['added']} added, "
        f"{result['updated']} updated, admin_synced={result['admin_synced']}"
    )


# Backward compatibility
seed_admin = seed


if __name__ == "__main__":
    seed()
