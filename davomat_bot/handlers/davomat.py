"""Davomat / Face ID flow.

1) Bosh menyu → "Test sessiyalari" tugmasi → tayyor sessiyalar ro'yxati.
2) Sessiya tanlash → o'sha sessiyaning (kun, smena) ro'yxati.
3) Kun+smena tanlash → "Davomatni olish" va "Face ID" tugmalari.
4) Davomatni olish → biriktirilgan region/zone kesimida statistika.
5) Face ID → `handlers/faceid.py` dagi flow.

Sessiya/smena haqida ma'lumotni FSM state ga emas, callback_data ga
joylaymiz — shunday qilib bot restart bo'lsa ham tugmalar ishlay beradi
(Memory storage). FSM faqat manual/QR kiritish bosqichlarida ishlatiladi.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery

from handlers.faceid import faceid_entry
from keyboards.inline import (
    action_kb,
    aggr_action_kb,
    back_to_main_kb,
    sessions_kb,
    smena_kb,
)
from services.api_client import ApiError, api_client
from services.user_state import get_region
from utils.callbacks import (
    ActionCB,
    AggrActionCB,
    AggrCB,
    BackCB,
    MainMenuCB,
    SessionCB,
    SmenaCB,
)
from utils.formatters import (
    format_session_header,
    format_session_stats,
    format_sessions_list,
)

logger = logging.getLogger(__name__)
router = Router(name="davomat")


async def _show_ready_sessions(cb: CallbackQuery) -> None:
    if cb.message is None:
        return
    try:
        sessions = await api_client.list_ready_sessions()
    except ApiError as e:
        logger.error("ready-sessions error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Sessiyalarni olishda xatolik. Keyinroq urinib ko'ring.",
            reply_markup=back_to_main_kb(),
        )
        return

    if not sessions:
        await cb.message.answer(
            "ℹ️ Hozircha faol test sessiyalari yo'q.",
            reply_markup=back_to_main_kb(),
        )
        return

    await cb.message.answer(
        format_sessions_list(sessions),
        parse_mode="HTML",
        reply_markup=sessions_kb(sessions),
    )


@router.callback_query(MainMenuCB.filter(F.action == "davomat"))
async def show_ready_sessions(cb: CallbackQuery, state: FSMContext) -> None:
    """Bosh menyudagi 'Test sessiyalari' — tayyor sessiyalar."""
    await state.clear()
    await cb.answer()
    await _show_ready_sessions(cb)


@router.callback_query(SessionCB.filter())
async def show_smenas(cb: CallbackQuery, callback_data: SessionCB) -> None:
    """Tanlangan sessiyaning kun+smena ro'yxati."""
    await cb.answer()
    if cb.message is None:
        return

    try:
        sessions = await api_client.list_ready_sessions()
    except ApiError as e:
        logger.error("ready-sessions error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Test tadbiri ma'lumotini olishda xatolik.",
            reply_markup=back_to_main_kb(),
        )
        return

    target = next(
        (s for s in sessions if int(s.get("id", 0)) == callback_data.session_id),
        None,
    )
    if not target:
        await cb.message.answer(
            "ℹ️ Tanlangan test tadbiri topilmadi (statusi o'zgargan bo'lishi mumkin).",
            reply_markup=back_to_main_kb(),
        )
        return

    smenas = target.get("smenas") or []
    if not smenas:
        await cb.message.answer(
            "ℹ️ Bu test tadbirida smena topilmadi.",
            reply_markup=back_to_main_kb(),
        )
        return

    await cb.message.answer(
        format_session_header(target),
        parse_mode="HTML",
        reply_markup=smena_kb(callback_data.session_id, smenas),
    )


@router.callback_query(SmenaCB.filter())
async def show_actions(cb: CallbackQuery, callback_data: SmenaCB) -> None:
    """Kun+smena tanlangach — `Davomatni olish` / `Face ID` tugmalari."""
    await cb.answer()
    if cb.message is None:
        return

    await cb.message.answer(
        "🛠 <b>Quyidagilardan birini tanlang:</b>\n\n"
        "• <b>Davomatni olish</b> — Viloyat/bino kesimida statistika\n"
        "• <b>Kelmaganlar ro'yxatini olish</b> — Excel fayl ko'rinishida\n"
        "• <b>Face ID</b> — pasport + selfi tekshiruvi va davomatga qo'shish\n"
        "• <b>Davomatdan olib tashlash</b> — JShShIR bo'yicha davomatdan chiqarish",
        parse_mode="HTML",
        reply_markup=action_kb(callback_data.session_id, callback_data.smena_id),
    )


