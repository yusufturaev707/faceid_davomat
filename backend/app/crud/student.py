"""CRUD operations for Student, StudentLog, CheatingLog."""

import base64
import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cheating_log import CheatingLog
from app.models.gender import Gender
from app.models.reason import Reason
from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_blacklist import StudentBlacklist
from app.models.student_log import StudentLog
from app.models.student_ps_data import StudentPsData
from app.models.test import Test
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.user import User
from app.models.zone import Zone
from app.schemas.student import (
    CheatingLogCreate,
    CheatingLogUpdate,
    StudentCreate,
    StudentLogBulkItem,
    StudentLogBulkResultItem,
    StudentLogCreate,
    StudentLogUpdate,
    StudentUpdate,
)

logger = logging.getLogger(__name__)


def _b64_to_bytes(val: str | None) -> bytes | None:
    if not val:
        return None
    try:
        if "," in val and val.index(",") < 80:
            val = val.split(",", 1)[1]
        return base64.b64decode(val)
    except Exception:
        return None


# ===================== Student =====================


def _student_to_dict(
    student: Student,
    ps_data: StudentPsData | None,
    *,
    zone_name: str | None = None,
    region_name: str | None = None,
    smena_name: str | None = None,
    test_session_id: int | None = None,
    test_name: str | None = None,
    gender_name: str | None = None,
    include_large_fields: bool = False,
) -> dict:
    result = {
        "id": student.id,
        "session_smena_id": student.session_smena_id,
        "test_session_id": test_session_id,
        "test_name": test_name,
        "zone_id": student.zone_id,
        "zone_name": zone_name,
        "region_name": region_name,
        "smena_name": smena_name,
        "last_name": student.last_name,
        "first_name": student.first_name,
        "middle_name": student.middle_name,
        "imei": student.imei,
        "gr_n": student.gr_n,
        "sp_n": student.sp_n,
        "s_code": student.s_code,
        "e_date": student.e_date,
        "subject_id": student.subject_id,
        "subject_name": student.subject_name,
        "lang_id": student.lang_id,
        "level_id": student.level_id,
        "is_ready": student.is_ready,
        "is_face": student.is_face,
        "is_image": student.is_image,
        "is_cheating": student.is_cheating,
        "is_blacklist": student.is_blacklist,
        "is_entered": student.is_entered,
    }
    if ps_data:
        ps_dict: dict = {
            "id": ps_data.id,
            "student_id": ps_data.student_id,
            "ps_ser": ps_data.ps_ser,
            "ps_num": ps_data.ps_num,
            "phone": ps_data.phone,
            "gender_id": ps_data.gender_id,
            "gender_name": gender_name,
        }
        if include_large_fields:
            ps_dict["ps_img"] = (
                base64.b64encode(ps_data.ps_img).decode("ascii")
                if ps_data.ps_img
                else None
            )
            ps_dict["embedding"] = (
                base64.b64encode(ps_data.embedding).decode("ascii")
                if ps_data.embedding
                else None
            )
        result["ps_data"] = ps_dict
    else:
        result["ps_data"] = None
    return result


def _build_student_query():
    """Build the base SELECT with all joins for student queries."""
    return (
        select(
            Student,
            StudentPsData,
            Zone.name.label("zone_name"),
            Region.name.label("region_name"),
            Smena.name.label("smena_name"),
            TestSessionSmena.test_session_id.label("test_session_id"),
            Test.name.label("test_name"),
            Gender.name.label("gender_name"),
        )
        .outerjoin(StudentPsData, Student.id == StudentPsData.student_id)
        .outerjoin(Gender, StudentPsData.gender_id == Gender.id)
        .outerjoin(Zone, Student.zone_id == Zone.id)
        .outerjoin(Region, Zone.region_id == Region.id)
        .outerjoin(
            TestSessionSmena,
            Student.session_smena_id == TestSessionSmena.id,
        )
        .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
        .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
        .outerjoin(Test, TestSession.test_id == Test.id)
    )


