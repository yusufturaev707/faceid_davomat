"""CRUD operations for Student, StudentLog, CheatingLog."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.cheating_log import CheatingLog
from app.models.gender import Gender
from app.models.reason import Reason
from app.models.region import Region
from app.models.smena import Smena
from app.models.student import Student
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
    StudentLogCreate,
    StudentLogUpdate,
    StudentUpdate,
)


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
            ps_dict["ps_img"] = ps_data.ps_img
            ps_dict["embedding"] = ps_data.embedding
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
            .outerjoin(TestSessionSmena, Student.session_smena_id == TestSessionSmena.id)
            .outerjoin(Smena, TestSessionSmena.test_smena_id == Smena.id)
            .outerjoin(TestSession, TestSessionSmena.test_session_id == TestSession.id)
            .outerjoin(Test, TestSession.test_id == Test.id)
        )

    if session_smena_id is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.session_smena_id == session_smena_id)

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
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.e_date >= e_date_from)

    if e_date_to is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.e_date <= e_date_to)

    if is_entered is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_entered == is_entered)

    if is_cheating is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_cheating == is_cheating)

    if is_blacklist is not None:
        stmt, count_stmt = _apply_filter(stmt, count_stmt, Student.is_blacklist == is_blacklist)

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
            student, ps_data,
            zone_name=zn, region_name=rn, smena_name=sn,
            test_session_id=tsid, test_name=tn, gender_name=gn,
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
            student, ps_data,
            zone_name=zn, region_name=rn, smena_name=sn,
            test_session_id=tsid, test_name=tn, gender_name=gn,
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
        student, ps_data,
        zone_name=zn, region_name=rn, smena_name=sn,
        test_session_id=tsid, test_name=tn, gender_name=gn,
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
        ps_data = db.query(StudentPsData).filter(StudentPsData.student_id == student_id).first()
        if ps_data:
            for key, val in ps_data_update.items():
                if val is not None:
                    setattr(ps_data, key, val)
        else:
            ps_data = StudentPsData(student_id=student_id, **{k: v for k, v in ps_data_update.items() if v is not None})
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
) -> tuple[list[dict], int]:
    stmt = (
        select(
            StudentLog,
            func.concat(Student.last_name, " ", Student.first_name).label(
                "student_full_name"
            ),
        )
        .join(Student, StudentLog.student_id == Student.id)
        .order_by(StudentLog.id.desc())
    )
    count_stmt = select(func.count(StudentLog.id))

    if student_id is not None:
        stmt = stmt.where(StudentLog.student_id == student_id)
        count_stmt = count_stmt.where(StudentLog.student_id == student_id)

    total = db.execute(count_stmt).scalar() or 0
    rows = db.execute(stmt.offset((page - 1) * per_page).limit(per_page)).all()

    items = []
    for log, student_full_name in rows:
        items.append(
            {
                "id": log.id,
                "student_id": log.student_id,
                "first_captured": log.first_captured,
                "last_captured": log.last_captured,
                "first_enter_time": log.first_enter_time,
                "last_enter_time": log.last_enter_time,
                "score": log.score,
                "max_score": log.max_score,
                "is_check_hand": log.is_check_hand,
                "ip_address": log.ip_address,
                "mac_address": log.mac_address,
                "student_full_name": student_full_name,
            }
        )

    return items, total


def create_student_log(db: Session, data: StudentLogCreate) -> StudentLog:
    log = StudentLog(**data.model_dump())
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def update_student_log(db: Session, log_id: int, data: StudentLogUpdate) -> StudentLog | None:
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


def update_cheating_log(db: Session, log_id: int, data: CheatingLogUpdate) -> CheatingLog | None:
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
