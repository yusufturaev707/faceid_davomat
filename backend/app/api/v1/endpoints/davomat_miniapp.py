"""Davomat Telegram Mini App endpointlari (`/api/v1/davomat-miniapp`).

Autentifikatsiya: `Authorization: tma <initData>` — Telegram imzolagan
`initData` har so'rovda bot tokeni bilan tekshiriladi (`core/telegram_webapp.py`),
so'ng `telegram_id` bo'yicha aktiv `DavomatBot` yozuvi olinadi. Shu sababli
foydalanuvchi o'chirilsa yoki bloklansa, keyingi so'rovdayoq kirish yopiladi.
API kalit yoki JWT bu yerda qabul qilinmaydi — bu klient brauzerda ishlaydi.

Biznes-logika bot kanali bilan umumiy: `services/davomat_bot_service.py`.
Mini App'ga xos qo'shimchalar:
  - `face-verify` imzolangan `verify_ticket` qaytaradi, `mark-attendance`
    faqat shu chipta bilan ishlaydi (klient talabgor/ball/selfie'ni
    almashtira olmaydi).
  - `passport-qr` — ID-karta QR matni yoki rasmidan pasport maydonlari.
  - Kelmaganlar Excel'i foydalanuvchining Telegram chatiga yuboriladi.

Flow:
  1. `GET  /me`                                — dostup + profil (regionlar).
  2. `GET  /sessions`                          — faol test sessiyalari, kun+smena.
  3. `GET  /sessions/{id}/stats`               — smena / kun / sessiya statistikasi.
  4. `POST /sessions/{id}/absentees/send`      — kelmaganlar Excel → Telegram chat.
  5. `POST /passport-qr`                       — QR → ps_ser/ps_num/jshshir.
  6. `POST /face-verify` → `POST /mark-attendance`.
  7. `POST /find-by-jshshir` → `POST /remove-attendance`.
  8. `GET  /reason-types`, `GET /reasons`, `POST /find-for-cheat` → `POST /cheating`.

`from __future__ import annotations` atayin yo'q: `@limiter.limit` wrapper'i
boshqa modul `__globals__` ida turadi va FastAPI satr ko'rinishidagi
annotatsiyalarni (body modelini) hal qila olmay, uni query parametr deb oladi.
"""

import hmac
import logging
from dataclasses import dataclass
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.core.rate_limit import limiter
from app.core.telegram_webapp import (
    InitDataError,
    TelegramWebAppUser,
    validate_init_data,
)
from app.crud.davomat_bot import get_bot_by_telegram_id
from app.dependencies import API_KEY_HEADER, get_db
from app.models.davomat_bot import DavomatBot
from app.models.user import User
from app.schemas.davomat_bot import (
    BotCheatResponse,
    BotFindByJshshirResponse,
    BotFindForCheatResponse,
    BotMarkAttendanceResponse,
    BotReadySessionResponse,
    BotReasonInfo,
    BotReasonTypeInfo,
    BotRemoveAttendanceResponse,
    BotSessionStatsResponse,
)
from app.schemas.davomat_miniapp import (
    MiniAppAbsenteesRequest,
    MiniAppAbsenteesResponse,
    MiniAppCheatRequest,
    MiniAppFaceVerifyRequest,
    MiniAppFaceVerifyResponse,
    MiniAppFindByJshshirRequest,
    MiniAppFindForCheatRequest,
    MiniAppMarkAttendanceRequest,
    MiniAppMeResponse,
    MiniAppPassportQrRequest,
    MiniAppPassportResponse,
    MiniAppRemoveAttendanceRequest,
)
from app.services import davomat_bot_service as svc
from app.services.davomat_bot_absentees import AbsenteesError, build_absentees_excel
from app.services.davomat_bot_stats import BotStatsError, compute_bot_stats
from app.services.davomat_miniapp import (
    PassportQrError,
    TelegramSendError,
    TicketError,
    decode_passport_qr_image,
    issue_verify_ticket,
    parse_passport_qr_text,
    read_verify_ticket,
    selfie_digest,
    send_document_to_chat,
)

