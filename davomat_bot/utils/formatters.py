"""Material design uslubidagi matn formatlovchilar (Telegram MarkdownV2 /HTML).

Sodda emoji + monospace blok bilan chiroyli ko'rsatish. Telegram HTML parse
mode ishlatamiz (escape qulayligi uchun).
"""

from __future__ import annotations

import html


def _esc(value: object) -> str:
    """HTML escape qilingan string."""
    return html.escape(str(value))


def _bar(percent: int, width: int = 12) -> str:
    """Sodda progress bar — Unicode bloklar bilan."""
    percent = max(0, min(100, percent))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def format_sessions_list(sessions: list[dict]) -> str:
    """Sessiya tanlash sahifasi uchun qisqa sarlavha.

    Batafsil info tugmalarning o'zida ko'rsatiladi (`sessiya nomi • sana`),
    shuning uchun bu yerda faqat bitta qator yetarli.
    """
    if not sessions:
        return "ℹ️ Hozircha faol test sessiyalari yo'q."
    return "👇 <b>Faol test sessiyasini tanlang:</b>"


def format_session_header(session: dict) -> str:
    """Bitta sessiya tanlangandagi sarlavha — test nomi va sanalar bilan."""
    name = session.get("name") or "—"
    test_name = session.get("test_name") or "—"
    start = session.get("start_date") or "—"
    finish = session.get("finish_date") or "—"
    return (
        f"📋 <b>{_esc(name)}</b>\n"
        f"📚 <b>Test:</b> {_esc(test_name)}\n"
        f"📅 <b>Sanalar:</b> {_esc(start)} → {_esc(finish)}\n\n"
        f"👇 Kun va smenani tanlang:"
    )


def format_user_greeting(fio: str, regions: list[str]) -> str:
    """Foydalanuvchi xush kelibsiz xabari."""
    rlist = ", ".join(_esc(r) for r in regions) or "—"
    return (
        f"👋 <b>Assalomu alaykum, {_esc(fio)}!</b>\n\n"
        f"🌍 <b>Sizga biriktirilgan viloyatlar:</b> {rlist}\n\n"
    )


def format_session_stats(payload: dict) -> str:
    """Statistika javobini chiroyli card ko'rinishida formatlash.

    `payload.scope` qiymatiga qarab sarlavha o'zgaradi:
      - `"smena"` — sana + smena nomi.
      - `"day"`   — kun yakuni (sana, "Barcha smenalar").
      - `"total"` — butun sessiya bo'yicha.
    """
    test_day = payload.get("test_day") or ""
    smena_name = payload.get("smena_name", "")
    scope = payload.get("scope") or "smena"
    title = payload.get("title") or ""
    regions = payload.get("regions", []) or []

    lines: list[str] = [
        "📊 <b>Davomat statistikasi</b>",
        "━━━━━━━━━━━━━━━━━━━━",
    ]
    if scope == "smena":
        lines.append(f"📅 <b>Sana:</b> {_esc(test_day)}")
        lines.append(f"🕐 <b>Smena:</b> {_esc(smena_name)}")
    elif scope == "day":
        lines.append(f"📅 <b>Sana:</b> {_esc(test_day)}")
        lines.append("🕐 <b>Smena:</b> Barcha smenalar (kun yakuni)")
    else:  # total
        lines.append("📅 <b>Sana:</b> Barcha kunlar")
        lines.append("🕐 <b>Smena:</b> Barcha smenalar")
    if title and scope != "smena":
        lines.append(f"🏷 <b>{_esc(title)}</b>")
    lines.append("")

    if not regions:
        lines.append("⚠️ Ma'lumot topilmadi.")
        return "\n".join(lines)

    for r in regions:
        total = int(r.get("total") or 0)
        entered = int(r.get("entered") or 0)
        not_entered = int(r.get("not_entered") or 0)
        cheating = int(r.get("cheating") or 0)
        pct = round((entered / total) * 100, 1) if total > 0 else 0

        lines.append(f"🏛 <b>{_esc(r.get('region_name', ''))}</b>")
        lines.append(f"   <code>{_bar(pct)}</code>  <b>{pct}%</b>")
        lines.append(
            f"   👥 Jami talabgor: <b>{total}</b> ta   ✅ Keldi: <b>{entered}</b> ta"
        )
        lines.append(
            f"   ⛔ Kelmaganlar: <b>{not_entered}</b> ta   🚫 Chetlatilgan: <b>{cheating}</b> ta"
        )

        zones = r.get("zones") or []
        if zones:
            lines.append("   <i>Binolar:</i>")
            for z in zones:
                z_total = int(z.get("total") or 0)
                z_entered = int(z.get("entered") or 0)
                z_not_entered = int(z.get("not_entered") or 0)
                z_cheating = int(z.get("cheating") or 0)
                z_pct = round((z_entered / z_total) * 100, 1) if z_total > 0 else 0
                lines.append(
                    f"   ▸ <b>{_esc(z.get('zone_name', ''))}</b> "
                    f"— {z_entered}/{z_total} "
                    f"({z_pct}%)  ⛔ {z_not_entered}  🚫 {z_cheating}"
                )
        lines.append("")

    return "\n".join(lines).rstrip()


