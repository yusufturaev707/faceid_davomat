"""Telegram `davomat_bot` serveri uchun endpointlar.

Bot backend ga `X-API-Key` orqali kiradi (boshqa endpointlar bilan bir xil
autentifikatsiya). Har bir so'rovda telegram_id orqali bot foydalanuvchisi
DB dan tekshiriladi. Foydalanuvchilar uchun asosiy interfeys — Telegram
Mini App (`endpoints/davomat_miniapp.py`); ikkala kanal ham biznes-logikani
`services/davomat_bot_service.py` dan oladi.

Quyidagi flow ni qo'llab-quvvatlaydi:
  1. `/check/{telegram_id}` — ruxsat va profile.
  2. `/ready-sessions` — statusi `active` (key=4) sessiyalar va ularning
     kun+smena ro'yxati.
  3. `/sessions/{id}/stats` — tanlangan smena bo'yicha biriktirilgan
     regionlar kesimida davomat statistikasi.
  4. `/face-verify` — pasport + jshshir + selfie. Backend GTSP'dan rasm
     oladi va selfie bilan solishtiradi. Bundan tashqari `jshshir` + tanlangan
     smena/kun bo'yicha DB validatsiyasi qiladi — talaba shu smenadami,
     boshqa smenadami yoki sessiyada umuman yo'qmi.
  5. `/mark-attendance` — yuz tasdiqlanganidan keyin, talabani davomatga
     qo'shish (Student.is_entered=True + StudentLog UPSERT).
  6. `/find-by-jshshir` — JShShIR bo'yicha tanlangan smenadagi talabgorlarni
     qaytarish (0/1/many). Remove-attendance flow uchun ishlatiladi.
  7. `/remove-attendance` — tasdiqlangan talabgorni davomatdan olib tashlash
     (Student.is_entered=False). StudentLog tegilmaydi — tarix saqlanadi.
"""

from __future__ import annotations

import logging
from datetime import date
from urllib.parse import quote as _url_quote

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.crud.davomat_bot import get_bot_by_telegram_id
from app.dependencies import get_current_active_user, get_db
from app.models.davomat_bot import DavomatBot
from app.models.user import User
from app.schemas.davomat_bot import (
    BotAccessResponse,
    BotCheatRequest,
    BotCheatResponse,
    BotFaceVerifyRequest,
    BotFaceVerifyResponse,
    BotFindByJshshirRequest,
    BotFindByJshshirResponse,
    BotFindForCheatRequest,
    BotFindForCheatResponse,
    BotMarkAttendanceRequest,
    BotMarkAttendanceResponse,
    BotReadySessionResponse,
    BotReasonInfo,
    BotReasonTypeInfo,
    BotRemoveAttendanceRequest,
    BotRemoveAttendanceResponse,
    BotSessionStatsResponse,
)
from app.services import davomat_bot_service as svc
from app.services.davomat_bot_absentees import (
    AbsenteesError,
    build_absentees_excel,
)
from app.services.davomat_bot_stats import BotStatsError, compute_bot_stats

logger = logging.getLogger("faceid.api.davomat_bot")
router = APIRouter()


