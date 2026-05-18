"""Davomat bot uchun statistikani hisoblovchi xizmat.

Tanlangan kontekstda — bitta smena, bitta kun (barcha smenalar) yoki butun
sessiya (barcha kun va smenalar) — foydalanuvchi biriktirilgan regionlar
kesimida har bir region va uning zonalari bo'yicha umumiy/ kirgan/
kirmagan/ chetlatilgan statistikasini qaytaradi.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.test_session_smena import TestSessionSmena
from app.models.zone import Zone
from app.schemas.davomat_bot import (
    BotRegionStat,
    BotSessionStatsResponse,
    BotZoneStat,
)


class BotStatsError(Exception):
    """Smena yoki sessiya topilmadi yoki mos kelmadi."""


def _resolve_session_smena_ids(
    db: Session,
    *,
    session_id: int,
    session_smena_id: int | None,
    test_day: date | None,
) -> tuple[list[int], date | None, str, int, str]:
    """Statistika hisoblanadigan session_smena_id'lar ro'yxatini aniqlaydi.

    Qaytaradi: (smena_ids, test_day, smena_name, smena_number, scope).

    - `session_smena_id` berilsa: bitta smena (scope="smena").
    - `test_day` berilsa: shu kunning barcha aktiv smenalari (scope="day").
    - Aks holda: sessiyaning barcha aktiv smenalari (scope="total").
    """
    if session_smena_id is not None:
        row = db.execute(
            select(
                TestSessionSmena.id,
                TestSessionSmena.test_session_id,
                TestSessionSmena.day,
                TestSessionSmena.number,
                Smena.name.label("smena_name"),
            )
            .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
            .where(TestSessionSmena.id == session_smena_id)
        ).first()
        if not row:
            raise BotStatsError("Smena topilmadi")
        if int(row.test_session_id) != int(session_id):
            raise BotStatsError("Tanlangan smena bu sessiyaga tegishli emas")
        return (
            [int(row.id)],
            row.day,
            row.smena_name or "",
            int(row.number or 0),
            "smena",
        )

    if test_day is not None:
        rows = db.execute(
            select(TestSessionSmena.id)
            .where(
                TestSessionSmena.test_session_id == session_id,
                TestSessionSmena.day == test_day,
                TestSessionSmena.is_active.is_(True),
            )
        ).all()
        ids = [int(r.id) for r in rows]
        if not ids:
            raise BotStatsError("Tanlangan kunda aktiv smenalar topilmadi")
        return (ids, test_day, "Kun yakuni", 0, "day")

    # Butun sessiya
    rows = db.execute(
        select(TestSessionSmena.id)
        .where(
            TestSessionSmena.test_session_id == session_id,
            TestSessionSmena.is_active.is_(True),
        )
    ).all()
    ids = [int(r.id) for r in rows]
    if not ids:
        raise BotStatsError("Sessiyada aktiv smenalar topilmadi")
    return (ids, None, "Umumiy", 0, "total")


def compute_bot_stats(
    db: Session,
    *,
    session_id: int,
    session_smena_id: int | None = None,
    test_day: date | None = None,
    allowed_region_ids: set[int],
) -> BotSessionStatsResponse:
    """Tanlangan kontekst (smena/kun/sessiya) bo'yicha statistika.

    Aniq bittasi berilishi kutiladi: `session_smena_id` (smena),
    `test_day` (kun) yoki ikkisi ham `None` (butun sessiya).

    Args:
        session_id: TestSession.id
        session_smena_id: bitta smena tanlash uchun (yoki None).
        test_day: bitta kun barcha smenalarini olish uchun (yoki None).
        allowed_region_ids: foydalanuvchi ko'ra oladigan region id'lari.

    Raises:
        BotStatsError: kontekst topilmadi yoki regionlar bo'sh.
    """
    if not allowed_region_ids:
        raise BotStatsError("Foydalanuvchiga region biriktirilmagan")

    smena_ids, resolved_day, smena_name, smena_number, scope = (
        _resolve_session_smena_ids(
            db,
            session_id=session_id,
            session_smena_id=session_smena_id,
            test_day=test_day,
        )
    )

    # Faqat ruxsat etilgan, aktiv regionlarni tanlash
    region_rows = db.execute(
        select(Region.id, Region.name, Region.number)
        .where(
            Region.id.in_(allowed_region_ids),
            Region.is_active.is_(True),
        )
        .order_by(Region.number, Region.name)
    ).all()

    region_meta: dict[int, tuple[str, int]] = {
        r.id: (r.name, int(r.number or 0)) for r in region_rows
    }
    if not region_meta:
        raise BotStatsError("Ruxsat etilgan regionlar topilmadi")

    # Aktiv zonalarni olamiz (faqat ruxsat etilgan regionlar)
    zone_rows = db.execute(
        select(Zone.id, Zone.region_id, Zone.name, Zone.number)
        .where(
            Zone.region_id.in_(region_meta.keys()),
            Zone.is_active.is_(True),
        )
        .order_by(Zone.number, Zone.name)
    ).all()

    zones_by_region: dict[int, list] = defaultdict(list)
    for z in zone_rows:
        zones_by_region[int(z.region_id)].append(z)

    zone_ids = [int(z.id) for z in zone_rows]

    # Bitta GROUP BY query bilan zone bo'yicha agregatsiya (barcha smenalarni
    # birlashtirib hisoblaymiz — multi-smena holatida ham bir kishi/yozuv
    # ikki marta sanalmaydi, chunki har bir Student yagona session_smena_id ga
    # bog'langan).
    zone_stats: dict[int, dict] = {
        zid: {"total": 0, "entered": 0, "cheating": 0} for zid in zone_ids
    }
    if zone_ids and smena_ids:
        rows = db.execute(
            select(
                Student.zone_id,
                func.count(Student.id).label("total"),
                func.sum(
                    case((Student.is_entered.is_(True), 1), else_=0)
                ).label("entered"),
                func.sum(
                    case((Student.is_cheating.is_(True), 1), else_=0)
                ).label("cheating"),
            )
            .where(
                Student.session_smena_id.in_(smena_ids),
                Student.zone_id.in_(zone_ids),
            )
            .group_by(Student.zone_id)
        ).all()
        for row in rows:
            zone_stats[int(row.zone_id)] = {
                "total": int(row.total or 0),
                "entered": int(row.entered or 0),
                "cheating": int(row.cheating or 0),
            }

    regions_payload: list[BotRegionStat] = []
    for region_id, (region_name, region_number) in sorted(
        region_meta.items(), key=lambda kv: kv[1][1]
    ):
        zones = zones_by_region.get(region_id, [])
        r_total = r_entered = r_cheating = 0
        zone_payload: list[BotZoneStat] = []
        for z in zones:
            s = zone_stats.get(int(z.id), {"total": 0, "entered": 0, "cheating": 0})
            total = s["total"]
            entered = s["entered"]
            cheating = s["cheating"]
            zone_payload.append(
                BotZoneStat(
                    zone_id=int(z.id),
                    zone_name=z.name,
                    zone_number=int(z.number or 0),
                    total=total,
                    entered=entered,
                    not_entered=max(0, total - entered),
                    cheating=cheating,
                )
            )
            r_total += total
            r_entered += entered
            r_cheating += cheating

        regions_payload.append(
            BotRegionStat(
                region_id=region_id,
                region_name=region_name,
                region_number=region_number,
                total=r_total,
                entered=r_entered,
                not_entered=max(0, r_total - r_entered),
                cheating=r_cheating,
                zones=zone_payload,
            )
        )

    if scope == "smena":
        title = ""
    elif scope == "day":
        title = (
            f"Kun yakuni — {resolved_day.isoformat()}"
            if resolved_day
            else "Kun yakuni"
        )
    else:
        title = "Umumiy statistika (barcha kunlar)"

    return BotSessionStatsResponse(
        session_id=session_id,
        session_smena_id=smena_ids[0] if scope == "smena" else 0,
        test_day=resolved_day,
        smena_number=smena_number,
        smena_name=smena_name,
        scope=scope,
        title=title,
        regions=regions_payload,
    )
