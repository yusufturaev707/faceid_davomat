"""Telegram `davomat_bot` uchun maxsus endpointlar.

Bot backend ga `X-API-Key` orqali kiradi (boshqa endpointlar bilan bir xil
autentifikatsiya). Har bir so'rovda telegram_id orqali bot foydalanuvchisi
DB dan tekshiriladi.

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
     qaytarish (0/1/many). Bot remove-attendance flow uchun ishlatadi.
  7. `/remove-attendance` — tasdiqlangan talabgorni davomatdan olib tashlash
     (Student.is_entered=False). StudentLog tegilmaydi — tarix saqlanadi.

Logikani buzmaslik uchun davomatga qo'shish ham `bulk_create_student_logs`
da ishlatilgan invariantlarga amal qiladi (StudentLog.student_id unique,
first_* faqat birinchi martagina to'ldiriladi).
"""

from __future__ import annotations

import base64
import logging
from datetime import date, datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session
from urllib.parse import quote as _url_quote

from app.config import settings
from app.crud.davomat_bot import get_bot_by_telegram_id
from app.crud.test_session import STATE_KEY_ACTIVE
from app.dependencies import get_current_active_user, get_db
from app.models.cheating_log import CheatingLog
from app.models.reason import Reason
from app.models.reason_type import ReasonType
from app.models.region import Region
from app.models.session_state import SessionState
from app.models.smena import Smena
from app.models.student import Student
from app.models.student_blacklist import StudentBlacklist
from app.models.student_log import StudentLog
from app.models.test_session import TestSession
from app.models.test_session_smena import TestSessionSmena
from app.models.user import User
from app.models.zone import Zone
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
    BotRegionInfo,
    BotRemoveAttendanceRequest,
    BotRemoveAttendanceResponse,
    BotRoleInfo,
    BotSessionStatsResponse,
    BotSmenaInfo,
    BotStudentSlot,
    BotUserResponse,
)
from app.services.davomat_bot_absentees import (
    AbsenteesError,
    build_absentees_excel,
)
from app.services.davomat_bot_stats import BotStatsError, compute_bot_stats

logger = logging.getLogger("faceid.api.davomat_bot")
router = APIRouter()


def _bot_to_user_response(bot) -> BotUserResponse:
    """`DavomatBot` ORM ni javob schemasiga aylantirish."""
    role_info = None
    if bot.role_ref:
        role_info = BotRoleInfo(
            id=int(bot.role_ref.id),
            name=bot.role_ref.name or "",
            key=int(bot.role_ref.key or 0),
        )
    regions: list[BotRegionInfo] = []
    for r in bot.regions:
        if r.region:
            regions.append(
                BotRegionInfo(
                    id=int(r.region.id),
                    name=r.region.name or "",
                    number=int(r.region.number or 0),
                )
            )
    return BotUserResponse(
        id=bot.id,
        fio=bot.fio,
        telegram_id=int(bot.telegram_id),
        is_active=bool(bot.is_active),
        role=role_info,
        regions=regions,
        allowed_region_ids=sorted(bot.allowed_region_ids),
    )


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
    return BotAccessResponse(allowed=True, user=_bot_to_user_response(bot))


