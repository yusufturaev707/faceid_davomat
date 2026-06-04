"""Statistika ma'lumotlarini chiroyli HTML matnga aylantiruvchi formatter."""
from __future__ import annotations

import datetime

CURRENT_YEAR = 2026
PREV_YEAR = 2025
LINE = "━━━━━━━━━━━━━━━━━━━━━"
TG_LIMIT = 4096  # Telegram bitta xabar limiti


def _int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def fmt(n) -> str:
    """Sonni bo'shliq bilan ajratib formatlaydi: 12345 -> '12 345'."""
    return f"{_int(n):,}".replace(",", " ")


def pct(part, whole) -> float:
    part, whole = _int(part), _int(whole)
    return (part / whole * 100) if whole else 0.0


def bar(value, total, length: int = 12) -> str:
    """Foizni vizual progress-bar ko'rinishida chizadi."""
    p = pct(value, total)
    filled = max(0, min(length, round(p / 100 * length)))
    return "▰" * filled + "▱" * (length - filled)


def total(data: list[dict], key: str) -> int:
    return sum(_int(r.get(key)) for r in data)


def _trend(now: int, prev: int) -> str:
    diff = now - prev
    if diff > 0:
        text = f"📈 +{fmt(diff)}"
    elif diff < 0:
        text = f"📉 {fmt(diff)}"
    else:
        return "➖ o'tgan yilga nisbatan o'zgarishsiz"
    if prev:
        text += f"  ({pct(diff, prev):+.1f}%)"
    return text + "  <i>(o'tgan yilga nisbatan)</i>"


def format_summary(data: list[dict]) -> str:
    """Umumiy statistika + viloyatlar ro'yxati (bitta matn)."""
    count_now = total(data, "count_2026")
    count_prev = total(data, "count_2025")
    male = total(data, "male_2026")
    female = total(data, "female_2026")
    graduated = total(data, "graduated_2026")
    graduated_not = total(data, "graduated_not_2026")
    paid = total(data, "paid_2026")
    unpaid = count_now - paid
    uz = total(data, "uz_2026")
    ru = total(data, "ru_2026")
    qq = total(data, "qq_2026")
    other = total(data, "lang_other_2026")

    now = datetime.datetime.now().strftime("%d.%m.%Y  %H:%M")

    s = []
    s.append("📊 <b>ABITURIYENTLAR STATISTIKASI</b>")
    s.append(f"🎓 <b>{PREV_YEAR}-{CURRENT_YEAR} o'quv yili qabuli</b>")
    s.append(LINE)

    s.append("🖥 <b>Ro'yxatdan o'tganlar</b>")
    s.append(f"      <b>{fmt(count_now)}</b> nafar")
    s.append(f"      {_trend(count_now, count_prev)}")
    s.append(f"      <i>{PREV_YEAR}-yil: {fmt(count_prev)} nafar</i>")
    s.append("")

    s.append("👥 <b>Jinsi bo'yicha taqsimot</b>")
    s.append(f"🙎🏻‍♂️ Erkaklar:  <b>{fmt(male)}</b>  ({pct(male, count_now):.1f}%)")
    s.append(f"      {bar(male, count_now)}")
    s.append(f"🙍🏻‍♀️ Ayollar:  <b>{fmt(female)}</b>  ({pct(female, count_now):.1f}%)")
    s.append(f"      {bar(female, count_now)}")
    s.append("")

    s.append("🎓 <b>Bitiruv yili bo'yicha</b>")
    s.append(f"🔹 Joriy yil bitiruvchilari:  <b>{fmt(graduated)}</b>")
    s.append(f"🔹 Avvalgi yillar:  <b>{fmt(graduated_not)}</b>")
    s.append("")

    s.append("💳 <b>To'lov holati</b>")
    s.append(f"✅ To'lov qilganlar:  <b>{fmt(paid)}</b>  ({pct(paid, count_now):.1f}%)")
    s.append(f"⏳ To'lanmaganlar:  <b>{fmt(unpaid)}</b>")
    s.append("")

    s.append("📚 <b>Ta'lim tili bo'yicha</b>")
    s.append(f"🇺🇿 O'zbek:  <b>{fmt(uz)}</b>  ({pct(uz, count_now):.1f}%)")
    s.append(f"🇷🇺 Rus:  <b>{fmt(ru)}</b>  ({pct(ru, count_now):.1f}%)")
    s.append(f"📗 Qoraqalpoq:  <b>{fmt(qq)}</b>  ({pct(qq, count_now):.1f}%)")
    s.append(f"🌐 Boshqa:  <b>{fmt(other)}</b>  ({pct(other, count_now):.1f}%)")
    s.append("")

    s.append(LINE)
    s.append("📍 <b>Hududlar bo'yicha taqsimot</b>")
    s.append("")

    ranked = sorted(data, key=lambda r: _int(r.get("count_2026")), reverse=True)
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    for i, r in enumerate(ranked):
        marker = medals.get(i, f"{i + 1}.")
        name = r.get("region_name", "Noma'lum")
        cnt = _int(r.get("count_2026"))
        share = pct(cnt, count_now)
        s.append(f"{marker} <b>{name}</b> — {fmt(cnt)} nafar ({share:.1f}%)")
        s.append(
            f"      🙎🏻‍♂️ {fmt(r.get('male_2026'))}  "
            f"🙍🏻‍♀️ {fmt(r.get('female_2026'))}  |  "
            f"🇺🇿 {fmt(r.get('uz_2026'))}  🇷🇺 {fmt(r.get('ru_2026'))}  "
            f"📗 {fmt(r.get('qq_2026'))}"
        )

    s.append("")
    s.append(f"🕔 <i>{now} holatiga</i>")
    return "\n".join(s)


def split_message(text: str, limit: int = TG_LIMIT) -> list[str]:
    """Uzun matnni Telegram limitiga moslab qator chegarasidan bo'laklarga bo'ladi."""
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks
