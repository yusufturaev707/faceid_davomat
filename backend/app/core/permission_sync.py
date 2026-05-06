"""Permission catalog auto-sync.

Startup vaqtida `ALL_PERMISSIONS` (kod) bilan `permissions` jadvalini sinxronlaydi:
- Yangi codename — DB ga qo'shiladi
- Mavjud codename — name/group yangilanadi
- DB'da bor, lekin koddan o'chirilgan — daxlsiz qoldirilad i (manual cleanup)
- Admin (key=1) roliga ALL_PERMISSIONS to'liq biriktiriladi (har doim full access)

Idempotent — qayta-qayta ishlatish xavfsiz.
"""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.permissions import ALL_PERMISSIONS
from app.db.session import SessionLocal
from app.models.permission import Permission
from app.models.role import Role

logger = logging.getLogger("faceid.core.permission_sync")

ADMIN_ROLE_KEY = 1


def sync_permission_catalog() -> dict:
    """DB'ni ALL_PERMISSIONS bilan sinxronlash.

    Returns: {"added": int, "updated": int, "admin_synced": bool}
    """
    db: Session = SessionLocal()
    added = 0
    updated = 0
    admin_synced = False
    try:
        existing = {
            p.codename: p
            for p in db.execute(select(Permission)).scalars().all()
        }

        for perm in ALL_PERMISSIONS:
            current = existing.get(perm.code)
            if current is None:
                current = Permission(
                    codename=perm.code, name=perm.name, group=perm.group
                )
                db.add(current)
                existing[perm.code] = current
                added += 1
            else:
                if current.name != perm.name or current.group != perm.group:
                    current.name = perm.name
                    current.group = perm.group
                    updated += 1
        db.flush()

        # Admin roliga barcha permissionlarni biriktirish (idempotent)
        admin_role = db.execute(
            select(Role).where(Role.key == ADMIN_ROLE_KEY)
        ).unique().scalar_one_or_none()
        if admin_role is not None:
            current_codes = {p.codename for p in admin_role.permissions}
            target_codes = set(existing.keys())
            if current_codes != target_codes:
                admin_role.permissions = list(existing.values())
                admin_synced = True

        db.commit()
        logger.info(
            "Permission catalog sync: +%d added, %d updated, admin_synced=%s",
            added,
            updated,
            admin_synced,
        )
        return {"added": added, "updated": updated, "admin_synced": admin_synced}
    except Exception:
        db.rollback()
        logger.exception("Permission catalog sync xatoligi")
        raise
    finally:
        db.close()
