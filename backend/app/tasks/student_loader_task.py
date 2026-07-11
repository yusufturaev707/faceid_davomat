"""Celery tasklar: tashqi API'dan studentlarni KUN BO'YICHA parallel yuklash.

Arxitektura (resumable, parallel):

1. `load_students_task` (COORDINATOR) — endpoint state=2 ga o'tganda chaqiriladi.
   Sessiya lock'ini oladi, kunlarni aniqlaydi (kerak bo'lsa allaqachon yuklangan
   kunlarni o'tkazib yuboradi) va har kun uchun alohida task'ni chord bilan
   ishga tushiradi. Chord tugagach `finalize_student_load` chaqiriladi.
2. `load_students_day_task` (KUNLIK) — bitta kunni mustaqil yuklaydi. Har kun
   o'z lock'i, o'z progress kaliti bilan. Bir kun xato bersa boshqalari saqlanadi.
3. `finalize_student_load` — barcha kunlar tugagach yakuniy holatni belgilaydi.

Frontend `/student-load-progress` orqali progress polling qiladi (kun-kalitlari
jamlanadi).
"""

import logging
import uuid

from celery import chord

from app.celery_app import celery_app
from app.config import settings
from app.db.session import SessionLocal
from app.models.test_session import TestSession
from app.services.student_loader import (
    StudentLoadError,
    _build_load_context,
    _get_redis,
    clear_session_load_keys,
    is_day_done,
    load_students_for_day,
    mark_progress_error,
    mark_progress_queued,
)

logger = logging.getLogger("faceid.tasks.student_loader")

# Sessiya lock — bir sessiya uchun bir vaqtda faqat BITTA coordinator/oqim.
# Coordinator NX bilan oladi; finalize oxirida o'chiradi (workflow serial).
_SESSION_LOCK_KEY = "student_load_lock:{session_id}"
_SESSION_LOCK_TTL = 43200  # 12 soat — butun oqim (barcha kunlar) uchun yetarli

# Kunlik lock — bitta kun taski redelivery bo'lsa dublikat ishlamasligi uchun.
_DAY_LOCK_KEY = "student_load_daylock:{session_id}:{day}"
_DAY_LOCK_TTL = settings.STUDENT_LOAD_TIME_LIMIT + 600


# ─────────────────────────── COORDINATOR ───────────────────────────


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.load_students",
    queue="storage",
    time_limit=900,  # coordinator qisqa — faqat kunlarni tarqatadi
    soft_time_limit=840,
)
def load_students_task(
    self, session_id: int, previous_state_id: int, force: bool = True
) -> dict:
    """Coordinator: kunlarni aniqlab, har biriga alohida task tarqatadi.

    Args:
        session_id: TestSession ID.
        previous_state_id: Xato/bekor bo'lsa qaytariladigan state.
        force: True — to'liq yangi yuklash (barcha kunlar, eski kalitlar tozalanadi);
               False — resumable qayta yuklash (allaqachon tugagan kunlar tashlanadi).
    """
    r = _get_redis()
    lock_key = _SESSION_LOCK_KEY.format(session_id=session_id)
    if r is not None:
        if not r.set(lock_key, "1", nx=True, ex=_SESSION_LOCK_TTL):
            logger.warning(
                "Session #%d: oqim allaqachon ishlayapti — dublikat coordinator "
                "o'tkazib yuborildi", session_id,
            )
            return {"status": "skipped", "message": "Allaqachon davom etmoqda"}

    db = SessionLocal()
    try:
        session = db.get(TestSession, session_id)
        if not session:
            mark_progress_error(session_id, f"Sessiya #{session_id} topilmadi")
            _release_session_lock(r, session_id)
            return {"status": "error", "message": "Sessiya topilmadi"}

        # Kontekst (validatsiya) — API/zona/smena sozlanmagan bo'lsa shu yerda xato
        try:
            ctx = _build_load_context(db, session)
        except StudentLoadError as e:
            logger.error("Session #%d: konfiguratsiya xatosi — %s", session_id, e.message)
            _rollback_state(db, session_id, previous_state_id)
            mark_progress_error(session_id, e.message)
            _release_session_lock(r, session_id)
            return {"status": "error", "message": e.message}

        if force:
            # To'liq yangi yuklash — eski progress/done/cancel kalitlarini tozalaymiz
            clear_session_load_keys(session_id)
            from app.services.student_loader import _clear_cancel_flag
            _clear_cancel_flag(r, session_id)

        # Yuklanadigan kunlar: force bo'lsa hammasi; aks holda tugamaganlar
        days = list(ctx.smena_days)
        if not force:
            days = [d for d in days if not is_day_done(session_id, d)]

        if not days:
            logger.info("Session #%d: yuklanadigan kun yo'q (hammasi tugagan)", session_id)
            _release_session_lock(r, session_id)
            return {"status": "completed", "message": "Barcha kunlar allaqachon yuklangan"}

        mark_progress_queued(
            session_id, f"{len(days)} kun navbatga qo'yildi — yuklash boshlanmoqda..."
        )
        logger.info(
            "Session #%d: %d kun tarqatilmoqda (force=%s): %s",
            session_id, len(days), force, days,
        )

        # Har kun uchun alohida task — parallel (chord), tugagach finalize
        header = [load_students_day_task.s(session_id, day) for day in days]
        callback = finalize_student_load.s(session_id, previous_state_id)
        chord(header)(callback)

        return {"status": "dispatched", "days": len(days)}
    except Exception as e:
        logger.exception("Session #%d: coordinator xatosi", session_id)
        _rollback_state(db, session_id, previous_state_id)
        mark_progress_error(session_id, f"Kutilmagan xatolik: {e}")
        _release_session_lock(r, session_id)
        return {"status": "error", "message": str(e)}
    finally:
        db.close()


