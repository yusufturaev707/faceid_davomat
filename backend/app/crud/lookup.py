"""Generic CRUD for lookup/reference tables."""

import re
from typing import Any

from functools import lru_cache

from sqlalchemy import func, inspect as sa_inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.reason import Reason
from app.models.region import Region
from app.models.role import Role
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student_blacklist import StudentBlacklist
from app.models.test import Test
from app.models.zone import Zone


# ---- Unique field → Uzbek label mapping ----

_UNIQUE_FIELD_LABELS: dict[str, str] = {
    "number": "Raqam",
    "key": "Kalit",
    "name": "Nomi",
    "username": "Foydalanuvchi nomi",
    "hash_key": "Hash kalit",
    "mac_address": "MAC manzil",
    "token": "Token",
    "key_hash": "API kalit",
}


def _parse_integrity_error(exc: IntegrityError) -> str:
    """Extract a user-friendly Uzbek message from IntegrityError."""
    msg = str(exc.orig) if exc.orig else str(exc)

    # PostgreSQL unique violation: Key (column)=(value) already exists
    match = re.search(r'Key \((\w+)\)=\((.+?)\) already exists', msg)
    if match:
        col, val = match.group(1), match.group(2)
        label = _UNIQUE_FIELD_LABELS.get(col, col)
        return f"{label} \"{val}\" allaqachon mavjud. Iltimos, boshqa qiymat kiriting"

    # PostgreSQL unique violation (table_column_key pattern)
    match = re.search(r'unique constraint "(\w+)"', msg, re.IGNORECASE)
    if match:
        constraint = match.group(1)
        # Try to extract column name from constraint name (e.g. regions_number_key → number)
        for field, label in _UNIQUE_FIELD_LABELS.items():
            if field in constraint:
                return f"{label} allaqachon mavjud. Iltimos, boshqa qiymat kiriting"
        return f"Bu qiymat allaqachon mavjud (takroriy ma'lumot kiritildi)"

    # ForeignKey violation
    if "foreign key" in msg.lower() or "ForeignKeyViolation" in msg:
        match_fk = re.search(r'is still referenced from table "(\w+)"', msg)
        if match_fk:
            table = match_fk.group(1)
            return f"Bu yozuv boshqa joyda ishlatilmoqda ({table}). Avval bog'liq ma'lumotlarni o'chiring"
        match_fk2 = re.search(r'is not present in table "(\w+)"', msg)
        if match_fk2:
            table = match_fk2.group(1)
            return f"Tanlangan qiymat topilmadi ({table}). Iltimos, to'g'ri qiymat tanlang"
        return "Bog'liq ma'lumotlar bilan ziddiyat yuz berdi"

    # Not null violation
    if "not-null" in msg.lower() or "NotNullViolation" in msg:
        match_nn = re.search(r'column "(\w+)"', msg)
        if match_nn:
            col = match_nn.group(1)
            label = _UNIQUE_FIELD_LABELS.get(col, col)
            return f"{label} maydoni bo'sh bo'lishi mumkin emas"
        return "Majburiy maydon to'ldirilmagan"

    return "Ma'lumotlarni saqlashda xatolik: takroriy yoki noto'g'ri qiymat kiritildi"


