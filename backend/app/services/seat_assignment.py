"""Kompyuterlarni nomzodlarga biriktirish — `students.sp_n` ga Proctoring raqami.

Admin test sessiyasida kun+smenani va Proctoring'dagi ochiq sessiyani
tanlaydi. Shu sessiyaning ISHCHI kompyuterlari olinadi va har bino ichida
nomzodlarga taqsimlanadi. Natija `sp_n` ga yoziladi — desktop client uni
yuklab oladi va Face ID'dan o'tgan nomzodga "JOY" sifatida ko'rsatadi
(client o'zgarmaydi). `proctoring_schedule_id` shu raqam endi KOMPYUTER
RAQAMI ekanini bildiradi va nomzod kirganda bron qaysi sessiyaga ketishini
aytadi (`tasks/proctoring_task.py`).

QOIDALAR:

* Bino ikki tizimda tashqi raqamlar bilan bog'lanadi:
  `regions.number` + `zone.number` = Proctoring `dtm_id` + `number`.
  Proctoring ro'yxatida umuman YO'Q bino — tegilmaydi (sessiya bitta
  binoga tegishli bo'lishi mumkin) va hisobotda alohida ko'rsatiladi.
* Bitta ODAMGA bitta kompyuter: bir JShShIR smenada bir necha qatorda
  bo'lishi mumkin (turli fan) — raqam hammasiga yoziladi, "egalik"
  (`proctoring_schedule_id`) esa faqat birinchisida.
* QAYTA ISHGA TUSHIRISH BARQAROR: to'g'ri biriktiruvga tegilmaydi. Avval
  Proctoring'da shu nomzodga allaqachon bron qilingan joy saqlanadi,
  keyin oldingi biriktiruv (kompyuter hali ishchi bo'lsa), qolganlar bo'sh
  joylarga guruh va familiya tartibida. Client ma'lumotni yuklab olgan
  bo'lsa ham, qayta ishga tushirish faqat buzilgan/yangi joylarni
  o'zgartiradi.
* Boshqa odamga bron qilingan joy (FaceID ro'yxatida yo'q JShShIR)
  chetlab o'tiladi.
* Joy yetmagan nomzodda `sp_n=0` — client "—" ko'rsatadi. Loader qiymati
  qoldirilsa, u KOMPYUTER RAQAMI bo'lib o'qilardi.
* Arizali (`is_applied`) nomzod joy olmaydi — client uni yuklab olmaydi.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.region import Region
from app.models.student import Student
from app.models.zone import Zone
from app.services import proctoring_client

logger = logging.getLogger("faceid.services.seat_assignment")


class SeatAssignmentError(Exception):
    """Biriktirishni boshlab bo'lmaydi (admin'ga ko'rsatiladigan sabab)."""


@dataclass
class ZoneReport:
    zone_id: int
    zone_name: str
    region_number: int
    zone_number: int
    candidates: int = 0  # odamlar soni (JShShIR bo'yicha)
    computers: int = 0  # ishchi va bo'sh (begona bronsiz) kompyuterlar
    kept: int = 0
    assigned: int = 0
    unassigned: int = 0


@dataclass
class AssignmentReport:
    schedule_id: int
    dry_run: bool
    zones: list[ZoneReport] = field(default_factory=list)
    # FaceID'da nomzodi bor, lekin Proctoring sessiyasida kompyuteri yo'q binolar.
    missing_zones: list[ZoneReport] = field(default_factory=list)
    changed_rows: int = 0

    @property
    def totals(self) -> dict:
        return {
            key: sum(getattr(z, key) for z in self.zones)
            for key in ("candidates", "computers", "kept", "assigned", "unassigned")
        }


def _person_key(row) -> str:
    return row.imei or f"id:{row.id}"