logger = logging.getLogger("faceid.api.davomat_miniapp")
router = APIRouter()

_XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


# ============================================================
# Autentifikatsiya
# ============================================================


@dataclass(frozen=True)
class MiniAppOperator:
    """Imzolangan Telegram foydalanuvchisi + unga mos aktiv `DavomatBot`."""

    telegram_user: TelegramWebAppUser
    bot: DavomatBot


def _ensure_configured() -> None:
    missing = [
        name
        for name, ok in (
            ("DAVOMAT_BOT_TOKEN", bool(settings.DAVOMAT_BOT_TOKEN)),
            ("DAVOMAT_MINIAPP_USER_ID", settings.DAVOMAT_MINIAPP_USER_ID > 0),
        )
        if not ok
    ]
    if missing:
        logger.error("Davomat Mini App sozlanmagan: %s", ", ".join(missing))
        raise HTTPException(
            status_code=503,
            detail="Davomat ilovasi serverda sozlanmagan. Administratorga murojaat qiling.",
        )


def get_telegram_user(request: Request) -> TelegramWebAppUser:
    """`Authorization: tma <initData>` ni tekshirib, Telegram foydalanuvchisini qaytaradi."""
    _ensure_configured()

    if request.headers.get(API_KEY_HEADER):
        # dependencies.get_current_user dagi kabi: ikki xil auth aralashmasin.
        raise HTTPException(status_code=400, detail="Bu endpoint API kalitni qabul qilmaydi")

    scheme, _, init_data = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "tma" or not init_data:
        raise HTTPException(
            status_code=401,
            detail="Ilovani Telegram bot orqali oching.",
        )

    try:
        return validate_init_data(
            init_data,
            settings.DAVOMAT_BOT_TOKEN,
            max_age_seconds=settings.DAVOMAT_MINIAPP_INIT_DATA_TTL,
        )
    except InitDataError as e:
        if e.expired:
            raise HTTPException(
                status_code=401,
                detail="Sessiya muddati tugagan. Ilovani yopib, qaytadan oching.",
            )
        logger.warning("Mini App initData rad etildi: %s", e)
        raise HTTPException(
            status_code=401,
            detail="Telegram ma'lumotlari tasdiqlanmadi. Ilovani qaytadan oching.",
        )


def get_operator(
    tg_user: TelegramWebAppUser = Depends(get_telegram_user),
    db: Session = Depends(get_db),
) -> MiniAppOperator:
    """Faqat `davomat_bots` da aktiv bo'lgan foydalanuvchilar."""
    bot = get_bot_by_telegram_id(db, tg_user.id)
    if bot is None:
        raise HTTPException(
            status_code=403,
            detail="Sizga davomat ilovasidan foydalanish ruxsati yo'q.",
        )
    return MiniAppOperator(telegram_user=tg_user, bot=bot)


# ============================================================
# Profil, sessiyalar, statistika
# ============================================================


@router.get("/me", response_model=MiniAppMeResponse)
def get_me(
    tg_user: TelegramWebAppUser = Depends(get_telegram_user),
    db: Session = Depends(get_db),
):
    """Dostup va profil. Ruxsat yo'q bo'lsa ham 200 — UI Telegram ID'ni ko'rsatadi."""
    bot = get_bot_by_telegram_id(db, tg_user.id)
    if bot is None:
        return MiniAppMeResponse(
            allowed=False,
            telegram_id=tg_user.id,
            message=(
                "Sizga davomat ilovasidan foydalanish ruxsati berilmagan. "
                "Telegram ID raqamingizni administratorga yuboring."
            ),
        )
    return MiniAppMeResponse(
        allowed=True,
        telegram_id=tg_user.id,
        user=svc.bot_to_user_response(bot),
    )