@router.get("/ready-sessions", response_model=list[BotReadySessionResponse])
def list_ready_sessions(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Holat `key=4` (ACTIVE / "Tayyor") bo'lgan test sessiyalarni qaytarish."""
    rows = (
        db.execute(
            select(TestSession)
            .join(SessionState, SessionState.id == TestSession.test_state_id)
            .where(SessionState.key == STATE_KEY_ACTIVE)
            .order_by(TestSession.id.desc())
        )
        .scalars()
        .all()
    )

    result: list[BotReadySessionResponse] = []
    for session in rows:
        smenas: list[BotSmenaInfo] = []
        sorted_smenas = sorted(
            session.smenas,
            key=lambda s: (s.day, (s.smena.number if s.smena else 0)),
        )
        for s in sorted_smenas:
            if not s.is_active or not s.smena:
                continue
            smenas.append(
                BotSmenaInfo(
                    id=int(s.id),
                    smena_id=int(s.smena.id),
                    smena_number=int(s.smena.number or 0),
                    smena_name=s.smena.name or "",
                    day=s.day,
                )
            )
        result.append(
            BotReadySessionResponse(
                id=int(session.id),
                name=session.name,
                test_name=session.test.name if session.test else "",
                start_date=session.start_date,
                finish_date=session.finish_date,
                smenas=smenas,
            )
        )
    return result


def _resolve_filter_regions(bot, region_id: int | None) -> set[int]:
    """Bot foydalanuvchisining ruxsat etilgan regionlari kesimida `region_id`
    filtrini qo'llash.

    - `region_id` berilmagan bo'lsa: barcha biriktirilgan regionlar (eski xulq).
    - `region_id` berilgan va biriktirilgan ro'yxatda bor: faqat shu region.
    - `region_id` berilgan, lekin biriktirilmagan: HTTP 403 (xavfsizlik).

    Bot 2+ regionga biriktirilgan foydalanuvchi `/start` da region tanlaganda
    har bir so'rovda shu `region_id` ni yuboradi — backend faqat shu region
    kesimida statistika/excel/qidiruv qaytaradi.
    """
    allowed = bot.allowed_region_ids
    if not allowed:
        raise HTTPException(
            status_code=400, detail="Foydalanuvchiga region biriktirilmagan"
        )
    if region_id is None:
        return allowed
    rid = int(region_id)
    if rid not in allowed:
        raise HTTPException(
            status_code=403,
            detail="Tanlangan region sizga biriktirilmagan",
        )
    return {rid}


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
    bot = get_bot_by_telegram_id(db, telegram_id)
    if not bot:
        raise HTTPException(
            status_code=403,
            detail="Botdan foydalanish ruxsati yo'q",
        )

    allowed = _resolve_filter_regions(bot, region_id)

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
    bot = get_bot_by_telegram_id(db, telegram_id)
    if not bot:
        raise HTTPException(
            status_code=403, detail="Botdan foydalanish ruxsati yo'q"
        )

    allowed = _resolve_filter_regions(bot, region_id)

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
# Face ID + DB validatsiya
# ============================================================


# Kirillcha lotincha lookalike: foydalanuvchi Telegram klaviaturasini almashtirib
# ketsa, "AD" o'rniga "АД" (Cyrillic) kiritishi mumkin. Ko'z bilan bir xil
# bo'lsa-da, URL'ga URL-encoded %D0%90%D0%94 sifatida ketadi va GTSP topa
# olmaydi. Pasport seriyalarida faqat lotin harflari ishlatilgani uchun
# Cyrillic→Latin lookalike map xavfsiz.
_CYRILLIC_TO_LATIN: dict[str, str] = {
    "А": "A",
    "В": "B",
    "С": "C",
    "Е": "E",
    "Н": "H",
    "К": "K",
    "М": "M",
    "О": "O",
    "Р": "P",
    "Т": "T",
    "Х": "X",
    "У": "Y",
    "а": "A",
    "в": "B",
    "с": "C",
    "е": "E",
    "н": "H",
    "к": "K",
    "м": "M",
    "о": "O",
    "р": "P",
    "т": "T",
    "х": "X",
    "у": "Y",
    # Faqat ko'rinishidan bir xil bo'lganlari mapped; qolganlari (Б, Г, Д ...)
    # pasport seriyalarida uchramaydi, lekin Д ni D ga mapping berib ketamiz
    # — chunki Cyrillic Д Latin D ga juda yaqin ishlatiladi.
    "Д": "D",
    "д": "D",
}


def _normalize_ps_ser(value: str) -> str:
    """Kirillcha lookalikelarni lotin harflariga aylantiramiz va uppercase qilamiz."""
    out = []
    for ch in (value or "").strip():
        out.append(_CYRILLIC_TO_LATIN.get(ch, ch))
    return "".join(out).upper()


def _call_gtsp(ps_value: str, imei_value: str) -> tuple[dict | None, str | None]:
    """GTSP API ni chaqirish. (data, err) qaytaradi.

    Xato bo'lganda err — odam o'qiy oladigan, foydalanuvchiga ko'rsatish
    mumkin bo'lgan matn. Diagnostika uchun chaqiruv parametrlari (ps_value
    va imei tail) INFO darajasida log qilinadi.
    """
    if not settings.API_GTSP:
        return None, "API_GTSP sozlamasi topilmadi"

    url = settings.API_GTSP.format(imei_value, ps_value)
    imei_tail = imei_value[-4:] if imei_value else "(empty)"
    logger.info("GTSP request: ps=%s, imei=***%s", ps_value, imei_tail)

    try:
        with httpx.Client(timeout=30, verify=False) as client:
            resp = client.get(url)
            resp.raise_for_status()
            result = resp.json()
    except httpx.HTTPStatusError as e:
        logger.error(
            "GTSP HTTP xatolik: status=%s ps=%s imei_tail=%s",
            e.response.status_code,
            ps_value,
            imei_tail,
        )
        return None, f"GTSP HTTP {e.response.status_code}"
    except Exception as e:
        logger.error(
            "GTSP ulanish xatolik: %s (ps=%s, imei_tail=%s)",
            e,
            ps_value,
            imei_tail,
        )
        return None, "GTSP API ga ulanib bo'lmadi"

    if result.get("status") != 1:
        msg = (result.get("data") or {}).get("message") or "Noma'lum xatolik"
        logger.warning(
            "GTSP status != 1: ps=%s imei_tail=%s msg=%s",
            ps_value,
            imei_tail,
            msg,
        )
        return None, f"GTSP: {msg}"

    data = result.get("data") or {}
    if not data.get("photo"):
        logger.warning(
            "GTSP javobida rasm yo'q: ps=%s imei_tail=%s keys=%s",
            ps_value,
            imei_tail,
            list(data.keys()),
        )
        return None, "GTSP javobida rasm yo'q"
    return data, None


def _build_slot(
    student: Student,
    tss: TestSessionSmena,
    zone: Zone,
    smena: Smena,
    region: Region,
) -> BotStudentSlot:
    fio = " ".join(
        p for p in [student.last_name, student.first_name, student.middle_name] if p
    ).strip()
    return BotStudentSlot(
        student_id=int(student.id),
        fio=fio,
        jshshir=student.imei,
        region_name=region.name if region else None,
        zone_name=zone.name if zone else None,
        test_day=tss.day.isoformat() if (tss and tss.day) else None,
        smena_number=int(tss.number or 0) if tss else None,
        smena_name=smena.name if smena else None,
        gr_n=int(student.gr_n or 0),
        sp_n=int(student.sp_n or 0),
        subject_name=student.subject_name,
        is_applied=bool(student.is_applied),
        is_entered=bool(student.is_entered),
    )


def _lookup_student_in_session(
    db: Session,
    *,
    jshshir: str,
    test_session_id: int,
    session_smena_id: int | None = None,
    region_id: int | None = None,
):
    """Talabani test sessiyasida (yoki aniq smenada/regionda) qidirish.

    `region_id` berilsa, faqat shu region kesimida — bot foydalanuvchi
    region tanlagan bo'lsa, boshqa regiondagi talaba topilmaydi (xuddi
    "smenada yo'q" kabi xulq).

    Qaytaradi: (student, tss, zone, smena, region) yoki None.
    """
    stmt = (
        select(Student, TestSessionSmena, Zone, Smena, Region)
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(Zone, Zone.id == Student.zone_id)
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .join(Region, Region.id == Zone.region_id)
        .where(
            Student.imei == jshshir,
            TestSessionSmena.test_session_id == test_session_id,
        )
    )
    if session_smena_id is not None:
        stmt = stmt.where(Student.session_smena_id == session_smena_id)
    if region_id is not None:
        stmt = stmt.where(Region.id == int(region_id))
    return db.execute(stmt).first()


def _ensure_region_assigned(bot, region_id: int | None) -> int | None:
    """Bot region_id ni yuborgan bo'lsa, biriktirilgan ekanini tekshirish.

    Qaytadi: tasdiqlangan `region_id` yoki `None` (bot region_id yubormagan
    bo'lsa).
    """
    if region_id is None:
        return None
    rid = int(region_id)
    if rid not in bot.allowed_region_ids:
        raise HTTPException(
            status_code=403,
            detail="Tanlangan region sizga biriktirilmagan",
        )
    return rid


@router.post("/face-verify", response_model=BotFaceVerifyResponse)
def bot_face_verify(
    body: BotFaceVerifyRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bot Face ID + DB validatsiya.

    Algoritm:
      1) telegram_id orqali bot foydalanuvchi tekshiriladi.
      2) jshshir tanlangan smenada bormi (Student + TestSessionSmena join).
         - Topilmasa, shu test sessiyasining boshqa smenasida bormi tekshiriladi.
           Topilsa → `wrong_slot` (slot to'ldiriladi).
           Topilmasa → `not_in_session`.
         - Topilsa va `is_applied=True` → `applied`.
      3) GTSP API chaqiriladi (ps_ser+ps_num+jshshir).
         Javob bo'lmasa → `wrong_passport`.
      4) `compare_two_faces` orqali yuz solishtiriladi.
         Yuz topilmasa → `no_face`. Aks holda → `in_smena` + verify natijasi.

    `can_attend=True` faqat: status=`in_smena`, verified=True, is_applied=False,
    is_entered=False.
    """
    from app.services.face_service import compare_two_faces

    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    # Tanlangan region biriktirilgan ekanini tekshirish (xavfsizlik).
    region_filter = _ensure_region_assigned(bot, body.region_id)

    # Cyrillic harflarni Latin'ga normalizatsiya qilamiz — Telegram klaviaturasi
    # АД (Cyrillic) yuborib qo'ysa, GTSP topa olmaydi.
    ps_ser_norm = _normalize_ps_ser(body.ps_ser)
    ps_num_norm = (body.ps_num or "").strip()
    ps_value = f"{ps_ser_norm}{ps_num_norm}"
    imei_value = (body.jshshir or "").strip()

    if ps_ser_norm != (body.ps_ser or "").strip().upper():
        logger.info(
            "ps_ser normalized: %r → %r (telegram_id=%s)",
            body.ps_ser,
            ps_ser_norm,
            body.telegram_id,
        )

    logger.info(
        "Bot face-verify: telegram_id=%s, ps=%s, session=%s, smena=%s",
        body.telegram_id,
        ps_value,
        body.session_id,
        body.session_smena_id,
    )

    # ── 1) Smena/session validatsiyasi ──────────────────────────────────
    current_tss = db.get(TestSessionSmena, body.session_smena_id)
    if current_tss is None or int(current_tss.test_session_id) != int(body.session_id):
        return BotFaceVerifyResponse(
            status="error",
            message="Tanlangan smena yoki sessiya noto'g'ri",
        )

    # ── 2) DB lookup: jshshir shu smenada va tanlangan regionda bormi ──
    matched = _lookup_student_in_session(
        db,
        jshshir=imei_value,
        test_session_id=int(body.session_id),
        session_smena_id=int(body.session_smena_id),
        region_id=region_filter,
    )

    other_slot: BotStudentSlot | None = None
    current_slot: BotStudentSlot | None = None

    if matched is None:
        # Shu sessiyaning boshqa smenasida (yoki regionda) bormi? Aslida
        # "boshqa smena/region" — foydalanuvchiga tushunarli xabar berish
        # uchun region filtrini olib tashlaymiz.
        other = _lookup_student_in_session(
            db,
            jshshir=imei_value,
            test_session_id=int(body.session_id),
        )
        if other is not None:
            other_slot = _build_slot(*other)
            return BotFaceVerifyResponse(
                status="wrong_slot",
                message=(
                    "Talabgor shu test sessiyasida bor, lekin boshqa kun / smena / binoda."
                    " Davomatga qo'shib bo'lmaydi."
                ),
                slot=other_slot,
            )
        # Hech qaerda yo'q — verify ham qilmaymiz: foydalanuvchi xatosi.
        return BotFaceVerifyResponse(
            status="not_in_session",
            message="Bu JShShIR tanlangan test sessiyasida topilmadi.",
        )

    stu, tss, zone, smena, region = matched
    current_slot = _build_slot(stu, tss, zone, smena, region)

    if stu.is_applied:
        return BotFaceVerifyResponse(
            status="applied",
            message=stu.desc_apply
            or "Talabgor to'lovni qaytarish uchun ariza bergan. Testga kirita olmaymiz",
            slot=current_slot,
        )

    # ── 3) GTSP chaqiruvi ───────────────────────────────────────────────
    data, err = _call_gtsp(ps_value, imei_value)
    if err is not None or not data:
        # Foydalanuvchiga GTSP'dan kelgan asl xato xabarini ham ko'rsatamiz —
        # shunda u nima notog'ri ekanini bilib oladi (masalan, JShShIR
        # pasport bilan mos kelmasligi va h.k.).
        detail = err or "Noma'lum xatolik"
        return BotFaceVerifyResponse(
            status="wrong_passport",
            message=(
                "Pasport ma'lumotlari xato kiritildi yoki GTSP'da topilmadi.\n"
                f"Tafsilot: {detail}"
            ),
            slot=current_slot,
        )

    photo_b64 = data.get("photo")

    # ── 4) Yuz solishtirish ─────────────────────────────────────────────
    try:
        verify_resp, _ps_bgr, _lv_bgr = compare_two_faces(photo_b64, body.selfie_b64)
    except HTTPException as e:
        return BotFaceVerifyResponse(
            status="no_face",
            message=str(e.detail),
            slot=current_slot,
        )
    except Exception as e:
        logger.error("compare_two_faces xatolik: %s", e)
        return BotFaceVerifyResponse(
            status="error",
            message=f"Yuz solishtirishda xatolik: {e}",
            slot=current_slot,
        )

    sname = data.get("sname") or ""
    fname = data.get("fname") or ""
    mname = data.get("mname") or ""
    fio_gtsp = (
        " ".join(p for p in [sname, fname, mname] if p).strip() or current_slot.fio
    )

    # 0..1 oraliqdagi cosine score'ni foydalanuvchi/StudentLog uchun 0..100
    # foiz integer ga yaxlitlaymiz. Threshold ham bir xil shkala uchun
    # foizga konvertatsiya qilinadi.
    score_pct = max(0, min(100, round(float(verify_resp.score) * 100)))
    threshold_pct = max(0, min(100, round(float(verify_resp.thresh_score) * 100)))

    return BotFaceVerifyResponse(
        status="in_smena",
        verified=bool(verify_resp.verified),
        score=score_pct,
        threshold=threshold_pct,
        can_attend=bool(verify_resp.verified) and not stu.is_entered,
        fio=fio_gtsp,
        photo_b64=photo_b64,
        selfie_b64=body.selfie_b64,
        message=verify_resp.message,
        slot=current_slot,
    )


# ============================================================
# Davomatga qo'shish
# ============================================================


def _b64_to_bytes(val: str | None) -> bytes | None:
    if not val:
        return None
    try:
        if "," in val and val.index(",") < 80:
            val = val.split(",", 1)[1]
        return base64.b64decode(val)
    except Exception:
        return None


@router.post("/mark-attendance", response_model=BotMarkAttendanceResponse)
def bot_mark_attendance(
    body: BotMarkAttendanceRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bot orqali tasdiqlangan talabani davomatga qo'shish.

    - `Student.is_entered=True` qiladi.
    - `StudentLog` ni UPSERT qiladi (`student_id` unique):
        - mavjud bo'lmasa — `first_captured`/`last_captured`= selfie bytes,
          `first_enter_time`/`last_enter_time`= hozirgi vaqt.
        - mavjud bo'lsa — `last_captured`/`last_enter_time` yangilanadi
          (first_* tegilmaydi).
    - `is_applied=True` bo'lsa — kirita olmaymiz, xato qaytaradi.

    Bot foydalanuvchisi tekshiriladi (telegram_id) — faqat ruxsat berilgan
    foydalanuvchilar yozuv qo'shadi.
    """
    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    region_filter = _ensure_region_assigned(bot, body.region_id)

    student = db.get(Student, body.student_id)
    if not student:
        return BotMarkAttendanceResponse(
            status="not_found", message="Talabgor topilmadi"
        )

    if int(student.session_smena_id) != int(body.session_smena_id):
        return BotMarkAttendanceResponse(
            status="not_found",
            student_id=student.id,
            message="Talabgor tanlangan smenaga tegishli emas",
        )

    # Talabgor tanlangan regionga tegishli ekanini tekshirish
    if region_filter is not None:
        zone = db.get(Zone, student.zone_id) if student.zone_id else None
        if zone is None or int(zone.region_id) != region_filter:
            return BotMarkAttendanceResponse(
                status="not_found",
                student_id=student.id,
                message="Talabgor tanlangan region kesimida emas",
            )

    if student.is_applied:
        return BotMarkAttendanceResponse(
            status="applied",
            student_id=student.id,
            message=student.desc_apply or "Talabgor arizali",
        )

    if student.is_entered:
        # Idempotent — log faqat last_* ni yangilaydi.
        log = db.execute(
            select(StudentLog).where(StudentLog.student_id == student.id)
        ).scalar()
        return BotMarkAttendanceResponse(
            status="already_entered",
            student_id=student.id,
            log_id=int(log.id) if log else None,
            message="Talabgor allaqachon davomatga qo'shilgan",
        )

    selfie_bytes = _b64_to_bytes(body.selfie_b64)
    now = datetime.now(timezone.utc)
    # Bot identification — `score`ga 0-100 foiz yoziladi, `max_score=0`
    # bo'lib qoladi (desktop client test bali bilan ishlatadigan field
    # bilan to'qnash kelmaslik uchun atayin teglamayapmiz).
    verify_score = int(body.verify_score or 0)

    try:
        log = db.execute(
            select(StudentLog).where(StudentLog.student_id == student.id)
        ).scalar()
        if log is None:
            log = StudentLog(
                student_id=student.id,
                first_captured=selfie_bytes,
                last_captured=selfie_bytes,
                first_enter_time=now,
                last_enter_time=now,
                score=verify_score,
                max_score=0,
                is_check_hand=True,
            )
            db.add(log)
        else:
            if log.first_captured is None and selfie_bytes is not None:
                log.first_captured = selfie_bytes
            if selfie_bytes is not None:
                log.last_captured = selfie_bytes
            if log.first_enter_time is None:
                log.first_enter_time = now
            log.last_enter_time = now
            log.is_check_hand = True
            # Score'ni eng yuqori qiymat bilan yangilab boramiz —
            # `bulk_create_student_logs` invariantiga mos.
            if verify_score > (log.score or 0):
                log.score = verify_score

        student.is_entered = True
        db.flush()
        db.commit()
        db.refresh(log)
    except Exception as e:
        db.rollback()
        logger.exception("mark-attendance failed: student_id=%s", body.student_id)
        return BotMarkAttendanceResponse(
            status="error",
            student_id=student.id,
            message=f"Davomatga qo'shishda xatolik: {e}",
        )

    logger.info(
        "Bot mark-attendance OK: telegram_id=%s, student_id=%s, log_id=%s",
        body.telegram_id,
        student.id,
        log.id,
    )
    return BotMarkAttendanceResponse(
        status="ok",
        student_id=student.id,
        log_id=int(log.id),
        message="Talabgor davomatga qo'shildi",
    )


