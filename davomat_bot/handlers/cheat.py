"""Chetlatish (cheating / disqualification) flow.

Smena tanlangach action menyuda "🚫 Chetlatish" tugmasi.

Qadam-baqadam:
  1) Foydalanuvchi JShShIR (14 ta raqam) kiritadi.
  2) Backend `find-for-cheat` ni chaqiramiz — butun sessiya bo'yicha
     (smena bilan cheklanmaymiz), faqat `is_cheating=False` bo'lganlar.
     - 0 → "Talabgor topilmadi" yoki "Allaqachon chetlatilgan".
     - 1 → to'g'ridan-to'g'ri chetlatish turi tanlashga o'tamiz.
     - 2+ → talabgorlar ro'yxati (FIO/viloyat/bino/guruh/joy/fan), tanlash.
  3) Chetlatish turini tanlash (reason_type).
  4) Tanlangan tur ichida sababni (reason) tanlash.
  5) Tasdiqlash: "✅ Ha, chetlatilsin" / "❌ Bekor qilish".
  6) Tasdiq → backend `cheating`. Bot rasmsiz ishlaydi.

CheatingLog backend tomonida `student_id` UNIQUE — qayta urinishda
`already_cheating` qaytariladi (idempotent).
"""

from __future__ import annotations

import logging
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.inline import (
    back_to_actions_kb,
    cancel_kb,
    cheat_confirm_kb,
    cheat_picks_kb,
    cheat_reasons_kb,
    cheat_types_kb,
)
from services.api_client import ApiError, api_client
from services.user_state import get_region
from states.cheat import CheatFlow
from utils.callbacks import (
    ActionCB,
    CheatConfirmCB,
    CheatPickCB,
    CheatReasonCB,
    CheatTypeCB,
)
from utils.formatters import (
    format_cheat_confirm,
    format_cheat_picks,
    format_cheat_slot,
)

logger = logging.getLogger(__name__)
router = Router(name="cheat")

_JSHSHIR_RE = re.compile(r"^\d{14}$")


# ───────────────────────────────────────────────────────────────────
# Entry — action menyudan "Chetlatish"
# ───────────────────────────────────────────────────────────────────