@router.get("/sessions", response_model=list[BotReadySessionResponse])
def list_sessions(
    _op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Faol (key=4) test sessiyalari va ularning kun+smena ro'yxati."""
    return svc.list_ready_sessions(db)


@router.get("/sessions/{session_id}/stats", response_model=BotSessionStatsResponse)
def session_stats(
    session_id: int,
    session_smena_id: int | None = Query(default=None),
    test_day: date | None = Query(default=None),
    region_id: int | None = Query(default=None),
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Smena (`session_smena_id`), kun (`test_day`) yoki butun sessiya statistikasi."""
    allowed = svc.resolve_filter_regions(op.bot, region_id)
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


@router.post(
    "/sessions/{session_id}/absentees/send",
    response_model=MiniAppAbsenteesResponse,
)
@limiter.limit("10/minute")
def send_absentees(
    request: Request,
    session_id: int,
    body: MiniAppAbsenteesRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Kelmaganlar ro'yxatini Excel qilib foydalanuvchi Telegram chatiga yuborish."""
    allowed = svc.resolve_filter_regions(op.bot, body.region_id)
    try:
        file_bytes, filename, count = build_absentees_excel(
            db,
            session_id=session_id,
            session_smena_id=body.session_smena_id,
            test_day=body.test_day,
            allowed_region_ids=allowed,
        )
    except AbsenteesError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if count == 0:
        return MiniAppAbsenteesResponse(
            status="empty",
            count=0,
            message="Kelmagan talabgorlar yo'q — fayl yuborilmadi.",
        )

    # Fayl tayyor — Telegram'ga yuklash davomida DB ulanishini band qilmaymiz.
    db.rollback()

    if body.session_smena_id is not None:
        scope_label = ""
    elif body.test_day is not None:
        scope_label = f" ({body.test_day.isoformat()} kuni bo'yicha)"
    else:
        scope_label = " (barcha kunlar bo'yicha)"
    caption = (
        f"📥 <b>Kelmaganlar ro'yxati</b>{scope_label}\n"
        f"👥 Jami: <b>{count}</b> ta talabgor"
    )

    try:
        send_document_to_chat(
            chat_id=op.telegram_user.id,
            file_bytes=file_bytes,
            filename=filename,
            caption=caption,
            content_type=_XLSX_MEDIA_TYPE,
        )
    except TelegramSendError as e:
        raise HTTPException(status_code=409 if e.user_fixable else 502, detail=str(e))

    return MiniAppAbsenteesResponse(
        status="sent",
        count=count,
        filename=filename,
        message="Fayl Telegram chatingizga yuborildi.",
    )


# ============================================================
# Face ID + davomat
# ============================================================


@router.post("/passport-qr", response_model=MiniAppPassportResponse)
@limiter.limit("30/minute")
def read_passport_qr(
    request: Request,
    body: MiniAppPassportQrRequest,
    _op: MiniAppOperator = Depends(get_operator),
):
    """ID-karta QR matni (native skaner) yoki QR rasmidan pasport ma'lumotlari."""
    try:
        if body.text:
            data = parse_passport_qr_text(body.text)
        else:
            data = decode_passport_qr_image(body.image_b64 or "")
    except PassportQrError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ImportError:
        logger.error("zxing-cpp o'rnatilmagan — QR rasmini o'qib bo'lmaydi")
        raise HTTPException(
            status_code=503,
            detail="QR rasmini o'qish serverda sozlanmagan. Native skaner yoki qo'lda kiritishdan foydalaning.",
        )
    return MiniAppPassportResponse(ps_ser=data.ps_ser, ps_num=data.ps_num, jshshir=data.jshshir)


@router.post("/face-verify", response_model=MiniAppFaceVerifyResponse)
@limiter.limit("30/minute")
def face_verify(
    request: Request,
    body: MiniAppFaceVerifyRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Pasport + selfie tekshiruvi. Davomatga qo'shish mumkin bo'lsa — `verify_ticket`."""
    result = svc.face_verify(
        db,
        op.bot,
        session_id=body.session_id,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
        ps_ser=body.ps_ser,
        ps_num=body.ps_num,
        jshshir=body.jshshir,
        selfie_b64=body.selfie_b64,
    )

    ticket: str | None = None
    selfie_bytes = svc.b64_to_bytes(body.selfie_b64)
    if result.status == "in_smena" and result.can_attend and result.slot and selfie_bytes:
        ticket = issue_verify_ticket(
            telegram_id=op.telegram_user.id,
            student_id=result.slot.student_id,
            session_smena_id=body.session_smena_id,
            region_id=body.region_id,
            score=result.score,
            selfie_sha256=selfie_digest(selfie_bytes),
        )

    return MiniAppFaceVerifyResponse(
        **result.model_dump(exclude={"selfie_b64"}),
        verify_ticket=ticket,
    )


@router.post("/mark-attendance", response_model=BotMarkAttendanceResponse)
def mark_attendance(
    body: MiniAppMarkAttendanceRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Face ID chiptasi bo'yicha talabgorni davomatga qo'shish."""
    try:
        ticket = read_verify_ticket(body.verify_ticket)
    except TicketError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if ticket.telegram_id != op.telegram_user.id:
        raise HTTPException(
            status_code=403, detail="Face ID tasdig'i boshqa foydalanuvchiga tegishli"
        )

    selfie_bytes = svc.b64_to_bytes(body.selfie_b64)
    if selfie_bytes is None or not hmac.compare_digest(
        selfie_digest(selfie_bytes), ticket.selfie_sha256
    ):
        raise HTTPException(
            status_code=400,
            detail="Selfie Face ID'da tekshirilgan rasm bilan mos kelmadi",
        )

    return svc.mark_attendance(
        db,
        op.bot,
        student_id=ticket.student_id,
        session_smena_id=ticket.session_smena_id,
        region_id=ticket.region_id,
        selfie_b64=body.selfie_b64,
        verify_score=ticket.score,
    )


# ============================================================
# Davomatdan olib tashlash
# ============================================================


@router.post("/find-by-jshshir", response_model=BotFindByJshshirResponse)
def find_by_jshshir(
    body: MiniAppFindByJshshirRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Tanlangan smenada davomatda turgan talabgorlarni JShShIR bo'yicha topish."""
    return svc.find_by_jshshir(
        db,
        op.bot,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
        jshshir=body.jshshir,
        only_entered=True,
    )


@router.post("/remove-attendance", response_model=BotRemoveAttendanceResponse)
def remove_attendance(
    body: MiniAppRemoveAttendanceRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    return svc.remove_attendance(
        db,
        op.bot,
        student_id=body.student_id,
        session_smena_id=body.session_smena_id,
        region_id=body.region_id,
    )


# ============================================================
# Chetlatish
# ============================================================


@router.get("/reason-types", response_model=list[BotReasonTypeInfo])
def list_reason_types(
    _op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    return svc.list_reason_types(db)


@router.get("/reasons", response_model=list[BotReasonInfo])
def list_reasons(
    reason_type_id: int | None = Query(default=None),
    _op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    return svc.list_reasons(db, reason_type_id)


@router.post("/find-for-cheat", response_model=BotFindForCheatResponse)
def find_for_cheat(
    body: MiniAppFindForCheatRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """JShShIR bo'yicha butun sessiyada (hali chetlatilmagan) talabgorlarni topish."""
    return svc.find_for_cheat(
        db,
        op.bot,
        session_id=body.session_id,
        region_id=body.region_id,
        jshshir=body.jshshir,
    )


@router.post("/cheating", response_model=BotCheatResponse)
def create_cheating(
    body: MiniAppCheatRequest,
    op: MiniAppOperator = Depends(get_operator),
    db: Session = Depends(get_db),
):
    """Talabgorni chetlatish. `CheatingLog.user_id` = `DAVOMAT_MINIAPP_USER_ID`."""
    service_user = db.get(User, settings.DAVOMAT_MINIAPP_USER_ID)
    if service_user is None:
        logger.error(
            "DAVOMAT_MINIAPP_USER_ID=%s users jadvalida topilmadi",
            settings.DAVOMAT_MINIAPP_USER_ID,
        )
        raise HTTPException(
            status_code=503,
            detail="Davomat ilovasi serverda noto'g'ri sozlangan. Administratorga murojaat qiling.",
        )

    return svc.create_cheating(
        db,
        op.bot,
        student_id=body.student_id,
        session_id=body.session_id,
        region_id=body.region_id,
        reason_id=body.reason_id,
        user_id=int(service_user.id),
    )
