"""Davomat statistikasini Telegram xabariga aylantirish («Davomatni guruhga yuborish»).

Mini App tugmasi bosilganda ayni vaqtdagi statistika bot nomidan foydalanuvchi
chatiga HTML xabar bo'lib keladi — u uni guruhga forward qiladi. Shuning uchun
xabar o'zi-o'zini tushuntirishi kerak: test, sana, smena, viloyat yakuni va
(viloyatda bir nechta faol bino bo'lsa) har bir bino. Inline tugma yo'q
(forward'da ma'nosiz).

Ko'rinishi:

    📊 DAVOMAT HISOBOTI

    🗂 Test tadbiri nomi
    📝 Imtihon nomi (to'liq)

    📅 10-oktabr, 2026-yil · Shanba
    🕘 1-smena

    📍 BUXORO VILOYATI
    ┃ ▰▰▰▰▰▰▰▰▰▱ 93,4%            (blockquote)
    ┃ 👥 Jami: 3 450
    ┃ ✅ Keldi: 3 210
    ┃ ❌ Kelmadi: 240
    🏢 Binolar · 2 ta
    ├ 🟢 1-bino
    │    ✅ 196/200 · 98% · ❌ 4
    └ 🔴 3-bino
         ✅ 70/100 · 70% · ❌ 30

    ━━━━━━━━━━━━
    🕒 Yuborildi: 10.10.2026 · 10:42

Telegram bitta xabarga 4096 belgi beradi — binolar ko'p bo'lsa hisobot bir
necha xabarga bo'linadi, har biri «1/2» belgisi va sarlavha bilan.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.test import Test
from app.models.test_session import TestSession
from app.schemas.davomat_bot import (
    BotRegionStat,
    BotSessionStatsResponse,
    BotZoneStat,
)
from app.services.davomat_bot_stats import BotStatsError, compute_bot_stats

UZ_TZ = timezone(timedelta(hours=5))

# Telegram limiti 4096 — HTML teglari ham hisobga kiradi; zaxira bilan.
MESSAGE_LIMIT = 3800

_MONTHS = (
    "yanvar", "fevral", "mart", "aprel", "may", "iyun",
    "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr",
)
_WEEKDAYS = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")

# Bino satrlari daraxt ko'rinishida — viloyat ichidagi bino ekani bilinsin.
_BRANCH, _LAST, _PIPE, _GAP = "├ ", "└ ", "│     ", "      "


def _esc(text: str) -> str:
    """Telegram HTML uchun — faqat `<`, `>`, `&` (apostrof `&#x27;` bo'lib qolmasin)."""
    return html.escape(text or "", quote=False)


def _num(value: int) -> str:
    """`12345` → `12 345`."""
    return f"{value:,}".replace(",", " ")


def _percent(part: int, total: int) -> float:
    return round(part * 100 / total, 1) if total else 0.0


def _pct(value: float) -> str:
    """`94.4` → `94,4%`, `100.0` → `100%`."""
    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text.replace('.', ',')}%"


def _status_dot(percent: float) -> str:
    if percent >= 95:
        return "🟢"
    if percent >= 80:
        return "🟡"
    return "🔴"


def _progress_bar(percent: float, width: int = 10) -> str:
    filled = min(width, max(0, round(percent * width / 100)))
    return "▰" * filled + "▱" * (width - filled)


def _head(stats: BotSessionStatsResponse, test_name: str, session_name: str) -> str:
    """Test tadbiri nomi, imtihon nomi, keyin sana va smena — har biri alohida qatorda."""
    lines = []
    if session_name and session_name.strip().lower() != test_name.strip().lower():
        lines.append(f"🗂 {_esc(session_name)}")
    lines += [f"📝 <b>{_esc(test_name)}</b>", ""]

    day = stats.test_day
    if stats.scope == "total" or day is None:
        lines.append("📅 <b>Barcha kunlar</b>")
    else:
        lines.append(
            f"📅 <b>{day.day}-{_MONTHS[day.month - 1]}, {day.year}-yil</b>"
            f" · {_WEEKDAYS[day.weekday()]}"
        )
    if stats.scope == "smena":
        smena = stats.smena_name or f"{stats.smena_number}-smena"
        lines.append(f"🕘 <b>{_esc(smena)}</b>")
    elif stats.scope == "day":
        lines.append("🕘 <b>Kun yakuni</b> · barcha smenalar")
    else:
        lines.append("🕘 <b>Barcha smenalar</b>")
    return "\n".join(lines)


def _region_block(region: BotRegionStat) -> str:
    percent = _percent(region.entered, region.total)
    rows = [
        f"{_progress_bar(percent)}  <b>{_pct(percent)}</b>",
        f"👥 Jami: <b>{_num(region.total)}</b>",
        f"✅ Keldi: <b>{_num(region.entered)}</b>",
        f"❌ Kelmadi: <b>{_num(region.not_entered)}</b>",
    ]
    if region.cheating:
        rows.append(f"⛔ Chetlatildi: <b>{_num(region.cheating)}</b>")
    # Viloyat nomi katta harfda — ichidagi binolardan ajralib tursin.
    return f"📍 <b>{_esc(region.region_name.upper())}</b>\n<blockquote>" + "\n".join(rows) + "</blockquote>"