# ─────────────────────────── KUNLIK TASK ───────────────────────────


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.load_students_day",
    queue="storage",
    time_limit=settings.STUDENT_LOAD_TIME_LIMIT,
    soft_time_limit=settings.STUDENT_LOAD_TIME_LIMIT - 300,
)
def load_students_day_task(self, session_id: int, day_str: str) -> dict:
    """Bitta kunni mustaqil yuklaydi (parallel ishlaydi)."""
    r = _get_redis()
    day_lock = _DAY_LOCK_KEY.format(session_id=session_id, day=day_str)
    token = str(uuid.uuid4())
    if r is not None:
        if not r.set(day_lock, token, nx=True, ex=_DAY_LOCK_TTL):
            logger.warning(
                "Session #%d kun %s: allaqachon yuklanmoqda — dublikat o'tkazildi",
                session_id, day_str,
            )
            return {"day": day_str, "status": "skipped", "loaded": 0}

    db = SessionLocal()
    try:
        session = db.get(TestSession, session_id)
        if not session:
            return {"day": day_str, "status": "error", "loaded": 0, "message": "sessiya yo'q"}
        # load_students_for_day EXCEPTION KO'TARMASLIGI kerak — lekin chord
        # buzilmasligi uchun bu yerda ham himoya to'ri (natija dict qaytaramiz).
        try:
            return load_students_for_day(db, session, day_str)
        except Exception as e:
            logger.exception("Kun %s: kutilmagan xatolik (session #%d)", day_str, session_id)
            return {"day": day_str, "status": "error", "loaded": 0, "message": str(e)}
    finally:
        db.close()
        if r is not None:
            try:
                if r.get(day_lock) == token:
                    r.delete(day_lock)
            except Exception:
                pass


# ─────────────────────────── FINALIZE ───────────────────────────