# ============================================================
# Davomatdan olib tashlash (Find by JShShIR + Remove)
# ============================================================


def _list_students_in_smena_by_jshshir(
    db: Session,
    *,
    jshshir: str,
    session_smena_id: int,
    only_entered: bool,
    region_id: int | None = None,
) -> list[tuple[Student, TestSessionSmena, Zone, Smena, Region]]:
    """JShShIR bo'yicha tanlangan smenadagi talabgorlarni qaytaradi.

    Bir JShShIR bilan bitta smenada bir nechta yozuv bo'lishi mumkin
    (turli fan/guruh kombinatsiyalarda) — shuning uchun list qaytaramiz.

    `region_id` berilsa, faqat shu region kesimida.
    """
    stmt = (
        select(Student, TestSessionSmena, Zone, Smena, Region)
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(Zone, Zone.id == Student.zone_id)
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .join(Region, Region.id == Zone.region_id)
        .where(
            Student.imei == jshshir,
            Student.session_smena_id == session_smena_id,
        )
        .order_by(Student.gr_n, Student.sp_n, Student.id)
    )
    if only_entered:
        stmt = stmt.where(Student.is_entered.is_(True))
    if region_id is not None:
        stmt = stmt.where(Region.id == int(region_id))
    return list(db.execute(stmt).all())