def _aggr_intro_text(scope: str, day: str) -> str:
    """Aggregat (kun/sessiya) tanlovi uchun amallar menyusi xabari.

    `day` = `"-"` total scope sentinel — sarlavhada ko'rsatilmaydi.
    """
    if scope == "day" and day and day != "-":
        header = f"📅 <b>{day} — kun yakuni</b>"
    else:
        header = "📊 <b>Umumiy statistika (barcha kunlar)</b>"
    return (
        f"{header}\n\n"
        "🛠 <b>Quyidagilardan birini tanlang:</b>\n\n"
        "• <b>Davomatni olish</b> — Viloyat/bino kesimida umumiy statistika\n"
        "• <b>Kelmaganlar ro'yxatini olish</b> — Excel fayl ko'rinishida"
    )


def _resolve_day(callback_data) -> str | None:
    """`AggrCB`/`AggrActionCB` dagi `day` field'ini API parametriga aylantirish.

    `"-"` sentinel → `None` (total scope); aks holda ISO date stringi qaytadi.
    """
    raw = (callback_data.day or "").strip()
    return raw if raw and raw != "-" else None


@router.callback_query(AggrCB.filter())
async def show_aggr_actions(cb: CallbackQuery, callback_data: AggrCB) -> None:
    """Aggregat (kun yoki butun sessiya) tanlangach amallar menyusini ochish.

    Bu menyuda Face ID va Davomatdan olib tashlash tugmalari yo'q — bu
    operatsiyalar bitta talaba va bitta smena kontekstida ma'noga ega.
    """
    await cb.answer()
    if cb.message is None:
        return

    await cb.message.answer(
        _aggr_intro_text(callback_data.scope, callback_data.day),
        parse_mode="HTML",
        reply_markup=aggr_action_kb(
            scope=callback_data.scope,
            session_id=callback_data.session_id,
            day=callback_data.day,
        ),
    )