def _apply_filter(stmt, count_stmt, condition):
    """Apply a WHERE condition to both the main and count statements."""
    return stmt.where(condition), count_stmt.where(condition)


def get_students_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    session_smena_id: int | None = None,
    zone_id: int | None = None,
    test_id: int | None = None,
    region_id: int | None = None,
    smena_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_entered: bool | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    is_face: bool | None = None,
    is_image: bool | None = None,
    is_ready: bool | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    stmt = _build_student_query().order_by(Student.id.desc())
    count_stmt = select(func.count(Student.id))

    # For count query that needs joins for test_id / region_id / smena_id
    count_needs_join = any(v is not None for v in [test_id, region_id, smena_id])
    if count_needs_join:
        count_stmt = (
            select(func.count(Student.id))
            .outerjoin(Zone, Student.zone_id == Zone.id)
            .outerjoin(Region, Zone.region_id == Region.id)
            .outerjoin(
                TestSessionSmena, Student.session_smena_id == TestSessionSmena.id
            )
            .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
            .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
            .outerjoin(Test, TestSession.test_id == Test.id)
        )

    if session_smena_id is not None:
        stmt, count_stmt = _apply_filter(
            stmt, count_stmt, Student.session_smena_id == session_smena_id
        )

    if zone_id is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.zone_id == zone_id)

    if test_id is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Test.id == test_id)

    if region_id is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Region.id == region_id)

    if smena_id is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Smena.id == smena_id)

    if gr_n is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.gr_n == gr_n)

    if e_date_from is not None:
        stmt, count_stmt = _apply_filter(
            stmt, count_stmt, Student.e_date >= e_date_from
        )

    if e_date_to is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.e_date <= e_date_to)

    if is_entered is not None:
        stmt, count_stmt = _apply_filter(
            stmt, count_stmt, Student.is_entered == is_entered
        )

    if is_cheating is not None:
        stmt, count_stmt = _apply_filter(
            stmt, count_stmt, Student.is_cheating == is_cheating
        )

    if is_blacklist is not None:
        stmt, count_stmt = _apply_filter(
            stmt, count_stmt, Student.is_blacklist == is_blacklist
        )

    if is_face is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_face == is_face)

    if is_image is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_image == is_image)

    if is_ready is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_ready == is_ready)

    if search:
        search_pattern = f"%{search}%"
        search_filter = (
            Student.last_name.ilike(search_pattern)
            | Student.first_name.ilike(search_pattern)
            | Student.imei.ilike(search_pattern)
        )
        stmt, count_stmt = _apply_filter(stmt, count_stmt, search_filter)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = [
        _student_to_dict(
            student,
            ps_data,
            zone_name=zn,
            region_name=rn,
            smena_name=sn,
            test_session_id=tsid,
            test_name=tn,
            gender_name=gn,
        )
        for student, ps_data, zn, rn, sn, tsid, tn, gn in rows
    ]
    return items, total


def get_students_by_session_and_zone(
    db: Session,
    *,
    test_session_id: int,
    zone_id: int,
) -> list[dict]:
    """Test sessiya va zonaga tegishli barcha studentlarni olish."""
    stmt = (
        _build_student_query()
        .where(
            TestSessionSmena.test_session_id == test_session_id,
            Student.zone_id == zone_id,
        )
        .order_by(Student.last_name, Student.first_name)
    )
    rows = db.execute(stmt).all()
    return [
        _student_to_dict(
            student,
            ps_data,
            zone_name=zn,
            region_name=rn,
            smena_name=sn,
            test_session_id=tsid,
            test_name=tn,
            gender_name=gn,
            include_large_fields=True,
        )
        for student, ps_data, zn, rn, sn, tsid, tn, gn in rows
    ]


def get_student(db: Session, student_id: int) -> dict | None:
    stmt = _build_student_query().where(Student.id == student_id)
    row = db.execute(stmt).first()
    if not row:
        return None
    student, ps_data, zn, rn, sn, tsid, tn, gn = row
    return _student_to_dict(
        student,
        ps_data,
        zone_name=zn,
        region_name=rn,
        smena_name=sn,
        test_session_id=tsid,
        test_name=tn,
        gender_name=gn,
        include_large_fields=True,
    )


