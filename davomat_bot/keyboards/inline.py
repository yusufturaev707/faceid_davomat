"""Inline keyboardlar — bot menyu va tanlovlar."""

from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.callbacks import (
    ActionCB,
    AggrActionCB,
    AggrCB,
    AttendanceCB,
    BackCB,
    CheatConfirmCB,
    CheatPickCB,
    CheatReasonCB,
    CheatTypeCB,
    FaceIDMethodCB,
    MainMenuCB,
    RegionPickCB,
    RemoveConfirmCB,
    RemovePickCB,
    SessionCB,
    SmenaCB,
)


def main_menu_kb(can_change_region: bool = False) -> InlineKeyboardMarkup:
    """Bosh menyu — `Davomatni olish` (sessiyalar ro'yxatiga kirish).

    `can_change_region=True` (foydalanuvchi 2+ regionga biriktirilgan)
    bo'lsa, qo'shimcha "Regionni almashtirish" tugmasi ko'rsatiladi.
    """
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📋 Faol test tadbirlari ro'yxati",
        callback_data=MainMenuCB(action="davomat").pack(),
    )
    if can_change_region:
        kb.button(
            text="🔄 Regionni almashtirish",
            callback_data=MainMenuCB(action="change_region").pack(),
        )
    kb.adjust(1)
    return kb.as_markup()


def region_pick_kb(regions: list[dict]) -> InlineKeyboardMarkup:
    """Region tanlash tugmalari (bot 2+ regionga biriktirilgan holatda).

    Har bir tugma `RegionPickCB(region_id=...)` ni packlaydi.
    """
    kb = InlineKeyboardBuilder()
    # `number` bo'yicha sortlash — natijada barqaror tartib.
    sorted_regions = sorted(
        regions, key=lambda r: (int(r.get("number") or 0), r.get("name") or "")
    )
    for r in sorted_regions:
        kb.button(
            text=f"🏛 {r.get('name', '')}",
            callback_data=RegionPickCB(region_id=int(r["id"])).pack(),
        )
    kb.adjust(1)
    return kb.as_markup()


def sessions_kb(sessions: list[dict]) -> InlineKeyboardMarkup:
    """Tayyor sessiyalarni tugmalar shaklida ko'rsatish."""
    kb = InlineKeyboardBuilder()
    for s in sessions:
        kb.button(
            text=f"📋 {s['name']}",
            callback_data=SessionCB(session_id=int(s["id"])).pack(),
        )
    kb.button(text="🔙 Orqaga", callback_data=BackCB(to="main").pack())
    kb.adjust(1)
    return kb.as_markup()