@router.callback_query(AggrActionCB.filter(F.action == "stats"))
async def show_aggr_stats(
    cb: CallbackQuery, callback_data: AggrActionCB
) -> None:
    """Kun yoki sessiya bo'yicha umumiy statistika."""
    await cb.answer("⏳ Statistika tayyorlanmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        payload = await api_client.get_session_stats(
            session_id=callback_data.session_id,
            telegram_id=cb.from_user.id,
            test_day=_resolve_day(callback_data),
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("aggr stats error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Statistikani olishda xatolik.",
            reply_markup=aggr_action_kb(
                scope=callback_data.scope,
                session_id=callback_data.session_id,
                day=callback_data.day,
            ),
        )
        return

    await cb.message.answer(
        format_session_stats(payload),
        parse_mode="HTML",
        reply_markup=aggr_action_kb(
            scope=callback_data.scope,
            session_id=callback_data.session_id,
            day=callback_data.day,
        ),
    )


@router.callback_query(AggrActionCB.filter(F.action == "absent"))
async def send_aggr_absentees_excel(
    cb: CallbackQuery, callback_data: AggrActionCB
) -> None:
    """Kun yoki butun sessiya bo'yicha kelmaganlar ro'yxatini Excel yuborish."""
    await cb.answer("⏳ Excel tayyorlanmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        file_bytes, filename, count = await api_client.get_absentees_excel(
            session_id=callback_data.session_id,
            telegram_id=cb.from_user.id,
            test_day=_resolve_day(callback_data),
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("aggr absentees-xlsx error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Kelmaganlar ro'yxatini olishda xatolik. Keyinroq urinib ko'ring.",
            reply_markup=aggr_action_kb(
                scope=callback_data.scope,
                session_id=callback_data.session_id,
                day=callback_data.day,
            ),
        )
        return

    day_value = _resolve_day(callback_data)
    if callback_data.scope == "day" and day_value:
        scope_label = f"{day_value} kuni bo'yicha"
    else:
        scope_label = "barcha kunlar bo'yicha"
    caption = (
        f"📥 <b>Kelmaganlar ro'yxati</b> ({scope_label})\n"
        f"👥 Jami: <b>{count}</b> ta talabgor"
    )
    await cb.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=caption,
        parse_mode="HTML",
        reply_markup=aggr_action_kb(
            scope=callback_data.scope,
            session_id=callback_data.session_id,
            day=callback_data.day,
        ),
    )


@router.callback_query(ActionCB.filter(F.action == "stats"))
async def show_session_stats(cb: CallbackQuery, callback_data: ActionCB) -> None:
    """Tanlangan kun+smena bo'yicha statistikani ko'rsatish."""
    await cb.answer("⏳ Statistika tayyorlanmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        payload = await api_client.get_session_stats(
            session_id=callback_data.session_id,
            telegram_id=cb.from_user.id,
            session_smena_id=callback_data.smena_id,
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("session-stats error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Statistikani olishda xatolik.",
            reply_markup=back_to_main_kb(),
        )
        return

    await cb.message.answer(
        format_session_stats(payload),
        parse_mode="HTML",
        reply_markup=action_kb(callback_data.session_id, callback_data.smena_id),
    )


@router.callback_query(ActionCB.filter(F.action == "absent"))
async def send_absentees_excel(
    cb: CallbackQuery, callback_data: ActionCB
) -> None:
    """Tanlangan kun+smena bo'yicha kelmaganlar ro'yxatini Excel ko'rinishida yuborish."""
    await cb.answer("⏳ Excel tayyorlanmoqda...")
    if cb.message is None or cb.from_user is None:
        return

    try:
        file_bytes, filename, count = await api_client.get_absentees_excel(
            session_id=callback_data.session_id,
            telegram_id=cb.from_user.id,
            session_smena_id=callback_data.smena_id,
            region_id=get_region(cb.from_user.id),
        )
    except ApiError as e:
        logger.error("absentees-xlsx error: %s %s", e.status, e.detail)
        await cb.message.answer(
            "⚠️ Kelmaganlar ro'yxatini olishda xatolik. Keyinroq urinib ko'ring.",
            reply_markup=action_kb(
                callback_data.session_id, callback_data.smena_id
            ),
        )
        return

    caption = (
        f"📥 <b>Kelmaganlar ro'yxati</b>\n"
        f"👥 Jami: <b>{count}</b> ta talabgor"
    )
    await cb.message.answer_document(
        BufferedInputFile(file_bytes, filename=filename),
        caption=caption,
        parse_mode="HTML",
        reply_markup=action_kb(
            callback_data.session_id, callback_data.smena_id
        ),
    )


@router.callback_query(ActionCB.filter(F.action == "faceid"))
async def goto_faceid(
    cb: CallbackQuery, callback_data: ActionCB, state: FSMContext
) -> None:
    """Face ID flow ga o'tish (`handlers/faceid.py`)."""
    await faceid_entry(
        cb,
        state=state,
        session_id=callback_data.session_id,
        smena_id=callback_data.smena_id,
    )


# === Orqaga qaytish handlerlari ===


@router.callback_query(BackCB.filter(F.to == "sessions"))
async def back_to_sessions(cb: CallbackQuery, state: FSMContext) -> None:
    """Smena tanlash sahifasidan sessiyalar ro'yxatiga qaytish."""
    await state.clear()
    await cb.answer()
    await _show_ready_sessions(cb)


@router.callback_query(BackCB.filter(F.to == "smenas"))
async def back_to_smenas(
    cb: CallbackQuery, callback_data: BackCB, state: FSMContext
) -> None:
    """Amallar / Face ID method sahifasidan smenalar ro'yxatiga qaytish."""
    await state.clear()
    # SessionCB handler'ini qayta ishlatamiz
    await show_smenas(cb, SessionCB(session_id=callback_data.session_id))


@router.callback_query(BackCB.filter(F.to == "actions"))
async def back_to_actions(
    cb: CallbackQuery, callback_data: BackCB, state: FSMContext
) -> None:
    """Face ID method yoki verify natijasidan amallar menyusiga qaytish."""
    await state.clear()
    await show_actions(
        cb,
        SmenaCB(
            session_id=callback_data.session_id,
            smena_id=callback_data.smena_id,
        ),
    )