def create_student(db: Session, data: StudentCreate) -> Student:
    student = Student(**data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


def update_student(db: Session, student_id: int, data: StudentUpdate) -> Student | None:
    student = db.get(Student, student_id)
    if not student:
        return None
    update_fields = data.model_dump(exclude_unset=True)
    ps_data_update = update_fields.pop("ps_data", None)
    for key, val in update_fields.items():
        setattr(student, key, val)
    # Update or create ps_data if provided
    if ps_data_update:
        # ps_img va embedding BYTEA ustunlar — base64 stringni bytes ga dekod qilamiz
        for binary_field in ("ps_img", "embedding"):
            if binary_field in ps_data_update and isinstance(
                ps_data_update[binary_field], str
            ):
                ps_data_update[binary_field] = _b64_to_bytes(
                    ps_data_update[binary_field]
                )

        ps_data = (
            db.query(StudentPsData)
            .filter(StudentPsData.student_id == student_id)
            .first()
        )
        if ps_data:
            for key, val in ps_data_update.items():
                if val is not None:
                    setattr(ps_data, key, val)
        else:
            ps_data = StudentPsData(
                student_id=student_id,
                **{k: v for k, v in ps_data_update.items() if v is not None},
            )
            db.add(ps_data)
    db.commit()
    db.refresh(student)
    return student


def delete_student(db: Session, student_id: int) -> bool:
    student = db.get(Student, student_id)
    if not student:
        return False

    session_smena_id = student.session_smena_id

    # Delete related records that reference this student
    db.query(CheatingLog).filter(CheatingLog.student_id == student_id).delete()
    db.query(StudentLog).filter(StudentLog.student_id == student_id).delete()
    db.query(StudentPsData).filter(StudentPsData.student_id == student_id).delete()
    db.delete(student)
    db.flush()

    # TestSession dagi count_total_student ni haqiqiy student soni bilan yangilash
    _sync_session_student_count(db, session_smena_id)

    db.commit()
    return True


def _sync_session_student_count(db: Session, session_smena_id: int) -> None:
    """TestSession.count_total_student ni DB dagi haqiqiy student soniga sinxronlash."""
    smena = db.get(TestSessionSmena, session_smena_id)
    if not smena:
        return
    test_session = db.get(TestSession, smena.test_session_id)
    if not test_session:
        return

    # Shu sessiyaga tegishli barcha smena ID lari
    smena_ids = [
        row[0]
        for row in db.execute(
            select(TestSessionSmena.id).where(
                TestSessionSmena.test_session_id == test_session.id
            )
        )
    ]
    # Haqiqiy student soni
    actual_count = (
        db.scalar(
            select(func.count(Student.id)).where(
                Student.session_smena_id.in_(smena_ids)
            )
        )
        if smena_ids
        else 0
    )
    test_session.count_total_student = actual_count


# ===================== StudentLog =====================


def get_student_logs_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    student_id: int | None = None,
    test_id: int | None = None,
    test_session_id: int | None = None,
    region_id: int | None = None,
    zone_id: int | None = None,
    smena_id: int | None = None,
    gr_n: int | None = None,
    e_date_from: str | None = None,
    e_date_to: str | None = None,
    is_cheating: bool | None = None,
    is_blacklist: bool | None = None,
    first_enter_from: str | None = None,
    first_enter_to: str | None = None,
    last_enter_from: str | None = None,
    last_enter_to: str | None = None,
    search: str | None = None,
) -> tuple[list[dict], int]:
    """StudentLog list — filter, search va range vaqt bo'yicha.

    List uchun og'ir LargeBinary (first_captured/last_captured) tanlanmaydi —
    faqat mavjud/yo'qligi (`has_first_captured`, `has_last_captured`) qaytariladi.
    To'liq rasmlar alohida `GET /students/logs/{id}` orqali olinadi.
    """
    has_first = (StudentLog.first_captured.isnot(None)).label("has_first")
    has_last = (StudentLog.last_captured.isnot(None)).label("has_last")

    stmt = (
        select(
            StudentLog.id,
            StudentLog.student_id,
            StudentLog.first_enter_time,
            StudentLog.last_enter_time,
            StudentLog.score,
            StudentLog.max_score,
            StudentLog.is_check_hand,
            StudentLog.ip_address,
            StudentLog.mac_address,
            has_first,
            has_last,
            Student.last_name,
            Student.first_name,
            Student.middle_name,
            Student.imei,
            Student.gr_n,
            Student.is_cheating,
            Student.is_blacklist,
            Student.e_date,
            Zone.id.label("zone_id"),
            Zone.name.label("zone_name"),
            Region.id.label("region_id"),
            Region.name.label("region_name"),
            Smena.id.label("smena_id"),
            Smena.name.label("smena_name"),
            TestSessionSmena.test_session_id.label("test_session_id"),
            Test.id.label("test_id"),
            Test.name.label("test_name"),
        )
        .join(Student, StudentLog.student_id == Student.id)
        .outerjoin(Zone, Student.zone_id == Zone.id)
        .outerjoin(Region, Zone.region_id == Region.id)
        .outerjoin(
            TestSessionSmena, Student.session_smena_id == TestSessionSmena.id
        )
        .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
        .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
        .outerjoin(Test, TestSession.test_id == Test.id)
        .order_by(StudentLog.id.desc())
    )
    count_stmt = (
        select(func.count(StudentLog.id))
        .join(Student, StudentLog.student_id == Student.id)
        .outerjoin(Zone, Student.zone_id == Zone.id)
        .outerjoin(Region, Zone.region_id == Region.id)
        .outerjoin(
            TestSessionSmena, Student.session_smena_id == TestSessionSmena.id
        )
        .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
        .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
        .outerjoin(Test, TestSession.test_id == Test.id)
    )

    def _apply(cond):
        nonlocal stmt, count_stmt
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    if student_id is not None:
        _apply(StudentLog.student_id == student_id)
    if test_id is not None:
        _apply(Test.id == test_id)
    if test_session_id is not None:
        _apply(TestSessionSmena.test_session_id == test_session_id)
    if region_id is not None:
        _apply(Region.id == region_id)
    if zone_id is not None:
        _apply(Student.zone_id == zone_id)
    if smena_id is not None:
        _apply(Smena.id == smena_id)
    if gr_n is not None:
        _apply(Student.gr_n == gr_n)
    if e_date_from:
        _apply(Student.e_date >= e_date_from)
    if e_date_to:
        _apply(Student.e_date <= e_date_to)
    if is_cheating is not None:
        _apply(Student.is_cheating == is_cheating)
    if is_blacklist is not None:
        _apply(Student.is_blacklist == is_blacklist)
    if first_enter_from:
        _apply(StudentLog.first_enter_time >= first_enter_from)
    if first_enter_to:
        _apply(StudentLog.first_enter_time <= first_enter_to)
    if last_enter_from:
        _apply(StudentLog.last_enter_time >= last_enter_from)
    if last_enter_to:
        _apply(StudentLog.last_enter_time <= last_enter_to)
    if search:
        p = f"%{search}%"
        _apply(
            Student.last_name.ilike(p)
            | Student.first_name.ilike(p)
            | Student.middle_name.ilike(p)
            | Student.imei.ilike(p)
        )

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = []
    for r in rows:
        full_name = " ".join(
            filter(None, [r.last_name, r.first_name, r.middle_name])
        )
        items.append(
            {
                "id": r.id,
                "student_id": r.student_id,
                "first_enter_time": r.first_enter_time,
                "last_enter_time": r.last_enter_time,
                "score": r.score,
                "max_score": r.max_score,
                "is_check_hand": r.is_check_hand,
                "ip_address": r.ip_address,
                "mac_address": r.mac_address,
                "has_first_captured": bool(r.has_first),
                "has_last_captured": bool(r.has_last),
                "student_full_name": full_name or None,
                "last_name": r.last_name,
                "first_name": r.first_name,
                "middle_name": r.middle_name,
                "imei": r.imei,
                "gr_n": r.gr_n,
                "is_cheating": r.is_cheating,
                "is_blacklist": r.is_blacklist,
                "e_date": r.e_date,
                "zone_id": r.zone_id,
                "zone_name": r.zone_name,
                "region_id": r.region_id,
                "region_name": r.region_name,
                "smena_id": r.smena_id,
                "smena_name": r.smena_name,
                "test_id": r.test_id,
                "test_name": r.test_name,
                "test_session_id": r.test_session_id,
            }
        )

    return items, total


