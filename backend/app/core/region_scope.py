"""Viloyat (region) qamrovi — bitta manba.

Ilgari bu mantiq `student.py` ichida rol `key` lari bo'yicha qattiq kodlangan
edi. Endi yagona mezon — `student:all_regions` permissioni:

    bor  → butun tizim (mijoz bergan region filtri saqlanadi)
    yo'q → faqat foydalanuvchining o'z `region_id` i

Endpointga KIRISH huquqi alohida (`PermissionChecker`) tekshiriladi; bu modul
faqat "qaysi viloyat ma'lumoti ko'rinadi" degan savolga javob beradi.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.core.permissions import P
from app.models.user import User

# Admin har doim global — `PermissionChecker` ham shu qoidada ishlaydi.
_ADMIN_ROLE_KEY = 1


def has_global_scope(user: User) -> bool:
    """Foydalanuvchi barcha viloyatlar ma'lumotini ko'ra oladimi?"""
    return user.role_key == _ADMIN_ROLE_KEY or user.has_perm(
        P.STUDENT_ALL_REGIONS.code
    )


def resolve_region_id(user: User, requested_region_id: int | None = None) -> int | None:
    """Amaldagi `region_id` filtrini qaytaradi.

    Returns:
        `None` — filtr yo'q (barcha viloyatlar), yoki aniq `region_id`.

    Raises:
        HTTPException(403): global qamrovi ham, biriktirilgan viloyati ham yo'q.
    """
    if has_global_scope(user):
        return requested_region_id
    if not user.region_id:
        raise HTTPException(
            status_code=403,
            detail="Foydalanuvchiga viloyat biriktirilmagan",
        )
    return int(user.region_id)
