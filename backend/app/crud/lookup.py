"""Generic CRUD for lookup/reference tables."""

import re
from typing import Any

from functools import lru_cache

from sqlalchemy import func, inspect as sa_inspect, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.gender import Gender
from app.models.reason import Reason
from app.models.reason_type import ReasonType
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
    """Extract a user-friendly Uzbek message from IntegrityError.

    Handles both English and Russian PostgreSQL locale messages.
    """
    msg = str(exc.orig) if exc.orig else str(exc)

    # PostgreSQL unique violation (EN): Key (column)=(value) already exists
    match = re.search(r'Key \((\w+)\)=\((.+?)\) already exists', msg)
    if not match:
        # PostgreSQL unique violation (RU): Ключ (column)=(value) уже существует
        match = re.search(r'[\u041a\u043a]\u043b\u044e\u0447 \((\w+)\)=\((.+?)\) \u0443\u0436\u0435 \u0441\u0443\u0449\u0435\u0441\u0442\u0432\u0443\u0435\u0442', msg)
    if match:
        col, val = match.group(1), match.group(2)
        label = _UNIQUE_FIELD_LABELS.get(col, col)
        return f"{label} \"{val}\" allaqachon mavjud. Iltimos, boshqa qiymat kiriting"

    # PostgreSQL unique constraint name (EN or RU)
    match = re.search(r'(?:unique constraint|уникальности) "(\w+)"', msg, re.IGNORECASE)
    if match:
        constraint = match.group(1)
        # Composite constraint — friendly message
        if constraint == "uq_session_smena_day":
            return "Bu sessiyada ushbu smena va sana kombinatsiyasi allaqachon mavjud"
        for field, label in _UNIQUE_FIELD_LABELS.items():
            if field in constraint:
                return f"{label} allaqachon mavjud. Iltimos, boshqa qiymat kiriting"
        return "Bu qiymat allaqachon mavjud (takroriy ma'lumot kiritildi)"

    # ForeignKey violation (EN + RU)
    is_fk = ("foreign key" in msg.lower() or "ForeignKeyViolation" in msg
             or "внешнего ключа" in msg.lower())
    if is_fk:
        # Referenced from another table
        match_fk = re.search(r'is still referenced from table "(\w+)"', msg)
        if not match_fk:
            match_fk = re.search(r'из таблицы "(\w+)"', msg)
        if match_fk:
            table = match_fk.group(1)
            return f"Bu yozuv boshqa joyda ishlatilmoqda ({table}). Avval bog'liq ma'lumotlarni o'chiring"

        # FK target not found
        match_fk2 = re.search(r'is not present in table "(\w+)"', msg)
        if not match_fk2:
            match_fk2 = re.search(r'отсутствует в таблице "(\w+)"', msg)
        if match_fk2:
            table = match_fk2.group(1)
            return f"Tanlangan qiymat topilmadi ({table}). Iltimos, to'g'ri qiymat tanlang"
        return "Bog'liq ma'lumotlar bilan ziddiyat yuz berdi"

    # Not null violation (EN + RU)
    is_not_null = ("not-null" in msg.lower() or "NotNullViolation" in msg
                   or "not_null" in msg.lower() or "не может быть NULL" in msg)
    if is_not_null:
        match_nn = re.search(r'column "(\w+)"', msg)
        if not match_nn:
            match_nn = re.search(r'столбце "(\w+)"', msg)
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
    return list(db.execute(stmt).unique().scalars().all())


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
def get_zones(db: Session, only_active: bool = False, region_id: int | None = None):
    stmt = select(Zone).order_by(Zone.id)
    if only_active:
        stmt = stmt.where(Zone.is_active.is_(True))
    if region_id is not None:
        stmt = stmt.where(Zone.region_id == region_id)
    return list(db.execute(stmt).unique().scalars().all())

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


# ---- ReasonType ----
def get_reason_types(db: Session, only_active: bool = False):
    return _get_all(db, ReasonType, only_active)

def get_reason_type(db: Session, item_id: int):
    return _get_by_id(db, ReasonType, item_id)

def create_reason_type(db: Session, data: dict):
    return _create(db, ReasonType, data)

def update_reason_type(db: Session, item_id: int, data: dict):
    return _update(db, ReasonType, item_id, data)

def delete_reason_type(db: Session, item_id: int):
    return _delete(db, ReasonType, item_id)


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


# ---- Gender ----
def get_genders(db: Session, only_active: bool = False):
    return _get_all(db, Gender, only_active)

def get_gender(db: Session, item_id: int):
    return _get_by_id(db, Gender, item_id)

def create_gender(db: Session, data: dict):
    return _create(db, Gender, data)

def update_gender(db: Session, item_id: int, data: dict):
    return _update(db, Gender, item_id, data)

def delete_gender(db: Session, item_id: int):
    return _delete(db, Gender, item_id)