def format_cheat_picks(matches: list[dict]) -> str:
    """JShShIR sessiyada bir nechta yozuvga ega bo'lganda — chetlatish uchun
    qaysi birini tanlash kerakligini ko'rsatuvchi karta.
    """
    lines = [
        "🚫 <b>Chetlatish — qaysi yozuvni tanlaysiz?</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "Bu JShShIR shu test sessiyasida bir nechta yozuvga ega:",
        "",
    ]
    for i, m in enumerate(matches, 1):
        lines.append(f"<b>{i}.</b> {_format_slot_block(m)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_cheat_slot(slot: dict) -> str:
    """Chetlatish flow'i — tanlangan talabgor ma'lumotini ko'rsatish."""
    return (
        "🚫 <b>Chetlatish</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_format_slot_block(slot)}"
    )


def format_cheat_confirm(slot: dict, type_name: str, reason_name: str) -> str:
    """Yakuniy tasdiqlash kartasi — tanlangan talaba + tur + sabab."""
    return (
        "⚠️ <b>Chetlatishni tasdiqlang</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_format_slot_block(slot)}\n\n"
        f"🏷 <b>Tur:</b> {_esc(type_name)}\n"
        f"📝 <b>Sabab:</b> {_esc(reason_name)}\n\n"
        "Tasdiqlasangiz, ushbu talabgor <b>chetlatiladi</b>."
    )


def format_remove_picks(matches: list[dict]) -> str:
    """Bir nechta talabgor topilganda — qaysi birini tanlash uchun ro'yxat.

    Har bir karta'da: FIO, viloyat, bino, guruh, joy, fan nomi.
    """
    lines = [
        "🔍 <b>Tanlangan smenada bir nechta talabgor topildi</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "Qaysi birini davomatdan olib tashlashni tanlang:",
        "",
    ]
    for i, m in enumerate(matches, 1):
        lines.append(f"<b>{i}.</b> {_format_slot_block(m)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_remove_confirm(slot: dict) -> str:
    """Tasdiqlash kartasi — yakuniy bosqich oldidan ko'rsatiladi."""
    return (
        "⚠️ <b>Davomatdan olib tashlashni tasdiqlang</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{_format_slot_block(slot)}\n\n"
        "Tasdiqlasangiz, ushbu talabgor davomatdan olib tashlanadi "
    )


def _format_slot_block(slot: dict) -> str:
    """Talaba slotini (region/zone/kun/smena/guruh) ko'rinarli formatda chiqarish."""
    fio = slot.get("fio") or "—"
    jshshir = slot.get("jshshir") or "—"
    region = slot.get("region_name") or "—"
    zone = slot.get("zone_name") or "—"
    day = slot.get("test_day") or "—"
    smena_number = slot.get("smena_number")
    smena_name = slot.get("smena_name") or "—"
    gr_n = slot.get("gr_n")
    sp_n = slot.get("sp_n")
    subject = slot.get("subject_name")

    smena_str = (
        f"#{smena_number} • {_esc(smena_name)}" if smena_number else _esc(smena_name)
    )
    lines = [
        f"👤 <b>FIO:</b> {_esc(fio)}",
        f"🆔 <b>JShShIR:</b> <code>{_esc(jshshir)}</code>",
        f"🏛 <b>Viloyat:</b> {_esc(region)}",
        f"🏫 <b>Bino:</b> {_esc(zone)}",
        f"📅 <b>Sana:</b> {_esc(day)}",
        f"🕐 <b>Smena:</b> {smena_str}",
    ]
    if gr_n:
        group_line = f"👥 <b>Guruh:</b> {gr_n}"
        if sp_n:
            group_line += f" • <b>Joy:</b> {sp_n}"
        lines.append(group_line)
    if subject:
        lines.append(f"📚 <b>Fan:</b> {_esc(subject)}")
    return "\n".join(lines)


def _format_verify_block(payload: dict) -> str:
    """Verify natijasi bloki — score/threshold 0-100 foiz integer."""
    verified = bool(payload.get("verified"))
    # Backend endi 0-100 oraliqdagi integer foizini yuboradi.
    score = int(payload.get("score") or 0)
    threshold = int(payload.get("threshold") or 0)
    bar = _bar(score)
    badge = "✅ <b>Yuz tasdiqlandi</b>" if verified else "❌ <b>Yuz tasdiqlanmadi</b>"
    return (
        f"{badge}\n"
        f"📈 <b>O'xshashlik:</b> <code>{bar}</code> <b>{score}%</b>  "
        f"<i>(chegara: {threshold}%)</i>"
    )


def format_face_verify_result(payload: dict, *, jshshir: str | None = None) -> str:
    """Bot Face ID javobini formatlash.

    `payload.status` qiymatiga qarab har xil maket:
      - `in_smena`        — to'liq slot + verify natijasi
      - `wrong_slot`      — boshqa smenadagi slot + verify yo'q
      - `not_in_session`  — qisqa xato
      - `wrong_passport`  — qisqa xato (slot bo'lsa qo'shamiz)
      - `no_face`         — yuz aniqlanmadi
      - `applied`         — talaba arizali
      - `error`           — boshqa xato
    """
    status = payload.get("status", "")
    message = payload.get("message") or ""
    slot = payload.get("slot") or {}
    fio_top = payload.get("fio")

    sep = "━━━━━━━━━━━━━━━━━━━━"

    if status == "in_smena":
        lines = [
            "🪪 <b>Face ID natijasi</b>",
            sep,
            _format_verify_block(payload),
            "",
            "📌 <b>Talabgor ma'lumotlari:</b>",
            _format_slot_block(slot),
        ]
        if message:
            lines.append(f"\n💬 {_esc(message)}")
        if fio_top and fio_top != slot.get("fio"):
            lines.append(f"\n<i>GTSP FIO:</i> {_esc(fio_top)}")
        if slot.get("is_entered"):
            lines.append("\nℹ️ <b>Talabgor allaqachon davomatga qo'shilgan.</b>")
        return "\n".join(lines)

    if status == "wrong_slot":
        lines = [
            "⚠️ <b>Talabgor bu smenada yo'q</b>",
            sep,
            f"💬 {_esc(message)}",
            "",
            "📌 <b>Talabgorning testdagi joyi:</b>",
            _format_slot_block(slot),
            "",
            "ℹ️ Bu holatda davomatga qo'sha olmaymiz.",
        ]
        return "\n".join(lines)

    if status == "not_in_session":
        return (
            "❌ <b>Talabgor bu test sessiyasida yo'q</b>\n\n"
            f"🆔 JShShIR: <code>{_esc(jshshir or '—')}</code>\n\n"
            f"💬 {_esc(message)}"
        )

    if status == "wrong_passport":
        lines = [
            "❌ <b>Pasport ma'lumotlari xato</b>",
            "",
            f"💬 {_esc(message)}",
        ]
        if slot:
            lines += [
                "",
                "📌 <b>Talabgorning testdagi joyi (DB):</b>",
                _format_slot_block(slot),
            ]
        return "\n".join(lines)

    if status == "no_face":
        return (
            "⚠️ <b>Yuz aniqlanmadi</b>\n\n"
            f"{_esc(message)}\n\n"
            "Iltimos, yorqin va to'g'ri yuz ko'rinishini yuboring."
        )

    if status == "applied":
        lines = ["⚠️ <b>Talabgor arizali</b>", "", f"💬 {_esc(message)}"]
        if slot:
            lines += ["", _format_slot_block(slot)]
        return "\n".join(lines)

    # error / unknown
    return f"⚠️ <b>Xatolik:</b> {_esc(message or status)}"
