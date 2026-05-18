"""Face ID flow.

Sessiya+kun+smena tanlangach `Face ID` tugmasidan kiriladi. Foydalanuvchi
2 ta usuldan birini tanlaydi:
  - **Qo'lda kiritish** — ps_ser, ps_num, jshshir bosqichma-bosqich.
  - **QR (ID Card orqasidan)** — bot pasport ma'lumotlarini avtomatik o'qiydi.

Keyin selfie yuboriladi. Backend:
  1) jshshir tanlangan smenada bormi tekshiradi;
  2) GTSP dan pasport rasmini oladi;
  3) `compare_two_faces` orqali yuz solishtiriladi.

Natija:
  - `in_smena` + verified → batafsil ma'lumot + "Davomatga qo'shish" tugmasi.
  - `wrong_slot` → talaba boshqa kun/smena/binoda — info-only, qo'shilmaydi.
  - `not_in_session` / `wrong_passport` / `no_face` / `applied` / `error`
    → mos xabar.
"""

from __future__ import annotations

import base64
import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import (
    attendance_confirm_kb,
    back_to_actions_kb,
    back_to_main_kb,
    cancel_kb,
    faceid_method_kb,
)
from services.api_client import ApiError, api_client
from services.user_state import get_region
from states.faceid import FaceIDManual, FaceIDQR
from utils.callbacks import AttendanceCB, FaceIDMethodCB
from utils.formatters import format_face_verify_result
from utils.qr_decoder import decode_qr_from_bytes

logger = logging.getLogger(__name__)
router = Router(name="faceid")


# Pasport seriya va raqamini birga qabul qilamiz: 2 ta harf + 7 ta raqam.
# Foydalanuvchi `AD2311141`, `ad-2311141`, `AD 2311141` kabi yozsa ham
# yo'l qo'yamiz — bo'shliq/defislardan tozalab keyin tekshiramiz.
_PASSPORT_RE = re.compile(r"^[A-Za-zА-Яа-я]{2}\d{7}$")
_JSHSHIR_RE = re.compile(r"^\d{14}$")

# Cyrillic→Latin lookalike — Uzbek pasport seriyalari faqat lotin harflari bilan
# yoziladi; foydalanuvchi Telegram klaviaturasini almashtirib AD o'rniga АД
# (Cyrillic) yuborib qo'ysa, normalizatsiya GTSP chaqiruvini saqlab qoladi.
_CYR_LAT: dict[str, str] = {
    "А": "A", "В": "B", "С": "C", "Е": "E", "Н": "H", "К": "K",
    "М": "M", "О": "O", "Р": "P", "Т": "T", "Х": "X", "У": "Y",
    "а": "A", "в": "B", "с": "C", "е": "E", "н": "H", "к": "K",
    "м": "M", "о": "O", "р": "P", "т": "T", "х": "X", "у": "Y",
    "Д": "D", "д": "D",
}


def _normalize_ps_ser(value: str) -> str:
    return "".join(_CYR_LAT.get(ch, ch) for ch in (value or "").strip()).upper()


# ───────────────────────────────────────────────────────────────────
# Entry
# ───────────────────────────────────────────────────────────────────


