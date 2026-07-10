"""OTM binolari (zonalari) sinxronizatsiyasi — tashqi `API_OTM_ZONES` dan.

Admin statistikadagi (manage-zones) "Yangilash" tugmasi shu servisni chaqiradi.
Tashqi API quyidagi strukturadagi ro'yxat qaytaradi::

    {
        "id": 1,
        "region_number": 1,
        "name": "Bilim va malakalarni baholash agentligi",
        "number": 1,
        "order": 1,
        "status": true
    }

Moslik:
    - `id`             -> `Zone.building_id` (tashqi bino identifikatori)
    - `region_number`  -> tizimdagi `Region.number`
    - `status`         -> `Zone.is_active`
    - `name` + `number` -> mavjudligini aniqlash kaliti (region ichida)

Mantiq: agar shu region ichida ayni `name` + `number` ga ega bino bor bo'lsa —
`building_id` yangilanadi (agar farq qilsa) va o'tkazib yuboriladi (mavjud),
aks holda yangi `Zone` insert qilinadi.

Hozircha tashqi API ishlamasligi mumkin — bu modul shunchaki ulanib, javob
kelganda to'g'ri qayta ishlashga tayyor turadi. Ishlamasa, foydalanuvchiga
tushunarli xato qaytariladi (boshqa logikaga ta'sir qilmaydi).
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.region import Region
from app.models.zone import Zone

logger = logging.getLogger("faceid.services.zone_sync")


class ZoneSyncNotConfigured(Exception):
    """`settings.API_OTM_ZONES` bo'sh — admin'ga sozlash kerakligini bildiramiz."""


class ZoneSyncError(Exception):
    """Tashqi API muvaffaqiyatsiz javob qaytardi (network, status, parsing)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _norm_name(name: object) -> str:
    """Bino nomini taqqoslash uchun normallashtirish (trim)."""
    return str(name or "").strip()


def _to_int(val: object) -> int | None:
    """Qiymatni butun songa keltirish, bo'lmasa None."""
    if isinstance(val, bool):  # bool — int subclass, alohida ushlaymiz
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip()
        if s.lstrip("-").isdigit():
            return int(s)
    return None


def _fetch_otm_zones(*, timeout: float = 20.0) -> list[dict]:
    """Tashqi API dan binolar ro'yxatini oladi.

    Raises:
        ZoneSyncNotConfigured: API_OTM_ZONES sozlanmagan.
        ZoneSyncError: tarmoq / HTTP / JSON xatosi yoki kutilmagan format.
    """
    if not settings.API_OTM_ZONES:
        raise ZoneSyncNotConfigured("API_OTM_ZONES sozlamasi topilmadi")

    headers = {}
    if settings.API_OTM_ZONES_TOKEN:
        headers["Authorization"] = f"Bearer {settings.API_OTM_ZONES_TOKEN}"

    try:
        with httpx.Client(timeout=timeout, verify=False) as client:
            resp = client.get(settings.API_OTM_ZONES, headers=headers)
            resp.raise_for_status()
            payload = resp.json()
    except httpx.HTTPStatusError as e:
        raise ZoneSyncError(
            f"OTM zonalar API HTTP xatolik: {e.response.status_code}"
        ) from e
    except httpx.RequestError as e:
        raise ZoneSyncError(f"OTM zonalar API ulanish xatolik: {e}") from e
    except ValueError as e:  # JSON parse
        raise ZoneSyncError(f"OTM zonalar API javobi noto'g'ri (JSON emas): {e}") from e

    # Javob to'g'ridan-to'g'ri ro'yxat, {"data": [...]} yoki OTM formati
    # {"status": 1, "message": ..., "data": {"items": [...]}} bo'lishi
    # mumkin — hammasini qo'llab-quvvatlaymiz.
    if isinstance(payload, dict):
        # status=0 — xatolik, sababi "message" maydonida keladi.
        if "status" in payload and _to_int(payload.get("status")) != 1:
            raise ZoneSyncError(
                f"OTM zonalar API xatolik qaytardi: "
                f"{payload.get('message') or 'sabab ko‘rsatilmagan'}"
            )
        items = payload.get("data") or payload.get("result") or payload.get("items")
        if isinstance(items, dict):
            items = items.get("items")
    else:
        items = payload

    if not isinstance(items, list):
        raise ZoneSyncError("OTM zonalar API kutilmagan format qaytardi (ro'yxat emas)")

    return items