@celery_app.task(
    bind=True,
    max_retries=0,
    name="tasks.finalize_student_load",
    queue="storage",
    time_limit=600,
)
def finalize_student_load(
    self, results: list, session_id: int, previous_state_id: int
) -> dict:
    """Barcha kunlar tugagach yakuniy holat: state, count, cleanup, lock release.

    results — kunlik tasklarning natija dict'lari ro'yxati.
    """
    results = results or []
    any_cancelled = any(r.get("status") == "cancelled" for r in results if isinstance(r, dict))
    any_error = any(r.get("status") == "error" for r in results if isinstance(r, dict))
    total_loaded = sum(
        int(r.get("loaded", 0) or 0) for r in results if isinstance(r, dict)
    )

    r = _get_redis()
    db = SessionLocal()
    try:
        if any_cancelled:
            # Bekor qilindi — barcha yuklangan studentlarni o'chirib, state qaytaramiz
            logger.info("Session #%d: bekor qilindi — tozalanmoqda", session_id)
            _rollback_state(db, session_id, previous_state_id)
            try:
                from app.crud.test_session import _delete_students_by_session
                _delete_students_by_session(db, session_id)
                db.commit()
            except Exception:
                db.rollback()
                logger.exception("Session #%d: bekor tozalashda xato", session_id)
            clear_session_load_keys(session_id)
            from app.services.student_loader import mark_progress_cancelled
            mark_progress_cancelled(
                session_id, "Yuklash bekor qilindi — sessiya avvalgi holatiga qaytarildi"
            )
            _release_session_lock(r, session_id)
            return {"status": "cancelled", "loaded": 0}

        # DB'dagi haqiqiy sonni yozamiz (resumable qayta yuklashlarda ham to'g'ri)
        try:
            session = db.get(TestSession, session_id)
            if session:
                actual = _count_session_students(db, session_id)
                session.count_total_student = actual
                db.commit()
                total_loaded = actual
        except Exception:
            db.rollback()
            logger.exception("Session #%d: count yangilashda xato", session_id)

        if total_loaded == 0 and not any_error:
            # Hech narsa yuklanmadi — state'ni qaytaramiz. Kun-kalitlarini avval
            # tozalaymiz, aks holda aggregatsiya ularni "completed" ko'rsatib qoladi.
            logger.warning("Session #%d: 0 talaba — state qaytarilmoqda", session_id)
            _rollback_state(db, session_id, previous_state_id)
            clear_session_load_keys(session_id)
            mark_progress_error(
                session_id,
                "Tashqi API'dan 0 ta talaba qaytdi — sessiya parametrlarini tekshiring",
            )
            _release_session_lock(r, session_id)
            return {"status": "error", "loaded": 0}

        # Muvaffaqiyat (yoki qisman) — state key=2 da qoladi, ma'lumot saqlanadi.
        # Xato bo'lgan kunlar aggregatsiyada "error" ko'rinadi; foydalanuvchi
        # "Qayta yuklash" bilan faqat o'shalarni qayta yuklashi mumkin (resumable).
        logger.info(
            "Session #%d yakunlandi: loaded=%d, xato_kun=%s",
            session_id, total_loaded, any_error,
        )
        _release_session_lock(r, session_id)
        return {"status": "error" if any_error else "completed", "loaded": total_loaded}
    finally:
        db.close()


# ─────────────────────────── Yordamchilar ───────────────────────────


def _count_session_students(db, session_id: int) -> int:
    from sqlalchemy import func, select as sa_select
    from app.models.student import Student
    from app.models.test_session_smena import TestSessionSmena

    smena_ids = [
        row[0]
        for row in db.execute(
            sa_select(TestSessionSmena.id).where(
                TestSessionSmena.test_session_id == session_id
            )
        )
    ]
    if not smena_ids:
        return 0
    return int(
        db.scalar(
            sa_select(func.count(Student.id)).where(
                Student.session_smena_id.in_(smena_ids)
            )
        ) or 0
    )


def _release_session_lock(r, session_id: int) -> None:
    if r is None:
        return
    try:
        r.delete(_SESSION_LOCK_KEY.format(session_id=session_id))
    except Exception:
        logger.warning("Session #%d: sessiya lock bo'shatishda xato", session_id)


def _rollback_state(db, session_id: int, previous_state_id: int) -> None:
    """Xatolik/bekor bo'lganda sessiyani avvalgi state'iga qaytarish."""
    try:
        db.rollback()
    except Exception:
        pass
    try:
        from app.crud.test_session import change_session_state
        change_session_state(db, session_id=session_id, new_state_id=previous_state_id)
        logger.info("Session #%d: state %d ga qaytarildi", session_id, previous_state_id)
    except Exception:
        logger.exception("Session #%d: state qaytarishda xatolik", session_id)