@router.callback_query(ActionCB.filter(F.action == "cheat"))
async def cheat_entry(
    cb: CallbackQuery, callback_data: ActionCB, state: FSMContext
) -> None:
    await state.clear()
    await state.update_data(
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
    )
    await state.set_state(CheatFlow.waiting_jshshir)
    await cb.answer()
    if cb.message is None:
        return
    await cb.message.answer(
        "🚫 <b>Chetlatish</b>\n\n"
        "✍️ JShShIR (PINFL) kiriting — <i>14 ta raqam</i>.\n\n"
        "Talabgor butun test sessiyasi bo'yicha qidiriladi.",
        parse_mode="HTML",
        reply_markup=cancel_kb(callback_data.session_id, callback_data.smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# JShShIR qabul qilish → backend qidiruvi
# ───────────────────────────────────────────────────────────────────


async def _show_types_for_student(
    target_msg: Message,
    *,
    telegram_id: int,
    student_id: int,
    session_id: int,
    smena_id: int,
    slot: dict,
) -> None:
    """Tanlangan talabgor uchun chetlatish turlarini ko'rsatish."""
    try:
        types = await api_client.list_reason_types()
    except ApiError as e:
        logger.error("reason-types error: %s %s", e.status, e.detail)
        await target_msg.answer(
            "⚠️ Chetlatish turlarini olishda xatolik.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        return
    if not types:
        await target_msg.answer(
            "ℹ️ Aktiv chetlatish turlari topilmadi.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        return

    await target_msg.answer(
        format_cheat_slot(slot) + "\n\n🏷 <b>Chetlatish turini tanlang:</b>",
        parse_mode="HTML",
        reply_markup=cheat_types_kb(types, student_id, session_id, smena_id),
    )


@router.message(CheatFlow.waiting_jshshir)
async def receive_jshshir(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    session_id = int(data.get("session_id") or 0)
    smena_id = int(data.get("smena_id") or 0)

    value = (message.text or "").strip()
    if not _JSHSHIR_RE.match(value):
        await message.answer(
            "⚠️ JShShIR 14 ta raqamdan iborat bo'lishi kerak. Qaytadan kiriting.",
            reply_markup=cancel_kb(session_id, smena_id),
        )
        return

    if not (session_id and smena_id):
        await state.clear()
        await message.answer(
            "⚠️ Sessiya ma'lumotlari yo'qoldi. Qaytadan boshlang.",
            reply_markup=cancel_kb(),
        )
        return

    if message.from_user is None:
        return

    try:
        resp = await api_client.find_for_cheat(
            telegram_id=message.from_user.id,
            session_id=session_id,
            jshshir=value,
            region_id=get_region(message.from_user.id),
        )
    except ApiError as e:
        logger.error("find-for-cheat error: %s %s", e.status, e.detail)
        await message.answer(
            "⚠️ Server xatoligi. Keyinroq urinib ko'ring.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception("find-for-cheat unexpected: %s", e)
        await message.answer(
            "⚠️ Kutilmagan xatolik.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return

    status = resp.get("status")
    matches = resp.get("matches") or []
    msg = resp.get("message") or ""

    if status == "already_cheating":
        await state.clear()
        await message.answer(
            f"ℹ️ {msg or 'Talabgor allaqachon chetlatilgan.'}",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        return

    if status == "not_found" or not matches:
        await state.clear()
        await message.answer(
            f"ℹ️ {msg or 'Talabgor topilmadi.'}",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        return

    if len(matches) == 1:
        # FSM ni reset qilamiz, lekin tanlangan slotni keshda saqlaymiz —
        # keyingi qadamlar (tur tanlash → sabab tanlash → tasdiqlash) shu
        # slot bo'yicha karta tuzadi. Aks holda tasdiqlashda FIO/viloyat/bino
        # "-" bo'lib chiqadi.
        slot = matches[0]
        await state.set_state(None)
        await state.update_data(
            session_id=session_id,
            smena_id=smena_id,
            matches=matches,
            selected_slot=slot,
        )
        await _show_types_for_student(
            message,
            telegram_id=message.from_user.id,
            student_id=int(slot["student_id"]),
            session_id=session_id,
            smena_id=smena_id,
            slot=slot,
        )
        return

    # 2+ ta yozuv — tanlash uchun ro'yxat. Matches'larni FSM data'da keshlaymiz.
    await state.set_state(None)
    await state.update_data(
        session_id=session_id,
        smena_id=smena_id,
        matches=matches,
    )
    await message.answer(
        format_cheat_picks(matches),
        parse_mode="HTML",
        reply_markup=cheat_picks_kb(matches, session_id, smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# Bir nechta yozuvdan tanlash → tur tanlashga o'tish
# ───────────────────────────────────────────────────────────────────


@router.callback_query(CheatPickCB.filter())
async def cheat_pick(
    cb: CallbackQuery, callback_data: CheatPickCB, state: FSMContext
) -> None:
    await cb.answer()
    if cb.message is None or cb.from_user is None:
        return

    data = await state.get_data()
    matches = data.get("matches") or []
    slot = next(
        (
            m
            for m in matches
            if int(m.get("student_id", 0)) == callback_data.student_id
        ),
        None,
    )
    if slot is None:
        # Kesh yo'qolgan — minimal slot yaratamiz; backend `cheating`
        # endpointi `session_id` orqali xavfsizlikni saqlaydi.
        slot = {"student_id": callback_data.student_id, "fio": "—"}

    # Tanlangan slotni keshda saqlab qo'yamiz — keyingi qadamlarda
    # (tur → sabab → tasdiqlash) shu slot bo'yicha karta tuziladi.
    await state.update_data(selected_slot=slot)

    await _show_types_for_student(
        cb.message,  # type: ignore[arg-type]
        telegram_id=cb.from_user.id,
        student_id=callback_data.student_id,
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
        slot=slot,
    )


# ───────────────────────────────────────────────────────────────────
# Tur tanlandi → sabablarni ko'rsatish
# ───────────────────────────────────────────────────────────────────


@router.callback_query(CheatTypeCB.filter())
async def cheat_type_picked(
    cb: CallbackQuery, callback_data: CheatTypeCB, state: FSMContext
) -> None:
    await cb.answer()
    if cb.message is None:
        return

    try:
        reasons = await api_client.list_reasons(
            reason_type_id=callback_data.type_id
        )
    except ApiError as e:
        logger.error("reasons error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Sabablarni olishda xatolik.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return

    if not reasons:
        await cb.message.answer(
            "ℹ️ Bu tur uchun aktiv sabab topilmadi.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return

    # Tur nomini keyingi qadamga olib o'tish uchun keshlaymiz
    try:
        all_types = await api_client.list_reason_types()
        type_name = next(
            (t.get("name", "") for t in all_types if int(t["id"]) == callback_data.type_id),
            "",
        )
    except Exception:
        type_name = ""
    await state.update_data(cheat_type_name=type_name)

    header = "📝 <b>Sababni tanlang:</b>"
    if type_name:
        header = f"🏷 <b>Tur:</b> {type_name}\n\n{header}"
    await cb.message.answer(
        header,
        parse_mode="HTML",
        reply_markup=cheat_reasons_kb(
            reasons,
            student_id=callback_data.student_id,
            session_id=callback_data.session_id,
            smena_id=callback_data.smena_id,
        ),
    )


# ───────────────────────────────────────────────────────────────────
# Sabab tanlandi → tasdiqlash kartasi
# ───────────────────────────────────────────────────────────────────


@router.callback_query(CheatReasonCB.filter())
async def cheat_reason_picked(
    cb: CallbackQuery, callback_data: CheatReasonCB, state: FSMContext
) -> None:
    await cb.answer()
    if cb.message is None or cb.from_user is None:
        return

    # Talabgor slotini va tur nomini keshdan olamiz. Avval `selected_slot`'ni
    # (single-match yoki cheat_pick orqali tanlangan), keyin matches ro'yxatini
    # (fallback) sinab ko'ramiz.
    data = await state.get_data()
    slot = data.get("selected_slot")
    if not slot or int(slot.get("student_id", 0)) != callback_data.student_id:
        matches = data.get("matches") or []
        slot = next(
            (
                m
                for m in matches
                if int(m.get("student_id", 0)) == callback_data.student_id
            ),
            None,
        ) or {"student_id": callback_data.student_id, "fio": "—"}

    # Sabab nomini olamiz (faqat ko'rsatish uchun)
    reason_name = ""
    try:
        reasons = await api_client.list_reasons()
        reason_name = next(
            (
                r.get("name", "")
                for r in reasons
                if int(r["id"]) == callback_data.reason_id
            ),
            "",
        )
    except Exception:
        reason_name = ""

    type_name = data.get("cheat_type_name") or ""

    await cb.message.answer(
        format_cheat_confirm(slot, type_name=type_name, reason_name=reason_name),
        parse_mode="HTML",
        reply_markup=cheat_confirm_kb(
            student_id=callback_data.student_id,
            reason_id=callback_data.reason_id,
            session_id=callback_data.session_id,
            smena_id=callback_data.smena_id,
        ),
    )


# ───────────────────────────────────────────────────────────────────
# Tasdiqlash → backend cheating
# ───────────────────────────────────────────────────────────────────


@router.callback_query(CheatConfirmCB.filter(F.decision == "no"))
async def cheat_cancel(
    cb: CallbackQuery, callback_data: CheatConfirmCB, state: FSMContext
) -> None:
    await state.clear()
    await cb.answer("Bekor qilindi")
    if cb.message is None:
        return
    await cb.message.answer(
        "❎ Chetlatish bekor qilindi.",
        reply_markup=back_to_actions_kb(
            callback_data.session_id, callback_data.smena_id
        ),
    )


@router.callback_query(CheatConfirmCB.filter(F.decision == "yes"))
async def cheat_confirm(
    cb: CallbackQuery, callback_data: CheatConfirmCB, state: FSMContext
) -> None:
    await state.clear()
    await cb.answer("⏳ Chetlatilmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        resp = await api_client.create_cheating(
            telegram_id=cb.from_user.id,
            student_id=callback_data.student_id,
            session_id=callback_data.session_id,
            reason_id=callback_data.reason_id,
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("cheating error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Server xatoligi.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return
    except Exception as e:
        logger.exception("cheating unexpected: %s", e)
        await cb.message.answer(
            "⚠️ Kutilmagan xatolik.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return

    status = resp.get("status")
    msg = resp.get("message") or ""

    if status == "ok":
        text = f"✅ <b>Talabgor chetlatildi</b>\n\n💬 {msg}"
    elif status == "already_cheating":
        text = f"ℹ️ <b>Talabgor allaqachon chetlatilgan</b>\n\n💬 {msg}"
    elif status == "invalid_reason":
        text = f"⚠️ <b>Sabab xato</b>\n\n💬 {msg}"
    elif status == "wrong_session":
        text = f"❌ <b>Sessiya nomos kelmadi</b>\n\n💬 {msg}"
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