def sync_zones_from_otm(db: Session) -> dict:
    """Tashqi `API_OTM_ZONES` dan binolarni o'qib, `building_id` bo'yicha upsert qiladi.

    Moslik kaliti — `Zone.building_id` <-> tashqi javobdagi `id`. Agar shu
    `building_id` ga ega bino bazada bor bo'lsa: maydonlari (nomi, raqami,
    viloyati, holati) yangilanadi; yo'q bo'lsa: yangi `Zone` insert qilinadi.

    Returns:
        dict — sinxronizatsiya yakuni:
            received          — API dan kelgan yozuvlar soni
            created           — yangi qo'shilgan binolar soni
            updated           — mavjud va biror maydoni yangilangan binolar
            unchanged         — mavjud, o'zgarishsiz binolar
            skipped_no_region — region_number topilmagani uchun tashlab ketilgan
            invalid           — id/name/number yetishmagani uchun yaroqsiz yozuvlar
            created_items     — qo'shilgan binolar ro'yxati (info uchun)
            updated_items     — yangilangan binolar va aniq o'zgarishlar (info uchun)
    """
    items = _fetch_otm_zones()

    # Region.number -> Region.id va Region.id -> Region.name xaritalari.
    region_rows = db.execute(select(Region.id, Region.number, Region.name)).all()
    region_by_number: dict[int, int] = {num: rid for rid, num, _ in region_rows}
    region_name_by_id: dict[int, str] = {rid: rname for rid, _, rname in region_rows}

    # Mavjud binolar: building_id -> Zone. building_id — moslik (upsert) kaliti.
    zones_by_building: dict[int, Zone] = {
        z.building_id: z
        for z in db.execute(select(Zone)).unique().scalars().all()
        if z.building_id is not None
    }

    received = len(items)
    created = 0
    updated = 0
    unchanged = 0
    skipped_no_region = 0
    invalid = 0

    created_items: list[dict] = []
    updated_items: list[dict] = []
    new_zones: list[Zone] = []

    def _region_name(rid: int) -> str:
        return region_name_by_id.get(rid, f"#{rid}")

    for item in items:
        if not isinstance(item, dict):
            invalid += 1
            continue

        building_id = _to_int(item.get("id"))
        name = _norm_name(item.get("name"))
        number = _to_int(item.get("number"))
        region_number = _to_int(item.get("region_number"))

        # building_id (tashqi `id`) endi majburiy — u moslik kaliti — va musbat
        # butun son bo'lishi shart (id <= 0 yaroqsiz hisoblanadi).
        if (
            building_id is None
            or building_id <= 0
            or not name
            or number is None
            or region_number is None
        ):
            invalid += 1
            continue

        region_id = region_by_number.get(region_number)
        if region_id is None:
            skipped_no_region += 1
            continue

        is_active = bool(item.get("status", True))

        zone = zones_by_building.get(building_id)
        if zone is not None:
            # Mavjud bino — o'zgargan maydonlarni aniqlab, yangilaymiz.
            changes: list[dict] = []
            if zone.name != name:
                changes.append({"field": "name", "old": zone.name, "new": name})
                zone.name = name
            if zone.number != number:
                changes.append(
                    {"field": "number", "old": zone.number, "new": number}
                )
                zone.number = number
            if zone.region_id != region_id:
                changes.append(
                    {
                        "field": "region",
                        "old": _region_name(zone.region_id),
                        "new": _region_name(region_id),
                    }
                )
                zone.region_id = region_id
            if zone.is_active != is_active:
                changes.append(
                    {"field": "is_active", "old": zone.is_active, "new": is_active}
                )
                zone.is_active = is_active

            if changes:
                updated += 1
                updated_items.append(
                    {
                        "building_id": building_id,
                        "name": name,
                        "number": number,
                        "region_name": _region_name(region_id),
                        "changes": changes,
                    }
                )
            else:
                unchanged += 1
            continue

        # Yangi bino.
        new_zone = Zone(
            region_id=region_id,
            name=name,
            number=number,
            is_active=is_active,
            building_id=building_id,
        )
        new_zones.append(new_zone)
        zones_by_building[building_id] = new_zone
        created += 1
        created_items.append(
            {
                "building_id": building_id,
                "name": name,
                "number": number,
                "region_name": _region_name(region_id),
                "changes": [],
            }
        )

    if new_zones:
        db.add_all(new_zones)
    if new_zones or updated:
        db.commit()

    result = {
        "received": received,
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "skipped_no_region": skipped_no_region,
        "invalid": invalid,
        "created_items": created_items,
        "updated_items": updated_items,
    }
    logger.info(
        "OTM zonalar sinxronizatsiyasi: received=%s created=%s updated=%s "
        "unchanged=%s skipped_no_region=%s invalid=%s",
        received,
        created,
        updated,
        unchanged,
        skipped_no_region,
        invalid,
    )
    return result