def assign_seats(
    db: Session, *, session_smena_id: int, schedule_id: int, dry_run: bool = False
) -> AssignmentReport:
    computers = proctoring_client.list_computers(schedule_id)
    seats_by_zone: dict[tuple[int, int], list] = defaultdict(list)
    for computer in computers:
        seats_by_zone[(computer.region_number, computer.zone_number)].append(computer)

    rows = db.execute(
        select(
            Student.id,
            Student.imei,
            Student.sp_n,
            Student.proctoring_schedule_id,
            Student.is_entered,
            Student.is_applied,
            Student.zone_id,
            Zone.name.label("zone_name"),
            Zone.number.label("zone_number"),
            Region.number.label("region_number"),
        )
        .join(Zone, Zone.id == Student.zone_id)
        .join(Region, Region.id == Zone.region_id)
        .where(Student.session_smena_id == session_smena_id)
        .order_by(
            Student.zone_id, Student.gr_n, Student.last_name, Student.first_name, Student.id
        )
    ).all()

    # Nomzod kirib, bron boshqa sessiyaga ketgan bo'lsa — sessiyani
    # almashtirish uning joyini Proctoring'da "egasiz" qoldirardi.
    conflict = next(
        (
            r for r in rows
            if r.is_entered
            and r.proctoring_schedule_id is not None
            and r.proctoring_schedule_id != schedule_id
            and (r.region_number, r.zone_number) in seats_by_zone
        ),
        None,
    )
    if conflict is not None:
        raise SeatAssignmentError(
            f"«{conflict.zone_name}» binosida nomzodlar boshqa Proctoring sessiyasi "
            "bilan kirib bo'lgan — sessiyani almashtirib bo'lmaydi"
        )

    by_zone: dict[int, list] = defaultdict(list)
    for r in rows:
        by_zone[r.zone_id].append(r)

    report = AssignmentReport(schedule_id=schedule_id, dry_run=dry_run)
    targets: dict[int, tuple[int, int | None]] = {}  # student_id -> (sp_n, schedule)

    for zone_rows in by_zone.values():
        first = zone_rows[0]
        zone_report = ZoneReport(
            zone_id=first.zone_id,
            zone_name=first.zone_name,
            region_number=first.region_number,
            zone_number=first.zone_number,
        )
        seats = seats_by_zone.get((first.region_number, first.zone_number))
        if not seats:
            zone_report.candidates = len({_person_key(r) for r in zone_rows if not r.is_applied})
            report.missing_zones.append(zone_report)
            continue

        # Odamlar — birinchi uchragan qatori tartibida (guruh, familiya).
        people: dict[str, list] = {}
        for r in zone_rows:
            if r.is_applied:
                targets[r.id] = (0, None)
                continue
            people.setdefault(_person_key(r), []).append(r)

        ours = {key for key in people if not key.startswith("id:")}
        usable = {s.number: s for s in seats if not s.is_booked or s.pinfl in ours}
        zone_report.candidates = len(people)
        zone_report.computers = len(usable)

        chosen: dict[str, int] = {}
        taken: set[int] = set()
        # 1) Proctoring'da allaqachon shu nomzodga bron qilingan joy — haqiqat o'sha yerda.
        for seat in usable.values():
            if seat.is_booked and seat.pinfl in people and seat.pinfl not in chosen:
                chosen[seat.pinfl] = seat.number
                taken.add(seat.number)
        # 2) Oldingi biriktiruv, kompyuter hali ishchi va bo'sh bo'lsa.
        for key, person_rows in people.items():
            if key in chosen:
                continue
            owner = next((r for r in person_rows if r.proctoring_schedule_id is not None), None)
            number = owner.sp_n if owner is not None else None
            if number in usable and number not in taken and not usable[number].is_booked:
                chosen[key] = number
                taken.add(number)
        zone_report.kept = len(chosen)
        # 3) Qolganlar — bo'sh joylar raqam tartibida.
        free = iter(sorted(n for n in usable if n not in taken and not usable[n].is_booked))
        for key in people:
            if key in chosen:
                continue
            number = next(free, None)
            if number is None:
                zone_report.unassigned += 1
                continue
            chosen[key] = number
            zone_report.assigned += 1

        for key, person_rows in people.items():
            number = chosen.get(key)
            for index, r in enumerate(person_rows):
                if number is None:
                    targets[r.id] = (0, None)
                else:
                    targets[r.id] = (number, schedule_id if index == 0 else None)
        report.zones.append(zone_report)

    current = {r.id: (r.sp_n, r.proctoring_schedule_id) for r in rows}
    changes = [
        {"id": sid, "sp_n": target[0], "proctoring_schedule_id": target[1]}
        for sid, target in targets.items()
        if current[sid] != target
    ]
    report.changed_rows = len(changes)
    if dry_run or not changes:
        return report

    # IKKI BOSQICH — qisman unikal indeks tufayli. Ikki nomzod joy
    # almashsa, bitta bosqichda birinchi UPDATE ikkinchisining hali
    # bo'shamagan raqamiga urilardi. Avval o'zgaradigan qatorlar
    # "egasiz" qilinadi, keyin yakuniy qiymatlar yoziladi.
    released = [
        {"id": c["id"], "proctoring_schedule_id": None}
        for c in changes
        if current[c["id"]][1] is not None
    ]
    if released:
        db.execute(update(Student), released)
    db.execute(update(Student), changes)
    db.commit()
    logger.info(
        "Kompyuter biriktirildi: smena=%s schedule=%s o'zgargan=%s %s",
        session_smena_id, schedule_id, len(changes), report.totals,
    )
    return report