def _zone_lines(zone: BotZoneStat, *, last: bool) -> str:
    percent = _percent(zone.entered, zone.total)
    detail = [
        f"✅ {_num(zone.entered)}/{_num(zone.total)} · <b>{_pct(percent)}</b>",
        f"❌ {_num(zone.not_entered)}",
    ]
    if zone.cheating:
        detail.append(f"⛔ {_num(zone.cheating)}")
    return (
        f"{_LAST if last else _BRANCH}{_status_dot(percent)} {_esc(zone.zone_name)}\n"
        f"{_GAP if last else _PIPE}{' · '.join(detail)}"
    )


@dataclass
class _Item:
    """Xabarga joylanadigan birlik: viloyat bloki yoki bitta bino."""

    region: BotRegionStat
    zone: BotZoneStat | None = None
    zones_count: int = 0

    def size(self) -> int:
        if self.zone is None:
            return len(_region_block(self.region)) + 40  # + binolar sarlavhasi
        return len(_zone_lines(self.zone, last=False)) + 2


def _render(items: list[_Item]) -> str:
    """Bir xabar qismi: viloyat bloklari va ularning binolari daraxti.

    Bo'linish viloyat binolari o'rtasiga tushsa, keyingi qism «davomi»
    sarlavhasi bilan boshlanadi; daraxt har qismda o'z `└` si bilan yopiladi.
    """
    chunks: list[str] = []
    i = 0
    while i < len(items):
        item = items[i]
        if item.zone is None:
            chunks.append(_region_block(item.region))
            i += 1
            continue
        run = [item]
        i += 1
        while i < len(items) and items[i].zone is not None and items[i].region is item.region:
            run.append(items[i])
            i += 1
        continued = not chunks or items[i - len(run) - 1].region is not item.region
        if continued:
            header = f"🏢 <b>{_esc(item.region.region_name)}</b> · binolar (davomi)"
        else:
            header = f"🏢 Binolar · {item.zones_count} ta"
        tree = "\n".join(
            _zone_lines(z.zone, last=(n == len(run) - 1)) for n, z in enumerate(run)
        )
        block = f"{header}\n{tree}"
        if continued:
            chunks.append(block)
        else:
            # Binolar viloyat blokiga yopishib turadi — bo'sh qatorsiz.
            chunks[-1] = f"{chunks[-1]}\n{block}"
    return "\n\n".join(chunks)


def _pack(items: list[_Item], limit: int) -> list[list[_Item]]:
    """Birliklarni (viloyat / bino) bo'linmasdan xabarlarga joylash."""
    parts: list[list[_Item]] = [[]]
    size = 0
    for item in items:
        extra = item.size()
        if parts[-1] and size + extra > limit:
            parts.append([])
            size = 0
        parts[-1].append(item)
        size += extra
    return parts


def format_stats_messages(
    stats: BotSessionStatsResponse,
    *,
    session_name: str,
    generated_at: datetime,
    test_name: str = "",
    limit: int = MESSAGE_LIMIT,
) -> list[str]:
    """Statistika → forward qilishga tayyor HTML xabar(lar).

    Talabgori yo'q viloyat va binolar (0 / 0) tashlab ketiladi — Mini App
    ekrani bilan bir xil. Viloyatda faol bino bitta bo'lsa, faqat viloyat
    yakuni ko'rsatiladi (bino satri uni takrorlagan bo'lardi).
    """
    local = generated_at.astimezone(UZ_TZ)
    head = _head(stats, test_name or session_name, session_name if test_name else "")
    footer = f"━━━━━━━━━━━━\n🕒 <i>Yuborildi: {local:%d.%m.%Y} · {local:%H:%M}</i>"

    items: list[_Item] = []
    for region in stats.regions:
        if region.total <= 0:
            continue
        items.append(_Item(region))
        zones = [z for z in region.zones if z.total > 0]
        if len(zones) > 1:
            items.extend(_Item(region, z, len(zones)) for z in zones)

    # Sarlavha har qismda (forward'da alohida ko'rinadi), futer faqat oxirgisida.
    room = max(500, limit - len(head) - len(footer) - 80)
    parts = _pack(items, room)
    total_parts = len(parts)

    messages: list[str] = []
    for index, part in enumerate(parts, start=1):
        counter = f" · {index}/{total_parts}" if total_parts > 1 else ""
        title = f"📊 <b>DAVOMAT HISOBOTI</b>{counter}"
        body = _render(part) if part else "Bu kontekstda talabgorlar yo'q."
        tail = f"\n\n{footer}" if index == total_parts else ""
        messages.append(f"{title}\n\n{head}\n\n{body}{tail}")
    return messages


def build_stats_messages(
    db: Session,
    *,
    session_id: int,
    session_smena_id: int | None,
    test_day: date | None,
    allowed_region_ids: set[int],
    now: datetime | None = None,
) -> tuple[list[str], int]:
    """(xabarlar, jami talabgorlar soni). `BotStatsError` — kontekst topilmadi."""
    row = db.execute(
        select(TestSession.name, Test.name)
        .outerjoin(Test, Test.id == TestSession.test_id)
        .where(TestSession.id == session_id)
    ).first()
    if row is None:
        raise BotStatsError("Test tadbiri topilmadi")
    session_name, test_name = row
    stats = compute_bot_stats(
        db,
        session_id=session_id,
        session_smena_id=session_smena_id,
        test_day=test_day,
        allowed_region_ids=allowed_region_ids,
    )
    total = sum(r.total for r in stats.regions)
    messages = format_stats_messages(
        stats,
        session_name=session_name or "",
        test_name=test_name or "",
        generated_at=now or datetime.now(UZ_TZ),
    )
    return messages, total