def get_student_log_detail(db: Session, log_id: int) -> dict | None:
    """Bitta StudentLog — rasmlari (base64) bilan to'liq ma'lumotlar."""
    row = db.execute(
        select(
            StudentLog,
            Student.last_name,
            Student.first_name,
            Student.middle_name,
            Student.imei,
            Student.gr_n,
            Student.is_cheating,
            Student.is_blacklist,
            Student.e_date,
            Zone.name.label("zone_name"),
            Region.name.label("region_name"),
            Smena.name.label("smena_name"),
            Test.name.label("test_name"),
            TestSessionSmena.test_session_id.label("test_session_id"),
        )
        .join(Student, StudentLog.student_id == Student.id)
        .outerjoin(Zone, Student.zone_id == Zone.id)
        .outerjoin(Region, Zone.region_id == Region.id)
        .outerjoin(TestSessionSmena, Student.session_smena_id == TestSessionSmena.id)
        .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
        .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
        .outerjoin(Test, TestSession.test_id == Test.id)
        .where(StudentLog.id == log_id)
    ).first()

    if not row:
        return None

    log = row[0]
    full_name = " ".join(filter(None, [row.last_name, row.first_name, row.middle_name]))
    return {
        "id": log.id,
        "student_id": log.student_id,
        "first_captured": (
            base64.b64encode(log.first_captured).decode("ascii")
            if log.first_captured
            else None
        ),
        "last_captured": (
            base64.b64encode(log.last_captured).decode("ascii")
            if log.last_captured
            else None
        ),
        "first_enter_time": log.first_enter_time,
        "last_enter_time": log.last_enter_time,
        "score": log.score,
        "max_score": log.max_score,
        "is_check_hand": log.is_check_hand,
        "ip_address": log.ip_address,
        "mac_address": log.mac_address,
        "student_full_name": full_name or None,
        "last_name": row.last_name,
        "first_name": row.first_name,
        "middle_name": row.middle_name,
        "imei": row.imei,
        "gr_n": row.gr_n,
        "is_cheating": row.is_cheating,
        "is_blacklist": row.is_blacklist,
        "e_date": row.e_date,
        "zone_name": row.zone_name,
        "region_name": row.region_name,
        "smena_name": row.smena_name,
        "test_name": row.test_name,
        "test_session_id": row.test_session_id,
    }