def smena_kb(session_id: int, smenas: list[dict]) -> InlineKeyboardMarkup:
    """Smena + kun tanlash.

    Har bir kun smenalaridan keyin shu kunning "Umumiy" tugmasi (barcha
    smenalar bo'yicha aggregat). Eng oxirida — butun sessiya bo'yicha
    "Umumiy statistika" tugmasi.

    Smenalar `day` bo'yicha guruhlanadi va backend `list_ready_sessions`
    natijasida sortlangan tartibda (kun, smena_number) keladi — shu
    invariantga tayanamiz.
    """
    kb = InlineKeyboardBuilder()
    current_day: str | None = None
    for s in smenas:
        day_str = str(s["day"])
        if current_day is not None and day_str != current_day:
            # Avvalgi kun guruhi tugadi — kunlik aggregat tugmasi
            kb.button(
                text=f"📅 {current_day} — Umumiy",
                callback_data=AggrCB(
                    scope="day", session_id=session_id, day=current_day
                ).pack(),
            )
        kb.button(
            text=f"📅 {day_str} • {s['smena_name']} (#{s['smena_number']})",
            callback_data=SmenaCB(
                session_id=session_id, smena_id=int(s["id"])
            ).pack(),
        )
        current_day = day_str
    # Oxirgi kun uchun aggregat tugma
    if current_day is not None:
        kb.button(
            text=f"📅 {current_day} — Umumiy",
            callback_data=AggrCB(
                scope="day", session_id=session_id, day=current_day
            ).pack(),
        )
    # Sessiya bo'yicha umumiy aggregat (day = "-" sentinel)
    kb.button(
        text="📊 Umumiy statistika (barcha kunlar)",
        callback_data=AggrCB(
            scope="total", session_id=session_id, day="-"
        ).pack(),
    )
    kb.button(
        text="🔙 Test tadbirlariga qaytish",
        callback_data=BackCB(to="sessions").pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def action_kb(session_id: int, smena_id: int) -> InlineKeyboardMarkup:
    """Smena tanlangach — keyingi amal: statistika / Face ID / olib tashlash."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📊 Davomatni olish",
        callback_data=ActionCB(
            action="stats", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="📥 Kelmaganlar ro'yxatini olish",
        callback_data=ActionCB(
            action="absent", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🪪 Face ID",
        callback_data=ActionCB(
            action="faceid", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🗑 Davomatdan olib tashlash",
        callback_data=ActionCB(
            action="remove", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🚫 Chetlatish",
        callback_data=ActionCB(
            action="cheat", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🔙 Smenalarga qaytish",
        callback_data=BackCB(
            to="smenas", session_id=session_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def cheat_picks_kb(
    matches: list[dict], session_id: int, smena_id: int
) -> InlineKeyboardMarkup:
    """JShShIR bo'yicha sessiyada bir nechta talabgor topilganda — qaysi
    birini chetlatishni tanlash uchun ro'yxat.
    """
    kb = InlineKeyboardBuilder()
    for i, m in enumerate(matches, 1):
        gr = m.get("gr_n") or "—"
        sp = m.get("sp_n") or "—"
        subj = m.get("subject_name") or ""
        if len(subj) > 18:
            subj = subj[:17] + "…"
        label = f"{i}. 👥 #{gr} • 🪑 {sp}"
        if subj:
            label += f" • 📚 {subj}"
        kb.button(
            text=label,
            callback_data=CheatPickCB(
                student_id=int(m["student_id"]),
                session_id=session_id,
                smena_id=smena_id,
            ).pack(),
        )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def cheat_types_kb(
    types: list[dict],
    student_id: int,
    session_id: int,
    smena_id: int,
) -> InlineKeyboardMarkup:
    """Chetlatish turlarini tanlash uchun tugmalar."""
    kb = InlineKeyboardBuilder()
    for t in types:
        name = t.get("name") or "—"
        if len(name) > 50:
            name = name[:49] + "…"
        kb.button(
            text=f"🏷 {name}",
            callback_data=CheatTypeCB(
                type_id=int(t["id"]),
                student_id=student_id,
                session_id=session_id,
                smena_id=smena_id,
            ).pack(),
        )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def cheat_reasons_kb(
    reasons: list[dict],
    student_id: int,
    session_id: int,
    smena_id: int,
) -> InlineKeyboardMarkup:
    """Tanlangan tur ichidagi sabablar — sabab tanlash uchun tugmalar."""
    kb = InlineKeyboardBuilder()
    for r in reasons:
        name = r.get("name") or "—"
        if len(name) > 50:
            name = name[:49] + "…"
        kb.button(
            text=f"• {name}",
            callback_data=CheatReasonCB(
                reason_id=int(r["id"]),
                student_id=student_id,
                session_id=session_id,
                smena_id=smena_id,
            ).pack(),
        )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def cheat_confirm_kb(
    student_id: int, reason_id: int, session_id: int, smena_id: int
) -> InlineKeyboardMarkup:
    """Chetlatishni yakuniy tasdiqlash."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Ha, chetlatilsin",
        callback_data=CheatConfirmCB(
            decision="yes",
            student_id=student_id,
            reason_id=reason_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="❌ Bekor qilish",
        callback_data=CheatConfirmCB(
            decision="no",
            student_id=student_id,
            reason_id=reason_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def aggr_action_kb(
    scope: str, session_id: int, day: str = "-"
) -> InlineKeyboardMarkup:
    """Aggregat (kun yoki sessiya) tanlovi uchun amallar menyusi.

    Faqat: Davomatni olish + Kelmaganlar ro'yxati. Face ID va davomatdan
    olib tashlash bu yerda ma'noga ega emas — bitta talabaga ishlovchi
    amallar bo'lib, ular alohida smena kontekstida bajariladi.

    `day` qiymati: "YYYY-MM-DD" (day scope) yoki `"-"` (total scope).
    """
    safe_day = day or "-"
    kb = InlineKeyboardBuilder()
    kb.button(
        text="📊 Davomatni olish",
        callback_data=AggrActionCB(
            action="stats", scope=scope, session_id=session_id, day=safe_day
        ).pack(),
    )
    kb.button(
        text="📥 Kelmaganlar ro'yxatini olish",
        callback_data=AggrActionCB(
            action="absent", scope=scope, session_id=session_id, day=safe_day
        ).pack(),
    )
    kb.button(
        text="🔙 Smenalarga qaytish",
        callback_data=BackCB(to="smenas", session_id=session_id).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def remove_picks_kb(
    matches: list[dict], session_id: int, smena_id: int
) -> InlineKeyboardMarkup:
    """JShShIR bo'yicha bir nechta talabgor topilganda — qaysi birini
    olib tashlashni tanlash uchun ro'yxat tugmalari.

    Tugmaning matni qisqa bo'ladi (guruh #N • joy N • fan) — to'liq tafsilot
    xabar matnida ko'rsatiladi.
    """
    kb = InlineKeyboardBuilder()
    for i, m in enumerate(matches, 1):
        gr = m.get("gr_n") or "—"
        sp = m.get("sp_n") or "—"
        subj = m.get("subject_name") or ""
        # Tugma matni cheklangan; juda uzun bo'lib ketmasligi uchun fan nomini
        # 20 belgigacha qisqartiramiz.
        if len(subj) > 20:
            subj = subj[:19] + "…"
        label = f"{i}. 👥 #{gr} • 🪑 {sp}"
        if subj:
            label += f" • 📚 {subj}"
        kb.button(
            text=label,
            callback_data=RemovePickCB(
                student_id=int(m["student_id"]),
                session_id=session_id,
                smena_id=smena_id,
            ).pack(),
        )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def remove_confirm_kb(
    student_id: int, session_id: int, smena_id: int
) -> InlineKeyboardMarkup:
    """Davomatdan olib tashlashni yakuniy tasdiqlash."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Ha, olib tashlansin",
        callback_data=RemoveConfirmCB(
            decision="yes",
            student_id=student_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="❌ Bekor qilish",
        callback_data=RemoveConfirmCB(
            decision="no",
            student_id=student_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def faceid_method_kb(session_id: int, smena_id: int) -> InlineKeyboardMarkup:
    """Face ID — pasport kiritish usulini tanlash."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✍️ Pasportni qo'lda kiritish",
        callback_data=FaceIDMethodCB(
            method="manual", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="📷 ID Card QR kodini yuborish",
        callback_data=FaceIDMethodCB(
            method="qr", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🔙 Orqaga",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def attendance_confirm_kb(
    student_id: int, session_id: int, smena_id: int
) -> InlineKeyboardMarkup:
    """Verify ✓ + smenada bor — "Davomatga qo'shish" / "Bekor qilish"."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="✅ Davomatga qo'shish",
        callback_data=AttendanceCB(
            decision="yes",
            student_id=student_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="❌ Bekor qilish",
        callback_data=AttendanceCB(
            decision="no",
            student_id=student_id,
            session_id=session_id,
            smena_id=smena_id,
        ).pack(),
    )
    kb.button(
        text="🔙 Bosh menyu",
        callback_data=BackCB(to="main").pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def back_to_actions_kb(session_id: int, smena_id: int) -> InlineKeyboardMarkup:
    """Verify natijasidan keyin (qo'shish kerak emas) — amallar menyusiga qaytish."""
    kb = InlineKeyboardBuilder()
    kb.button(
        text="🔙 Amallarga qaytish",
        callback_data=BackCB(
            to="actions", session_id=session_id, smena_id=smena_id
        ).pack(),
    )
    kb.button(
        text="🏠 Bosh menyu",
        callback_data=BackCB(to="main").pack(),
    )
    kb.adjust(1)
    return kb.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Bosh menyu", callback_data=BackCB(to="main").pack())
    return kb.as_markup()


def cancel_kb(session_id: int = 0, smena_id: int = 0) -> InlineKeyboardMarkup:
    """FSM ichidan bekor qilish — amallar menyusiga (yoki bosh menyu)."""
    kb = InlineKeyboardBuilder()
    if session_id and smena_id:
        kb.button(
            text="❌ Bekor qilish",
            callback_data=BackCB(
                to="actions", session_id=session_id, smena_id=smena_id
            ).pack(),
        )
    else:
        kb.button(text="❌ Bekor qilish", callback_data=BackCB(to="main").pack())
    return kb.as_markup()