async def faceid_entry(
    cb: CallbackQuery,
    *,
    state: FSMContext,
    session_id: int,
    smena_id: int,
) -> None:
    """`davomat.py` dan chaqiriladi — usulni tanlash ekrani."""
    await state.clear()
    await state.update_data(session_id=session_id, smena_id=smena_id)
    await cb.answer()
    if cb.message is None:
        return
    await cb.message.answer(
        "🪪 <b>Face ID tekshiruvi</b>\n\n"
        "Pasport ma'lumotlarini qanday kiritishni xohlaysiz?",
        parse_mode="HTML",
        reply_markup=faceid_method_kb(session_id, smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# Manual flow
# ───────────────────────────────────────────────────────────────────


@router.callback_query(FaceIDMethodCB.filter(F.method == "manual"))
async def manual_start(
    cb: CallbackQuery, callback_data: FaceIDMethodCB, state: FSMContext
) -> None:
    await cb.answer()
    if cb.message is None:
        return
    await state.update_data(
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
    )
    await state.set_state(FaceIDManual.waiting_passport)
    await cb.message.answer(
        "✍️ <b>1/3 — Pasport seriya va raqamini kiriting</b>\n\n"
        "<i>Bitta qatorda, masalan:</i> <code>AD1234567</code>\n"
        "<i>(2 ta harf + 7 ta raqam)</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(callback_data.session_id, callback_data.smena_id),
    )


@router.message(FaceIDManual.waiting_passport)
async def manual_passport(message: Message, state: FSMContext) -> None:
    """Pasport seriya+raqamini bitta xabarda qabul qilish.

    Bo'shliq/defislar tozalanadi, kirillcha lookalikelar lotin'ga normallashadi,
    keyin `_PASSPORT_RE` bo'yicha tekshiriladi va `ps_ser` (2 harf) + `ps_num`
    (7 raqam) ga ajratiladi.
    """
    data = await state.get_data()
    raw = (message.text or "").strip()
    cleaned = re.sub(r"[\s\-_]", "", raw)

    if not _PASSPORT_RE.match(cleaned):
        await message.answer(
            "⚠️ Noto'g'ri format. Pasport seriya + raqami quyidagicha bo'lishi kerak:\n\n"
            "<b>2 ta harf + 7 ta raqam</b>, masalan: <code>AD2311141</code>",
            parse_mode="HTML",
            reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
        )
        return

    ps_ser = _normalize_ps_ser(cleaned[:2])
    ps_num = cleaned[2:]
    if ps_ser != cleaned[:2].upper():
        logger.info("manual passport normalized: %r → %s%s", raw, ps_ser, ps_num)

    await state.update_data(ps_ser=ps_ser, ps_num=ps_num)
    await state.set_state(FaceIDManual.waiting_jshshir)
    await message.answer(
        f"✅ Qabul qilindi: <code>{ps_ser}{ps_num}</code>\n\n"
        "✍️ <b>2/3 — JShShIR (PINFL) kiriting</b>\n\n"
        "<i>14 ta raqam.</i>",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


@router.message(FaceIDManual.waiting_jshshir)
async def manual_jshshir(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    value = (message.text or "").strip()
    if not _JSHSHIR_RE.match(value):
        await message.answer(
            "⚠️ JShShIR 14 ta raqamdan iborat bo'lishi kerak. Qaytadan kiriting.",
            reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
        )
        return
    await state.update_data(jshshir=value)
    await state.set_state(FaceIDManual.waiting_selfie)
    await message.answer(
        "📸 <b>3/3 — Endi yuzingizning rasmini yuboring</b>\n\n"
        "Iltimos, yorqin va to'g'ri yuz ko'rinishini yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


@router.message(FaceIDManual.waiting_selfie, F.photo)
async def manual_selfie(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _run_face_verify(
        message=message,
        state=state,
        data=data,
    )


@router.message(FaceIDManual.waiting_selfie)
async def manual_selfie_not_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        "⚠️ Iltimos yuzingiz rasmini <b>foto</b> sifatida yuboring (fayl emas).",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


# ───────────────────────────────────────────────────────────────────
# QR flow
# ───────────────────────────────────────────────────────────────────


@router.callback_query(FaceIDMethodCB.filter(F.method == "qr"))
async def qr_start(
    cb: CallbackQuery, callback_data: FaceIDMethodCB, state: FSMContext
) -> None:
    await cb.answer()
    if cb.message is None:
        return
    await state.update_data(
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
    )
    await state.set_state(FaceIDQR.waiting_qr_image)
    await cb.message.answer(
        "📷 <b>ID Card orqasidagi QR kodni yuboring</b>\n\n"
        "QR koddagi pasport ma'lumotlari avtomatik o'qib olinadi.",
        parse_mode="HTML",
        reply_markup=cancel_kb(callback_data.session_id, callback_data.smena_id),
    )


@router.message(FaceIDQR.waiting_qr_image, F.photo)
async def qr_image(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    if not message.photo or message.bot is None:
        return
    photo = message.photo[-1]
    buf = await message.bot.download(photo.file_id)
    if buf is None:
        await message.answer("⚠️ Rasmni yuklab bo'lmadi. Qayta urinib ko'ring.")
        return
    image_bytes = buf.read()

    parsed = decode_qr_from_bytes(image_bytes)
    if not parsed or not (parsed.ps_ser and parsed.ps_num and parsed.jshshir):
        await message.answer(
            "⚠️ QR koddan to'liq ma'lumot o'qib bo'lmadi.\n\n"
            "Iltimos, ID Card <b>orqa tomonidagi</b> QR kodning aniq fotosini yuboring, "
            "yoki qo'lda kiritish usulidan foydalaning.",
            parse_mode="HTML",
            reply_markup=back_to_main_kb(),
        )
        return

    await state.update_data(
        ps_ser=parsed.ps_ser,
        ps_num=parsed.ps_num,
        jshshir=parsed.jshshir,
    )
    await state.set_state(FaceIDQR.waiting_selfie)
    await message.answer(
        f"✅ <b>QR o'qildi</b>\n\n"
        f"📄 Seriya: <code>{parsed.ps_ser}</code>\n"
        f"📄 Raqam: <code>{parsed.ps_num}</code>\n"
        f"🆔 JShShIR: <code>{parsed.jshshir}</code>\n\n"
        f"📸 Endi yuzingizning rasmini yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


@router.message(FaceIDQR.waiting_qr_image)
async def qr_image_not_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        "⚠️ Iltimos QR kodni <b>foto</b> sifatida yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


@router.message(FaceIDQR.waiting_selfie, F.photo)
async def qr_selfie(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await _run_face_verify(
        message=message,
        state=state,
        data=data,
    )


@router.message(FaceIDQR.waiting_selfie)
async def qr_selfie_not_photo(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(
        "⚠️ Iltimos yuzingiz rasmini <b>foto</b> sifatida yuboring.",
        parse_mode="HTML",
        reply_markup=cancel_kb(data.get("session_id", 0), data.get("smena_id", 0)),
    )


# ───────────────────────────────────────────────────────────────────
# Shared verify pipeline
# ───────────────────────────────────────────────────────────────────


async def _run_face_verify(
    *,
    message: Message,
    state: FSMContext,
    data: dict,
) -> None:
    """Selfie ni yuklab, backend `face-verify` ga jo'natib, natijani ko'rsatish.

    Natija statusiga qarab:
      - `in_smena` + can_attend → "Davomatga qo'shish" tugmasi.
      - boshqa hollarda → faqat ma'lumot, qo'shish tugmasi yo'q.
    """
    if message.from_user is None or message.bot is None or not message.photo:
        return

    session_id = int(data.get("session_id") or 0)
    smena_id = int(data.get("smena_id") or 0)
    ps_ser = data.get("ps_ser")
    ps_num = data.get("ps_num")
    jshshir = data.get("jshshir")

    if not (session_id and smena_id and ps_ser and ps_num and jshshir):
        await state.clear()
        await message.answer(
            "⚠️ Sessiya ma'lumotlari yo'qoldi. Qaytadan boshlang.",
            reply_markup=back_to_main_kb(),
        )
        return

    progress = await message.answer("⏳ Yuz solishtirilmoqda...")

    photo = message.photo[-1]
    buf = await message.bot.download(photo.file_id)
    if buf is None:
        await progress.edit_text("⚠️ Selfie ni yuklab bo'lmadi. Qayta urinib ko'ring.")
        return
    selfie_bytes = buf.read()
    selfie_b64 = base64.b64encode(selfie_bytes).decode("ascii")

    try:
        payload = await api_client.face_verify(
            telegram_id=message.from_user.id,
            session_id=session_id,
            session_smena_id=smena_id,
            ps_ser=ps_ser,
            ps_num=ps_num,
            jshshir=jshshir,
            selfie_b64=selfie_b64,
            region_id=get_region(message.from_user.id),
        )
    except ApiError as e:
        logger.error("face-verify error: %s %s", e.status, e.detail)
        await progress.edit_text(
            "⚠️ Tekshirishda server xatoligi. Keyinroq urinib ko'ring.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception("face-verify unexpected: %s", e)
        await progress.edit_text(
            "⚠️ Kutilmagan xatolik. Keyinroq urinib ko'ring.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return

    text = format_face_verify_result(payload, jshshir=jshshir)

    can_attend = bool(payload.get("can_attend"))
    status = payload.get("status")
    slot = payload.get("slot") or {}
    student_id = int(slot.get("student_id") or 0)

    if status == "in_smena" and can_attend and student_id:
        # Selfie va verify foizini keyin mark-attendance ga yuborish uchun
        # saqlaymiz. Score backend tomonida 0-100 integer sifatida keladi.
        verify_score = int(payload.get("score") or 0)
        await state.update_data(
            last_selfie_b64=selfie_b64,
            last_verify_score=verify_score,
        )
        kb = attendance_confirm_kb(
            student_id=student_id,
            session_id=session_id,
            smena_id=smena_id,
        )
        await progress.edit_text(text, parse_mode="HTML", reply_markup=kb)
        # FSM clear qilmaymiz — selfie b64 va score keyingi callbackda kerak.
        return

    # Qolgan barcha holatlarda — davomatga qo'shish tugmasi yo'q
    await state.clear()
    await progress.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=back_to_actions_kb(session_id, smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# Davomatga qo'shish (confirm callback)
# ───────────────────────────────────────────────────────────────────


@router.callback_query(AttendanceCB.filter(F.decision == "no"))
async def attendance_cancel(
    cb: CallbackQuery, callback_data: AttendanceCB, state: FSMContext
) -> None:
    await state.clear()
    await cb.answer("Bekor qilindi")
    if cb.message is None:
        return
    await cb.message.answer(
        "❎ Davomatga qo'shish bekor qilindi.",
        reply_markup=back_to_actions_kb(
            callback_data.session_id, callback_data.smena_id
        ),
    )


@router.callback_query(AttendanceCB.filter(F.decision == "yes"))
async def attendance_confirm(
    cb: CallbackQuery, callback_data: AttendanceCB, state: FSMContext
) -> None:
    await cb.answer("⏳ Qo'shilmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    data = await state.get_data()
    selfie_b64 = data.get("last_selfie_b64")
    verify_score = int(data.get("last_verify_score") or 0)

    try:
        resp = await api_client.mark_attendance(
            telegram_id=cb.from_user.id,
            student_id=callback_data.student_id,
            session_smena_id=callback_data.smena_id,
            selfie_b64=selfie_b64,
            verify_score=verify_score,
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("mark-attendance error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Davomatga qo'shishda server xatoligi.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return
    except Exception as e:
        logger.exception("mark-attendance unexpected: %s", e)
        await cb.message.answer(
            "⚠️ Kutilmagan xatolik.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return
    finally:
        await state.clear()

    status = resp.get("status")
    msg = resp.get("message") or ""

    score_line = (
        f"\n📈 <b>Yuz o'xshashligi:</b> {verify_score}%"
        if verify_score
        else ""
    )

    if status == "ok":
        text = f"✅ <b>Davomatga qo'shildi</b>{score_line}\n\n💬 {msg}"
    elif status == "already_entered":
        text = f"ℹ️ <b>Talabgor allaqachon kirgan</b>\n\n💬 {msg}"
    elif status == "applied":
        text = f"⚠️ <b>Talabgor arizali</b>\n\n💬 {msg}"
    elif status == "not_found":
        text = f"❌ <b>Talabgor topilmadi</b>\n\n💬 {msg}"
    else:
        text = f"⚠️ <b>Xatolik</b>\n\n💬 {msg}"

    await cb.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=back_to_actions_kb(
            callback_data.session_id, callback_data.smena_id
        ),
    )