def create_student_log(db: Session, data: StudentLogCreate) -> StudentLog:
    """Student uchun log yaratish yoki mavjudini yangilash (student_id unique).

    Mavjud bo'lsa: last_captured, last_enter_time, score (max), max_score (max),
    ip_address, mac_address yangilanadi. first_* maydonlari o'zgarmaydi.
    """
    payload = data.model_dump()
    for field in ("first_captured", "last_captured"):
        val = payload.get(field)
        if isinstance(val, str) and val:
            try:
                if "," in val and val.index(",") < 80:
                    val = val.split(",", 1)[1]
                payload[field] = base64.b64decode(val)
            except Exception:
                payload[field] = None

    existing = db.execute(
        select(StudentLog).where(StudentLog.student_id == payload["student_id"])
    ).scalar()

    if existing:
        if payload.get("last_captured") is not None:
            existing.last_captured = payload["last_captured"]
        if payload.get("last_enter_time") is not None:
            existing.last_enter_time = payload["last_enter_time"]
        if payload.get("score") is not None:
            existing.score = max(existing.score or 0, payload["score"] or 0)
        if payload.get("max_score") is not None:
            existing.max_score = max(existing.max_score or 0, payload["max_score"] or 0)
        if payload.get("is_check_hand") is not None:
            existing.is_check_hand = payload["is_check_hand"]
        if payload.get("ip_address") is not None:
            existing.ip_address = payload["ip_address"]
        if payload.get("mac_address") is not None:
            existing.mac_address = payload["mac_address"]
        db.commit()
        db.refresh(existing)
        return existing

    log = StudentLog(**payload)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def bulk_create_student_logs(
    db: Session,
    items: list[StudentLogBulkItem],
    *,
    user_id: int,
) -> list[StudentLogBulkResultItem]:
    """Desktop clientdan keladigan batch verify yozuvlarini qayta ishlash.

    Har bir item uchun:
      - StudentLog yozuvi yaratiladi yoki yangilanadi (student_id unique).
      - Agar is_rejected=True bo'lsa:
          * CheatingLog ga (student_id, reason_id, user_id) insert qilinadi.
          * Student.is_cheating=True, is_blacklist=True.
          * StudentBlacklist jadvaliga (imei, description=reason_name) insert
            qilinadi. Bu jadval insert-only — hech qachon update qilinmaydi.
      - Aks holda Student.is_entered=True.

    Bitta itemning xatosi boshqalarga ta'sir qilmaydi — har bir item o'z
    savepoint'ida. Umumiy session oxirida commit.
    """
    results: list[StudentLogBulkResultItem] = []

    for item in items:
        sp = db.begin_nested()  # SAVEPOINT
        try:
            student = db.get(Student, item.student_id)
            if not student:
                sp.rollback()
                results.append(
                    StudentLogBulkResultItem(
                        client_entry_id=item.client_entry_id,
                        student_id=item.student_id,
                        status="error",
                        error="student not found",
                    )
                )
                continue

            # UPSERT: student_id unique — mavjud bo'lsa update, yo'q bo'lsa create.
            # first_* maydonlar birinchi martagina to'ldiriladi, keyingi sync'da
            # faqat last_* / score / max_score / network maydonlar yangilanadi.
            first_captured_bytes = _b64_to_bytes(item.first_captured)
            last_captured_bytes = _b64_to_bytes(item.last_captured)

            log = db.execute(
                select(StudentLog).where(StudentLog.student_id == item.student_id)
            ).scalar()

            if log is None:
                log = StudentLog(
                    student_id=item.student_id,
                    first_captured=first_captured_bytes,
                    last_captured=last_captured_bytes,
                    first_enter_time=item.first_enter_time,
                    last_enter_time=item.last_enter_time,
                    score=item.score,
                    max_score=item.max_score,
                    is_check_hand=item.is_check_hand,
                    ip_address=item.ip_address,
                    mac_address=item.mac_address,
                )
                db.add(log)
            else:
                if last_captured_bytes is not None:
                    log.last_captured = last_captured_bytes
                if item.last_enter_time is not None:
                    log.last_enter_time = item.last_enter_time
                log.score = max(log.score or 0, item.score or 0)
                log.max_score = max(log.max_score or 0, item.max_score or 0)
                if item.is_check_hand:
                    log.is_check_hand = True
                if item.ip_address is not None:
                    log.ip_address = item.ip_address
                if item.mac_address is not None:
                    log.mac_address = item.mac_address
                # first_* yozuvlari faqat bo'sh bo'lsagina to'ldiriladi
                if log.first_captured is None and first_captured_bytes is not None:
                    log.first_captured = first_captured_bytes
                if log.first_enter_time is None and item.first_enter_time is not None:
                    log.first_enter_time = item.first_enter_time

            if item.is_rejected:
                reason_name: str | None = None
                if item.reject_reason_id is not None:
                    reason_name = db.execute(
                        select(Reason.name).where(Reason.id == item.reject_reason_id)
                    ).scalar()

                    # CheatingLog — student_id unique. Mavjud bo'lsa update,
                    # yo'q bo'lsa insert. updated_at SQLAlchemy onupdate orqali
                    # avtomatik yangilanadi.
                    existing_cl = db.execute(
                        select(CheatingLog).where(
                            CheatingLog.student_id == item.student_id
                        )
                    ).scalar()
                    if existing_cl is None:
                        db.add(
                            CheatingLog(
                                student_id=item.student_id,
                                reason_id=item.reject_reason_id,
                                user_id=user_id,
                            )
                        )
                    else:
                        existing_cl.reason_id = item.reject_reason_id
                        existing_cl.user_id = user_id

                # StudentBlacklist — imei unique; faqat birinchi martagina
                # insert qilinadi, keyingi sync'larda tegilmaydi.
                imei = item.imei or student.imei
                if imei:
                    exists_bl = db.execute(
                        select(StudentBlacklist.id).where(
                            StudentBlacklist.imei == imei
                        )
                    ).scalar()
                    if exists_bl is None:
                        db.add(
                            StudentBlacklist(
                                imei=imei,
                                description=reason_name,
                            )
                        )

                if not student.is_cheating:
                    student.is_cheating = True
                if not student.is_blacklist:
                    student.is_blacklist = True
            else:
                if not student.is_entered:
                    student.is_entered = True

            db.flush()
            sp.commit()
            results.append(
                StudentLogBulkResultItem(
                    client_entry_id=item.client_entry_id,
                    student_id=item.student_id,
                    status="ok",
                    log_id=log.id,
                )
            )
        except Exception as e:
            sp.rollback()
            logger.exception("bulk_create_student_logs: student_id=%s failed", item.student_id)
            results.append(
                StudentLogBulkResultItem(
                    client_entry_id=item.client_entry_id,
                    student_id=item.student_id,
                    status="error",
                    error=str(e)[:200],
                )
            )

    db.commit()
    return results