class DuplicateError(Exception):
    """Raised when a unique constraint is violated."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# ---- Pre-check uniqueness (prevents sequence increment on failure) ----

@lru_cache(maxsize=None)
def _get_unique_columns(model: type) -> tuple[str, ...]:
    """Return unique column names (excluding PK). Cached per model — O(1) after first call."""
    mapper = sa_inspect(model)
    return tuple(
        col.key for col in mapper.columns
        if col.unique and not col.primary_key
    )


def _check_unique_before_write(
    db: Session,
    model: type,
    data: dict[str, Any],
    *,
    exclude_id: int | None = None,
) -> None:
    """Check unique constraints BEFORE insert/update — single SELECT query.

    Uses OR to combine all unique field checks into one query instead of N queries.
    If no unique fields need checking, returns immediately (zero queries).
    """
    unique_cols = _get_unique_columns(model)

    # Collect only the unique fields that are present in data
    checks: list[tuple[str, Any]] = []
    for col_name in unique_cols:
        if col_name in data and data[col_name] is not None:
            checks.append((col_name, data[col_name]))

    if not checks:
        return  # Nothing to check → zero queries

    # Single SELECT with OR: WHERE (number = 3) OR (key = 5)
    conditions = [getattr(model, col) == val for col, val in checks]
    stmt = select(model).where(or_(*conditions))
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)

    existing = db.execute(stmt).scalars().first()
    if not existing:
        return  # No duplicates

    # Find which field conflicts
    for col_name, val in checks:
        if getattr(existing, col_name) == val:
            label = _UNIQUE_FIELD_LABELS.get(col_name, col_name)
            raise DuplicateError(
                f'{label} "{val}" allaqachon mavjud. '
                f"Iltimos, boshqa qiymat kiriting"
            )


# ---- Generic helpers ----

def _get_all(db: Session, model: type, only_active: bool = False) -> list:
    stmt = select(model).order_by(model.id)
    if only_active and hasattr(model, "is_active"):
        stmt = stmt.where(model.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())


def _get_by_id(db: Session, model: type, item_id: int):
    return db.get(model, item_id)


def _create(db: Session, model: type, data: dict[str, Any]):
    # Pre-check unique fields BEFORE insert → prevents sequence gap
    _check_unique_before_write(db, model, data)
    obj = model(**data)
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(obj)
    return obj


def _update(db: Session, model: type, item_id: int, data: dict[str, Any]):
    obj = db.get(model, item_id)
    if not obj:
        return None
    # Pre-check unique fields BEFORE update → prevents sequence gap
    _check_unique_before_write(db, model, data, exclude_id=item_id)
    for k, v in data.items():
        if v is not None:
            setattr(obj, k, v)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    db.refresh(obj)
    return obj


def _delete(db: Session, model: type, item_id: int) -> bool:
    obj = db.get(model, item_id)
    if not obj:
        return False
    try:
        db.delete(obj)
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise DuplicateError(_parse_integrity_error(e)) from e
    return True


# ---- Test ----
def get_tests(db: Session, only_active: bool = False):
    return _get_all(db, Test, only_active)

def get_test(db: Session, item_id: int):
    return _get_by_id(db, Test, item_id)

def create_test(db: Session, data: dict):
    return _create(db, Test, data)

def update_test(db: Session, item_id: int, data: dict):
    return _update(db, Test, item_id, data)

def delete_test(db: Session, item_id: int):
    return _delete(db, Test, item_id)


# ---- Smena ----
def get_smenas(db: Session, only_active: bool = False):
    return _get_all(db, Smena, only_active)

def get_smena(db: Session, item_id: int):
    return _get_by_id(db, Smena, item_id)

def create_smena(db: Session, data: dict):
    return _create(db, Smena, data)

def update_smena(db: Session, item_id: int, data: dict):
    return _update(db, Smena, item_id, data)

def delete_smena(db: Session, item_id: int):
    return _delete(db, Smena, item_id)


# ---- SessionState ----
def get_session_states(db: Session, only_active: bool = False):
    return _get_all(db, SessionState, only_active)

def get_session_state(db: Session, item_id: int):
    return _get_by_id(db, SessionState, item_id)

def create_session_state(db: Session, data: dict):
    return _create(db, SessionState, data)

def update_session_state(db: Session, item_id: int, data: dict):
    return _update(db, SessionState, item_id, data)

def delete_session_state(db: Session, item_id: int):
    return _delete(db, SessionState, item_id)


# ---- Region ----
def get_regions(db: Session, only_active: bool = False):
    return _get_all(db, Region, only_active)

def get_region(db: Session, item_id: int):
    return _get_by_id(db, Region, item_id)

def create_region(db: Session, data: dict):
    return _create(db, Region, data)

def update_region(db: Session, item_id: int, data: dict):
    return _update(db, Region, item_id, data)

def delete_region(db: Session, item_id: int):
    return _delete(db, Region, item_id)


# ---- Zone ----
def get_zones(db: Session, only_active: bool = False):
    stmt = select(Zone).order_by(Zone.id)
    if only_active:
        stmt = stmt.where(Zone.is_active.is_(True))
    return list(db.execute(stmt).scalars().all())

def get_zone(db: Session, item_id: int):
    return _get_by_id(db, Zone, item_id)

def create_zone(db: Session, data: dict):
    return _create(db, Zone, data)

def update_zone(db: Session, item_id: int, data: dict):
    return _update(db, Zone, item_id, data)

def delete_zone(db: Session, item_id: int):
    return _delete(db, Zone, item_id)


# ---- Role ----
def get_roles(db: Session, only_active: bool = False):
    return _get_all(db, Role, only_active)

def get_role(db: Session, item_id: int):
    return _get_by_id(db, Role, item_id)

def create_role(db: Session, data: dict):
    return _create(db, Role, data)

def update_role(db: Session, item_id: int, data: dict):
    return _update(db, Role, item_id, data)

def delete_role(db: Session, item_id: int):
    return _delete(db, Role, item_id)


# ---- Reason ----
def get_reasons(db: Session, only_active: bool = False):
    return _get_all(db, Reason, only_active)

def get_reason(db: Session, item_id: int):
    return _get_by_id(db, Reason, item_id)

def create_reason(db: Session, data: dict):
    return _create(db, Reason, data)

def update_reason(db: Session, item_id: int, data: dict):
    return _update(db, Reason, item_id, data)

def delete_reason(db: Session, item_id: int):
    return _delete(db, Reason, item_id)


# ---- StudentBlacklist ----
def get_blacklist(db: Session):
    return list(db.execute(select(StudentBlacklist).order_by(StudentBlacklist.id)).scalars().all())

def get_blacklist_item(db: Session, item_id: int):
    return _get_by_id(db, StudentBlacklist, item_id)

def create_blacklist_item(db: Session, data: dict):
    return _create(db, StudentBlacklist, data)

def update_blacklist_item(db: Session, item_id: int, data: dict):
    return _update(db, StudentBlacklist, item_id, data)

def delete_blacklist_item(db: Session, item_id: int):
    return _delete(db, StudentBlacklist, item_id)
