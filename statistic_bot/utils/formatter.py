"""Statistika ma'lumotlarini chiroyli HTML matnga aylantiruvchi formatter.

Yil DINAMIK: hech qayerda qotib qolmagan. Tashqi API kalitlari
`count_<yil>` ko'rinishida — joriy/o'tgan yil ma'lumotdan avtomatik
aniqlanadi (`_detect_years`). Shu tufayli keyingi mavsumda (2027, ...)
kod o'zgartirilmaydi.
"""
from __future__ import annotations

import datetime
import re

LINE = "━━━━━━━━━━━━━━━━━━━━━"
TG_LIMIT = 4096  # Telegram bitta xabar limiti

_YEAR_KEY_RE = re.compile(r"^count_(\d{4})$")


def _detect_years(data: list[dict]) -> tuple[int, int]:
    """Ma'lumotdan joriy va o'tgan yilni aniqlaydi (eng katta = joriy)."""
    years: set[int] = set()
    for row in data:
        for k in row.keys():
            m = _YEAR_KEY_RE.match(k)
            if m:
                years.add(int(m.group(1)))
    if years:
        cur = max(years)
        below = [y for y in years if y < cur]
        return cur, (max(below) if below else cur - 1)
    now = datetime.datetime.now().year
    return now, now - 1


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


def _format_prev_block(data: list[dict], prev_year: int) -> list[str]:
    """Faqat ruxsatlilar uchun: o'tgan yil ma'lumotlari (alohida blok)."""
    py = str(prev_year)
    count = total(data, f"count_{py}")
    male = total(data, f"male_{py}")
    female = total(data, f"female_{py}")
    graduated = total(data, f"graduated_{py}")
    graduated_not = count - graduated
    paid = total(data, f"paid_{py}")
    unpaid = count - paid

    block = []
    block.append(f"📅 <b>{prev_year}-yil ma'lumotlari</b>")
    block.append(f"🖥 Ro'yxatdan o'tganlar:  <b>{fmt(count)}</b> nafar")
    block.append("")
    block.append(f" <b>Shundan:</b>")
    block.append(f"🎓 Joriy yil bitiruvchilari:  <b>{fmt(graduated)}</b>")
    block.append(f"🔹 Avvalgi yil bitiruvchilari:  <b>{fmt(graduated_not)}</b>")
    block.append("")
    block.append(f"🙎🏻‍♂️ Erkaklar:  <b>{fmt(male)}</b>  ({pct(male, count):.1f}%)")
    block.append(f"🙍🏻‍♀️ Ayollar:  <b>{fmt(female)}</b>  ({pct(female, count):.1f}%)")
    block.append("")
    block.append(f"✅ To'lov qilganlar:  <b>{fmt(paid)}</b>  ({pct(paid, count):.1f}%)")
    block.append(f"❌ To'l qilmaganlar:  <b>{fmt(unpaid)}</b>")
    block.append("")
    return block


def format_summary(data: list[dict], show_prev: bool = False) -> str:
    """Umumiy statistika + viloyatlar ro'yxati (bitta matn).

    Yil dinamik aniqlanadi. `show_prev=True` bo'lsa (Admin/Rahbar) to'lov
    holati va o'tgan yil bloki ham qo'shiladi.
    """
    year, prev_year = _detect_years(data)
    cy, py = str(year), str(prev_year)

    count_now = total(data, f"count_{cy}")
    count_prev = total(data, f"count_{py}")
    male = total(data, f"male_{cy}")
    female = total(data, f"female_{cy}")
    graduated = total(data, f"graduated_{cy}")
    graduated_not = total(data, f"graduated_not_{cy}")
    paid = total(data, f"paid_{cy}")
    unpaid = count_now - paid
    uz = total(data, f"uz_{cy}")
    ru = total(data, f"ru_{cy}")
    qq = total(data, f"qq_{cy}")
    other = total(data, f"lang_other_{cy}")

    now = datetime.datetime.now().strftime("%d.%m.%Y  %H:%M")

    s = []
    s.append("📊 <b>ABITURIYENTLAR STATISTIKASI</b>")
    s.append(f"🎓 <b>{year}-{year + 1} o'quv yili qabuli</b>")
    s.append(LINE)

    s.append("🖥 <b>Ro'yxatdan o'tganlar</b>")
    s.append(f"       <b>{fmt(count_now)}</b> nafar")
    s.append(f"      {_trend(count_now, count_prev)}")
    s.append(f"      <i>{prev_year}-yil: {fmt(count_prev)} nafar</i>")
    s.append("")

    s.append("🎓 <b>Shundan:</b>")
    s.append(f"🔹 Joriy yil bitiruvchilari:  <b>{fmt(graduated)}</b>")
    s.append(f"🔹 Avvalgi yil bitiruvchilari:  <b>{fmt(graduated_not)}</b>")
    s.append("")

    s.append("👥 <b>Jins bo'yicha taqsimot</b>")
    s.append(f"🙎🏻‍♂️ Erkaklar:  <b>{fmt(male)}</b>  ({pct(male, count_now):.1f}%)")
    s.append(f"      {bar(male, count_now)}")
    s.append(f"🙍🏻‍♀️ Ayollar:  <b>{fmt(female)}</b>  ({pct(female, count_now):.1f}%)")
    s.append(f"      {bar(female, count_now)}")
    s.append("")

    if show_prev:
        s.append("💳 <b>To'lov holati</b>")
        s.append(f"✅ To'lov qilganlar:  <b>{fmt(paid)}</b>  ({pct(paid, count_now):.1f}%)")
        s.append(f"⏳ To'lov qilmaganlar:  <b>{fmt(unpaid)}</b>")
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

    ranked = sorted(data, key=lambda r: _int(r.get(f"count_{cy}")), reverse=True)
    medals = {0: "🥇", 1: "🥈", 2: "🥉"}
    for i, r in enumerate(ranked):
        marker = medals.get(i, f"{i + 1}.")
        name = r.get("region_name", "Noma'lum")
        cnt = _int(r.get(f"count_{cy}"))
        share = pct(cnt, count_now)
        s.append(f"{i + 1}. <b>{name}</b> — {fmt(cnt)} nafar ({share:.1f}%)")

    s.append("--------------------------------")
    s.append("")
    if show_prev:
        s.extend(_format_prev_block(data, prev_year))

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