def update_student_log(
    db: Session, log_id: int, data: StudentLogUpdate
) -> StudentLog | None:
    log = db.get(StudentLog, log_id)
    if not log:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(log, key, val)
    db.commit()
    db.refresh(log)
    return log


def delete_student_log(db: Session, log_id: int) -> bool:
    log = db.get(StudentLog, log_id)
    if not log:
        return False
    db.delete(log)
    db.commit()
    return True


# ===================== CheatingLog =====================


def get_cheating_logs_paginated(
    db: Session,
    *,
    page: int = 1,
    per_page: int = 20,
    student_id: int | None = None,
) -> tuple[list[dict], int]:
    stmt = (
        select(
            CheatingLog,
            func.concat(Student.last_name, " ", Student.first_name).label(
                "student_full_name"
            ),
            Reason.name.label("reason_name"),
            User.username.label("username"),
        )
        .join(Student, CheatingLog.student_id == Student.id)
        .join(Reason, CheatingLog.reason_id == Reason.id)
        .join(User, CheatingLog.user_id == User.id)
        .order_by(CheatingLog.id.desc())
    )
    count_stmt = select(func.count(CheatingLog.id))

    if student_id is not None:
        stmt = stmt.where(CheatingLog.student_id == student_id)
        count_stmt = count_stmt.where(CheatingLog.student_id == student_id)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = []
    for log, student_full_name, reason_name, username in rows:
        items.append(
            {
                "id": log.id,
                "student_id": log.student_id,
                "reason_id": log.reason_id,
                "user_id": log.user_id,
                "image_path": log.image_path,
                "student_full_name": student_full_name,
                "reason_name": reason_name,
                "username": username,
            }
        )

    return items, total


def create_cheating_log(db: Session, data: CheatingLogCreate) -> CheatingLog:
    log = CheatingLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_cheating_log(
    db: Session, log_id: int, data: CheatingLogUpdate
) -> CheatingLog | None:
    log = db.get(CheatingLog, log_id)
    if not log:
        return None
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(log, key, val)
    db.commit()
    db.refresh(log)
    return log


def delete_cheating_log(db: Session, log_id: int) -> bool:
    log = db.get(CheatingLog, log_id)
    if not log:
        return False
    db.delete(log)
    db.commit()
    return True