def _require_bot(db: Session, telegram_id: int) -> DavomatBot:
    bot = get_bot_by_telegram_id(db, telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")
    return bot


@router.get("/check/{telegram_id}", response_model=BotAccessResponse)
def check_bot_access(
    telegram_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """`telegram_id` orqali botga dostup berilganligini tekshirish."""
    bot = get_bot_by_telegram_id(db, telegram_id)
    if not bot:
        return BotAccessResponse(
            allowed=False,
            message="Sizga botdan foydalanish ruxsati berilmagan",
        )
    return BotAccessResponse(allowed=True, user=svc.bot_to_user_response(bot))


@router.get("/ready-sessions", response_model=list[BotReadySessionResponse])
def list_ready_sessions(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Holat `key=4` (ACTIVE / "Tayyor") bo'lgan test sessiyalarni qaytarish."""
    return svc.list_ready_sessions(db)


@router.get(
    "/sessions/{session_id}/stats",
    response_model=BotSessionStatsResponse,
)
def bot_session_stats(
    session_id: int,
    telegram_id: int,
    session_smena_id: int | None = Query(
        default=None,
        description="Bitta smena (None bo'lsa, day/total ishlaydi)",
    ),
    test_day: date | None = Query(
        default=None,
        description="Bitta kun barcha smenalari (session_smena_id bo'lmasa)",
    ),
    region_id: int | None = Query(
        default=None,
        description=(
            "Yagona region kesimi. Bot 2+ regionga biriktirilgan foydalanuvchi"
            " /start da region tanlagandan keyin shu parametr yuboriladi."
            " Yo'q bo'lsa — barcha biriktirilgan regionlar bo'yicha."
        ),
    ),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Tanlangan kontekst bo'yicha statistikani qaytarish.

    Parametrlar kombinatsiyasi:
      - `session_smena_id` berilsa: bitta smena bo'yicha.
      - `test_day` berilsa: shu kunning barcha aktiv smenalari bo'yicha.
      - Ikkalasi ham `None`: butun sessiyaning barcha aktiv smenalari.

    `region_id` berilsa, statistika faqat shu region kesimida hisoblanadi
    (bot foydalanuvchi shu regionga biriktirilgan bo'lishi shart).
    """
    bot = _require_bot(db, telegram_id)
    allowed = svc.resolve_filter_regions(bot, region_id)

    try:
        return compute_bot_stats(
            db,
            session_id=session_id,
            session_smena_id=session_smena_id,
            test_day=test_day,
            allowed_region_ids=allowed,
        )
    except BotStatsError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/sessions/{session_id}/absentees.xlsx",
    response_class=Response,
)
def bot_session_absentees_xlsx(
    session_id: int,
    telegram_id: int,
    session_smena_id: int | None = Query(
        default=None,
        description="Bitta smena (None bo'lsa, day/total ishlaydi)",
    ),
    test_day: date | None = Query(
        default=None,
        description="Bitta kun barcha smenalari (session_smena_id bo'lmasa)",
    ),
    region_id: int | None = Query(
        default=None,
        description="Yagona region kesimi (bot `/start` da tanlagan region)",
    ),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Tanlangan kontekst bo'yicha kelmaganlar ro'yxati (.xlsx).

    `region_id` berilsa, faqat shu region kesimida; aks holda barcha
    biriktirilgan regionlar kesimida.

    Parametrlar kombinatsiyasi:
      - `session_smena_id` berilsa: bitta smena bo'yicha (oldingidek).
      - `test_day` berilsa: shu kunning barcha aktiv smenalari bo'yicha aggregat.
      - Ikkalasi ham `None`: butun sessiyaning barcha aktiv smenalari aggregat.
    """
    bot = _require_bot(db, telegram_id)
    allowed = svc.resolve_filter_regions(bot, region_id)

    try:
        file_bytes, filename, count = build_absentees_excel(
            db,
            session_id=session_id,
            session_smena_id=session_smena_id,
            test_day=test_day,
            allowed_region_ids=allowed,
        )
    except AbsenteesError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Telegram/Excel uchun ASCII fallback + RFC 5987 (UTF-8) filename — turli
    # client'lar bilan yaxshi mos.
    safe_ascii = filename.encode("ascii", "ignore").decode() or "absentees.xlsx"
    encoded = _url_quote(filename)
    headers = {
        "Content-Disposition": (
            f'attachment; filename="{safe_ascii}"; filename*=UTF-8\'\'{encoded}'
        ),
        "X-Absent-Count": str(count),
    }
    return Response(
        content=file_bytes,
        media_type=(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        headers=headers,
    )


# ============================================================
# Face ID + davomat
# ============================================================


@router.post("/face-verify", response_model=BotFaceVerifyResponse)
def bot_face_verify(
    body: BotFaceVerifyRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bot Face ID + DB validatsiya (`svc.face_verify` ga qarang)."""
    bot = _require_bot(db, body.telegram_id)
    return svc.face_verify(
        db,
        bot,
        session_id=body.session_id,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
        ps_ser=body.ps_ser,
        ps_num=body.ps_num,
        jshshir=body.jshshir,
        selfie_b64=body.selfie_b64,
    )


@router.post("/mark-attendance", response_model=BotMarkAttendanceResponse)
def bot_mark_attendance(
    body: BotMarkAttendanceRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Tasdiqlangan talabani davomatga qo'shish (`svc.mark_attendance`)."""
    bot = _require_bot(db, body.telegram_id)
    return svc.mark_attendance(
        db,
        bot,
        student_id=body.student_id,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
        selfie_b64=body.selfie_b64,
        verify_score=body.verify_score,
    )


@router.post("/find-by-jshshir", response_model=BotFindByJshshirResponse)
def bot_find_by_jshshir(
    body: BotFindByJshshirRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Davomatdan olib tashlash uchun talabgorlarni topish."""
    bot = _require_bot(db, body.telegram_id)
    return svc.find_by_jshshir(
        db,
        bot,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
        jshshir=body.jshshir,
        only_entered=body.only_entered,
    )


@router.post("/remove-attendance", response_model=BotRemoveAttendanceResponse)
def bot_remove_attendance(
    body: BotRemoveAttendanceRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Tasdiqlangan talabgorni davomatdan olib tashlash."""
    bot = _require_bot(db, body.telegram_id)
    return svc.remove_attendance(
        db,
        bot,
        student_id=body.student_id,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
    )


# ============================================================
# Chetlatish (cheating)
# ============================================================


@router.get("/reason-types", response_model=list[BotReasonTypeInfo])
def bot_list_reason_types(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Aktiv chetlatish turlari."""
    return svc.list_reason_types(db)


@router.get("/reasons", response_model=list[BotReasonInfo])
def bot_list_reasons(
    reason_type_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Aktiv sabablar (`reason_type_id` bo'yicha filtr)."""
    return svc.list_reasons(db, reason_type_id)


@router.post("/find-for-cheat", response_model=BotFindForCheatResponse)
def bot_find_for_cheat(
    body: BotFindForCheatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """JShShIR bo'yicha sessiyada chetlatish uchun talabgorlarni topish."""
    bot = _require_bot(db, body.telegram_id)
    return svc.find_for_cheat(
        db,
        bot,
        session_id=body.session_id,
        region_id=body.region_id,
        jshshir=body.jshshir,
    )


@router.post("/cheating", response_model=BotCheatResponse)
def bot_create_cheating(
    body: BotCheatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Talabgorni chetlatish (rasmsiz). `CheatingLog.user_id` = API key egasi."""
    bot = _require_bot(db, body.telegram_id)
    return svc.create_cheating(
        db,
        bot,
        student_id=body.student_id,
        session_id=body.session_id,
        region_id=body.region_id,
        reason_id=body.reason_id,
        user_id=int(_user.id),
    )