@router.post("/find-by-jshshir", response_model=BotFindByJshshirResponse)
def bot_find_by_jshshir(
    body: BotFindByJshshirRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Bot davomatdan olib tashlash flow uchun talabgorlarni topish.

    Faqat tanlangan smenada va (default) `is_entered=True` bo'lganlarni
    qaytaradi. Bir JShShIR bilan bir nechta yozuv chiqsa, bot foydalanuvchiga
    qaysi birini olib tashlashni tanlatadi.
    """
    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    region_filter = _ensure_region_assigned(bot, body.region_id)

    jshshir = (body.jshshir or "").strip()
    rows = _list_students_in_smena_by_jshshir(
        db,
        jshshir=jshshir,
        session_smena_id=body.session_smena_id,
        only_entered=body.only_entered,
        region_id=region_filter,
    )

    if not rows:
        # Talabgor smenada umuman yo'qmi yoki bor-u davomatga qo'shilmaganmi —
        # bot foydalanuvchiga ko'rsatadigan farqlash uchun yana bir tekshiruv.
        if body.only_entered:
            any_rows = _list_students_in_smena_by_jshshir(
                db,
                jshshir=jshshir,
                session_smena_id=body.session_smena_id,
                only_entered=False,
                region_id=region_filter,
            )
            if any_rows:
                return BotFindByJshshirResponse(
                    status="not_found",
                    message=(
                        "Bu JShShIR shu smenada bor, lekin davomatga qo'shilmagan."
                    ),
                )
        return BotFindByJshshirResponse(
            status="not_found",
            message="Bu JShShIR tanlangan smenada topilmadi.",
        )

    matches = [_build_slot(stu, tss, zone, smena, region) for stu, tss, zone, smena, region in rows]
    return BotFindByJshshirResponse(status="ok", matches=matches)


@router.post("/remove-attendance", response_model=BotRemoveAttendanceResponse)
def bot_remove_attendance(
    body: BotRemoveAttendanceRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Tasdiqlangan talabgorni davomatdan olib tashlash.

    Faqat `Student.is_entered` `True → False` ga o'zgartiriladi. StudentLog
    yozuvi tegilmaydi — tarixiy ma'lumotlar (first_captured, score, ...) saqlanadi.
    Talabgor keyinroq qayta qo'shilsa, `last_captured`/`last_enter_time` yangilanadi.
    """
    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    region_filter = _ensure_region_assigned(bot, body.region_id)

    student = db.get(Student, body.student_id)
    if not student:
        return BotRemoveAttendanceResponse(
            status="not_found", message="Talabgor topilmadi"
        )

    if int(student.session_smena_id) != int(body.session_smena_id):
        return BotRemoveAttendanceResponse(
            status="not_found",
            student_id=student.id,
            message="Talabgor tanlangan smenaga tegishli emas",
        )

    if region_filter is not None:
        zone = db.get(Zone, student.zone_id) if student.zone_id else None
        if zone is None or int(zone.region_id) != region_filter:
            return BotRemoveAttendanceResponse(
                status="not_found",
                student_id=student.id,
                message="Talabgor tanlangan region kesimida emas",
            )

    if not student.is_entered:
        return BotRemoveAttendanceResponse(
            status="not_entered",
            student_id=student.id,
            message="Talabgor davomatga qo'shilmagan — olib tashlash kerak emas",
        )

    try:
        student.is_entered = False
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception(
            "remove-attendance failed: student_id=%s", body.student_id
        )
        return BotRemoveAttendanceResponse(
            status="error",
            student_id=student.id,
            message=f"Olib tashlashda xatolik: {e}",
        )

    logger.info(
        "Bot remove-attendance OK: telegram_id=%s, student_id=%s",
        body.telegram_id,
        student.id,
    )
    return BotRemoveAttendanceResponse(
        status="ok",
        student_id=student.id,
        message="Talabgor davomatdan olib tashlandi",
    )


# ============================================================
# Chetlatish (cheating) — turlar/sabablar lookup va kiritish
# ============================================================


@router.get("/reason-types", response_model=list[BotReasonTypeInfo])
def bot_list_reason_types(
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Aktiv chetlatish turlarini qaytarish.

    Bot tomonida foydalanuvchi turini tanlaydi, keyin shu turga tegishli
    sabablardan birini tanlaydi.
    """
    rows = (
        db.execute(
            select(ReasonType)
            .where(ReasonType.is_active.is_(True))
            .order_by(ReasonType.key)
        )
        .scalars()
        .all()
    )
    return [
        BotReasonTypeInfo(id=int(r.id), name=r.name, key=int(r.key or 0))
        for r in rows
    ]


@router.get("/reasons", response_model=list[BotReasonInfo])
def bot_list_reasons(
    reason_type_id: int | None = None,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Aktiv sabablarni qaytarish.

    `reason_type_id` berilsa — faqat shu turga tegishli sabablar; aks holda
    barcha aktiv sabablar.
    """
    stmt = select(Reason).where(Reason.is_active.is_(True))
    if reason_type_id is not None:
        stmt = stmt.where(Reason.reason_type_id == reason_type_id)
    stmt = stmt.order_by(Reason.key)
    rows = db.execute(stmt).scalars().all()
    return [
        BotReasonInfo(
            id=int(r.id),
            reason_type_id=int(r.reason_type_id) if r.reason_type_id else None,
            name=r.name,
            key=int(r.key or 0),
        )
        for r in rows
    ]


def _list_students_in_session_by_jshshir(
    db: Session,
    *,
    jshshir: str,
    test_session_id: int,
    exclude_cheating: bool = True,
    region_id: int | None = None,
) -> list[tuple[Student, TestSessionSmena, Zone, Smena, Region]]:
    """JShShIR bo'yicha butun test sessiyasidagi talabgorlarni qaytaradi.

    `exclude_cheating=True` bo'lsa allaqachon chetlatilganlar (is_cheating=True)
    chiqarib tashlanadi. `region_id` berilsa, faqat shu region kesimida.
    """
    stmt = (
        select(Student, TestSessionSmena, Zone, Smena, Region)
        .join(TestSessionSmena, TestSessionSmena.id == Student.session_smena_id)
        .join(Zone, Zone.id == Student.zone_id)
        .join(Smena, Smena.id == TestSessionSmena.test_smena_id)
        .join(Region, Region.id == Zone.region_id)
        .where(
            Student.imei == jshshir,
            TestSessionSmena.test_session_id == test_session_id,
        )
        .order_by(
            TestSessionSmena.day,
            TestSessionSmena.number,
            Student.gr_n,
            Student.sp_n,
            Student.id,
        )
    )
    if exclude_cheating:
        stmt = stmt.where(Student.is_cheating.is_(False))
    if region_id is not None:
        stmt = stmt.where(Region.id == int(region_id))
    return list(db.execute(stmt).all())


@router.post("/find-for-cheat", response_model=BotFindForCheatResponse)
def bot_find_for_cheat(
    body: BotFindForCheatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """JShShIR bo'yicha tanlangan test sessiyasida talabgorlarni topish
    (chetlatish flow).

    Bir JShShIR sessiyada bir nechta yozuvga ega bo'lishi mumkin (turli
    smenalar/fanlar). Bir nechta bo'lsa, bot foydalanuvchiga tanlatadi.
    """
    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    region_filter = _ensure_region_assigned(bot, body.region_id)

    jshshir = (body.jshshir or "").strip()

    rows = _list_students_in_session_by_jshshir(
        db,
        jshshir=jshshir,
        test_session_id=int(body.session_id),
        exclude_cheating=True,
        region_id=region_filter,
    )
    if rows:
        matches = [
            _build_slot(stu, tss, zone, smena, region)
            for stu, tss, zone, smena, region in rows
        ]
        return BotFindForCheatResponse(status="ok", matches=matches)

    # Topilmadi — chetlatilgan yoki umuman yo'qmi farqlash uchun
    any_rows = _list_students_in_session_by_jshshir(
        db,
        jshshir=jshshir,
        test_session_id=int(body.session_id),
        exclude_cheating=False,
        region_id=region_filter,
    )
    if any_rows:
        # Hammasi allaqachon chetlatilgan
        return BotFindForCheatResponse(
            status="already_cheating",
            message="Bu talabgor allaqachon chetlatilgan.",
        )
    return BotFindForCheatResponse(
        status="not_found",
        message="Bu JShShIR tanlangan test sessiyasida topilmadi.",
    )


@router.post("/cheating", response_model=BotCheatResponse)
def bot_create_cheating(
    body: BotCheatRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_active_user),
):
    """Talabgorni chetlatish (rasmsiz).

    Desktop bulk endpoint bilan bir xil semantika:
      - `CheatingLog` yaratadi: `student_id` (UNIQUE), `reason_id`, `user_id`
        (= API key egasi). `image_path=None` — bot rasmsiz ishlaydi.
      - `Student.is_cheating=True`, `Student.is_blacklist=True`,
        `Student.is_entered=True` (chetlatilgan ham binoga kelgan deb
        hisoblanadi — statistikada Keldi'da turishi uchun).
      - `StudentBlacklist`ga (imei, description=reason.name) insert qilinadi
        (imei UNIQUE — faqat birinchi martagina, idempotent).

    `student_id` allaqachon chetlatilgan bo'lsa, `already_cheating`
    qaytariladi (idempotent — yangi yozuv qo'shilmaydi).
    """
    bot = get_bot_by_telegram_id(db, body.telegram_id)
    if not bot:
        raise HTTPException(status_code=403, detail="Botdan foydalanish ruxsati yo'q")

    region_filter = _ensure_region_assigned(bot, body.region_id)

    student = db.get(Student, body.student_id)
    if not student:
        return BotCheatResponse(status="not_found", message="Talabgor topilmadi")

    # Talabgorning shu sessiyaga tegishliligini tekshirish — XSS/ID-spoof himoyasi.
    tss = db.get(TestSessionSmena, student.session_smena_id)
    if tss is None or int(tss.test_session_id) != int(body.session_id):
        return BotCheatResponse(
            status="wrong_session",
            student_id=student.id,
            message="Talabgor tanlangan test sessiyasiga tegishli emas",
        )

    if region_filter is not None:
        zone = db.get(Zone, student.zone_id) if student.zone_id else None
        if zone is None or int(zone.region_id) != region_filter:
            return BotCheatResponse(
                status="wrong_session",
                student_id=student.id,
                message="Talabgor tanlangan region kesimida emas",
            )

    reason = db.get(Reason, body.reason_id)
    if reason is None or not reason.is_active:
        return BotCheatResponse(
            status="invalid_reason",
            student_id=student.id,
            message="Tanlangan sabab topilmadi yoki aktiv emas",
        )

    if student.is_cheating:
        # Mavjud yozuvni qaytaramiz (idempotent)
        existing = db.execute(
            select(CheatingLog).where(CheatingLog.student_id == student.id)
        ).scalar()
        return BotCheatResponse(
            status="already_cheating",
            student_id=student.id,
            log_id=int(existing.id) if existing else None,
            message="Talabgor allaqachon chetlatilgan",
        )

    try:
        log = CheatingLog(
            student_id=student.id,
            reason_id=int(reason.id),
            user_id=int(_user.id),
            image_path=None,
        )
        db.add(log)
        student.is_cheating = True
        student.is_blacklist = True
        # Chetlatilgan ham binoga kelgan deb hisoblanadi — statistikada
        # Keldi'da turishi uchun is_entered=True qilamiz.
        if not student.is_entered:
            student.is_entered = True

        # StudentBlacklist — imei UNIQUE; faqat birinchi martagina insert
        # qilinadi (keyingi chetlatishlarda tegilmaydi). Imei student'dan
        # olinadi — bot bu yerda alohida JShShIR yubormaydi.
        imei = student.imei
        if imei:
            exists_bl = db.execute(
                select(StudentBlacklist.id).where(StudentBlacklist.imei == imei)
            ).scalar()
            if exists_bl is None:
                db.add(
                    StudentBlacklist(
                        imei=imei,
                        description=reason.name,
                    )
                )

        db.flush()
        db.commit()
        db.refresh(log)
    except Exception as e:
        db.rollback()
        logger.exception(
            "bot create_cheating failed: student_id=%s reason_id=%s",
            body.student_id,
            body.reason_id,
        )
        return BotCheatResponse(
            status="error",
            student_id=student.id,
            message=f"Chetlatishda xatolik: {e}",
        )

    logger.info(
        "Bot chetlatish OK: telegram_id=%s, student_id=%s, reason_id=%s, log_id=%s",
        body.telegram_id,
        student.id,
        reason.id,
        log.id,
    )
    return BotCheatResponse(
        status="ok",
        student_id=student.id,
        log_id=int(log.id),
        message="Talabgor chetlatildi",
    )
