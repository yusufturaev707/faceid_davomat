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

# Qamrov permissioni. `student.py` dagi `_has_global_scope` shuni tekshiradi.
_ALL_REGIONS_CODE = "student:all_regions"

# Migratsiyagacha global qamrovga ega bo'lgan rol key'lari. Faqat bir
# martalik backfill uchun ishlatiladi — ish vaqtidagi mantiqda `key`
# endi umuman qatnashmaydi.
_LEGACY_GLOBAL_ROLE_KEYS = (2, 3)

# Kengroq permissiondan ajratib chiqarilgan yangi permissionlar.
#   {yangi_codename: manba_codename}
# Yangi permission BIRINCHI marta yaratilganda, manba permissionga ega bo'lgan
# har bir rolga u ham beriladi — shunda mavjud rollarning xulqi o'zgarmaydi,
# lekin admin endi faqat shu imkoniyatni alohida olib tashlay oladi.
# Koddan butunlay olib tashlangan permissionlar. Sync ularni DB'dan ham
# (rollarga bog'lanishi bilan birga) o'chiradi — aks holda adminkada
# hech narsa qilmaydigan yozuv bo'lib osilib qolardi.
# DIQQAT: bu yerga faqat o'rniga backfill qilingan codename qo'shilsin.
_REMOVED_PERMISSIONS: tuple[str, ...] = (
    "lookup:read",
    "lookup:create",
    "lookup:update",
    "lookup:delete",
)


_DERIVED_PERMISSIONS: dict[str, str] = {
    "student:fetch_gtsp": "student:update",
    "test_session:load_students": "test_session:update",
    "test_session:embedding": "test_session:update",
    "test_session:cancel_process": "test_session:update",
    "statistics:export": "statistics:read",
    "statistics:absentees": "statistics:read",
    "student:export_excel": "student:read",
    "student:export_pdf": "student:read",
    "cheating_log:export": "cheating_log:read",
    # Ma'lumotnomalar: har bir bo'lim eski umumiy `lookup:*` dan meros oladi
    "region:read": "lookup:read",
    "region:create": "lookup:create",
    "region:update": "lookup:update",
    "region:delete": "lookup:delete",
    "zone:read": "lookup:read",
    "zone:create": "lookup:create",
    "zone:update": "lookup:update",
    "zone:delete": "lookup:delete",
    "test:read": "lookup:read",
    "test:create": "lookup:create",
    "test:update": "lookup:update",
    "test:delete": "lookup:delete",
    "smena:read": "lookup:read",
    "smena:create": "lookup:create",
    "smena:update": "lookup:update",
    "smena:delete": "lookup:delete",
    "session_state:read": "lookup:read",
    "session_state:create": "lookup:create",
    "session_state:update": "lookup:update",
    "session_state:delete": "lookup:delete",
    "reason:read": "lookup:read",
    "reason:create": "lookup:create",
    "reason:update": "lookup:update",
    "reason:delete": "lookup:delete",
    "reason_type:read": "lookup:read",
    "reason_type:create": "lookup:create",
    "reason_type:update": "lookup:update",
    "reason_type:delete": "lookup:delete",
    "gender:read": "lookup:read",
    "gender:create": "lookup:create",
    "gender:update": "lookup:update",
    "gender:delete": "lookup:delete",
    "blacklist:read": "lookup:read",
    "blacklist:create": "lookup:create",
    "blacklist:update": "lookup:update",
    "blacklist:delete": "lookup:delete",
}


def _backfill_all_regions(db: Session, perm: Permission) -> None:
    """Eski global qamrovli rollarga (key 2, 3) yangi qamrov permissionini berish.

    Faqat permission birinchi marta yaratilganda chaqiriladi, shuning uchun
    idempotent va admin qarorlarini bekor qilmaydi.
    """
    roles = db.execute(
        select(Role).where(Role.key.in_(_LEGACY_GLOBAL_ROLE_KEYS))
    ).unique().scalars().all()
    for role in roles:
        if perm not in role.permissions:
            role.permissions = list(role.permissions) + [perm]
            logger.info(
                "Backfill: %s -> rol '%s' (key=%s)", perm.codename, role.name, role.key
            )


def _prune_removed(db: Session, existing: dict) -> int:
    """Koddan olib tashlangan permissionlarni DB'dan ham o'chiradi.

    Avval `role_permissions` bog'lanishlari uziladi, so'ng permission qatori
    o'chiriladi. Idempotent: yozuv yo'q bo'lsa hech narsa qilmaydi.
    """
    removed = 0
    for code in _REMOVED_PERMISSIONS:
        perm = existing.get(code)
        if perm is None:
            continue
        for role in db.execute(select(Role)).unique().scalars().all():
            if any(p.codename == code for p in role.permissions):
                role.permissions = [
                    p for p in role.permissions if p.codename != code
                ]
        db.delete(perm)
        existing.pop(code, None)
        removed += 1
        logger.info("Eskirgan permission o'chirildi: %s", code)
    return removed


def _backfill_derived(db: Session, existing: dict, added_codes: set[str]) -> None:
    """Yangi ajratilgan permissionlarni manba permissionga ega rollarga berish.

    Faqat shu sync'da YANGI yaratilgan codename'lar uchun ishlaydi, shuning
    uchun bir martalik: keyingi startuplarda admin qarorlari saqlanadi.
    """
    for new_code, source_code in _DERIVED_PERMISSIONS.items():
        if new_code not in added_codes:
            continue
        new_perm = existing.get(new_code)
        source_perm = existing.get(source_code)
        if new_perm is None or source_perm is None:
            continue
        roles = db.execute(select(Role)).unique().scalars().all()
        for role in roles:
            codes = {p.codename for p in role.permissions}
            if source_code in codes and new_code not in codes:
                role.permissions = list(role.permissions) + [new_perm]
                logger.info(
                    "Backfill: %s -> rol '%s' (manba: %s)",
                    new_code, role.name, source_code,
                )


def sync_permission_catalog() -> dict:
    """DB'ni ALL_PERMISSIONS bilan sinxronlash.

    Returns: {"added": int, "updated": int, "admin_synced": bool}
    """
    db: Session = SessionLocal()
    added = 0
    updated = 0
    admin_synced = False
    added_codes: set[str] = set()
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
                added_codes.add(perm.code)
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

        # Bir martalik backfill: `student:all_regions` shu sync'da YANGI
        # yaratilgan bo'lsa — ilgari global qamrovga ega bo'lgan rollarga
        # (eski qattiq kodlangan key 2 va 3) uni beramiz, toki ularning
        # xulqi o'zgarmasin. Permission allaqachon mavjud bo'lsa hech narsa
        # qilinmaydi — ya'ni admin uni qo'lda olib tashlasa, qayta qo'shilmaydi.
        if _ALL_REGIONS_CODE in added_codes:
            _backfill_all_regions(db, existing[_ALL_REGIONS_CODE])

        # Kengroq permissiondan ajratilgan yangi permissionlar uchun backfill
        _backfill_derived(db, existing, added_codes)

        # Backfill'DAN KEYIN: manba (`lookup:*`) meros berib bo'lgach, uni
        # katalogdan ham, rollardan ham olib tashlaymiz.
        _prune_removed(db, existing)

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
