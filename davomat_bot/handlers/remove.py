"""Davomatdan olib tashlash flow.

Smena tanlangach action menyuda 3-tugma — "🗑 Davomatdan olib tashlash".

Qadam-baqadam:
  1) Foydalanuvchi JShShIR (14 ta raqam) kiritadi.
  2) Backend `find-by-jshshir` ni chaqiramiz — faqat tanlangan smenadagi
     va hozir davomatda turgan talabgorlar.
     - 0 → "Talabgor topilmadi" yoki "Davomatga qo'shilmagan" xabari.
     - 1 → to'g'ridan-to'g'ri tasdiqlash kartasi.
     - 2+ → talabgorlar ro'yxati (FIO/viloyat/bino/guruh/joy/fan), tanlash.
  3) Tasdiqlash: "✅ Ha, olib tashlansin" / "❌ Bekor qilish".
  4) Tasdiq → backend `remove-attendance` (`Student.is_entered=False`).

StudentLog tegilmaydi — tarixiy yozuv saqlanadi.
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
    remove_confirm_kb,
    remove_picks_kb,
)
from services.api_client import ApiError, api_client
from services.user_state import get_region
from states.remove import RemoveAttendance
from utils.callbacks import ActionCB, RemoveConfirmCB, RemovePickCB
from utils.formatters import format_remove_confirm, format_remove_picks

logger = logging.getLogger(__name__)
router = Router(name="remove")

_JSHSHIR_RE = re.compile(r"^\d{14}$")


# ───────────────────────────────────────────────────────────────────
# Entry — action menyudan "Davomatdan olib tashlash"
# ───────────────────────────────────────────────────────────────────


@router.callback_query(ActionCB.filter(F.action == "remove"))
async def remove_entry(
    cb: CallbackQuery, callback_data: ActionCB, state: FSMContext
) -> None:
    await state.clear()
    await state.update_data(
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
    )
    await state.set_state(RemoveAttendance.waiting_jshshir)
    await cb.answer()
    if cb.message is None:
        return
    await cb.message.answer(
        "🗑 <b>Davomatdan olib tashlash</b>\n\n"
        "✍️ JShShIR (PINFL) kiriting — <i>14 ta raqam</i>.\n\n"
        "Talabgor faqat tanlangan smenada qidiriladi.",
        parse_mode="HTML",
        reply_markup=cancel_kb(callback_data.session_id, callback_data.smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# JShShIR qabul qilish → backend qidiruvi
# ───────────────────────────────────────────────────────────────────


@router.message(RemoveAttendance.waiting_jshshir)
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
        resp = await api_client.find_by_jshshir(
            telegram_id=message.from_user.id,
            session_smena_id=smena_id,
            jshshir=value,
            only_entered=True,
            region_id=get_region(message.from_user.id),
        )
    except ApiError as e:
        logger.error("find-by-jshshir error: %s %s", e.status, e.detail)
        await message.answer(
            "⚠️ Server xatoligi. Keyinroq urinib ko'ring.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return
    except Exception as e:
        logger.exception("find-by-jshshir unexpected: %s", e)
        await message.answer(
            "⚠️ Kutilmagan xatolik.",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        await state.clear()
        return

    status = resp.get("status")
    matches = resp.get("matches") or []
    msg = resp.get("message") or ""

    if status == "not_found" or not matches:
        await state.clear()
        await message.answer(
            f"ℹ️ {msg or 'Talabgor topilmadi.'}",
            reply_markup=back_to_actions_kb(session_id, smena_id),
        )
        return

    if len(matches) == 1:
        # To'g'ridan-to'g'ri tasdiqlash sahifasi.
        slot = matches[0]
        await state.clear()
        await message.answer(
            format_remove_confirm(slot),
            parse_mode="HTML",
            reply_markup=remove_confirm_kb(
                student_id=int(slot["student_id"]),
                session_id=session_id,
                smena_id=smena_id,
            ),
        )
        return

    # 2+ ta — qaysi birini olib tashlashni tanlash.
    # Matches'larni FSM data'da keshlaymiz — pick callback'i ularni qayta
    # ko'rsatish uchun ishlatadi (memory storage bot restart bo'lsa kesh
    # yo'qoladi va fallback ishga tushadi).
    await state.set_state(None)
    await state.update_data(
        session_id=session_id,
        smena_id=smena_id,
        matches=matches,
    )
    await message.answer(
        format_remove_picks(matches),
        parse_mode="HTML",
        reply_markup=remove_picks_kb(matches, session_id, smena_id),
    )


# ───────────────────────────────────────────────────────────────────
# Bir nechta yozuvdan tanlash → tasdiqlash sahifasi
# ───────────────────────────────────────────────────────────────────


@router.callback_query(RemovePickCB.filter())
async def remove_pick(
    cb: CallbackQuery, callback_data: RemovePickCB, state: FSMContext
) -> None:
    """Talabgorlar ro'yxatidan bittasi tanlandi — tasdiqlash kartasini ko'rsatish."""
    await cb.answer()
    if cb.message is None or cb.from_user is None:
        return

    data = await state.get_data()
    matches = data.get("matches") or []
    slot = next(
        (m for m in matches if int(m.get("student_id", 0)) == callback_data.student_id),
        None,
    )

    if slot is not None:
        text = format_remove_confirm(slot)
    else:
        # FSM kesh yo'qolgan (bot restart yoki eski xabar). Backend qaytadan
        # so'rashga JShShIR kerak — biz uni saqlamaganmiz. Shuning uchun
        # minimal karta bilan davom etamiz; backend remove-attendance shartlari
        # `session_smena_id` + `student_id` orqali xavfsizlikni saqlaydi.
        text = (
            "⚠️ <b>Davomatdan olib tashlashni tasdiqlang</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Talabgor ID: <code>{callback_data.student_id}</code>\n\n"
            "Tasdiqlasangiz, ushbu talabgor davomatdan olib tashlanadi "
        )

    await cb.message.answer(
        text,
        parse_mode="HTML",
        reply_markup=remove_confirm_kb(
            student_id=callback_data.student_id,
            session_id=callback_data.session_id,
            smena_id=callback_data.smena_id,
        ),
    )


# ───────────────────────────────────────────────────────────────────
# Tasdiqlash → backend remove-attendance
# ───────────────────────────────────────────────────────────────────


@router.callback_query(RemoveConfirmCB.filter(F.decision == "no"))
async def remove_cancel(
    cb: CallbackQuery, callback_data: RemoveConfirmCB, state: FSMContext
) -> None:
    await state.clear()
    await cb.answer("Bekor qilindi")
    if cb.message is None:
        return
    await cb.message.answer(
        "❎ Olib tashlash bekor qilindi.",
        reply_markup=back_to_actions_kb(
            callback_data.session_id, callback_data.smena_id
        ),
    )


@router.callback_query(RemoveConfirmCB.filter(F.decision == "yes"))
async def remove_confirm(
    cb: CallbackQuery, callback_data: RemoveConfirmCB, state: FSMContext
) -> None:
    await state.clear()
    await cb.answer("⏳ Olib tashlanmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        resp = await api_client.remove_attendance(
            telegram_id=cb.from_user.id,
            student_id=callback_data.student_id,
            session_smena_id=callback_data.smena_id,
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("remove-attendance error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Server xatoligi.",
            reply_markup=back_to_actions_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return
    except Exception as e:
        logger.exception("remove-attendance unexpected: %s", e)
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
        text = f"✅ <b>Muvaffaqiyatli bajarildi</b>\n\n💬 {msg}"
    elif status == "not_entered":
        text = f"ℹ️ <b>Talabgor davomatda emas edi</b>\n\n💬 {msg}"
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
